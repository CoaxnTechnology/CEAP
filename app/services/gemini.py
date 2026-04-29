import time
import random

from google import genai as _genai_module
from google.genai import errors as genai_errors
from app.config import GeminiConfig

_genai_client = (
    _genai_module.Client(api_key=GeminiConfig.API_KEY) if GeminiConfig.API_KEY else None
)

_RETRYABLE_STATUS_CODES = {503, 500, 429}
_MAX_RETRIES = 3
_BASE_DELAY = 2.0


class GeminiServiceError(Exception):
    pass


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
                raise GeminiServiceError(str(exc)) from exc

            delay = _BASE_DELAY * (2**attempt) + random.uniform(0, 1)
            time.sleep(delay)

    raise GeminiServiceError(str(last_exc)) from last_exc
