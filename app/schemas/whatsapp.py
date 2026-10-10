import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.phone import normalize_phone_number


class MessageCreate(BaseModel):
    conversation_id: uuid.UUID | None = None
    phone_number: str | None = None
    content: str
    message_type: str | None = "text"
    media_url: str | None = None

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        if v is not None:
            return normalize_phone_number(v)
        return v


class MessageTemplateCreate(BaseModel):
    conversation_id: uuid.UUID | None = None
    phone_number: str
    template_name: str
    language_code: str | None = "en_US"
    components: list[dict[str, Any]] | None = None

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        return normalize_phone_number(v)


class MessageMediaCreate(BaseModel):
    conversation_id: uuid.UUID | None = None
    phone_number: str | None = None
    media_url: str
    media_type: str = Field(..., description="image, video, audio, or document")
    caption: str | None = None

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: str | None) -> str | None:
        if v is not None:
            return normalize_phone_number(v)
        return v


class MessageOut(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    sender: str
    content: str
    message_type: str
    media_url: str | None
    status: str
    external_message_id: str | None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ConversationOut(BaseModel):
    id: uuid.UUID
    lead_id: uuid.UUID | None
    phone_number: str
    unread_count: int
    is_self_test: bool = False
    last_message_at: datetime
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class SelfTestMessageRequest(BaseModel):
    phone_number: str
    content: str | None = None

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        return normalize_phone_number(v)
