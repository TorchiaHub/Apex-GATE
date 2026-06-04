from __future__ import annotations

from collections.abc import AsyncGenerator
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings


def _ensure_sqlite_dir(url: str) -> None:
    """Create the parent directory for a SQLite file if it doesn't exist."""
    if not url.startswith("sqlite"):
        return
    path_str = url.split("://", 1)[-1].lstrip("/")
    if not path_str or path_str == ":memory:":
        return
    Path(path_str).parent.mkdir(parents=True, exist_ok=True)


_ensure_sqlite_dir(settings.AUTH_DATABASE_URL)
auth_engine = create_async_engine(settings.AUTH_DATABASE_URL, echo=False)

AuthSessionLocal = async_sessionmaker(
    auth_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_auth_session() -> AsyncGenerator[AsyncSession, None]:
    async with AuthSessionLocal() as session:
        yield session


async def init_auth_db() -> None:
    from app.auth.models import AuthBase

    async with auth_engine.begin() as conn:
        await conn.run_sync(AuthBase.metadata.create_all)
