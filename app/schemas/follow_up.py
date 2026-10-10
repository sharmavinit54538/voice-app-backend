import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class FollowUpCreate(BaseModel):
    lead_id: uuid.UUID
    scheduled_at: datetime
    notes: str | None = None

class FollowUpUpdate(BaseModel):
    scheduled_at: datetime | None = None
    status: str | None = None
    notes: str | None = None

class FollowUpOut(FollowUpCreate):
    id: uuid.UUID
    status: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
