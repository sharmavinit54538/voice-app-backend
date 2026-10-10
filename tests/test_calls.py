from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.call import Call


@pytest.mark.asyncio
async def test_initiate_call_sets_started_at_and_normalizes_phone(
    client: AsyncClient, db_session: AsyncSession
):
    response = await client.post(
        "/api/calls/initiate",
        json={
            "phone_number": " 98765-43210 ",
            "direction": "outbound",
            "status": "ongoing",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["phone_number"] == "+919876543210"
    assert data["status"] == "ongoing"
    assert data["started_at"] is not None

    call = (
        await db_session.execute(
            select(Call).where(Call.phone_number == "+919876543210")
        )
    ).scalar_one_or_none()
    assert call is not None
    assert call.started_at is not None
    assert call.duration == 0


@pytest.mark.asyncio
async def test_end_call_computes_duration_on_server_and_ignores_query_param(
    client: AsyncClient, db_session: AsyncSession
):
    # 1. Create a Call that started 45 seconds ago
    started_time = datetime.now(UTC) - timedelta(seconds=45)
    call = Call(
        phone_number="+919876543210",
        direction="outbound",
        status="ongoing",
        duration=0,
        started_at=started_time,
    )
    db_session.add(call)
    await db_session.commit()
    await db_session.refresh(call)

    # 2. Client passes ?duration=9999 (should be IGNORED by server)
    response = await client.post(f"/api/calls/{call.id}/end?duration=9999")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["ended_at"] is not None

    # Server computed duration should be ~45s (allow small clock tolerance: 44-48)
    assert data["duration"] != 9999
    assert 44 <= data["duration"] <= 50

    await db_session.refresh(call)
    assert call.duration != 9999
    assert 44 <= call.duration <= 50
    assert call.ended_at is not None


@pytest.mark.asyncio
async def test_transcribe_endpoint_returns_501_not_implemented(
    client: AsyncClient, db_session: AsyncSession
):
    call = Call(
        phone_number="+919876543210",
        direction="outbound",
        status="completed",
        recording_url="https://audio.example.com/rec123.mp3",
    )
    db_session.add(call)
    await db_session.commit()
    await db_session.refresh(call)

    response = await client.post(f"/api/calls/{call.id}/transcribe")
    assert response.status_code == 501
    data = response.json()
    assert "detail" in data
    assert "not implemented" in data["detail"].lower()
