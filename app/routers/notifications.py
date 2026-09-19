import uuid
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy import update
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.notification import Notification
from app.schemas.notification import NotificationOut

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])

@router.get("", response_model=List[NotificationOut])
async def list_notifications(
    unread_only: bool = False, db: AsyncSession = Depends(get_db)
):
    query = select(Notification).order_by(Notification.created_at.desc()).limit(100)
    if unread_only:
        query = query.where(Notification.is_read == False)
    res = await db.execute(query)
    return res.scalars().all()

@router.patch("/{notification_id}/read")
async def mark_notification_read(
    notification_id: uuid.UUID, db: AsyncSession = Depends(get_db)
):
    await db.execute(
        update(Notification).where(Notification.id == notification_id).values(is_read=True)
    )
    await db.commit()
    return {"success": True, "message": "Notification marked read"}

@router.post("/read-all")
async def mark_all_notifications_read(db: AsyncSession = Depends(get_db)):
    await db.execute(update(Notification).values(is_read=True))
    await db.commit()
    return {"success": True, "message": "All notifications marked read"}
