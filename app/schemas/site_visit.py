import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SiteVisitCreate(BaseModel):
    lead_id: uuid.UUID
    project_name: str
    visit_date: datetime
    notes: str | None = None

class SiteVisitUpdate(BaseModel):
    project_name: str | None = None
    visit_date: datetime | None = None
    status: str | None = None
    notes: str | None = None

class SiteVisitReschedule(BaseModel):
    visit_date: datetime
    notes: str | None = None

class SiteVisitOut(SiteVisitCreate):
    id: uuid.UUID
    status: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
