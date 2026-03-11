import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.db import get_db
from app.main import app
from app.models import Base

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_patient.db"

engine = create_async_engine(TEST_DATABASE_URL, echo=False)
test_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with test_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture(autouse=True)
async def mock_publisher():
    with patch("app.events.publisher.publish_event", new_callable=AsyncMock) as mock:
        with patch("app.api.routes.publish_event", mock):
            yield mock


def create_test_token(user_id: uuid.UUID | None = None, role: str = "admin") -> str:
    if user_id is None:
        user_id = uuid.uuid4()
    payload = {
        "sub": str(user_id),
        "role": role,
        "exp": datetime.now(UTC) + timedelta(minutes=30),
        "type": "access",
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


@pytest_asyncio.fixture
def auth_headers() -> dict[str, str]:
    token = create_test_token(role="admin")
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
def doctor_headers() -> dict[str, str]:
    token = create_test_token(role="doctor")
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
def patient_role_headers() -> dict[str, str]:
    token = create_test_token(role="patient")
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
