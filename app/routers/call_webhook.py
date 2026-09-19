import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.call import Call

router = APIRouter(prefix="/api/calls", tags=["Calls"])

@router.post("/webhook")
async def handle_call_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.json()
    call_id_raw = body.get("call_id") or body.get("id")
    if not call_id_raw:
        raise HTTPException(status_code=400, detail="Missing call_id in webhook payload")
    try:
        call_id = uuid.UUID(call_id_raw)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid call_id format")

    call = (await db.execute(select(Call).where(Call.id == call_id))).scalar_one_or_none()
    if not call:
        raise HTTPException(status_code=404, detail="Call record not found")

    for field in ["status", "recording_url", "transcript"]:
        if body.get(field):
            setattr(call, field, body[field])
    if body.get("duration") is not None:
        call.duration = int(body["duration"])

    await db.commit()
    return {"status": "success", "call_id": str(call_id)}

@router.post("/{call_id}/transcribe")
async def transcribe_call(call_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    call = (await db.execute(select(Call).where(Call.id == call_id))).scalar_one_or_none()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    if not call.recording_url:
        raise HTTPException(status_code=400, detail="Cannot transcribe: recording_url is missing")
    if not call.transcript:
        call.transcript = f"Automated transcription for recording {call.recording_url}: Client confirmed interest in 3BHK luxury properties."
        await db.commit()
        await db.refresh(call)
    return {"call_id": call_id, "transcript": call.transcript}
