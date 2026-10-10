from unittest.mock import patch
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.exceptions import AIServiceError
from app.models.call import Call
from app.services.gemini_client import call_gemini


@pytest.mark.asyncio
async def test_call_gemini_unconfigured_api_key():
    with patch("app.services.gemini_client.GEMINI_API_KEY", ""):
        with pytest.raises(AIServiceError) as exc_info:
            await call_gemini("Test prompt")
        assert exc_info.value.status_code == 503
        assert "not configured" in exc_info.value.message


@pytest.mark.asyncio
async def test_call_gemini_retries_and_raises_error():
    mock_client = patch("app.services.gemini_client.get_gemini_client")
    with (
        patch("app.services.gemini_client.GEMINI_API_KEY", "fake-key"),
        mock_client as mock_get_client,
    ):
        mock_instance = mock_get_client.return_value
        mock_instance.aio.models.generate_content.side_effect = RuntimeError(
            "Service Unavailable"
        )

        with pytest.raises(AIServiceError) as exc_info:
            await call_gemini("Test prompt", max_retries=2)
        assert exc_info.value.status_code == 502
        assert "Gemini API call failed after 2 attempts" in exc_info.value.message


@pytest.mark.asyncio
async def test_ai_chat_endpoint_returns_502_on_gemini_error(
    client: AsyncClient,
):
    with patch(
        "app.routers.ai.call_gemini",
        side_effect=AIServiceError("Gemini service is down", status_code=502),
    ):
        response = await client.post(
            "/api/ai/chat",
            json={"prompt": "Hello", "system_prompt": "You are helpful"},
        )
        assert response.status_code == 502
        data = response.json()
        assert "detail" in data
        assert "Gemini service is down" in data["detail"]


@pytest.mark.asyncio
async def test_call_ai_analysis_does_not_persist_error_to_db(
    client: AsyncClient, db_session: AsyncSession
):
    # 1. Create a Call with a transcript
    call = Call(
        phone_number="+919876543210",
        direction="outbound",
        status="ongoing",
        duration=30,
        transcript="Customer wants 3BHK in Gurgaon",
    )
    db_session.add(call)
    await db_session.commit()
    await db_session.refresh(call)

    # 2. Mock Gemini to fail with AIServiceError
    with patch(
        "app.routers.call_ai.analyze_call_transcript",
        side_effect=AIServiceError("Gemini quota exceeded", status_code=502),
    ):
        response = await client.post(f"/api/calls/{call.id}/ai-analysis")
        assert response.status_code == 502
        data = response.json()
        assert "Gemini quota exceeded" in data["detail"]

    # 3. Verify in DB that call_summary and analysis were NOT set to any error string
    await db_session.refresh(call)
    assert call.call_summary is None
    assert call.analysis is None


@pytest.mark.asyncio
async def test_ai_summarize_call_does_not_persist_error_to_db(
    client: AsyncClient, db_session: AsyncSession
):
    # 1. Create a Call with transcript
    call = Call(
        phone_number="+919876543210",
        direction="outbound",
        status="completed",
        duration=45,
        transcript="Discussion about 2BHK flat pricing",
    )
    db_session.add(call)
    await db_session.commit()
    await db_session.refresh(call)

    # 2. Mock Gemini failure
    with patch(
        "app.services.gemini_service.call_gemini",
        side_effect=AIServiceError(
            "Model overloaded", status_code=502
        ),
    ):
        response = await client.post(
            "/api/ai/summarize-call", json={"call_id": str(call.id)}
        )
        assert response.status_code == 502

    # 3. Ensure call_summary is NOT populated with error text
    await db_session.refresh(call)
    assert call.call_summary is None
