import uuid
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.call import Call
from app.models.whatsapp import WhatsAppConversation, WhatsAppMessage
from app.schemas.call import CallOut
from app.schemas.whatsapp import MessageOut

router = APIRouter(prefix="/api/leads", tags=["Leads"])

@router.get("/{lead_id}/calls", response_model=List[CallOut])
async def get_lead_calls(
    lead_id: uuid.UUID, db: AsyncSession = Depends(get_db)
):
    res = await db.execute(
        select(Call).where(Call.lead_id == lead_id).order_by(Call.created_at.desc())
    )
    return res.scalars().all()

@router.get("/{lead_id}/messages", response_model=List[MessageOut])
async def get_lead_messages(
    lead_id: uuid.UUID, db: AsyncSession = Depends(get_db)
):
    res = await db.execute(
        select(WhatsAppMessage)
        .join(
            WhatsAppConversation,
            WhatsAppMessage.conversation_id == WhatsAppConversation.id
        )
        .where(WhatsAppConversation.lead_id == lead_id)
        .order_by(WhatsAppMessage.created_at.asc())
    )
    return res.scalars().all()
