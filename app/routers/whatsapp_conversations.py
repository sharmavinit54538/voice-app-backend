import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import update
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.whatsapp import WhatsAppConversation, WhatsAppMessage
from app.schemas.whatsapp import ConversationOut, MessageOut

router = APIRouter(prefix="/api/whatsapp", tags=["WhatsApp"])

@router.get("/conversations", response_model=List[ConversationOut])
async def get_conversations(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(WhatsAppConversation).order_by(WhatsAppConversation.last_message_at.desc()))
    return res.scalars().all()

@router.get("/conversations/{conversation_id}", response_model=ConversationOut)
async def get_single_conversation(conversation_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    conv = (await db.execute(select(WhatsAppConversation).where(WhatsAppConversation.id == conversation_id))).scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv

@router.get("/conversations/{conversation_id}/messages", response_model=List[MessageOut])
async def get_conversation_messages(conversation_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(WhatsAppMessage).where(WhatsAppMessage.conversation_id == conversation_id).order_by(WhatsAppMessage.created_at.asc()))
    return res.scalars().all()

@router.post("/conversations/{conversation_id}/mark-read")
async def mark_conversation_read(conversation_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    await db.execute(update(WhatsAppConversation).where(WhatsAppConversation.id == conversation_id).values(unread_count=0))
    await db.execute(update(WhatsAppMessage).where(WhatsAppMessage.conversation_id == conversation_id, WhatsAppMessage.sender == "user").values(status="read"))
    await db.commit()
    return {"success": True, "message": "Marked read"}
