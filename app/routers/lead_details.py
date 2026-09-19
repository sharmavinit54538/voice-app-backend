import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.lead import Lead
from app.schemas.lead import LeadUpdate, LeadOut

router = APIRouter(prefix="/api/leads", tags=["Leads"])

@router.get("/{lead_id}", response_model=LeadOut)
async def get_lead_by_id(
    lead_id: uuid.UUID, db: AsyncSession = Depends(get_db)
):
    res = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = res.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead

@router.patch("/{lead_id}", response_model=LeadOut)
async def update_lead(
    lead_id: uuid.UUID, payload: LeadUpdate, db: AsyncSession = Depends(get_db)
):
    res = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = res.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(lead, k, v)
    await db.commit()
    await db.refresh(lead)
    return lead

@router.delete("/{lead_id}")
async def delete_lead(lead_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = res.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    await db.delete(lead)
    await db.commit()
    return {"success": True, "message": "Lead deleted"}
