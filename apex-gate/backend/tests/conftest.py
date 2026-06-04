"""Pytest fixtures for APEX GATE. Uses SQLite in-memory DBs per test."""
from __future__ import annotations

import os

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
TEST_AUTH_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


def _fernet_key() -> str:
    from cryptography.fernet import Fernet
    return Fernet.generate_key().decode()


@pytest_asyncio.fixture(scope="function")
async def app():
    os.environ.setdefault("SECRET_KEY", "test-secret-key-min-32-chars-here-ok!")
    os.environ["FERNET_KEY"] = _fernet_key()
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
    os.environ["AUTH_DATABASE_URL"] = TEST_AUTH_DATABASE_URL

    from app.main import app as fastapi_app
    from app.models import Base as AppBase
    from app.auth.models import AuthBase
    from app.database import get_session
    from app.auth.database import get_auth_session
    from app.limiter import limiter

    # Disable rate limiting so limiter state does not bleed across tests.
    limiter.enabled = False

    app_engine = create_async_engine(TEST_DATABASE_URL)
    async with app_engine.begin() as conn:
        await conn.run_sync(AppBase.metadata.create_all)
    AppSession = async_sessionmaker(app_engine, class_=AsyncSession, expire_on_commit=False)

    auth_engine = create_async_engine(TEST_AUTH_DATABASE_URL)
    async with auth_engine.begin() as conn:
        await conn.run_sync(AuthBase.metadata.create_all)
    AuthSession = async_sessionmaker(auth_engine, class_=AsyncSession, expire_on_commit=False)

    async def _get_session():
        async with AppSession() as s:
            yield s

    async def _get_auth_session():
        async with AuthSession() as s:
            yield s

    fastapi_app.dependency_overrides[get_session] = _get_session
    fastapi_app.dependency_overrides[get_auth_session] = _get_auth_session

    yield fastapi_app

    fastapi_app.dependency_overrides.clear()
    async with app_engine.begin() as conn:
        await conn.run_sync(AppBase.metadata.drop_all)
    async with auth_engine.begin() as conn:
        await conn.run_sync(AuthBase.metadata.drop_all)
    await app_engine.dispose()
    await auth_engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture(scope="function")
async def auth_headers(client: AsyncClient) -> dict[str, str]:
    await client.post("/auth/register", json={"username": "admin", "email": "admin@test.local", "password": "Test1234!"})
    r = await client.post("/auth/login", json={"username": "admin", "password": "Test1234!"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest_asyncio.fixture(scope="function")
async def other_auth_headers(client: AsyncClient, auth_headers: dict) -> dict[str, str]:
    await client.post("/auth/register", json={"username": "user2", "email": "user2@test.local", "password": "Test1234!"}, headers=auth_headers)
    r = await client.post("/auth/login", json={"username": "user2", "password": "Test1234!"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
