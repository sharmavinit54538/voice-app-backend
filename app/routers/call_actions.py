import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import require_user
from app.core.phone import normalize_phone_number
from app.models.call import Call
from app.models.user import User
from app.schemas.call import CallCreate, CallOut, SelfTestCallRequest

router = APIRouter(prefix="/api/calls", tags=["Calls"])


@router.post("/initiate", response_model=CallOut)
async def initiate_call(
    payload: CallCreate, db: AsyncSession = Depends(get_db)
) -> Call:
    now = datetime.now(timezone.utc)
    normalized_phone = normalize_phone_number(payload.phone_number)
    call = Call(
        lead_id=payload.lead_id,
        phone_number=normalized_phone,
        direction="outbound",
        status="ongoing",
        duration=0,
        started_at=now,
    )
    db.add(call)
    await db.commit()
    await db.refresh(call)
    return call


@router.post("/self-test", response_model=CallOut)
async def self_test_call(
    payload: SelfTestCallRequest,
    current_user: User = Depends(require_user),  # noqa: ARG001
    db: AsyncSession = Depends(get_db),
) -> Call:
    now = datetime.now(timezone.utc)
    normalized_phone = normalize_phone_number(payload.phone_number)
    call = Call(
        lead_id=None,
        phone_number=normalized_phone,
        direction="outbound",
        status="ongoing",
        duration=0,
        is_self_test=True,
        started_at=now,
    )
    db.add(call)
    await db.commit()
    await db.refresh(call)
    return call


@router.post("/{call_id}/end", response_model=CallOut)
async def end_call(
    call_id: uuid.UUID,
    duration: Optional[int] = Query(
        None,
        ge=0,
        description="Ignored by server; duration is computed from timestamps",
    ),  # noqa: ARG001
    db: AsyncSession = Depends(get_db),
) -> Call:
    call = (
        await db.execute(select(Call).where(Call.id == call_id))
    ).scalar_one_or_none()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    now = datetime.now(timezone.utc)
    call.ended_at = now
    call.status = "completed"

    start_reference = call.started_at or call.created_at or now
    # Ensure start_reference has timezone
    if start_reference.tzinfo is None:
        start_reference = start_reference.replace(tzinfo=timezone.utc)

    computed_duration = max(0, int((now - start_reference).total_seconds()))
    call.duration = computed_duration

    await db.commit()
    await db.refresh(call)
    return call


@router.get("/{call_id}/status")
async def get_call_status(
    call_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    res = await db.execute(
        select(Call.status, Call.duration).where(Call.id == call_id)
    )
    call = res.first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    return {"id": call_id, "status": call[0], "duration": call[1]}
