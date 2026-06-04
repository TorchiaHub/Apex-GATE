#!/usr/bin/env python3
"""Print SECRET_KEY and FERNET_KEY values ready to paste into .env."""
import secrets
from cryptography.fernet import Fernet

print(f"SECRET_KEY={secrets.token_hex(32)}")
print(f"FERNET_KEY={Fernet.generate_key().decode()}")
