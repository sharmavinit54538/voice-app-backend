import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, field_validator
from app.core.phone import normalize_phone_number


class LeadCreate(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None
    status: Optional[str] = "new"
    source: Optional[str] = "direct"
    assigned_to: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        return normalize_phone_number(v)


class LeadUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    status: Optional[str] = None
    source: Optional[str] = None
    assigned_to: Optional[str] = None
    notes: Optional[str] = None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
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
    data: List[LeadOut]
