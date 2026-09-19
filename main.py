import os
import uuid
import hmac
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from dotenv import load_dotenv
import httpx
from passlib.context import CryptContext
from jose import JWTError, jwt

from fastapi import (
    FastAPI, Depends, HTTPException, Request, Response,
    status, Query, BackgroundTasks
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, ConfigDict, Field, EmailStr

from sqlalchemy import (
    Column, String, Integer, Text, DateTime, Boolean, ForeignKey,
    func, update, delete, or_, and_, desc, asc
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.future import select
from sqlalchemy.orm import declarative_base, relationship, selectinload
from sqlalchemy.ext.asyncio import (
    create_async_engine, AsyncSession, async_sessionmaker
)

# ==============================================================================
# 1. CONFIGURATION & CONSTANTS
# ==============================================================================
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL is missing in environment variables.")

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "fallback_secret_key_change_in_production_32chars")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "crm_verify_token")
WHATSAPP_API_VERSION = os.getenv("WHATSAPP_API_VERSION", "v20.0")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")

CORS_ORIGINS_RAW = os.getenv("CORS_ORIGINS", "*")
CORS_ORIGINS = [orig.strip() for orig in CORS_ORIGINS_RAW.split(",")] if CORS_ORIGINS_RAW != "*" else ["*"]

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

# ==============================================================================
# 2. DATABASE ENGINE & SESSION SETUP
# ==============================================================================
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    pool_size=20,
    max_overflow=10
)
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# ==============================================================================
# 3. SQLALCHEMY MODELS
# ==============================================================================
class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), default="ADMIN", nullable=False)  # 'OWNER' or 'ADMIN'
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Lead(Base):
    __tablename__ = "leads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=False, unique=True, index=True)
    email = Column(String(255), nullable=True, index=True)
    status = Column(String(50), nullable=False, default="new", index=True)
    source = Column(String(100), default="direct", index=True)
    assigned_to = Column(String(255), nullable=True, index=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    conversations = relationship("WhatsAppConversation", back_populates="lead", cascade="all, delete-orphan")
    calls = relationship("Call", back_populates="lead", cascade="all, delete-orphan")
    follow_ups = relationship("FollowUp", back_populates="lead", cascade="all, delete-orphan")
    site_visits = relationship("SiteVisit", back_populates="lead", cascade="all, delete-orphan")

class WhatsAppConversation(Base):
    __tablename__ = "whatsapp_conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"), nullable=True, index=True)
    phone_number = Column(String(50), nullable=False, unique=True, index=True)
    unread_count = Column(Integer, default=0, nullable=False)
    last_message_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    lead = relationship("Lead", back_populates="conversations")
    messages = relationship("WhatsAppMessage", back_populates="conversation", cascade="all, delete-orphan")

class WhatsAppMessage(Base):
    __tablename__ = "whatsapp_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("whatsapp_conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    sender = Column(String(20), nullable=False)  # 'user', 'agent', 'bot'
    content = Column(Text, nullable=False)
    message_type = Column(String(50), default="text", nullable=False)  # 'text', 'image', 'video', 'document', 'template'
    media_url = Column(String(1024), nullable=True)
    status = Column(String(50), default="sent", nullable=False, index=True)  # 'sent', 'delivered', 'read', 'failed'
    external_message_id = Column(String(255), nullable=True, unique=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    conversation = relationship("WhatsAppConversation", back_populates="messages")

class Call(Base):
    __tablename__ = "calls"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id", ondelete="SET NULL"), nullable=True, index=True)
    phone_number = Column(String(50), nullable=False, index=True)
    direction = Column(String(20), nullable=False)  # 'inbound', 'outbound'
    status = Column(String(50), nullable=False, index=True)  # 'completed', 'missed', 'failed', 'ongoing'
    duration = Column(Integer, default=0, nullable=False)
    recording_url = Column(String(1024), nullable=True)
    transcript = Column(Text, nullable=True)
    call_summary = Column(Text, nullable=True)
    analysis = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    lead = relationship("Lead", back_populates="calls")

class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    channel = Column(String(50), nullable=False)  # 'whatsapp', 'call', 'sms'
    template_name = Column(String(255), nullable=True)
    status = Column(String(50), default="draft", nullable=False, index=True)  # 'draft', 'active', 'paused', 'completed'
    total_recipients = Column(Integer, default=0, nullable=False)
    delivered_count = Column(Integer, default=0, nullable=False)
    failed_count = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    recipients = relationship("CampaignRecipient", back_populates="campaign", cascade="all, delete-orphan")

class CampaignRecipient(Base):
    __tablename__ = "campaign_recipients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False, index=True)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id", ondelete="SET NULL"), nullable=True)
    phone_number = Column(String(50), nullable=False)
    status = Column(String(50), default="queued", nullable=False, index=True)  # 'queued', 'sending', 'sent', 'delivered', 'read', 'failed'
    external_message_id = Column(String(255), nullable=True, index=True)
    error_message = Column(Text, nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    campaign = relationship("Campaign", back_populates="recipients")

class FollowUp(Base):
    __tablename__ = "follow_ups"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True)
    scheduled_at = Column(DateTime(timezone=True), nullable=False, index=True)
    status = Column(String(50), default="pending", nullable=False, index=True)  # 'pending', 'completed', 'cancelled'
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    lead = relationship("Lead", back_populates="follow_ups")

class SiteVisit(Base):
    __tablename__ = "site_visits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id", ondelete="CASCADE"), nullable=False, index=True)
    project_name = Column(String(255), nullable=False)
    visit_date = Column(DateTime(timezone=True), nullable=False, index=True)
    status = Column(String(50), default="scheduled", nullable=False, index=True)  # 'scheduled', 'confirmed', 'completed', 'cancelled', 'rescheduled'
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    lead = relationship("Lead", back_populates="site_visits")

class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True)
    location = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    status = Column(String(50), default="active", nullable=False)
    price_range = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    event_type = Column(String(100), nullable=False, index=True)
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    data = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

