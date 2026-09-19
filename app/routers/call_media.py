import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.call import Call

router = APIRouter(prefix="/api/calls", tags=["Calls"])

@router.get("/{call_id}/recording")
async def get_call_recording(call_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    call = (await db.execute(select(Call).where(Call.id == call_id))).scalar_one_or_none()
    if not call or not call.recording_url:
        raise HTTPException(status_code=404, detail="Recording URL not found for this call")
    return {"recording_url": call.recording_url}

@router.get("/{call_id}/transcript")
async def get_call_transcript(call_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    call = (await db.execute(select(Call).where(Call.id == call_id))).scalar_one_or_none()
    if not call or not call.transcript:
        raise HTTPException(status_code=404, detail="Transcript not found for this call")
    return {"transcript": call.transcript}
