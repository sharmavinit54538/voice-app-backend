import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.follow_up import FollowUp
from app.schemas.follow_up import FollowUpCreate, FollowUpUpdate, FollowUpOut

router = APIRouter(prefix="/api/follow-ups", tags=["Follow-ups"])

@router.get("", response_model=List[FollowUpOut])
async def list_follow_ups(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(FollowUp).order_by(FollowUp.scheduled_at.desc()))
    return res.scalars().all()

@router.get("/{follow_up_id}", response_model=FollowUpOut)
async def get_follow_up(follow_up_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    fu = (await db.execute(select(FollowUp).where(FollowUp.id == follow_up_id))).scalar_one_or_none()
    if not fu:
        raise HTTPException(status_code=404, detail="Follow-up not found")
    return fu

@router.post("", response_model=FollowUpOut, status_code=201)
async def create_follow_up(payload: FollowUpCreate, db: AsyncSession = Depends(get_db)):
    fu = FollowUp(**payload.model_dump())
    db.add(fu)
    await db.commit()
    await db.refresh(fu)
    return fu

@router.patch("/{follow_up_id}", response_model=FollowUpOut)
async def update_follow_up(follow_up_id: uuid.UUID, payload: FollowUpUpdate, db: AsyncSession = Depends(get_db)):
    fu = (await db.execute(select(FollowUp).where(FollowUp.id == follow_up_id))).scalar_one_or_none()
    if not fu:
        raise HTTPException(status_code=404, detail="Follow-up not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(fu, k, v)
    await db.commit()
    await db.refresh(fu)
    return fu

@router.delete("/{follow_up_id}")
async def delete_follow_up(follow_up_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    fu = (await db.execute(select(FollowUp).where(FollowUp.id == follow_up_id))).scalar_one_or_none()
    if not fu:
        raise HTTPException(status_code=404, detail="Follow-up not found")
    await db.delete(fu)
    await db.commit()
    return {"success": True, "message": "Follow-up deleted"}
