import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict

class FollowUpCreate(BaseModel):
    lead_id: uuid.UUID
    scheduled_at: datetime
    notes: Optional[str] = None

class FollowUpUpdate(BaseModel):
    scheduled_at: Optional[datetime] = None
    status: Optional[str] = None
    notes: Optional[str] = None

class FollowUpOut(FollowUpCreate):
    id: uuid.UUID
    status: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
