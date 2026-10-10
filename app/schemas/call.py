import uuid
from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, field_validator
from app.core.phone import normalize_phone_number


class CallCreate(BaseModel):
    lead_id: Optional[uuid.UUID] = None
    phone_number: str
    direction: str
    status: str
    duration: Optional[int] = 0
    recording_url: Optional[str] = None
    transcript: Optional[str] = None
    call_summary: Optional[str] = None
    started_at: Optional[datetime] = None
    answered_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        return normalize_phone_number(v)


class CallUpdate(BaseModel):
    phone_number: Optional[str] = None
    direction: Optional[str] = None
    status: Optional[str] = None
    duration: Optional[int] = None
    recording_url: Optional[str] = None
    transcript: Optional[str] = None
    call_summary: Optional[str] = None
    analysis: Optional[Dict[str, Any]] = None
    started_at: Optional[datetime] = None
    answered_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return normalize_phone_number(v)
        return v


class CallOut(CallCreate):
    id: uuid.UUID
    analysis: Optional[Dict[str, Any]] = None
    is_self_test: bool = False
    started_at: Optional[datetime] = None
    answered_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class SelfTestCallRequest(BaseModel):
    phone_number: str

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        return normalize_phone_number(v)
