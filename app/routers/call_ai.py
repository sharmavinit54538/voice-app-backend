import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.call import Call
from app.schemas.call import CallOut
from app.services.gemini_service import analyze_call_transcript, summarize_call_record

router = APIRouter(prefix="/api/calls", tags=["Calls"])

@router.post("/{call_id}/ai-analysis", response_model=CallOut)
async def analyze_call_ai(call_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Call).where(Call.id == call_id))
    call = res.scalar_one_or_none()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    if not call.transcript:
        raise HTTPException(status_code=400, detail="Call transcript is required for AI analysis")

    ai_res = await analyze_call_transcript(call.transcript)
    call.call_summary = ai_res
    call.analysis = {"raw_analysis": ai_res, "analyzed_at": datetime.now(timezone.utc).isoformat()}
    await db.commit()
    await db.refresh(call)
    return call

@router.post("/{call_id}/ai-summary")
async def summarize_call_ai(call_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await summarize_call_record(call_id, db)