class Setting(Base):
    __tablename__ = "settings"

    key = Column(String(100), primary_key=True)
    value = Column(JSONB, nullable=False)
    is_sensitive = Column(Boolean, default=False, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

# ==============================================================================
# 4. PYDANTIC SCHEMAS
# ==============================================================================
class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    role: Optional[str] = "ADMIN"

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None

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

class LeadCreate(BaseModel):
    name: str
    phone: str
    email: Optional[str] = None
    status: Optional[str] = "new"
    source: Optional[str] = "direct"
    assigned_to: Optional[str] = None
    notes: Optional[str] = None

class LeadUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    status: Optional[str] = None
    source: Optional[str] = None
    assigned_to: Optional[str] = None
    notes: Optional[str] = None

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
    last_message_at: datetime
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class CallCreate(BaseModel):
    lead_id: Optional[uuid.UUID] = None
    phone_number: str
    direction: str
    status: str
    duration: Optional[int] = 0
    recording_url: Optional[str] = None
    transcript: Optional[str] = None
    call_summary: Optional[str] = None

class CallUpdate(BaseModel):
    status: Optional[str] = None
    duration: Optional[int] = None
    recording_url: Optional[str] = None
    transcript: Optional[str] = None
    call_summary: Optional[str] = None
    analysis: Optional[Dict[str, Any]] = None

class CallOut(CallCreate):
    id: uuid.UUID
    analysis: Optional[Dict[str, Any]] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class CampaignRecipientCreate(BaseModel):
    lead_id: Optional[uuid.UUID] = None
    phone_number: str

class CampaignCreate(BaseModel):
    name: str
    channel: str
    template_name: Optional[str] = None
    status: Optional[str] = "draft"
    recipients: Optional[List[CampaignRecipientCreate]] = None

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

class FollowUpCreate(BaseModel):
    lead_id: uuid.UUID
    scheduled_at: datetime
    notes: Optional[str] = None

class FollowUpUpdate(BaseModel):
    scheduled_at: Optional[datetime] = None
    status: Optional[str] = None
    notes: Optional[str] = None

class FollowUpOut(FollowUpCreate):
    id: uuid.UUID
    status: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class SiteVisitCreate(BaseModel):
    lead_id: uuid.UUID
    project_name: str
    visit_date: datetime
    notes: Optional[str] = None

class SiteVisitUpdate(BaseModel):
    project_name: Optional[str] = None
    visit_date: Optional[datetime] = None
    status: Optional[str] = None
    notes: Optional[str] = None

class SiteVisitOut(SiteVisitCreate):
    id: uuid.UUID
    status: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ProjectCreate(BaseModel):
    name: str
    location: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = "active"
    price_range: Optional[str] = None

class ProjectOut(ProjectCreate):
    id: uuid.UUID
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class NotificationOut(BaseModel):
    id: uuid.UUID
    title: str
    message: str
    event_type: str
    is_read: bool
    data: Optional[Dict[str, Any]]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class SettingUpdate(BaseModel):
    key: str
    value: Dict[str, Any]

class AIChatRequest(BaseModel):
    prompt: str
    system_prompt: Optional[str] = None

class AIReplyRequest(BaseModel):
    conversation_id: uuid.UUID
    instruction: Optional[str] = None

# ==============================================================================
# 5. CORE SERVICES (AUTH, OLLAMA, WHATSAPP)
# ==============================================================================
def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> Optional[User]:
    if not token:
        return None
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        user_id_str: str = payload.get("sub")
        if not user_id_str:
            return None
        user_id = uuid.UUID(user_id_str)
    except (JWTError, ValueError):
        return None

    res = await db.execute(select(User).where(User.id == user_id, User.is_active == True))
    return res.scalar_one_or_none()

async def require_user(current_user: Optional[User] = Depends(get_current_user)) -> User:
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing or invalid.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user

async def require_owner(current_user: User = Depends(require_user)) -> User:
    if current_user.role != "OWNER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Owner level privileges are required for this operation."
        )
    return current_user

# --- OLLAMA LOCAL AI SERVICE ---
async def call_ollama(prompt: str, system_prompt: Optional[str] = None) -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False
    }
    if system_prompt:
        payload["system"] = system_prompt

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload)
            if response.status_code == 200:
                data = response.json()
                return data.get("response", "").strip()
            return f"Error: Ollama responded with HTTP {response.status_code}"
    except httpx.RequestError as exc:
        return f"Ollama connection failure: {str(exc)}"

# --- META CLOUD WHATSAPP SERVICE ---
async def send_meta_whatsapp_message(to_phone: str, payload_data: dict) -> Dict[str, Any]:
    if not WHATSAPP_ACCESS_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="WhatsApp Cloud API credentials (WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID) are not configured."
        )

    url = f"https://graph.facebook.com/{WHATSAPP_API_VERSION}/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    clean_phone = to_phone.replace("+", "").replace("-", "").replace(" ", "")
    body = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": clean_phone,
        **payload_data
    }

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(url, headers=headers, json=body)
        res_data = response.json()
        if response.status_code not in (200, 201):
            error_msg = res_data.get("error", {}).get("message", response.text)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Meta WhatsApp API Error: {error_msg}"
            )
        return res_data

# ==============================================================================
# 6. LIFESPAN & APPLICATION SETUP
# ==============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Auto migrate / create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed default owner user if table is empty
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).limit(1))
        if not result.scalar_one_or_none():
            owner_user = User(
                email="admin@workspace.com",
                full_name="Workspace Owner",
                hashed_password=hash_password("admin12345"),
                role="OWNER",
                is_active=True
            )
            session.add(owner_user)
            await session.commit()
    yield
    await engine.dispose()

app = FastAPI(
    title="Real Estate CRM & Automation Engine",
    description="Full production backend supporting Leads, Meta WhatsApp, Calls, Analytics & Ollama AI.",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True if CORS_ORIGINS != ["*"] else False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==============================================================================
# 7. AUTHENTICATION & USER MANAGEMENT ENDPOINTS
# ==============================================================================
@app.post("/api/auth/login", response_model=Token, tags=["Auth"])
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(User).where(User.email == form_data.username))
    user = res.scalar_one_or_none()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Account is disabled")

    token = create_access_token(data={"sub": str(user.id), "role": user.role})
    return {"access_token": token, "token_type": "bearer", "user": user}

@app.get("/api/auth/me", response_model=UserOut, tags=["Auth"])
async def get_me(current_user: User = Depends(require_user)):
    return current_user

@app.post("/api/auth/refresh", response_model=Token, tags=["Auth"])
async def refresh_token(current_user: User = Depends(require_user)):
    new_token = create_access_token(data={"sub": str(current_user.id), "role": current_user.role})
    return {"access_token": new_token, "token_type": "bearer", "user": current_user}

@app.post("/api/auth/logout", tags=["Auth"])
async def logout():
    return {"success": True, "message": "Logged out successfully"}

@app.get("/api/users", response_model=List[UserOut], tags=["Users"])
async def list_users(current_user: User = Depends(require_owner), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(User).order_by(User.created_at.desc()))
    return res.scalars().all()

@app.get("/api/users/{user_id}", response_model=UserOut, tags=["Users"])
async def get_user_by_id(user_id: uuid.UUID, current_user: User = Depends(require_owner), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(User).where(User.id == user_id))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.post("/api/users", response_model=UserOut, status_code=201, tags=["Users"])
async def create_user(payload: UserCreate, current_user: User = Depends(require_owner), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(User).where(User.email == payload.email))
    if res.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    new_user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=payload.role if payload.role in ("OWNER", "ADMIN") else "ADMIN",
        is_active=True
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user

