import asyncio
import logging

from google import genai
from google.genai import types

from app.core.config import GEMINI_API_KEY, GEMINI_MODEL
from app.core.exceptions import AIServiceError

logger = logging.getLogger(__name__)

_client: genai.Client | None = None


def get_gemini_client() -> genai.Client | None:
    global _client
    if _client is None and GEMINI_API_KEY:
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


async def call_gemini(
    prompt: str,
    system_instruction: str | None = None,
    model: str | None = None,
    max_retries: int = 3,
    timeout_seconds: float = 30.0,
) -> str:
    """
    Executes a Gemini API request with automatic timeout, exponential backoff retries,
    and raises AIServiceError instead of returning raw error strings.
    """
    if not GEMINI_API_KEY:
        raise AIServiceError(
            "Gemini API key is not configured in the environment.",
            status_code=503,
        )

    client = get_gemini_client()
    if not client:
        raise AIServiceError(
            "Failed to initialize Gemini client.",
            status_code=503,
        )

    selected_model = model or GEMINI_MODEL or "gemini-2.5-flash"
    config = None
    if system_instruction:
        config = types.GenerateContentConfig(
            system_instruction=system_instruction
        )

    last_error: Exception | None = None

    for attempt in range(max_retries):
        try:
            # Enforce request timeout per attempt
            response = await asyncio.wait_for(
                client.aio.models.generate_content(
                    model=selected_model, contents=prompt, config=config
                ),
                timeout=timeout_seconds,
            )
            result_text = response.text.strip() if response.text else ""
            return result_text
        except TimeoutError as exc:
            last_error = exc
            logger.warning(
                "Gemini request timed out on attempt %d/%d",
                attempt + 1,
                max_retries,
            )
        except Exception as exc:
            last_error = exc
            logger.warning(
                "Gemini API error on attempt %d/%d: %s",
                attempt + 1,
                max_retries,
                str(exc),
            )

        if attempt < max_retries - 1:
            backoff_delay = 0.5 * (2**attempt)  # 0.5s, 1.0s, 2.0s
            await asyncio.sleep(backoff_delay)

    error_msg = f"Gemini API call failed after {max_retries} attempts: {last_error!s}"
    logger.error(error_msg)
    raise AIServiceError(error_msg, status_code=502)
