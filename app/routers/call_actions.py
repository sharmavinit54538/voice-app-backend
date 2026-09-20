
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.call import Call
from app.schemas.call import CallCreate, CallOut

router = APIRouter(prefix="/api/calls", tags=["Calls"])

@router.post("/initiate", response_model=CallOut)
async def initiate_call(payload: CallCreate, db: AsyncSession = Depends(get_db)):
    call = Call(
        lead_id=payload.lead_id, phone_number=payload.phone_number,
        direction="outbound", status="ongoing", duration=0
    )
    db.add(call)
    await db.commit()
    await db.refresh(call)
    return call

@router.post("/{call_id}/end", response_model=CallOut)
async def end_call(
    call_id: uuid.UUID, duration: int = Query(0, ge=0), db: AsyncSession = Depends(get_db)
):
    call = (await db.execute(select(Call).where(Call.id == call_id))).scalar_one_or_none()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    call.status, call.duration = "completed", duration
    await db.commit()
    await db.refresh(call)
    return call

@router.get("/{call_id}/status")
async def get_call_status(call_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Call.status, Call.duration).where(Call.id == call_id))
    call = res.first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    return {"id": call_id, "status": call[0], "duration": call[1]}