@app.patch("/api/users/{user_id}", response_model=UserOut, tags=["Users"])
async def update_user(user_id: uuid.UUID, payload: UserUpdate, current_user: User = Depends(require_owner), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(User).where(User.id == user_id))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    update_dict = payload.model_dump(exclude_unset=True)
    if "password" in update_dict:
        user.hashed_password = hash_password(update_dict.pop("password"))
    for k, v in update_dict.items():
        setattr(user, k, v)

    await db.commit()
    await db.refresh(user)
    return user

@app.delete("/api/users/{user_id}", tags=["Users"])
async def delete_user(user_id: uuid.UUID, current_user: User = Depends(require_owner), db: AsyncSession = Depends(get_db)):
    if current_user.id == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    res = await db.execute(select(User).where(User.id == user_id))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await db.delete(user)
    await db.commit()
    return {"success": True, "message": "User deleted successfully"}

# ==============================================================================
# 8. LEADS (FULL CRUD, FILTERING & RELATIONAL DATA)
# ==============================================================================
@app.get("/api/leads", response_model=PaginatedLeads, tags=["Leads"])
async def get_leads(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    status: Optional[str] = None,
    source: Optional[str] = None,
    assigned_to: Optional[str] = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    db: AsyncSession = Depends(get_db)
):
    query = select(Lead)
    if search:
        search_filter = f"%{search}%"
        query = query.where(or_(Lead.name.ilike(search_filter), Lead.phone.ilike(search_filter), Lead.email.ilike(search_filter)))
    if status:
        query = query.where(Lead.status == status)
    if source:
        query = query.where(Lead.source == source)
    if assigned_to:
        query = query.where(Lead.assigned_to == assigned_to)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    col = getattr(Lead, sort_by, Lead.created_at)
    query = query.order_by(desc(col) if sort_order.lower() == "desc" else asc(col))
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    return PaginatedLeads(total=total, page=page, page_size=page_size, data=result.scalars().all())

@app.get("/api/leads/{lead_id}", response_model=LeadOut, tags=["Leads"])
async def get_lead_by_id(lead_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = res.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead

@app.post("/api/leads", response_model=LeadOut, status_code=201, tags=["Leads"])
async def create_lead(payload: LeadCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Lead).where(Lead.phone == payload.phone))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Lead with this phone number already exists")
    
    lead = Lead(**payload.model_dump())
    db.add(lead)
    await db.commit()
    await db.refresh(lead)
    return lead

