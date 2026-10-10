from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import GEMINI_MODEL
from app.core.database import get_db
from app.core.exceptions import AIServiceError
from app.schemas.ai import (
    AIChatRequest,
    AIGenerateReplyRequest,
    AISummarizeCallRequest,
)
from app.services.gemini_client import call_gemini
from app.services.gemini_service import summarize_call_record

router = APIRouter(prefix="/api/ai", tags=["AI"])


@router.post("/chat")
async def ai_chat(payload: AIChatRequest) -> Dict[str, Any]:
    try:
        reply = await call_gemini(
            payload.prompt, system_instruction=payload.system_prompt
        )
        return {"model": GEMINI_MODEL, "response": reply}
    except AIServiceError as exc:
        raise HTTPException(
            status_code=exc.status_code, detail=exc.message
        ) from exc


@router.post("/generate-reply")
async def ai_generate_reply(payload: AIGenerateReplyRequest) -> Dict[str, Any]:
    prompt = (
        f"Context:\n{payload.context}\n\n"
        f"Instruction: {payload.instruction or 'Generate an appropriate response'}\n\n"
        "Response:"
    )
    try:
        reply = await call_gemini(
            prompt,
            system_instruction="You are a helpful real estate assistant.",
        )
        return {"model": GEMINI_MODEL, "reply": reply}
    except AIServiceError as exc:
        raise HTTPException(
            status_code=exc.status_code, detail=exc.message
        ) from exc


@router.post("/summarize-call")
async def ai_summarize_call(
    payload: AISummarizeCallRequest, db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    try:
        return await summarize_call_record(payload.call_id, db)
    except AIServiceError as exc:
        raise HTTPException(
            status_code=exc.status_code, detail=exc.message
        ) from exc
