import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict

class CampaignRecipientCreate(BaseModel):
    lead_id: Optional[uuid.UUID] = None
    phone_number: str

class CampaignCreate(BaseModel):
    name: str
    channel: str
    template_name: Optional[str] = None
    status: Optional[str] = "draft"
    recipients: Optional[List[CampaignRecipientCreate]] = None

class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    template_name: Optional[str] = None
    status: Optional[str] = None

class CampaignOut(BaseModel):
    id: uuid.UUID
    name: str
    channel: str
    template_name: Optional[str]
    status: str
    total_recipients: int
    delivered_count: int
    failed_count: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
