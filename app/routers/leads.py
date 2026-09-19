from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.lead import Lead
from app.schemas.lead import LeadCreate, LeadOut, PaginatedLeads
from app.services.lead_query import build_leads_query

router = APIRouter(prefix="/api/leads", tags=["Leads"])

@router.get("", response_model=PaginatedLeads)
async def get_leads(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    status: Optional[str] = None,
    source: Optional[str] = None,
    assigned_to: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    db: AsyncSession = Depends(get_db)
):
    query = build_leads_query(search, status, source, assigned_to, sort_by, sort_order)
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0
    result = await db.execute(query.offset((page - 1) * page_size).limit(page_size))
    return PaginatedLeads(
        total=total, page=page, page_size=page_size, data=result.scalars().all()
    )

@router.post("", response_model=LeadOut, status_code=201)
async def create_lead(payload: LeadCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Lead).where(Lead.phone == payload.phone))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400, detail="Lead with this phone number already exists"
        )
    lead = Lead(**payload.model_dump())
    db.add(lead)
    await db.commit()
    await db.refresh(lead)
    return lead
