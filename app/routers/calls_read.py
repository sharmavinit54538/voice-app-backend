import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.call import Call
from app.schemas.call import CallOut

router = APIRouter(prefix="/api/calls", tags=["Calls"])

@router.get("", response_model=List[CallOut])
async def list_calls(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Call).order_by(Call.created_at.desc()))
    return res.scalars().all()

@router.get("/{call_id}", response_model=CallOut)
async def get_call(call_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    call = (await db.execute(select(Call).where(Call.id == call_id))).scalar_one_or_none()
    if not call:
        raise HTTPException(status_code=404, detail="Call record not found")
    return call
