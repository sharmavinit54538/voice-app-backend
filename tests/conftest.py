from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.ext.compiler import compiles

import app.models  # noqa: F401
from app.core.database import Base, get_db
from app.main import app as fastapi_app


# Support PostgreSQL JSONB and UUID types in SQLite for tests
@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


@compiles(UUID, "sqlite")
def compile_uuid_sqlite(type_, compiler, **kw):
    return "CHAR(36)"


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a fresh SQLite in-memory database session for each test."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Provide an HTTP async test client with overridden database session."""

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    fastapi_app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(
        transport=transport, base_url="http://test"
    ) as async_client:
        yield async_client
    fastapi_app.dependency_overrides.clear()
