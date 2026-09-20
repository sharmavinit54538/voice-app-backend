import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict

class CallCreate(BaseModel):
    lead_id: Optional[uuid.UUID] = None
    phone_number: str
    direction: str
    status: str
    duration: Optional[int] = 0
    recording_url: Optional[str] = None
    transcript: Optional[str] = None
    call_summary: Optional[str] = None

class CallUpdate(BaseModel):
    status: Optional[str] = None
    duration: Optional[int] = None
    recording_url: Optional[str] = None
    transcript: Optional[str] = None
    call_summary: Optional[str] = None
    analysis: Optional[Dict[str, Any]] = None

class CallOut(CallCreate):
    id: uuid.UUID
    analysis: Optional[Dict[str, Any]] = None
    is_self_test: bool = False
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class SelfTestCallRequest(BaseModel):
    phone_number: str

