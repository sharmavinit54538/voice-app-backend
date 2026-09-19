from typing import Optional
from sqlalchemy import or_, desc, asc
from sqlalchemy.future import select
from app.models.lead import Lead

def build_leads_query(
    search: Optional[str] = None,
    status: Optional[str] = None,
    source: Optional[str] = None,
    assigned_to: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc"
):
    query = select(Lead)
    if search:
        f = f"%{search}%"
        query = query.where(or_(Lead.name.ilike(f), Lead.phone.ilike(f), Lead.email.ilike(f)))
    if status:
        query = query.where(Lead.status == status)
    if source:
        query = query.where(Lead.source == source)
    if assigned_to:
        query = query.where(Lead.assigned_to == assigned_to)
    col = getattr(Lead, sort_by, Lead.created_at)
    return query.order_by(desc(col) if sort_order.lower() == "desc" else asc(col))
