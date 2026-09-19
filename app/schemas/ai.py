import uuid
from typing import Optional
from pydantic import BaseModel

class AIChatRequest(BaseModel):
    prompt: str
    system_prompt: Optional[str] = None

class AIReplyRequest(BaseModel):
    conversation_id: uuid.UUID
    instruction: Optional[str] = None

class AIGenerateReplyRequest(BaseModel):
    context: str
    instruction: Optional[str] = None

class AISummarizeConversationRequest(BaseModel):
    conversation_id: uuid.UUID

class AISummarizeCallRequest(BaseModel):
    call_id: uuid.UUID