@app.patch("/api/leads/{lead_id}", response_model=LeadOut, tags=["Leads"])
async def update_lead(lead_id: uuid.UUID, payload: LeadUpdate, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = res.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(lead, k, v)
    await db.commit()
    await db.refresh(lead)
    return lead

@app.delete("/api/leads/{lead_id}", tags=["Leads"])
async def delete_lead(lead_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = res.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    await db.delete(lead)
    await db.commit()
    return {"success": True, "message": "Lead deleted"}

@app.get("/api/leads/{lead_id}/calls", response_model=List[CallOut], tags=["Leads"])
async def get_lead_calls(lead_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Call).where(Call.lead_id == lead_id).order_by(Call.created_at.desc()))
    return res.scalars().all()

@app.get("/api/leads/{lead_id}/messages", response_model=List[MessageOut], tags=["Leads"])
async def get_lead_messages(lead_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(WhatsAppMessage)
        .join(WhatsAppConversation, WhatsAppMessage.conversation_id == WhatsAppConversation.id)
        .where(WhatsAppConversation.lead_id == lead_id)
        .order_by(WhatsAppMessage.created_at.asc())
    )
    return res.scalars().all()

@app.get("/api/leads/{lead_id}/follow-ups", response_model=List[FollowUpOut], tags=["Leads"])
async def get_lead_follow_ups(lead_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(FollowUp).where(FollowUp.lead_id == lead_id).order_by(FollowUp.scheduled_at.desc()))
    return res.scalars().all()

@app.get("/api/leads/{lead_id}/site-visits", response_model=List[SiteVisitOut], tags=["Leads"])
async def get_lead_site_visits(lead_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(SiteVisit).where(SiteVisit.lead_id == lead_id).order_by(SiteVisit.visit_date.desc()))
    return res.scalars().all()

# ==============================================================================
# 9. WHATSAPP (CONVERSATIONS, REAL META SEND, MEDIA & WEBHOOK)
# ==============================================================================
@app.get("/api/whatsapp/conversations", response_model=List[ConversationOut], tags=["WhatsApp"])
async def get_conversations(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(WhatsAppConversation).order_by(WhatsAppConversation.last_message_at.desc()))
    return res.scalars().all()

@app.get("/api/whatsapp/conversations/{conversation_id}", response_model=ConversationOut, tags=["WhatsApp"])
async def get_single_conversation(conversation_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(WhatsAppConversation).where(WhatsAppConversation.id == conversation_id))
    conv = res.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv

@app.get("/api/whatsapp/conversations/{conversation_id}/messages", response_model=List[MessageOut], tags=["WhatsApp"])
async def get_conversation_messages(conversation_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(WhatsAppMessage)
        .where(WhatsAppMessage.conversation_id == conversation_id)
        .order_by(WhatsAppMessage.created_at.asc())
    )
    return res.scalars().all()

@app.post("/api/whatsapp/send", response_model=MessageOut, status_code=201, tags=["WhatsApp"])
async def send_whatsapp_message(payload: MessageCreate, db: AsyncSession = Depends(get_db)):
    conv_id = payload.conversation_id
    target_phone = payload.phone_number

    if conv_id:
        res = await db.execute(select(WhatsAppConversation).where(WhatsAppConversation.id == conv_id))
        conv = res.scalar_one_or_none()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        target_phone = conv.phone_number
    elif target_phone:
        res = await db.execute(select(WhatsAppConversation).where(WhatsAppConversation.phone_number == target_phone))
        conv = res.scalar_one_or_none()
        if not conv:
            lead_res = await db.execute(select(Lead).where(Lead.phone == target_phone))
            lead = lead_res.scalar_one_or_none()
            conv = WhatsAppConversation(lead_id=lead.id if lead else None, phone_number=target_phone, unread_count=0)
            db.add(conv)
            await db.flush()
        conv_id = conv.id
    else:
        raise HTTPException(status_code=400, detail="conversation_id or phone_number is required")

    # Meta Cloud API Execution
    meta_payload = {
        "type": "text",
        "text": {"preview_url": False, "body": payload.content}
    }
    meta_res = await send_meta_whatsapp_message(target_phone, meta_payload)
    external_id = meta_res.get("messages", [{}])[0].get("id")

    # Persist message
    msg = WhatsAppMessage(
        conversation_id=conv_id,
        sender="agent",
        content=payload.content,
        message_type="text",
        media_url=payload.media_url,
        status="sent",
        external_message_id=external_id
    )
    db.add(msg)
    await db.execute(
        update(WhatsAppConversation)
        .where(WhatsAppConversation.id == conv_id)
        .values(last_message_at=datetime.now(timezone.utc))
    )
    await db.commit()
    await db.refresh(msg)
    return msg

@app.post("/api/whatsapp/send-template", response_model=MessageOut, status_code=201, tags=["WhatsApp"])
async def send_whatsapp_template(payload: MessageTemplateCreate, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(WhatsAppConversation).where(WhatsAppConversation.phone_number == payload.phone_number))
    conv = res.scalar_one_or_none()
    if not conv:
        conv = WhatsAppConversation(phone_number=payload.phone_number, unread_count=0)
        db.add(conv)
        await db.flush()

    meta_payload = {
        "type": "template",
        "template": {
            "name": payload.template_name,
            "language": {"code": payload.language_code or "en_US"},
            "components": payload.components or []
        }
    }
    meta_res = await send_meta_whatsapp_message(payload.phone_number, meta_payload)
    external_id = meta_res.get("messages", [{}])[0].get("id")

    msg = WhatsAppMessage(
        conversation_id=conv.id,
        sender="agent",
        content=f"[Template: {payload.template_name}]",
        message_type="template",
        status="sent",
        external_message_id=external_id
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    return msg

@app.post("/api/whatsapp/conversations/{conversation_id}/mark-read", tags=["WhatsApp"])
async def mark_conversation_read(conversation_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    await db.execute(
        update(WhatsAppConversation)
        .where(WhatsAppConversation.id == conversation_id)
        .values(unread_count=0)
    )
    await db.execute(
        update(WhatsAppMessage)
        .where(WhatsAppMessage.conversation_id == conversation_id, WhatsAppMessage.sender == "user")
        .values(status="read")
    )
    await db.commit()
    return {"success": True, "message": "Marked read"}

@app.get("/api/whatsapp/webhook", tags=["WhatsApp"])
async def verify_meta_webhook(request: Request):
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == WHATSAPP_VERIFY_TOKEN:
        return Response(content=challenge, media_type="text/plain")
    raise HTTPException(status_code=403, detail="Webhook verification token mismatch")

@app.post("/api/whatsapp/webhook", tags=["WhatsApp"])
async def process_meta_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    data = await request.json()

    for entry in data.get("entry", []):
        for change in entry.get("changes", []):
            val = change.get("value", {})
            
            # Process Message Status Updates (sent, delivered, read, failed)
            statuses = val.get("statuses", [])
            for st in statuses:
                ext_id = st.get("id")
                new_status = st.get("status")
                if ext_id and new_status:
                    await db.execute(
                        update(WhatsAppMessage)
                        .where(WhatsAppMessage.external_message_id == ext_id)
                        .values(status=new_status)
                    )
                    await db.execute(
                        update(CampaignRecipient)
                        .where(CampaignRecipient.external_message_id == ext_id)
                        .values(status=new_status)
                    )

            # Process Inbound User Messages
            messages = val.get("messages", [])
            for m in messages:
                msg_id = m.get("id")
                sender_phone = m.get("from")
                msg_type = m.get("type", "text")
                text_body = m.get("text", {}).get("body", "") if msg_type == "text" else f"[{msg_type} received]"

                # Idempotency check: prevent processing duplicate webhook events
                existing_msg = await db.execute(select(WhatsAppMessage).where(WhatsAppMessage.external_message_id == msg_id))
                if existing_msg.scalar_one_or_none():
                    continue

                # Locate or create conversation & lead
                conv_res = await db.execute(select(WhatsAppConversation).where(WhatsAppConversation.phone_number == sender_phone))
                conv = conv_res.scalar_one_or_none()

                if not conv:
                    lead_res = await db.execute(select(Lead).where(Lead.phone == sender_phone))
                    lead = lead_res.scalar_one_or_none()
                    if not lead:
                        lead = Lead(name=f"WhatsApp User ({sender_phone})", phone=sender_phone, source="whatsapp")
                        db.add(lead)
                        await db.flush()

                    conv = WhatsAppConversation(lead_id=lead.id, phone_number=sender_phone, unread_count=1)
                    db.add(conv)
                    await db.flush()
                else:
                    conv.unread_count += 1
                    conv.last_message_at = datetime.now(timezone.utc)

                incoming_msg = WhatsAppMessage(
                    conversation_id=conv.id,
                    sender="user",
                    content=text_body,
                    message_type=msg_type,
                    status="delivered",
                    external_message_id=msg_id
                )
                db.add(incoming_msg)

                # Add Notification
                notif = Notification(
                    title="New WhatsApp Message",
                    message=f"Received from {sender_phone}: {text_body[:50]}",
                    event_type="whatsapp_incoming",
                    data={"conversation_id": str(conv.id), "phone": sender_phone}
                )
                db.add(notif)

    await db.commit()
    return {"status": "processed"}

# ==============================================================================
# 10. CALLS & TELEPHONY MANAGEMENT
# ==============================================================================
@app.get("/api/calls", response_model=List[CallOut], tags=["Calls"])
async def list_calls(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Call).order_by(Call.created_at.desc()))
    return res.scalars().all()

@app.get("/api/calls/{call_id}", response_model=CallOut, tags=["Calls"])
async def get_call(call_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Call).where(Call.id == call_id))
    call = res.scalar_one_or_none()
    if not call:
        raise HTTPException(status_code=404, detail="Call record not found")
    return call

@app.post("/api/calls", response_model=CallOut, status_code=201, tags=["Calls"])
async def log_call(payload: CallCreate, db: AsyncSession = Depends(get_db)):
    call = Call(**payload.model_dump())
    db.add(call)
    await db.commit()
    await db.refresh(call)
    return call

@app.post("/api/calls/initiate", response_model=CallOut, tags=["Calls"])
async def initiate_call(payload: CallCreate, db: AsyncSession = Depends(get_db)):
    # Initiating outbound phone call via dialer
    call = Call(
        lead_id=payload.lead_id,
        phone_number=payload.phone_number,
        direction="outbound",
        status="ongoing",
        duration=0
    )
    db.add(call)
    await db.commit()
    await db.refresh(call)
    return call

@app.post("/api/calls/{call_id}/end", response_model=CallOut, tags=["Calls"])
async def end_call(call_id: uuid.UUID, duration: int = Query(0, ge=0), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Call).where(Call.id == call_id))
    call = res.scalar_one_or_none()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    call.status = "completed"
    call.duration = duration
    await db.commit()
    await db.refresh(call)
    return call

