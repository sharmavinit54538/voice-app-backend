import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field

class MessageCreate(BaseModel):
    conversation_id: Optional[uuid.UUID] = None
    phone_number: Optional[str] = None
    content: str
    message_type: Optional[str] = "text"
    media_url: Optional[str] = None

class MessageTemplateCreate(BaseModel):
    conversation_id: Optional[uuid.UUID] = None
    phone_number: str
    template_name: str
    language_code: Optional[str] = "en_US"
    components: Optional[List[Dict[str, Any]]] = None

class MessageMediaCreate(BaseModel):
    conversation_id: Optional[uuid.UUID] = None
    phone_number: Optional[str] = None
    media_url: str
    media_type: str = Field(..., description="image, video, audio, or document")
    caption: Optional[str] = None

class MessageOut(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    sender: str
    content: str
    message_type: str
    media_url: Optional[str]
    status: str
    external_message_id: Optional[str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ConversationOut(BaseModel):
    id: uuid.UUID
    lead_id: Optional[uuid.UUID]
    phone_number: str
    unread_count: int
    is_self_test: bool = False
    last_message_at: datetime
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class SelfTestMessageRequest(BaseModel):
    phone_number: str
    content: Optional[str] = None

