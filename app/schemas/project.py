import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProjectCreate(BaseModel):
    name: str
    location: str | None = None
    description: str | None = None
    status: str | None = "active"
    price_range: str | None = None

class ProjectUpdate(BaseModel):
    name: str | None = None
    location: str | None = None
    description: str | None = None
    status: str | None = None
    price_range: str | None = None

class ProjectOut(ProjectCreate):
    id: uuid.UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
