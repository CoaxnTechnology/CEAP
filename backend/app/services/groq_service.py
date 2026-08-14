# ponytail: legacy filename "gemini" kept so all callers keep their imports; provider is now Groq.
import hashlib
import json
import random
import time

import groq
from groq import APIConnectionError, APIError, APIStatusError

from app.config import GroqConfig

_client = (
    groq.Groq(
        api_key=GroqConfig.API_KEY,
        timeout=25.0,
        max_retries=0,
    ) if GroqConfig.API_KEY else None
)

_RETRYABLE_STATUS_CODES = {503, 500, 429}
_MAX_RETRIES = 3
_BASE_DELAY = 2.0

_cache = {}


def _cache_key(context: str) -> str:
    return hashlib.md5(context.encode()).hexdigest()


def _cached_generate_recommendations(
    context: str,
    fallback: list | None = None,
    max_items: int = 4,
) -> list:
    """Generate recommendations with fire‑and‑cache: same context → cached result."""
    key = _cache_key(context)
    if key in _cache:
        return _cache[key]  # ← serve cached
    result = generate_recommendations(context, fallback, max_items)
    _cache[key] = result  # ← store for next hit
    return result


def _cached_generate_briefing(context: str, fallback: dict) -> dict:
    """Generate briefing with fire‑and‑cache: same context → cached result."""
    key = _cache_key(context)
    if key in _cache:
        return _cache[key]  # ← serve cached
    result = generate_briefing(context, fallback)
    _cache[key] = result  # ← store for next hit
    return result


def generate_answer(prompt: str) -> str:
    """Generate a response from the Groq LLM for a free-form prompt.

    Returns the cleaned text, or empty string if no API key or on error.
    """
    if not _client:
        return ""
    try:
        response = _client.chat.completions.create(
            model=GroqConfig.MODEL,
            messages=[{"role": "user", "content": prompt}],
        )
        text = _strip_code_fence(response.choices[0].message.content or "")
        return text
    except Exception:
        return ""


def generate_answer_stream(prompt: str):
    """Stream the LLM response token by token.

    Yields content deltas. Returns None if no API key.
    """
    if not _client:
        return
    try:
        stream = _client.chat.completions.create(
            model=GroqConfig.MODEL,
            messages=[{"role": "user", "content": prompt}],
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                yield delta
        return
    except (APIError, APIConnectionError) as exc:
        raise GeminiServiceError(_redact_key(str(exc))) from exc


def generate_followup_suggestions(question: str, answer: str) -> list[str]:
    """Suggest 3 short follow-up questions based on a Q&A pair.

    Returns a JSON array of strings, or an empty list if no API key.
    """
    if not _client or not answer:
        return []
    prompt = (
        "Based on the following Q&A, suggest 3 short follow-up questions "
        "the user might ask next. Return ONLY a JSON array of strings.\n\n"
        f"Question: {question}\nAnswer: {answer}\n\n"
        'Example: ["What are the key metrics?", "How does this compare to last quarter?", "What are the next steps?"]\n'
    )
    try:
        response = _client.chat.completions.create(
            model=GroqConfig.MODEL,
            messages=[{"role": "user", "content": prompt}],
        )
        text = _strip_code_fence(response.choices[0].message.content or "")
        data = json.loads(text)
        if isinstance(data, list):
            return data
        return []
    except Exception:
        return []


def generate_answer_with_tools(
    system_prompt: str,
    user_message: str,
    tool_defs: list,
    history: list | None = None,
) -> dict:
    """Generate an answer with optional tool calls.

    Returns a dict with keys 'text' (string) and 'tool_calls' (list)
    and optionally 'error'.
    """
    if not _client:
        return {"text": "", "tool_calls": [], "error": "No Groq key set"}

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    if history:
        for msg in history:
            role = "user" if msg.get("role") == "user" else "assistant"
            content = msg.get("content", "")
            if content:
                messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": user_message})

    tools = _get_tools(tool_defs)

    executed_tools = []

    for attempt in range(3):
        try:
            response = _client.chat.completions.create(
                model=GroqConfig.MODEL,
                messages=messages,
                tools=tools,
            )
        except (APIError, APIConnectionError) as exc:
            if attempt == 2:
                raise GeminiServiceError(_redact_key(str(exc))) from exc
            time.sleep(1)
            continue

        msg = response.choices[0].message
        if not getattr(msg, "tool_calls", None):
            return {"text": msg.content or "", "tool_calls": executed_tools}

        from flask import session

        from app.services.tool_executor import execute_tool

        user_email = session.get("user", "")
        assistant_tool_calls = []
        for tc in msg.tool_calls:
            fn = tc.function
            args = fn.arguments
            if isinstance(args, str):
                try:
                    args = json.loads(args or "{}")
                except json.JSONDecodeError:
                    args = {}
            tool_result = execute_tool(fn.name, dict(args), user_email)
            executed_tools.append({"name": fn.name, "args": args, "result": tool_result})

        if not getattr(msg, "tool_calls", None):
            return {"text": msg.content or "", "tool_calls": executed_tools}

        # re-run with the executed tool results appended
        messages.append(
            {"role": "tool", "content": json.dumps({"tool_results": executed_tools})}
        )

    # final response after tool loop
    msg = response.choices[0].message
    return {"text": msg.content or "", "tool_calls": executed_tools}


def _get_tools(tool_defs: list) -> list:
    """Return the full tool list, lazily initialising from ALL_TOOLS once.

    Uses a module-level flag to initialise only on first call.
    """
    global _tool_list_loaded  # 👆 declare we're using the module-level variable
    if not _tool_list_loaded:
        from app.services.tools import ALL_TOOLS, TOOL_NAME_MAP
        _tool_list_loaded = True
        global _ALL_TOOLS_CACHE  # 👆 declare we're using this too
        _ALL_TOOLS_CACHE = ALL_TOOLS
    # normalise: if each item is a name string, look it up; otherwise return as-is
    normalised = []
    for t in tool_defs:
        if isinstance(t, str):
            normalised.append(TOOL_NAME_MAP.get(t, t))
        else:
            normalised.append(t)
    return normalised


_ALL_TOOLS_CACHE = None


def _redact_key(text: str) -> str:
    if GroqConfig.API_KEY:
        return text.replace(GroqConfig.API_KEY, "[REDACTED]")
    return text


def _strip_code_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1]
        text = text.rsplit("```", 1)[0]
    return text.strip()


