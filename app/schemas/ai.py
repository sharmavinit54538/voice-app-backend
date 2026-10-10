import uuid

from pydantic import BaseModel


class AIChatRequest(BaseModel):
    prompt: str
    system_prompt: str | None = None

class AIReplyRequest(BaseModel):
    conversation_id: uuid.UUID
    instruction: str | None = None

class AIGenerateReplyRequest(BaseModel):
    context: str
    instruction: str | None = None

class AISummarizeConversationRequest(BaseModel):
    conversation_id: uuid.UUID

class AISummarizeCallRequest(BaseModel):
    call_id: uuid.UUID
