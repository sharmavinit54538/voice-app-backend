from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.future import select
from app.core.config import CORS_ORIGINS
from app.core.database import engine, Base, AsyncSessionLocal
from app.core.security import hash_password
from app.models.user import User
import app.models
from app.routers import register_routers

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).limit(1))
        if not result.scalar_one_or_none():
            session.add(User(
                email="admin@workspace.com",
                full_name="Workspace Owner",
                hashed_password=hash_password("admin12345"),
                role="OWNER",
                is_active=True
            ))
            await session.commit()
    yield
    await engine.dispose()

app = FastAPI(
    title="Real Estate CRM & Automation Engine",
    description="Full production backend supporting Leads, Meta WhatsApp, Calls, Analytics & Gemini AI.",
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

register_routers(app)
