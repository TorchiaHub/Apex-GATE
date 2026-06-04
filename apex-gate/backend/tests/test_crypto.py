"""Unit tests for app/crypto.py."""
from __future__ import annotations

import hashlib
import os

import pytest

os.environ.setdefault("SECRET_KEY", "test-secret-key-min-32-chars-here-ok!")


@pytest.fixture(autouse=True)
def set_fernet_env(monkeypatch):
    from cryptography.fernet import Fernet
    monkeypatch.setenv("FERNET_KEY", Fernet.generate_key().decode())
    import importlib
    import app.crypto as m
    importlib.reload(m)


def _c():
    import app.crypto as m
    return m


def test_encrypt_decrypt_roundtrip():
    c = _c()
    pt = "sk-test-key-12345678"
    assert c.decrypt_key(c.encrypt_key(pt)) == pt


def test_encrypt_differs_each_call():
    c = _c()
    pt = "sk-test-key"
    assert c.encrypt_key(pt) != c.encrypt_key(pt)


def test_mask_key_standard():
    masked = _c().mask_key("sk-abc123xyz789")
    assert "..." in masked
    assert masked.startswith("sk-a")
    assert masked.endswith("789")


def test_mask_key_short():
    assert _c().mask_key("abc") == "***"


def test_generate_virtual_key_format():
    pt, digest = _c().generate_virtual_key()
    assert pt.startswith("apg-")
    assert len(digest) == 64


def test_generate_virtual_key_unique():
    c = _c()
    k1, _ = c.generate_virtual_key()
    k2, _ = c.generate_virtual_key()
    assert k1 != k2


def test_sha256_deterministic():
    c = _c()
    assert c.sha256_hash("test") == c.sha256_hash("test")
    assert c.sha256_hash("test") != c.sha256_hash("other")


def test_virtual_key_hash_matches():
    c = _c()
    pt, digest = c.generate_virtual_key()
    assert digest == hashlib.sha256(pt.encode()).hexdigest()
