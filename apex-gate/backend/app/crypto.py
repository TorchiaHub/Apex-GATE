from __future__ import annotations

import hashlib
import secrets

from cryptography.fernet import Fernet

from app.config import settings


_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        _fernet = Fernet(settings.FERNET_KEY.encode())
    return _fernet


def encrypt_key(plaintext: str) -> str:
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_key(ciphertext: str) -> str:
    return _get_fernet().decrypt(ciphertext.encode()).decode()


def mask_key(plaintext: str) -> str:
    if len(plaintext) <= 8:
        return "***"
    return plaintext[:4] + "..." + plaintext[-4:]


def generate_virtual_key() -> tuple[str, str]:
    raw = secrets.token_urlsafe(32)
    plaintext = f"apg-{raw}"
    digest = sha256_hash(plaintext)
    return plaintext, digest


def sha256_hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()
