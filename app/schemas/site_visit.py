import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

class SiteVisitCreate(BaseModel):
    lead_id: uuid.UUID
    project_name: str
    visit_date: datetime
    notes: Optional[str] = None

class SiteVisitUpdate(BaseModel):
    project_name: Optional[str] = None
    visit_date: Optional[datetime] = None
    status: Optional[str] = None
    notes: Optional[str] = None

class SiteVisitReschedule(BaseModel):
    visit_date: datetime
    notes: Optional[str] = None

class SiteVisitOut(SiteVisitCreate):
    id: uuid.UUID
    status: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
