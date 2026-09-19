import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import update
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.follow_up import FollowUp

router = APIRouter(prefix="/api/follow-ups", tags=["Follow-ups"])

@router.post("/{follow_up_id}/complete")
async def complete_follow_up(follow_up_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    fu = (await db.execute(select(FollowUp).where(FollowUp.id == follow_up_id))).scalar_one_or_none()
    if not fu:
        raise HTTPException(status_code=404, detail="Follow-up not found")
    await db.execute(update(FollowUp).where(FollowUp.id == follow_up_id).values(status="completed"))
    await db.commit()
    return {"success": True, "message": "Follow-up completed"}

@router.post("/{follow_up_id}/cancel")
async def cancel_follow_up(follow_up_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    fu = (await db.execute(select(FollowUp).where(FollowUp.id == follow_up_id))).scalar_one_or_none()
    if not fu:
        raise HTTPException(status_code=404, detail="Follow-up not found")
    fu.status = "cancelled"
    await db.commit()
    return {"success": True, "message": "Follow-up cancelled"}