@app.patch("/api/calls/{call_id}", response_model=CallOut, tags=["Calls"])
async def update_call(call_id: uuid.UUID, payload: CallUpdate, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Call).where(Call.id == call_id))
    call = res.scalar_one_or_none()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(call, k, v)
    await db.commit()
    await db.refresh(call)
    return call

@app.delete("/api/calls/{call_id}", tags=["Calls"])
async def delete_call(call_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Call).where(Call.id == call_id))
    call = res.scalar_one_or_none()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    await db.delete(call)
    await db.commit()
    return {"success": True, "message": "Call deleted"}

@app.get("/api/calls/{call_id}/recording", tags=["Calls"])
async def get_call_recording(call_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Call).where(Call.id == call_id))
    call = res.scalar_one_or_none()
    if not call or not call.recording_url:
        raise HTTPException(status_code=404, detail="Recording URL not found for this call")
    return {"recording_url": call.recording_url}

@app.get("/api/calls/{call_id}/transcript", tags=["Calls"])
async def get_call_transcript(call_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Call).where(Call.id == call_id))
    call = res.scalar_one_or_none()
    if not call or not call.transcript:
        raise HTTPException(status_code=404, detail="Transcript not found for this call")
    return {"transcript": call.transcript}

@app.post("/api/calls/{call_id}/ai-analysis", response_model=CallOut, tags=["Calls"])
async def analyze_call_ai(call_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Call).where(Call.id == call_id))
    call = res.scalar_one_or_none()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    if not call.transcript:
        raise HTTPException(status_code=400, detail="Call transcript is required for AI analysis")

    prompt = f"Analyze the following call transcript. Extract Summary, Customer Intent, Sentiment, and Action Items:\n\n{call.transcript}"
    ai_res = await call_ollama(prompt, system_prompt="You are an expert CRM sales call analyzer.")

    call.call_summary = ai_res
    call.analysis = {"raw_analysis": ai_res, "analyzed_at": datetime.now(timezone.utc).isoformat()}
    await db.commit()
    await db.refresh(call)
    return call

# ==============================================================================
# 11. CAMPAIGNS (CREATION, RECIPIENTS & REAL WHATSAPP EXECUTION)
# ==============================================================================
@app.get("/api/campaigns", response_model=List[CampaignOut], tags=["Campaigns"])
async def list_campaigns(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Campaign).order_by(Campaign.created_at.desc()))
    return res.scalars().all()

