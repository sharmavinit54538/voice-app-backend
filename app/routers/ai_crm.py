from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import GEMINI_MODEL
from app.core.database import get_db
from app.models.whatsapp import WhatsAppMessage
from app.schemas.ai import AISummarizeConversationRequest
from app.services.gemini_service import extract_lead_from_text, summarize_conversation_history

router = APIRouter(prefix="/api/ai", tags=["AI"])

@router.post("/extract-lead")
async def ai_extract_lead(text: str = Query(..., description="Raw text containing lead contact information")):
    extracted = await extract_lead_from_text(text)
    return {"model": GEMINI_MODEL, "extracted_data": extracted}

@router.post("/summarize-conversation")
async def ai_summarize_conversation(payload: AISummarizeConversationRequest, db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(WhatsAppMessage).where(WhatsAppMessage.conversation_id == payload.conversation_id)
        .order_by(WhatsAppMessage.created_at.asc())
    )
    messages = res.scalars().all()
    if not messages:
        raise HTTPException(status_code=404, detail="No messages found in this conversation")
    history = "\n".join([f"{m.sender.upper()}: {m.content}" for m in messages])
    summary = await summarize_conversation_history(history)
    return {"conversation_id": payload.conversation_id, "summary": summary, "model": GEMINI_MODEL}
