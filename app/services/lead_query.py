
from sqlalchemy import asc, desc, or_
from sqlalchemy.future import select
from sqlalchemy.sql import Select

from app.core.phone import normalize_phone_number
from app.models.lead import Lead


def build_leads_query(
    search: str | None = None,
    status: str | None = None,
    source: str | None = None,
    assigned_to: str | None = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> Select:
    query = select(Lead)
    if search:
        f = f"%{search}%"
        conditions = [
            Lead.name.ilike(f),
            Lead.phone.ilike(f),
            Lead.email.ilike(f),
        ]
        # If search looks like a phone number, also search for its normalized form
        try:
            norm_search = normalize_phone_number(search)
            conditions.append(Lead.phone.ilike(f"%{norm_search}%"))
        except Exception:
            pass
        query = query.where(or_(*conditions))

    if status:
        query = query.where(Lead.status == status)
    if source:
        query = query.where(Lead.source == source)
    if assigned_to:
        query = query.where(Lead.assigned_to == assigned_to)

    col = getattr(Lead, sort_by, Lead.created_at)
    return query.order_by(
        desc(col) if sort_order.lower() == "desc" else asc(col)
    )
