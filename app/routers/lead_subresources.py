import uuid
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.call import Call
from app.models.whatsapp import WhatsAppConversation, WhatsAppMessage
from app.models.follow_up import FollowUp
from app.models.site_visit import SiteVisit
from app.schemas.call import CallOut
from app.schemas.whatsapp import MessageOut
from app.schemas.follow_up import FollowUpOut
from app.schemas.site_visit import SiteVisitOut

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

@router.get("/{lead_id}/follow-ups", response_model=List[FollowUpOut])
async def get_lead_follow_ups(
    lead_id: uuid.UUID, db: AsyncSession = Depends(get_db)
):
    res = await db.execute(
        select(FollowUp).where(FollowUp.lead_id == lead_id).order_by(FollowUp.scheduled_at.desc())
    )
    return res.scalars().all()

@router.get("/{lead_id}/site-visits", response_model=List[SiteVisitOut])
async def get_lead_site_visits(
    lead_id: uuid.UUID, db: AsyncSession = Depends(get_db)
):
    res = await db.execute(
        select(SiteVisit).where(SiteVisit.lead_id == lead_id).order_by(SiteVisit.visit_date.desc())
    )
    return res.scalars().all()
