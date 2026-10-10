import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.core.phone import normalize_phone_number


class LeadCreate(BaseModel):
    name: str
    phone: str
    email: str | None = None
    status: str | None = "new"
    source: str | None = "direct"
    assigned_to: str | None = None
    notes: str | None = None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        return normalize_phone_number(v)


class LeadUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    status: str | None = None
    source: str | None = None
    assigned_to: str | None = None
    notes: str | None = None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        if v is not None:
            return normalize_phone_number(v)
        return v


class LeadOut(LeadCreate):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class PaginatedLeads(BaseModel):
    total: int
    page: int
    page_size: int
    data: list[LeadOut]
