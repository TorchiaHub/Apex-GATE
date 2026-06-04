"""Integration tests for /api/v1/keys endpoints."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

_PLAINTEXT = "sk-test-plaintext-key-abcdef1234567890"


async def _provider_id(client, headers, slug="openai"):
    r = await client.get(f"/api/v1/providers/{slug}", headers=headers)
    if r.status_code != 200:
        pytest.skip(f"Provider '{slug}' not seeded — skip key tests")
    return r.json()["id"]


async def _create(client, headers, provider_id):
    r = await client.post("/api/v1/keys", json={"provider_id": provider_id, "name": "Test", "api_key_plaintext": _PLAINTEXT, "tier": "free"}, headers=headers)
    assert r.status_code in (200, 201)
    return r.json()


async def test_create_never_returns_plaintext(client: AsyncClient, auth_headers: dict):
    pid = await _provider_id(client, auth_headers)
    body = await _create(client, auth_headers, pid)
    assert "key_masked" in body
    assert _PLAINTEXT not in str(body)
    assert "key_encrypted" not in body


async def test_list_never_returns_plaintext(client: AsyncClient, auth_headers: dict):
    pid = await _provider_id(client, auth_headers)
    await _create(client, auth_headers, pid)
    r = await client.get("/api/v1/keys", headers=auth_headers)
    assert r.status_code == 200
    for key in r.json():
        assert _PLAINTEXT not in str(key)
        assert "key_encrypted" not in key


async def test_delete_removes_key(client: AsyncClient, auth_headers: dict):
    pid = await _provider_id(client, auth_headers)
    created = await _create(client, auth_headers, pid)
    r = await client.delete(f"/api/v1/keys/{created['id']}", headers=auth_headers)
    assert r.status_code in (200, 204)
    assert (await client.get(f"/api/v1/keys/{created['id']}", headers=auth_headers)).status_code == 404


async def test_key_isolated_per_user(client: AsyncClient, auth_headers: dict, other_auth_headers: dict):
    pid = await _provider_id(client, auth_headers)
    created = await _create(client, auth_headers, pid)
    assert (await client.get(f"/api/v1/keys/{created['id']}", headers=other_auth_headers)).status_code == 404
