import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.call import Call
from app.schemas.call import CallCreate, CallUpdate, CallOut

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

@router.post("", response_model=CallOut, status_code=201)
async def log_call(payload: CallCreate, db: AsyncSession = Depends(get_db)):
    call = Call(**payload.model_dump())
    db.add(call)
    await db.commit()
    await db.refresh(call)
    return call

@router.patch("/{call_id}", response_model=CallOut)
async def update_call(call_id: uuid.UUID, payload: CallUpdate, db: AsyncSession = Depends(get_db)):
    call = (await db.execute(select(Call).where(Call.id == call_id))).scalar_one_or_none()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(call, k, v)
    await db.commit()
    await db.refresh(call)
    return call

@router.delete("/{call_id}")
async def delete_call(call_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    call = (await db.execute(select(Call).where(Call.id == call_id))).scalar_one_or_none()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    await db.delete(call)
    await db.commit()
    return {"success": True, "message": "Call deleted"}
