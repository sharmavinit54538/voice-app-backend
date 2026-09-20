from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import GEMINI_MODEL
from app.core.database import get_db
from app.schemas.ai import AIChatRequest, AIGenerateReplyRequest, AISummarizeCallRequest
from app.services.gemini_client import call_gemini
from app.services.gemini_service import summarize_call_record

router = APIRouter(prefix="/api/ai", tags=["AI"])

@router.post("/chat")
async def ai_chat(payload: AIChatRequest):
    reply = await call_gemini(payload.prompt, system_instruction=payload.system_prompt)
    return {"model": GEMINI_MODEL, "response": reply}

@router.post("/generate-reply")
async def ai_generate_reply(payload: AIGenerateReplyRequest):
    prompt = (
        f"Context:\n{payload.context}\n\n"
        f"Instruction: {payload.instruction or 'Generate an appropriate response'}\n\n"
        "Response:"
    )
    reply = await call_gemini(
        prompt, system_instruction="You are a helpful real estate assistant."
    )
    return {"model": GEMINI_MODEL, "reply": reply}

@router.post("/summarize-call")
async def ai_summarize_call(
    payload: AISummarizeCallRequest, db: AsyncSession = Depends(get_db)
):
    return await summarize_call_record(payload.call_id, db)