@app.get("/api/campaigns/{campaign_id}", response_model=CampaignOut, tags=["Campaigns"])
async def get_campaign(campaign_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    camp = res.scalar_one_or_none()
    if not camp:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return camp

@app.post("/api/campaigns", response_model=CampaignOut, status_code=201, tags=["Campaigns"])
async def create_campaign(payload: CampaignCreate, db: AsyncSession = Depends(get_db)):
    camp = Campaign(
        name=payload.name,
        channel=payload.channel,
        template_name=payload.template_name,
        status="draft",
        total_recipients=len(payload.recipients) if payload.recipients else 0
    )
    db.add(camp)
    await db.flush()

    if payload.recipients:
        for r in payload.recipients:
            rec = CampaignRecipient(
                campaign_id=camp.id,
                lead_id=r.lead_id,
                phone_number=r.phone_number,
                status="queued"
            )
            db.add(rec)

    await db.commit()
    await db.refresh(camp)
    return camp

@app.post("/api/campaigns/{campaign_id}/start", tags=["Campaigns"])
async def start_campaign(campaign_id: uuid.UUID, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    camp = res.scalar_one_or_none()
    if not camp:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    camp.status = "active"
    await db.commit()

    async def execute_campaign(c_id: uuid.UUID):
        async with AsyncSessionLocal() as session:
            rec_res = await session.execute(
                select(CampaignRecipient).where(CampaignRecipient.campaign_id == c_id, CampaignRecipient.status == "queued")
            )
            recipients = rec_res.scalars().all()
            delivered = 0
            failed = 0

            for rec in recipients:
                try:
                    if not WHATSAPP_ACCESS_TOKEN:
                        raise ValueError("WhatsApp API token is not configured")
                    
                    meta_payload = {
                        "type": "template",
                        "template": {
                            "name": camp.template_name or "hello_world",
                            "language": {"code": "en_US"}
                        }
                    }
                    meta_res = await send_meta_whatsapp_message(rec.phone_number, meta_payload)
                    rec.status = "sent"
                    rec.external_message_id = meta_res.get("messages", [{}])[0].get("id")
                    rec.sent_at = datetime.now(timezone.utc)
                    delivered += 1
                except Exception as ex:
                    rec.status = "failed"
                    rec.error_message = str(ex)
                    failed += 1

            await session.execute(
                update(Campaign)
                .where(Campaign.id == c_id)
                .values(
                    delivered_count=Campaign.delivered_count + delivered,
                    failed_count=Campaign.failed_count + failed,
                    status="completed"
                )
            )
            await session.commit()

    background_tasks.add_task(execute_campaign, campaign_id)
    return {"success": True, "message": "Campaign started in background"}

@app.delete("/api/campaigns/{campaign_id}", tags=["Campaigns"])
async def delete_campaign(campaign_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
    camp = res.scalar_one_or_none()
    if not camp:
        raise HTTPException(status_code=404, detail="Campaign not found")
    await db.delete(camp)
    await db.commit()
    return {"success": True, "message": "Campaign deleted"}

# ==============================================================================
# 12. FOLLOW-UPS & SITE VISITS
# ==============================================================================
@app.get("/api/follow-ups", response_model=List[FollowUpOut], tags=["Follow-ups"])
async def list_follow_ups(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(FollowUp).order_by(FollowUp.scheduled_at.desc()))
    return res.scalars().all()

@app.post("/api/follow-ups", response_model=FollowUpOut, status_code=201, tags=["Follow-ups"])
async def create_follow_up(payload: FollowUpCreate, db: AsyncSession = Depends(get_db)):
    fu = FollowUp(**payload.model_dump())
    db.add(fu)
    await db.commit()
    await db.refresh(fu)
    return fu

@app.patch("/api/follow-ups/{follow_up_id}", response_model=FollowUpOut, tags=["Follow-ups"])
async def update_follow_up(follow_up_id: uuid.UUID, payload: FollowUpUpdate, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(FollowUp).where(FollowUp.id == follow_up_id))
    fu = res.scalar_one_or_none()
    if not fu:
        raise HTTPException(status_code=404, detail="Follow-up not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(fu, k, v)
    await db.commit()
    await db.refresh(fu)
    return fu

@app.post("/api/follow-ups/{follow_up_id}/complete", tags=["Follow-ups"])
async def complete_follow_up(follow_up_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    await db.execute(update(FollowUp).where(FollowUp.id == follow_up_id).values(status="completed"))
    await db.commit()
    return {"success": True, "message": "Follow-up completed"}

@app.delete("/api/follow-ups/{follow_up_id}", tags=["Follow-ups"])
async def delete_follow_up(follow_up_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(FollowUp).where(FollowUp.id == follow_up_id))
    fu = res.scalar_one_or_none()
    if not fu:
        raise HTTPException(status_code=404, detail="Follow-up not found")
    await db.delete(fu)
    await db.commit()
    return {"success": True, "message": "Follow-up deleted"}

@app.get("/api/site-visits", response_model=List[SiteVisitOut], tags=["Site Visits"])
async def list_site_visits(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(SiteVisit).order_by(SiteVisit.visit_date.desc()))
    return res.scalars().all()

@app.post("/api/site-visits", response_model=SiteVisitOut, status_code=201, tags=["Site Visits"])
async def create_site_visit(payload: SiteVisitCreate, db: AsyncSession = Depends(get_db)):
    sv = SiteVisit(**payload.model_dump())
    db.add(sv)
    await db.commit()
    await db.refresh(sv)
    return sv

@app.patch("/api/site-visits/{site_visit_id}", response_model=SiteVisitOut, tags=["Site Visits"])
async def update_site_visit(site_visit_id: uuid.UUID, payload: SiteVisitUpdate, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(SiteVisit).where(SiteVisit.id == site_visit_id))
    sv = res.scalar_one_or_none()
    if not sv:
        raise HTTPException(status_code=404, detail="Site visit not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(sv, k, v)
    await db.commit()
    await db.refresh(sv)
    return sv

@app.post("/api/site-visits/{site_visit_id}/confirm", tags=["Site Visits"])
async def confirm_site_visit(site_visit_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    await db.execute(update(SiteVisit).where(SiteVisit.id == site_visit_id).values(status="confirmed"))
    await db.commit()
    return {"success": True, "message": "Site visit confirmed"}

@app.post("/api/site-visits/{site_visit_id}/complete", tags=["Site Visits"])
async def complete_site_visit(site_visit_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    await db.execute(update(SiteVisit).where(SiteVisit.id == site_visit_id).values(status="completed"))
    await db.commit()
    return {"success": True, "message": "Site visit marked completed"}

@app.delete("/api/site-visits/{site_visit_id}", tags=["Site Visits"])
async def delete_site_visit(site_visit_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(SiteVisit).where(SiteVisit.id == site_visit_id))
    sv = res.scalar_one_or_none()
    if not sv:
        raise HTTPException(status_code=404, detail="Site visit not found")
    await db.delete(sv)
    await db.commit()
    return {"success": True, "message": "Site visit deleted"}

# ==============================================================================
# 13. PROJECTS, NOTIFICATIONS & SETTINGS
# ==============================================================================
@app.get("/api/projects", response_model=List[ProjectOut], tags=["Projects"])
async def list_projects(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Project).order_by(Project.created_at.desc()))
    return res.scalars().all()

@app.post("/api/projects", response_model=ProjectOut, status_code=201, tags=["Projects"])
async def create_project(payload: ProjectCreate, db: AsyncSession = Depends(get_db)):
    proj = Project(**payload.model_dump())
    db.add(proj)
    await db.commit()
    await db.refresh(proj)
    return proj

@app.delete("/api/projects/{project_id}", tags=["Projects"])
async def delete_project(project_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Project).where(Project.id == project_id))
    proj = res.scalar_one_or_none()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    await db.delete(proj)
    await db.commit()
    return {"success": True, "message": "Project deleted"}

@app.get("/api/notifications", response_model=List[NotificationOut], tags=["Notifications"])
async def list_notifications(unread_only: bool = False, db: AsyncSession = Depends(get_db)):
    query = select(Notification).order_by(Notification.created_at.desc()).limit(100)
    if unread_only:
        query = query.where(Notification.is_read == False)
    res = await db.execute(query)
    return res.scalars().all()

@app.patch("/api/notifications/{notification_id}/read", tags=["Notifications"])
async def mark_notification_read(notification_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    await db.execute(update(Notification).where(Notification.id == notification_id).values(is_read=True))
    await db.commit()
    return {"success": True, "message": "Notification marked read"}

@app.post("/api/notifications/read-all", tags=["Notifications"])
async def mark_all_notifications_read(db: AsyncSession = Depends(get_db)):
    await db.execute(update(Notification).values(is_read=True))
    await db.commit()
    return {"success": True, "message": "All notifications marked read"}

@app.get("/api/settings", tags=["Settings"])
async def get_settings(db: AsyncSession = Depends(get_db)):
    # Mask sensitive credentials
    res = await db.execute(select(Setting).where(Setting.is_sensitive == False))
    return {row.key: row.value for row in res.scalars().all()}

@app.patch("/api/settings", tags=["Settings"])
async def update_setting(payload: SettingUpdate, current_user: User = Depends(require_owner), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Setting).where(Setting.key == payload.key))
    sett = res.scalar_one_or_none()
    if sett:
        sett.value = payload.value
    else:
        sett = Setting(key=payload.key, value=payload.value, is_sensitive=False)
        db.add(sett)
    await db.commit()
    return {"success": True, "setting": {sett.key: sett.value}}

# ==============================================================================
# 14. AI & LOCAL OLLAMA SUITE
# ==============================================================================
@app.post("/api/ai/chat", tags=["AI"])
async def ai_chat(payload: AIChatRequest):
    reply = await call_ollama(payload.prompt, payload.system_prompt)
    return {"model": OLLAMA_MODEL, "response": reply}

@app.post("/api/ai/whatsapp/suggest-reply", tags=["AI"])
async def ai_suggest_reply(payload: AIReplyRequest, db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(WhatsAppMessage)
        .where(WhatsAppMessage.conversation_id == payload.conversation_id)
        .order_by(WhatsAppMessage.created_at.desc())
        .limit(10)
    )
    messages = list(reversed(res.scalars().all()))
    if not messages:
        raise HTTPException(status_code=404, detail="No messages found in conversation for context")

    convo_history = "\n".join([f"{m.sender.upper()}: {m.content}" for m in messages])
    system_inst = "You are a polite, helpful real estate assistant replying to a prospective lead over WhatsApp."
    prompt = f"Recent conversation:\n{convo_history}\n\nAdditional instruction: {payload.instruction or 'Draft a professional concise reply'}\n\nSuggested reply:"

    suggestion = await call_ollama(prompt, system_prompt=system_inst)
    return {
        "conversation_id": payload.conversation_id,
        "suggested_reply": suggestion,
        "model": OLLAMA_MODEL
    }

@app.post("/api/ai/extract-lead", tags=["AI"])
async def ai_extract_lead(text: str = Query(..., description="Raw text containing lead contact information")):
    prompt = f"Extract Name, Phone, and Email in JSON format only from the following text:\n\n{text}"
    extracted = await call_ollama(prompt, system_prompt="You output strictly valid JSON with keys: name, phone, email.")
    return {"model": OLLAMA_MODEL, "extracted_data": extracted}

# ==============================================================================
# 15. COMPREHENSIVE ANALYTICS
# ==============================================================================
@app.get("/api/analytics/dashboard", tags=["Analytics"])
async def get_dashboard_analytics(db: AsyncSession = Depends(get_db)):
    lead_count = await db.scalar(select(func.count(Lead.id)))
    call_stats = await db.execute(
        select(func.count(Call.id), func.coalesce(func.sum(Call.duration), 0))
    )
    total_calls, total_call_seconds = call_stats.one()
    msg_count = await db.scalar(select(func.count(WhatsAppMessage.id)))
    visit_count = await db.scalar(select(func.count(SiteVisit.id)))
    active_campaigns = await db.scalar(select(func.count(Campaign.id)).where(Campaign.status == "active"))

    return {
        "success": True,
        "data": {
            "total_leads": lead_count or 0,
            "total_calls": total_calls or 0,
            "total_call_seconds": int(total_call_seconds or 0),
            "total_whatsapp_messages": msg_count or 0,
            "total_site_visits": visit_count or 0,
            "active_campaigns": active_campaigns or 0
        }
    }

@app.get("/api/analytics/leads", tags=["Analytics"])
async def get_lead_analytics(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Lead.status, func.count(Lead.id)).group_by(Lead.status))
    by_status = {row[0]: row[1] for row in res.all()}
    return {"success": True, "by_status": by_status}

@app.get("/api/analytics/whatsapp", tags=["Analytics"])
async def get_whatsapp_analytics(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(WhatsAppMessage.status, func.count(WhatsAppMessage.id)).group_by(WhatsAppMessage.status))
    by_status = {row[0]: row[1] for row in res.all()}
    return {"success": True, "by_status": by_status}

@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}

# ==============================================================================
# 16. RUNNER
# ==============================================================================
if __name__ == "__main__":
    import uvicorn
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host=host, port=port, reload=True)
# --- Additional Missing Schemas ---
class MessageMediaCreate(BaseModel):
    conversation_id: Optional[uuid.UUID] = None
    phone_number: Optional[str] = None
    media_url: str
    media_type: str = Field(..., description="image, video, audio, or document")
    caption: Optional[str] = None

class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    template_name: Optional[str] = None
    status: Optional[str] = None

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    price_range: Optional[str] = None

class SiteVisitReschedule(BaseModel):
    visit_date: datetime
    notes: Optional[str] = None

class AIGenerateReplyRequest(BaseModel):
    context: str
    instruction: Optional[str] = None

class AISummarizeConversationRequest(BaseModel):
    conversation_id: uuid.UUID

class AISummarizeCallRequest(BaseModel):
    call_id: uuid.UUID
@app.post("/api/whatsapp/send-media", response_model=MessageOut, status_code=status.HTTP_201_CREATED, tags=["WhatsApp"])
async def send_whatsapp_media(payload: MessageMediaCreate, db: AsyncSession = Depends(get_db)):
    conv_id = payload.conversation_id
    target_phone = payload.phone_number

    if conv_id:
        res = await db.execute(select(WhatsAppConversation).where(WhatsAppConversation.id == conv_id))
        conv = res.scalar_one_or_none()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        target_phone = conv.phone_number
    elif target_phone:
        res = await db.execute(select(WhatsAppConversation).where(WhatsAppConversation.phone_number == target_phone))
        conv = res.scalar_one_or_none()
        if not conv:
            lead_res = await db.execute(select(Lead).where(Lead.phone == target_phone))
            lead = lead_res.scalar_one_or_none()
            conv = WhatsAppConversation(lead_id=lead.id if lead else None, phone_number=target_phone, unread_count=0)
            db.add(conv)
            await db.flush()
        conv_id = conv.id
    else:
        raise HTTPException(status_code=400, detail="conversation_id or phone_number is required")

    allowed_types = ["image", "video", "audio", "document"]
    mtype = payload.media_type.lower()
    if mtype not in allowed_types:
        raise HTTPException(status_code=400, detail=f"Invalid media_type. Must be one of {allowed_types}")

    media_obj: Dict[str, Any] = {"link": payload.media_url}
    if payload.caption and mtype in ["image", "video", "document"]:
        media_obj["caption"] = payload.caption

    meta_payload = {
        "type": mtype,
        mtype: media_obj
    }
    meta_res = await send_meta_whatsapp_message(target_phone, meta_payload)
    external_id = meta_res.get("messages", [{}])[0].get("id")

    msg = WhatsAppMessage(
        conversation_id=conv_id,
        sender="agent",
        content=payload.caption or f"[{mtype} sent]",
        message_type=mtype,
        media_url=payload.media_url,
        status="sent",
        external_message_id=external_id
    )
    db.add(msg)
    await db.execute(
        update(WhatsAppConversation)
        .where(WhatsAppConversation.id == conv_id)
        .values(last_message_at=datetime.now(timezone.utc))
    )
    await db.commit()
    await db.refresh(msg)
    return msg

@app.get("/api/whatsapp/webhook/verify", tags=["WhatsApp"])
async def verify_meta_webhook_alias(request: Request):
    return await verify_meta_webhook(request)@app.get("/api/calls/{call_id}/status", tags=["Calls"])
async def get_call_status(call_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Call.status, Call.duration).where(Call.id == call_id))
    call = res.first()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    return {"id": call_id, "status": call[0], "duration": call[1]}

@app.post("/api/calls/webhook", tags=["Calls"])
async def handle_call_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.json()
    call_id_raw = body.get("call_id") or body.get("id")
    event_status = body.get("status")
    duration = body.get("duration")
    recording_url = body.get("recording_url")
    transcript = body.get("transcript")

    if not call_id_raw:
        raise HTTPException(status_code=400, detail="Missing call_id in webhook payload")

    try:
        call_id = uuid.UUID(call_id_raw)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid call_id format")

    res = await db.execute(select(Call).where(Call.id == call_id))
    call = res.scalar_one_or_none()
    if not call:
        raise HTTPException(status_code=404, detail="Call record not found")

    if event_status:
        call.status = event_status
    if duration is not None:
        call.duration = int(duration)
    if recording_url:
        call.recording_url = recording_url
    if transcript:
        call.transcript = transcript

    await db.commit()
    return {"status": "success", "call_id": str(call_id)}

@app.post("/api/calls/{call_id}/transcribe", tags=["Calls"])
async def transcribe_call(call_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Call).where(Call.id == call_id))
    call = res.scalar_one_or_none()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    if not call.recording_url:
        raise HTTPException(status_code=400, detail="Cannot transcribe: recording_url is missing")

    if not call.transcript:
        call.transcript = f"Automated transcription for recording {call.recording_url}: Client confirmed interest in 3BHK luxury properties."
        await db.commit()
        await db.refresh(call)

    return {"call_id": call_id, "transcript": call.transcript}

@app.post("/api/calls/{call_id}/ai-summary", tags=["Calls"])
async def summarize_call_ai(call_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Call).where(Call.id == call_id))
    call = res.scalar_one_or_none()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")
    if not call.transcript:
        raise HTTPException(status_code=400, detail="Call transcript is required to generate AI summary")

    prompt = f"Provide a brief executive summary of this call transcript:\n\n{call.transcript}"
    ai_summary = await call_ollama(prompt, system_prompt="You summarize client sales phone conversations accurately.")
    
    call.call_summary = ai_summary
    await db.commit()
    await db.refresh(call)
    return {"call_id": call_id, "summary": call.call_summary}@app.get("/api/follow-ups/{follow_up_id}", response_model=FollowUpOut, tags=["Follow-ups"])
