import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict

class NotificationOut(BaseModel):
    id: uuid.UUID
    title: str
    message: str
    event_type: str
    is_read: bool
    data: Optional[Dict[str, Any]]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
