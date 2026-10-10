from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.future import select
from app.core.config import CORS_ORIGINS
from app.core.database import AsyncSessionLocal, Base, engine
from app.core.exceptions import AIServiceError, InvalidPhoneNumberError
from app.core.security import hash_password
import app.models  # noqa: F401
from app.models.user import User
from app.routers import register_routers


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).limit(1))
        if not result.scalar_one_or_none():
            session.add(
                User(
                    email="admin@workspace.com",
                    full_name="Workspace Owner",
                    hashed_password=hash_password("admin12345"),
                    role="OWNER",
                    is_active=True,
                )
            )
            await session.commit()
    yield
    await engine.dispose()


app = FastAPI(
    title="Real Estate CRM & Automation Engine",
    description="Full production backend supporting Leads, Meta WhatsApp, Calls, Analytics & Gemini AI.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True if CORS_ORIGINS != ["*"] else False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AIServiceError)
async def ai_service_error_handler(
    request: Request, exc: AIServiceError  # noqa: ARG001
) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
    )


@app.exception_handler(InvalidPhoneNumberError)
async def invalid_phone_error_handler(
    request: Request, exc: InvalidPhoneNumberError  # noqa: ARG001
) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={"detail": exc.message},
    )


register_routers(app)
