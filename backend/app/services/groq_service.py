# ponytail: legacy filename "gemini" kept so all callers keep their imports; provider is now Groq.
import hashlib
import json
import random
import time

import groq
from groq import APIConnectionError, APIError, APIStatusError

from app.config import GroqConfig


class GeminiServiceError(Exception):
    pass


def _get_api_key() -> str:
    """Current Groq key — DB (AppSetting) wins over env, so UI changes take effect without restart."""
    try:
        from app.db import SessionLocal
        from app.models import AppSetting

        db = SessionLocal()
        try:
            row = db.query(AppSetting).filter(AppSetting.key == "groq_api_key").first()
            if row and (row.value or "").strip():
                return row.value.strip()
        finally:
            db.close()
    except Exception:
        pass
    import os

    return (GroqConfig.API_KEY or os.getenv("GROQ_API_KEY") or "").strip()


def _get_model() -> str:
    try:
        from app.db import SessionLocal
        from app.models import AppSetting

        db = SessionLocal()
        try:
            row = db.query(AppSetting).filter(AppSetting.key == "groq_model").first()
            if row and (row.value or "").strip():
                return row.value.strip()
        finally:
            db.close()
    except Exception:
        pass
    import os

    return (GroqConfig.MODEL or os.getenv("GROQ_MODEL") or "llama-3.3-70b-versatile").strip()


_client = None
_client_key = None


def _get_client():
    global _client, _client_key
    key = _get_api_key()
    if not key:
        return None
    if _client is None or _client_key != key:
        _client = groq.Groq(api_key=key, timeout=25.0, max_retries=0)
        _client_key = key
    return _client

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
    client = _get_client()
    if not client:
        return ""
    try:
        response = client.chat.completions.create(
            model=_get_model(),
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
    client = _get_client()
    if not client:
        return
    try:
        stream = client.chat.completions.create(
            model=_get_model(),
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
    client = _get_client()
    if not client or not answer:
        return []
    prompt = (
        "Based on the following Q&A, suggest 3 short follow-up questions "
        "the user might ask next. Return ONLY a JSON array of strings.\n\n"
        f"Question: {question}\nAnswer: {answer}\n\n"
        'Example: ["What are the key metrics?", "How does this compare to last quarter?", "What are the next steps?"]\n'
    )
    try:
        response = client.chat.completions.create(
            model=_get_model(),
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
    client = _get_client()
    if not client:
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

    tools = _build_tools(tool_defs)

    executed_tools = []

    for attempt in range(4):
        try:
            response = client.chat.completions.create(
                model=_get_model(),
                messages=messages,
                tools=tools,
            )
        except (APIError, APIConnectionError) as exc:
            # ponytail: Groq 400s a tool call the moment the model emits a
            # malformed/empty call (e.g. missing file_id). That's a soft failure:
            # retry once WITHOUT tools so the user still gets a clean text answer.
            if getattr(exc, "status_code", None) == 400 and tools:
                try:
                    plain = client.chat.completions.create(
                        model=_get_model(),
                        messages=messages,
                    )
                    return {
                        "text": plain.choices[0].message.content or "",
                        "tool_calls": executed_tools,
                    }
                except (APIError, APIConnectionError):
                    pass
            if attempt == 3:
                raise GeminiServiceError(_redact_key(str(exc))) from exc
            time.sleep(2 * (attempt + 1))
            continue

        msg = response.choices[0].message
        if not getattr(msg, "tool_calls", None):
            # ponytail: Groq sometimes emits llama-style <function=name>{args}</function>
            # markup as plain text instead of structured tool_calls. Parse it into a
            # real call so the answer uses actual data instead of leaking the markup.
            markup_calls = _parse_function_markup(msg.content or "")
            if markup_calls:
                msg.tool_calls = markup_calls
            else:
                return {"text": msg.content or "", "tool_calls": executed_tools}

        from flask import session

        from app.services.tool_executor import execute_tool

        user_email = session.get("user", "")
        assistant_tool_calls = []
        tool_results_by_id = {}
        for tc in msg.tool_calls:
            fn = tc.function
            args = fn.arguments
            if isinstance(args, str):
                try:
                    args = json.loads(args or "{}")
                except json.JSONDecodeError:
                    args = {}
            if not isinstance(args, dict):
                args = {}
            tool_result = execute_tool(fn.name, dict(args), user_email)
            executed_tools.append({"name": fn.name, "args": args, "result": tool_result})
            tool_results_by_id[tc.id] = tool_result
            assistant_tool_calls.append(
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": fn.name, "arguments": fn.arguments},
                }
            )

        messages.append(
            {"role": "assistant", "content": None, "tool_calls": assistant_tool_calls}
        )
        for tc in msg.tool_calls:
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(tool_results_by_id[tc.id]),
                }
            )

    return {
        "text": "",
        "tool_calls": executed_tools,
        "error": "Max tool call iterations reached",
    }


def _parse_function_markup(text: str) -> list:
    """Parse llama-style '<function=name>{json}</function>' tags into tool-call
    objects shaped like Groq's structured tool calls. Returns [] if none found."""
    import re

    import types

    calls = []
    for match in re.finditer(r"<?function=([^>]+)>(.*?)</function>", text, re.DOTALL):
        name = match.group(1).strip().strip("`")
        args_text = match.group(2).strip()
        try:
            args = json.loads(args_text or "{}")
        except json.JSONDecodeError:
            args = {}
        call = types.SimpleNamespace(
            id=f"markup_{len(calls)}",
            type="function",
            function=types.SimpleNamespace(
                name=name, arguments=json.dumps(args)
            ),
        )
        calls.append(call)
    return calls


def _build_tools(tool_defs: list) -> list:
    """Normalise tool definitions into the Groq tool schema."""
    from app.services.tools import TOOL_NAME_MAP

    tools = []
    for td in tool_defs:
        if isinstance(td, str):
            td = TOOL_NAME_MAP.get(td)
            if not td:
                continue
        params = dict(td.get("parameters") or {})
        if not params.get("properties"):
            params["properties"] = {}
        tools.append(
            {
                "type": "function",
                "function": {
                    "name": td["name"],
                    "description": td.get("description", ""),
                    "parameters": params,
                },
            }
        )
    return tools


def _redact_key(text: str) -> str:
    key = _get_api_key()
    if key:
        return text.replace(key, "[REDACTED]")
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
    client = _get_client()
    if not client:
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
            response = client.chat.completions.create(
                model=_get_model(),
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
    client = _get_client()
    if not client:
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
            response = client.chat.completions.create(
                model=_get_model(),
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
