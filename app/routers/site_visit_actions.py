import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import update
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.site_visit import SiteVisit
from app.schemas.site_visit import SiteVisitReschedule, SiteVisitOut

router = APIRouter(prefix="/api/site-visits", tags=["Site Visits"])

@router.post("/{site_visit_id}/confirm")
async def confirm_site_visit(site_visit_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    await db.execute(update(SiteVisit).where(SiteVisit.id == site_visit_id).values(status="confirmed"))
    await db.commit()
    return {"success": True, "message": "Site visit confirmed"}

@router.post("/{site_visit_id}/complete")
async def complete_site_visit(site_visit_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    await db.execute(update(SiteVisit).where(SiteVisit.id == site_visit_id).values(status="completed"))
    await db.commit()
    return {"success": True, "message": "Site visit marked completed"}

@router.post("/{site_visit_id}/reschedule", response_model=SiteVisitOut)
async def reschedule_site_visit(
    site_visit_id: uuid.UUID, payload: SiteVisitReschedule, db: AsyncSession = Depends(get_db)
):
    sv = (await db.execute(select(SiteVisit).where(SiteVisit.id == site_visit_id))).scalar_one_or_none()
    if not sv:
        raise HTTPException(status_code=404, detail="Site visit not found")
    sv.visit_date, sv.status = payload.visit_date, "rescheduled"
    if payload.notes:
        sv.notes = payload.notes
    await db.commit()
    await db.refresh(sv)
    return sv

@router.post("/{site_visit_id}/cancel")
async def cancel_site_visit(site_visit_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    sv = (await db.execute(select(SiteVisit).where(SiteVisit.id == site_visit_id))).scalar_one_or_none()
    if not sv:
        raise HTTPException(status_code=404, detail="Site visit not found")
    sv.status = "cancelled"
    await db.commit()
    return {"success": True, "message": "Site visit cancelled"}
