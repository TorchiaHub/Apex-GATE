#!/usr/bin/env python3
"""Interactive CLI script to create the first admin user."""
from __future__ import annotations

import asyncio
import sys


async def create_admin() -> None:
    from app.auth.database import AuthSessionLocal, init_auth_db
    from app.auth.models import User
    from app.auth.service import hash_password

    await init_auth_db()

    from sqlalchemy import select

    print("=== APEX GATE — Create Admin User ===")
    username = input("Username: ").strip()
    email = input("Email: ").strip()
    password = input("Password: ").strip()

    if not username or not email or not password:
        print("Error: all fields required.", file=sys.stderr)
        sys.exit(1)

    async with AuthSessionLocal() as db:
        result = await db.execute(select(User).where((User.username == username) | (User.email == email)))
        if result.scalar_one_or_none() is not None:
            print("Error: username or email already exists.", file=sys.stderr)
            sys.exit(1)

        user = User(username=username, email=email, hashed_password=hash_password(password), is_admin=True, is_active=True)
        db.add(user)
        await db.commit()
        await db.refresh(user)

    print(f"Admin created: {user.username} ({user.id})")


if __name__ == "__main__":
    asyncio.run(create_admin())
