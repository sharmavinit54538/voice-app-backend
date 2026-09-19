import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

class LeadCreate(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None
    status: Optional[str] = "new"
    source: Optional[str] = "direct"
    assigned_to: Optional[str] = None
    notes: Optional[str] = None

class LeadUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    status: Optional[str] = None
    source: Optional[str] = None
    assigned_to: Optional[str] = None
    notes: Optional[str] = None

class LeadOut(LeadCreate):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class PaginatedLeads(BaseModel):
    total: int
    page: int
    page_size: int
    data: List[LeadOut]