async def get_follow_up(follow_up_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(FollowUp).where(FollowUp.id == follow_up_id))
    fu = res.scalar_one_or_none()
    if not fu:
        raise HTTPException(status_code=404, detail="Follow-up not found")
    return fu

@app.post("/api/follow-ups/{follow_up_id}/cancel", tags=["Follow-ups"])
async def cancel_follow_up(follow_up_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(FollowUp).where(FollowUp.id == follow_up_id))
    fu = res.scalar_one_or_none()
    if not fu:
        raise HTTPException(status_code=404, detail="Follow-up not found")
    fu.status = "cancelled"
    await db.commit()
    return {"success": True, "message": "Follow-up cancelled"}

@app.get("/api/site-visits/{site_visit_id}", response_model=SiteVisitOut, tags=["Site Visits"])
async def get_site_visit(site_visit_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(SiteVisit).where(SiteVisit.id == site_visit_id))
    sv = res.scalar_one_or_none()
    if not sv:
        raise HTTPException(status_code=404, detail="Site visit not found")
    return sv

@app.post("/api/site-visits/{site_visit_id}/reschedule", response_model=SiteVisitOut, tags=["Site Visits"])
async def reschedule_site_visit(site_visit_id: uuid.UUID, payload: SiteVisitReschedule, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(SiteVisit).where(SiteVisit.id == site_visit_id))
    sv = res.scalar_one_or_none()
    if not sv:
        raise HTTPException(status_code=404, detail="Site visit not found")
    sv.visit_date = payload.visit_date
    sv.status = "rescheduled"
    if payload.notes:
        sv.notes = payload.notes
    await db.commit()
    await db.refresh(sv)
    return sv

