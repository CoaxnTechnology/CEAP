import json
import time
import random

from google import genai as _genai_module
from google.genai import errors as genai_errors, types as genai_types
from app.config import GeminiConfig

_genai_client = (
    _genai_module.Client(api_key=GeminiConfig.API_KEY) if GeminiConfig.API_KEY else None
)

_RETRYABLE_STATUS_CODES = {503, 500, 429}
_MAX_RETRIES = 3
_BASE_DELAY = 2.0


class GeminiServiceError(Exception):
    pass


def _redact_key(text: str) -> str:
    if GeminiConfig.API_KEY:
        return text.replace(GeminiConfig.API_KEY, "[REDACTED]")
    return text


def generate_answer(prompt: str) -> str | None:
    if not _genai_client:
        return None

    last_exc = None
    for attempt in range(_MAX_RETRIES):
        try:
            response = _genai_client.models.generate_content(
                model=GeminiConfig.MODEL, contents=prompt
            )
            return response.text
        except (genai_errors.ServerError, genai_errors.APIError) as exc:
            last_exc = exc
            status_code = getattr(exc, "code", None)
            if (
                status_code not in _RETRYABLE_STATUS_CODES
                or attempt == _MAX_RETRIES - 1
            ):
                raise GeminiServiceError(_redact_key(str(exc))) from exc

            delay = _BASE_DELAY * (2**attempt) + random.uniform(0, 1)
            time.sleep(delay)

    raise GeminiServiceError(_redact_key(str(last_exc))) from last_exc


def generate_answer_stream(prompt: str):
    if not _genai_client:
        return

    for attempt in range(_MAX_RETRIES):
        try:
            stream = _genai_client.models.generate_content_stream(
                model=GeminiConfig.MODEL, contents=prompt
            )
            for chunk in stream:
                if chunk.text:
                    yield chunk.text
            return
        except (genai_errors.ServerError, genai_errors.APIError) as exc:
            status_code = getattr(exc, "code", None)
            if status_code not in _RETRYABLE_STATUS_CODES or attempt == _MAX_RETRIES - 1:
                raise GeminiServiceError(_redact_key(str(exc))) from exc
            delay = _BASE_DELAY * (2**attempt) + random.uniform(0, 1)
            time.sleep(delay)


def generate_followup_suggestions(question: str, answer: str) -> list[str]:
    if not _genai_client or not answer:
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
            response = _genai_client.models.generate_content(
                model=GeminiConfig.MODEL, contents=prompt
            )
            if not response.text:
                return []
            text = response.text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[-1]
                text = text.rsplit("```", 1)[0]
            suggestions = json.loads(text)
            if isinstance(suggestions, list) and len(suggestions) <= 6:
                return [str(s).strip() for s in suggestions if str(s).strip()]
            return []
        except (genai_errors.ServerError, genai_errors.APIError, json.JSONDecodeError):
            if attempt == _MAX_RETRIES - 1:
                return []
            delay = _BASE_DELAY * (2**attempt) + random.uniform(0, 1)
            time.sleep(delay)

    return []


def _convert_to_schema(properties: dict) -> dict:
    type_map = {
        "string": "STRING",
        "integer": "INTEGER",
        "number": "NUMBER",
        "boolean": "BOOLEAN",
        "array": "ARRAY",
        "object": "OBJECT",
    }

    def _convert_value(v: dict):
        schema_type = type_map.get(v.get("type", "string"), "STRING")
        kwargs = {"type": schema_type, "description": v.get("description", "")}

        if "enum" in v:
            kwargs["enum"] = v["enum"]
        if schema_type == "ARRAY" and "items" in v:
            kwargs["items"] = _convert_value(v["items"])
        if schema_type == "OBJECT" and "properties" in v:
            kwargs["properties"] = {
                k: _convert_value(pv) for k, pv in v["properties"].items()
            }
            if "required" in v:
                kwargs["required"] = v["required"]

        return genai_types.Schema(**kwargs)

    return _convert_value(properties)


def _build_function_declarations(tool_defs: list) -> list:
    declarations = []
    for td in tool_defs:
        if not td.get("parameters", {}).get("properties"):
            td["parameters"]["properties"] = {}
        schema = _convert_to_schema(td["parameters"])
        declarations.append(
            genai_types.FunctionDeclaration(
                name=td["name"],
                description=td.get("description", ""),
                parameters=schema,
            )
        )
    return declarations


def generate_answer_with_tools(
    system_prompt: str,
    user_message: str,
    tool_defs: list,
    history: list = None,
) -> dict:
    if not _genai_client:
        return {"text": "", "tool_calls": [], "error": "No Gemini key set"}

    function_declarations = _build_function_declarations(tool_defs)
    tool = genai_types.Tool(function_declarations=function_declarations)

    contents = []
    if history:
        for msg in history:
            role = "user" if msg.get("role") == "user" else "model"
            contents.append(
                genai_types.Content(
                    role=role,
                    parts=[genai_types.Part(text=msg.get("content", ""))],
                )
            )

    contents.append(
        genai_types.Content(
            role="user",
            parts=[genai_types.Part(text=user_message)],
        )
    )

    config = genai_types.GenerateContentConfig(
        system_instruction=system_prompt if system_prompt else None,
        tools=[tool],
    )

    executed_tools = []

    for attempt in range(3):
        try:
            response = _genai_client.models.generate_content(
                model=GeminiConfig.MODEL,
                contents=contents,
                config=config,
            )
        except (genai_errors.ServerError, genai_errors.APIError) as exc:
            if attempt == 2:
                raise GeminiServiceError(_redact_key(str(exc)))
            time.sleep(1)
            continue

        if not response.candidates:
            return {"text": "", "tool_calls": executed_tools, "error": "No response"}

        candidate = response.candidates[0]
        if not candidate.content or not candidate.content.parts:
            return {"text": "", "tool_calls": executed_tools, "error": "Empty response"}

        first_part = candidate.content.parts[0]

        if hasattr(first_part, "function_call") and first_part.function_call:
            fc = first_part.function_call
            from app.services.tool_executor import execute_tool
            from flask import session

            user_email = session.get("user", "")
            tool_result = execute_tool(fc.name, dict(fc.args), user_email)

            executed_tools.append({
                "name": fc.name,
                "args": dict(fc.args),
                "result": tool_result,
            })

            func_response_part = genai_types.Part(
                function_response=genai_types.FunctionResponse(
                    name=fc.name,
                    response=tool_result,
                )
            )

            contents.append(
                genai_types.Content(
                    role="model",
                    parts=[genai_types.Part(function_call=fc)],
                )
            )
            contents.append(
                genai_types.Content(
                    role="user",
                    parts=[func_response_part],
                )
            )
        else:
            text = first_part.text if hasattr(first_part, "text") else ""
            return {"text": text, "tool_calls": executed_tools}

    return {"text": "", "tool_calls": executed_tools, "error": "Max tool call iterations reached"}
