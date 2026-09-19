from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.call import Call
from app.models.campaign import Campaign
from app.models.follow_up import FollowUp
from app.models.site_visit import SiteVisit

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])

@router.get("/calls")
async def get_calls_analytics(db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(
            Call.status,
            func.count(Call.id),
            func.coalesce(func.sum(Call.duration), 0)
        ).group_by(Call.status)
    )
    data = [{"status": row[0], "count": row[1], "total_seconds": int(row[2])} for row in res.all()]
    return {"success": True, "calls_by_status": data}

@router.get("/campaigns")
async def get_campaigns_analytics(db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(
            Campaign.id,
            Campaign.name,
            Campaign.status,
            Campaign.total_recipients,
            Campaign.delivered_count,
            Campaign.failed_count
        )
    )
    data = [
        {"id": r[0], "name": r[1], "status": r[2], "total_recipients": r[3], "delivered_count": r[4], "failed_count": r[5]}
        for r in res.all()
    ]
    return {"success": True, "campaigns": data}

@router.get("/follow-ups")
async def get_follow_ups_analytics(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(FollowUp.status, func.count(FollowUp.id)).group_by(FollowUp.status))
    return {"success": True, "follow_ups_by_status": {row[0]: row[1] for row in res.all()}}

@router.get("/site-visits")
async def get_site_visits_analytics(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(SiteVisit.status, func.count(SiteVisit.id)).group_by(SiteVisit.status))
    return {"success": True, "site_visits_by_status": {row[0]: row[1] for row in res.all()}}
