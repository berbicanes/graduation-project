import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.core.security import create_refresh_token as generate_refresh_jwt
from app.core.security import hash_password
from app.models import RefreshToken, User


async def create_user(db: AsyncSession, email: str, password: str, full_name: str, role: str = "patient") -> User:
    user = User(
        email=email,
        hashed_password=hash_password(password),
        full_name=full_name,
        role=role,
    )
    db.add(user)
    await db.flush()
    return user


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def create_refresh_token(db: AsyncSession, user_id: uuid.UUID) -> str:
    token_str = generate_refresh_jwt(user_id)
    expires_at = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    refresh = RefreshToken(user_id=user_id, token=token_str, expires_at=expires_at)
    db.add(refresh)
    await db.flush()
    return token_str


async def get_refresh_token(db: AsyncSession, token: str) -> RefreshToken | None:
    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token == token).options(selectinload(RefreshToken.user))
    )
    return result.scalar_one_or_none()


async def delete_refresh_token(db: AsyncSession, token: str) -> None:
    result = await db.execute(select(RefreshToken).where(RefreshToken.token == token))
    refresh = result.scalar_one_or_none()
    if refresh:
        await db.delete(refresh)
        await db.flush()
