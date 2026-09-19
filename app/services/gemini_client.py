from typing import Optional
from google import genai
from google.genai import types
from app.core.config import GEMINI_API_KEY, GEMINI_MODEL

_client: Optional[genai.Client] = None

def get_gemini_client() -> Optional[genai.Client]:
    global _client
    if _client is None and GEMINI_API_KEY:
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client

async def call_gemini(
    prompt: str,
    system_instruction: Optional[str] = None,
    model: Optional[str] = None
) -> str:
    try:
        client = get_gemini_client()
        if not client:
            return "Gemini API Error: GEMINI_API_KEY is not configured in environment."

        selected_model = model or GEMINI_MODEL or "gemini-2.5-flash"
        config = None
        if system_instruction:
            config = types.GenerateContentConfig(
                system_instruction=system_instruction
            )

        response = await client.aio.models.generate_content(
            model=selected_model,
            contents=prompt,
            config=config
        )
        return response.text.strip() if response.text else ""
    except Exception as exc:
        return f"Gemini API Exception: {str(exc)}"
