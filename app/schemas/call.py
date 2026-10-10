import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator

from app.core.phone import normalize_phone_number


class CallCreate(BaseModel):
    lead_id: uuid.UUID | None = None
    phone_number: str
    direction: str
    status: str
    duration: int | None = 0
    recording_url: str | None = None
    transcript: str | None = None
    call_summary: str | None = None
    started_at: datetime | None = None
    answered_at: datetime | None = None
    ended_at: datetime | None = None

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        return normalize_phone_number(v)


class CallUpdate(BaseModel):
    phone_number: str | None = None
    direction: str | None = None
    status: str | None = None
    duration: int | None = None
    recording_url: str | None = None
    transcript: str | None = None
    call_summary: str | None = None
    analysis: dict[str, Any] | None = None
    started_at: datetime | None = None
    answered_at: datetime | None = None
    ended_at: datetime | None = None

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        if v is not None:
            return normalize_phone_number(v)
        return v


class CallOut(CallCreate):
    id: uuid.UUID
    analysis: dict[str, Any] | None = None
    is_self_test: bool = False
    started_at: datetime | None = None
    answered_at: datetime | None = None
    ended_at: datetime | None = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class SelfTestCallRequest(BaseModel):
    phone_number: str

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        return normalize_phone_number(v)
