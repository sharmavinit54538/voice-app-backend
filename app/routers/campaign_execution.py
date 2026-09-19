import uuid
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.campaign import Campaign
from app.services.campaign_service import execute_campaign_task

router = APIRouter(prefix="/api/campaigns", tags=["Campaigns"])

@router.post("/{campaign_id}/start")
async def start_campaign(
    campaign_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    camp = (await db.execute(select(Campaign).where(Campaign.id == campaign_id))).scalar_one_or_none()
    if not camp:
        raise HTTPException(status_code=404, detail="Campaign not found")
    camp.status = "active"
    await db.commit()
    background_tasks.add_task(execute_campaign_task, campaign_id, camp.template_name or "hello_world")
    return {"success": True, "message": "Campaign started in background"}
