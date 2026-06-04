"""Integration tests for /auth/* endpoints."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def _register(client, username, password, email, headers=None):
    return await client.post("/auth/register", json={"username": username, "email": email, "password": password}, headers=headers or {})


async def _login(client, username, password):
    return await client.post("/auth/login", json={"username": username, "password": password})


async def test_first_user_is_admin(client: AsyncClient):
    r = await _register(client, "first", "Pass1234!", "first@test.local")
    assert r.status_code == 201
    assert r.json()["is_admin"] is True


async def test_login_returns_tokens(client: AsyncClient):
    await _register(client, "u", "Pass1234!", "u@test.local")
    r = await _login(client, "u", "Pass1234!")
    assert r.status_code == 200
    assert "access_token" in r.json()
    assert "refresh_token" in r.json()


async def test_login_wrong_password(client: AsyncClient):
    await _register(client, "u2", "Pass1234!", "u2@test.local")
    assert (await _login(client, "u2", "WRONG")).status_code == 401


async def test_refresh_issues_new_token(client: AsyncClient):
    await _register(client, "u3", "Pass1234!", "u3@test.local")
    tokens = (await _login(client, "u3", "Pass1234!")).json()
    r = await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 200
    assert r.json()["refresh_token"] != tokens["refresh_token"]


async def test_logout_revokes_token(client: AsyncClient):
    await _register(client, "u4", "Pass1234!", "u4@test.local")
    tokens = (await _login(client, "u4", "Pass1234!")).json()
    await client.post("/auth/logout", json={"refresh_token": tokens["refresh_token"]})
    r = await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 401


async def test_me_requires_auth(client: AsyncClient):
    assert (await client.get("/auth/me")).status_code == 401


async def test_me_returns_user(client: AsyncClient, auth_headers: dict):
    r = await client.get("/auth/me", headers=auth_headers)
    assert r.status_code == 200
    body = r.json()
    assert "username" in body
    assert "hashed_password" not in body
