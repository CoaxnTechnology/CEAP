# ponytail: legacy filename "gemini" kept so all callers keep their imports; provider is now Groq.
import json
import random
import time

import groq
from groq import APIConnectionError, APIError, APIStatusError

from app.config import GroqConfig

_client = (
    groq.Groq(api_key=GroqConfig.API_KEY) if GroqConfig.API_KEY else None
)

_RETRYABLE_STATUS_CODES = {503, 500, 429}
_MAX_RETRIES = 3
_BASE_DELAY = 2.0


class GeminiServiceError(Exception):
    pass


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

    Returns `fallback` (a dict with "summary" and "bullets") when no API key
    is set or the LLM call fails or returns an unparseable shape.
    """
    if not _client:
        return fallback

    prompt = (
        "You are CEAP for Schools, an AI assistant for a school principal. "
        "From the live data below, write a short briefing as JSON with exactly two keys:\n"
        "- \"summary\": one sentence (under 180 characters) on the most important item.\n"
        "- \"bullets\": an array of 4-6 objects, each {\"type\": string, \"text\": string}. "
        "type must be one of success, warning, alert, info, ai. Use success for good news, "
        "warning/alert for gaps or risks, ai for AI-suggested actions. Each text under 110 "
        "characters, plain text, no markdown.\n"
        "Return ONLY a JSON object, no other text.\n\n"
        f"LIVE DATA:\n{context}"
    )

    def _clean_bullets(items):
        cleaned = []
        for item in items:
            if not isinstance(item, dict):
                continue
            text = item.get("text") or item.get("message") or item.get("action")
            btype = item.get("type")
            if isinstance(text, str) and text.strip() and btype in _BULLET_TYPES:
                cleaned.append({"type": btype, "text": text.strip()})
        return cleaned

    for attempt in range(_MAX_RETRIES):
        try:
            response = _client.chat.completions.create(
                model=GroqConfig.MODEL,
                messages=[{"role": "user", "content": prompt}],
            )
            text = _strip_code_fence(response.choices[0].message.content or "")
            data = json.loads(text)
            if not isinstance(data, dict):
                return fallback
            summary = data.get("summary")
            bullets = _clean_bullets(data.get("bullets") or [])
            if not (isinstance(summary, str) and summary.strip() and bullets):
                return fallback
            return {"summary": summary.strip(), "bullets": bullets}
        except (APIError, APIConnectionError, json.JSONDecodeError):
            if attempt == _MAX_RETRIES - 1:
                return fallback
            time.sleep(1)

    return fallback


def _is_retryable(exc: Exception) -> bool:
    if isinstance(exc, APIConnectionError):
        return True
    if isinstance(exc, APIStatusError):
        return exc.status_code in _RETRYABLE_STATUS_CODES
    return False


def generate_answer(prompt: str) -> str | None:
    if not _client:
        return None

    last_exc = None
    for attempt in range(_MAX_RETRIES):
        try:
            response = _client.chat.completions.create(
                model=GroqConfig.MODEL,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.choices[0].message.content
        except (APIError, APIConnectionError) as exc:
            last_exc = exc
            if not _is_retryable(exc) or attempt == _MAX_RETRIES - 1:
                raise GeminiServiceError(_redact_key(str(exc))) from exc
            delay = _BASE_DELAY * (2**attempt) + random.uniform(0, 1)
            time.sleep(delay)

    raise GeminiServiceError(_redact_key(str(last_exc))) from last_exc


def generate_answer_stream(prompt: str):
    if not _client:
        return

    for attempt in range(_MAX_RETRIES):
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
            if not _is_retryable(exc) or attempt == _MAX_RETRIES - 1:
                raise GeminiServiceError(_redact_key(str(exc))) from exc
            delay = _BASE_DELAY * (2**attempt) + random.uniform(0, 1)
            time.sleep(delay)


def generate_followup_suggestions(question: str, answer: str) -> list[str]:
    if not _client or not answer:
        return []

    prompt = (
        "Based on the following Q&A, suggest 3 short follow-up questions "
        "the user might ask next. Return ONLY a JSON array of strings.\n\n"
        f"Question: {question}\nAnswer: {answer}\n\n"
        'Example: ["What are the key metrics?", "How does this compare to last quarter?", "What are the next steps?"]\n'
        "Return only the JSON array, no other text."
    )

    for attempt in range(_MAX_RETRIES):
        try:
            response = _client.chat.completions.create(
                model=GroqConfig.MODEL,
                messages=[{"role": "user", "content": prompt}],
            )
            text = _strip_code_fence(response.choices[0].message.content or "")
            if not text:
                return []
            suggestions = json.loads(text)
            if isinstance(suggestions, list) and len(suggestions) <= 6:
                return [str(s).strip() for s in suggestions if str(s).strip()]
            return []
        except (APIError, APIConnectionError, json.JSONDecodeError):
            if attempt == _MAX_RETRIES - 1:
                return []
            delay = _BASE_DELAY * (2**attempt) + random.uniform(0, 1)
            time.sleep(delay)

    return []


def _build_tools(tool_defs: list) -> list:
    tools = []
    for td in tool_defs:
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


def generate_answer_with_tools(
    system_prompt: str,
    user_message: str,
    tool_defs: list,
    history: list | None = None,
) -> dict:
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

    tools = _build_tools(tool_defs)
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
                raise GeminiServiceError(_redact_key(str(exc)))
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

            executed_tools.append({
                "name": fn.name,
                "args": args,
                "result": tool_result,
            })
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
            fn = tc.function
            args = fn.arguments
            if isinstance(args, str):
                try:
                    args = json.loads(args or "{}")
                except json.JSONDecodeError:
                    args = {}
            tool_result = execute_tool(fn.name, dict(args), user_email)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(tool_result),
                }
            )

    return {"text": "", "tool_calls": executed_tools, "error": "Max tool call iterations reached"}
