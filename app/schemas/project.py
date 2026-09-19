import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

class ProjectCreate(BaseModel):
    name: str
    location: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = "active"
    price_range: Optional[str] = None

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    price_range: Optional[str] = None

class ProjectOut(ProjectCreate):
    id: uuid.UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
