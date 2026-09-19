import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.campaign import Campaign, CampaignRecipient
from app.schemas.campaign import CampaignCreate, CampaignOut

router = APIRouter(prefix="/api/campaigns", tags=["Campaigns"])

@router.get("", response_model=List[CampaignOut])
async def list_campaigns(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Campaign).order_by(Campaign.created_at.desc()))
    return res.scalars().all()

@router.get("/{campaign_id}", response_model=CampaignOut)
async def get_campaign(campaign_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    camp = res.scalar_one_or_none()
    if not camp:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return camp

@router.post("", response_model=CampaignOut, status_code=201)
async def create_campaign(payload: CampaignCreate, db: AsyncSession = Depends(get_db)):
    camp = Campaign(
        name=payload.name,
        channel=payload.channel,
        template_name=payload.template_name,
        status="draft",
        total_recipients=len(payload.recipients) if payload.recipients else 0
    )
    db.add(camp)
    await db.flush()
    if payload.recipients:
        for r in payload.recipients:
            db.add(CampaignRecipient(
                campaign_id=camp.id, lead_id=r.lead_id,
                phone_number=r.phone_number, status="queued"
            ))
    await db.commit()
    await db.refresh(camp)
    return camp

@router.delete("/{campaign_id}")
async def delete_campaign(campaign_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    camp = res.scalar_one_or_none()
    if not camp:
        raise HTTPException(status_code=404, detail="Campaign not found")
    await db.delete(camp)
    await db.commit()
    return {"success": True, "message": "Campaign deleted"}
