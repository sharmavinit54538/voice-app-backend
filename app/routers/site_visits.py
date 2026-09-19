import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.site_visit import SiteVisit
from app.schemas.site_visit import SiteVisitCreate, SiteVisitUpdate, SiteVisitOut

router = APIRouter(prefix="/api/site-visits", tags=["Site Visits"])

@router.get("", response_model=List[SiteVisitOut])
async def list_site_visits(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(SiteVisit).order_by(SiteVisit.visit_date.desc()))
    return res.scalars().all()

@router.get("/{site_visit_id}", response_model=SiteVisitOut)
async def get_site_visit(site_visit_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    sv = (await db.execute(select(SiteVisit).where(SiteVisit.id == site_visit_id))).scalar_one_or_none()
    if not sv:
        raise HTTPException(status_code=404, detail="Site visit not found")
    return sv

@router.post("", response_model=SiteVisitOut, status_code=201)
async def create_site_visit(payload: SiteVisitCreate, db: AsyncSession = Depends(get_db)):
    sv = SiteVisit(**payload.model_dump())
    db.add(sv)
    await db.commit()
    await db.refresh(sv)
    return sv

@router.patch("/{site_visit_id}", response_model=SiteVisitOut)
async def update_site_visit(site_visit_id: uuid.UUID, payload: SiteVisitUpdate, db: AsyncSession = Depends(get_db)):
    sv = (await db.execute(select(SiteVisit).where(SiteVisit.id == site_visit_id))).scalar_one_or_none()
    if not sv:
        raise HTTPException(status_code=404, detail="Site visit not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(sv, k, v)
    await db.commit()
    await db.refresh(sv)
    return sv

@router.delete("/{site_visit_id}")
async def delete_site_visit(site_visit_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    sv = (await db.execute(select(SiteVisit).where(SiteVisit.id == site_visit_id))).scalar_one_or_none()
    if not sv:
        raise HTTPException(status_code=404, detail="Site visit not found")
    await db.delete(sv)
    await db.commit()
    return {"success": True, "message": "Site visit deleted"}
