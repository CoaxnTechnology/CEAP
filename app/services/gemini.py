from google import genai as _genai_module
from google.genai import errors as genai_errors
from app.config import GeminiConfig

_genai_client = (
    _genai_module.Client(api_key=GeminiConfig.API_KEY) if GeminiConfig.API_KEY else None
)


class GeminiServiceError(Exception):
    pass


def generate_answer(prompt: str) -> str:
    if not _genai_client:
        return None
    try:
        response = _genai_client.models.generate_content(
            model=GeminiConfig.MODEL, contents=prompt
        )
        return response.text
    except (genai_errors.ServerError, genai_errors.APIError) as exc:
        raise GeminiServiceError(str(exc)) from exc
