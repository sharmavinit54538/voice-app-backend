from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.lead import Lead
from app.models.call import Call
from app.models.whatsapp import WhatsAppConversation, WhatsAppMessage
from app.models.site_visit import SiteVisit
from app.models.campaign import Campaign

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])

@router.get("/dashboard")
async def get_dashboard_analytics(db: AsyncSession = Depends(get_db)):
    lead_count = await db.scalar(select(func.count(Lead.id)))
    call_stats = await db.execute(
        select(func.count(Call.id), func.coalesce(func.sum(Call.duration), 0))
        .where(Call.is_self_test == False)
    )
    total_calls, total_call_seconds = call_stats.one()
    msg_count = await db.scalar(
        select(func.count(WhatsAppMessage.id))
        .join(WhatsAppConversation, WhatsAppMessage.conversation_id == WhatsAppConversation.id)
        .where(WhatsAppConversation.is_self_test == False)
    )
    visit_count = await db.scalar(select(func.count(SiteVisit.id)))
    active_campaigns = await db.scalar(
        select(func.count(Campaign.id)).where(Campaign.status == "active")
    )
    return {
        "success": True,
        "data": {
            "total_leads": lead_count or 0,
            "total_calls": total_calls or 0,
            "total_call_seconds": int(total_call_seconds or 0),
            "total_whatsapp_messages": msg_count or 0,
            "total_site_visits": visit_count or 0,
            "active_campaigns": active_campaigns or 0
        }
    }

@router.get("/leads")
async def get_lead_analytics(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Lead.status, func.count(Lead.id)).group_by(Lead.status))
    return {"success": True, "by_status": {row[0]: row[1] for row in res.all()}}

@router.get("/whatsapp")
async def get_whatsapp_analytics(db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(WhatsAppMessage.status, func.count(WhatsAppMessage.id))
        .join(WhatsAppConversation, WhatsAppMessage.conversation_id == WhatsAppConversation.id)
        .where(WhatsAppConversation.is_self_test == False)
        .group_by(WhatsAppMessage.status)
    )
    return {"success": True, "by_status": {row[0]: row[1] for row in res.all()}}
