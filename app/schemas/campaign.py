import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.core.phone import normalize_phone_number


class CampaignRecipientCreate(BaseModel):
    lead_id: uuid.UUID | None = None
    phone_number: str

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        return normalize_phone_number(v)


class CampaignCreate(BaseModel):
    name: str
    channel: str
    template_name: str | None = None
    status: str | None = "draft"
    recipients: list[CampaignRecipientCreate] | None = None


class CampaignUpdate(BaseModel):
    name: str | None = None
    template_name: str | None = None
    status: str | None = None


class CampaignOut(BaseModel):
    id: uuid.UUID
    name: str
    channel: str
    template_name: str | None
    status: str
    total_recipients: int
    delivered_count: int
    failed_count: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
