import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    role: str | None = "ADMIN"

class UserUpdate(BaseModel):
    full_name: str | None = None
    password: str | None = None
    role: str | None = None
    is_active: bool | None = None

class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserOut
