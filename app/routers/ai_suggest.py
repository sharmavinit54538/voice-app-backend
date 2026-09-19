from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import GEMINI_MODEL
from app.core.database import get_db
from app.models.whatsapp import WhatsAppMessage
from app.schemas.ai import AIReplyRequest
from app.services.gemini_service import suggest_whatsapp_reply

router = APIRouter(prefix="/api/ai", tags=["AI"])

@router.post("/whatsapp/suggest-reply")
async def ai_suggest_reply(payload: AIReplyRequest, db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(WhatsAppMessage)
        .where(WhatsAppMessage.conversation_id == payload.conversation_id)
        .order_by(WhatsAppMessage.created_at.desc())
        .limit(10)
    )
    messages = list(reversed(res.scalars().all()))
    if not messages:
        raise HTTPException(
            status_code=404, detail="No messages found in conversation for context"
        )
    history = "\n".join([f"{m.sender.upper()}: {m.content}" for m in messages])
    suggestion = await suggest_whatsapp_reply(history, payload.instruction)
    return {
        "conversation_id": payload.conversation_id,
        "suggested_reply": suggestion,
        "model": GEMINI_MODEL
    }