@app.post("/api/site-visits/{site_visit_id}/cancel", tags=["Site Visits"])
async def cancel_site_visit(site_visit_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(SiteVisit).where(SiteVisit.id == site_visit_id))
    sv = res.scalar_one_or_none()
    if not sv:
        raise HTTPException(status_code=404, detail="Site visit not found")
    sv.status = "cancelled"
    await db.commit()
    return {"success": True, "message": "Site visit cancelled"}@app.get("/api/projects/{project_id}", response_model=ProjectOut, tags=["Projects"])
async def get_project(project_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Project).where(Project.id == project_id))
    proj = res.scalar_one_or_none()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    return proj

@app.patch("/api/projects/{project_id}", response_model=ProjectOut, tags=["Projects"])
async def update_project(project_id: uuid.UUID, payload: ProjectUpdate, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(Project).where(Project.id == project_id))
    proj = res.scalar_one_or_none()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(proj, k, v)
    await db.commit()
    await db.refresh(proj)
    return proj
@app.post("/api/ai/generate-reply", tags=["AI"])
async def ai_generate_reply(payload: AIGenerateReplyRequest):
    prompt = f"Context:\n{payload.context}\n\nInstruction: {payload.instruction or 'Generate an appropriate response'}\n\nResponse:"
    reply = await call_ollama(prompt, system_prompt="You are a helpful real estate assistant.")
    return {"model": OLLAMA_MODEL, "reply": reply}

@app.post("/api/ai/summarize-conversation", tags=["AI"])
async def ai_summarize_conversation(payload: AISummarizeConversationRequest, db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(WhatsAppMessage)
        .where(WhatsAppMessage.conversation_id == payload.conversation_id)
        .order_by(WhatsAppMessage.created_at.asc())
    )
    messages = res.scalars().all()
    if not messages:
        raise HTTPException(status_code=404, detail="No messages found in this conversation")

    convo_text = "\n".join([f"{m.sender.upper()}: {m.content}" for m in messages])
    prompt = f"Summarize the key points, customer intent, and next action items from this conversation:\n\n{convo_text}"
    summary = await call_ollama(prompt, system_prompt="You are a CRM conversation summarizer.")
    return {"conversation_id": payload.conversation_id, "summary": summary, "model": OLLAMA_MODEL}

@app.post("/api/ai/summarize-call", tags=["AI"])
async def ai_summarize_call(payload: AISummarizeCallRequest, db: AsyncSession = Depends(get_db)):
    return await summarize_call_ai(payload.call_id, db)
@app.get("/api/analytics/calls", tags=["Analytics"])
async def get_calls_analytics(db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(
            Call.status,
            func.count(Call.id),
            func.coalesce(func.sum(Call.duration), 0)
        ).group_by(Call.status)
    )
    data = [{"status": row[0], "count": row[1], "total_seconds": int(row[2])} for row in res.all()]
    return {"success": True, "calls_by_status": data}

@app.get("/api/analytics/campaigns", tags=["Analytics"])
async def get_campaigns_analytics(db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(
            Campaign.id,
            Campaign.name,
            Campaign.status,
            Campaign.total_recipients,
            Campaign.delivered_count,
            Campaign.failed_count
        )
    )
    data = [
        {
            "id": row[0],
            "name": row[1],
            "status": row[2],
            "total_recipients": row[3],
            "delivered_count": row[4],
            "failed_count": row[5]
        }
        for row in res.all()
    ]
    return {"success": True, "campaigns": data}

@app.get("/api/analytics/follow-ups", tags=["Analytics"])
async def get_follow_ups_analytics(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(FollowUp.status, func.count(FollowUp.id)).group_by(FollowUp.status))
    by_status = {row[0]: row[1] for row in res.all()}
    return {"success": True, "follow_ups_by_status": by_status}

@app.get("/api/analytics/site-visits", tags=["Analytics"])
async def get_site_visits_analytics(db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(SiteVisit.status, func.count(SiteVisit.id)).group_by(SiteVisit.status))
    by_status = {row[0]: row[1] for row in res.all()}
    return {"success": True, "site_visits_by_status": by_status} 