def generate_recommendations(
    context: str, fallback: list | None = None, max_items: int = 4
) -> list:
    """Generate concise contextual recommendation bullets from live data.

    Returns `fallback` when no API key is set or the LLM call fails.
    """
    if not _client:
        return fallback or []

    prompt = (
        "You are CEAP for Schools, an AI assistant for a school principal. "
        "From the live data below, write a JSON array of 3-5 concise, specific, "
        "actionable recommendation strings (each under 100 characters, plain text, no markdown, "
        "no objects). Return ONLY a JSON array of strings, no other text.\n\n"
        f"LIVE DATA:\n{context}"
    )

    def _as_text(item):
        if isinstance(item, str):
            return item.strip()
        if isinstance(item, dict):
            for key in ("action", "recommendation", "text", "message", "title"):
                if key in item and isinstance(item[key], str):
                    return item[key].strip()
            return " ".join(str(v) for v in item.values()).strip()
        return str(item).strip()

    for attempt in range(_MAX_RETRIES):
        try:
            response = _client.chat.completions.create(
                model=GroqConfig.MODEL,
                messages=[{"role": "user", "content": prompt}],
            )
            text = _strip_code_fence(response.choices[0].message.content or "")
            items = json.loads(text)
            if isinstance(items, list) and items:
                cleaned = [t for t in (_as_text(i) for i in items) if t]
                if cleaned:
                    return cleaned[:max_items]
            return fallback or []
        except (APIError, APIConnectionError, json.JSONDecodeError):
            if attempt == _MAX_RETRIES - 1:
                return fallback or []
            time.sleep(1)

    return fallback or []


_BULLET_TYPES = ("success", "warning", "alert", "ai", "info")


def generate_briefing(context: str, fallback: dict) -> dict:
    """Generate a one-line summary plus typed briefing bullets from live data.

    Returns `fallback` when no API key is set or the LLM call fails.
    """
    if not _client:
        return fallback

    prompt = (
        "You are CEAP for Schools, an AI assistant for a school principal. "
        "From the live data below, write a one-line summary and a list of typed "
        "bullets (success/warning/alert/info). Return a JSON dict with keys "
        "'summary' (string) and 'bullets' (list of dicts with 'type' and 'text').\n\n"
        f"LIVE DATA:\n{context}"
    )

    def _as_text(item):
        if isinstance(item, str):
            return item.strip()
        if isinstance(item, dict):
            for key in ("action", "recommendation", "text", "message", "title"):
                if key in item and isinstance(item[key], str):
                    return item[key].strip()
            return " ".join(str(v) for v in item.values()).strip()
        return str(item).strip()

    for attempt in range(_MAX_RETRIES):
        try:
            response = _client.chat.completions.create(
                model=GroqConfig.MODEL,
                messages=[{"role": "user", "content": prompt}],
            )
            text = _strip_code_fence(response.choices[0].message.content or "")
            data = json.loads(text)
            if isinstance(data, dict) and "summary" in data and "bullets" in data:
                return data
            return fallback
        except (APIError, APIConnectionError, json.JSONDecodeError):
            if attempt == _MAX_RETRIES - 1:
                return fallback
            time.sleep(1)

    return fallback