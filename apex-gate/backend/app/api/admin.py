from __future__ import annotations

from pydantic import BaseModel, EmailStr

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import require_admin
from app.auth.models import User
from app.auth.service import hash_password
from app.auth.database import get_auth_session
from app.database import get_session
from app.models.exhaustion_state import ExhaustionState

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


class AdminUserUpdate(BaseModel):
    is_active: bool | None = None
    is_admin: bool | None = None
    email: EmailStr | None = None
    password: str | None = None


def _user_dict(u: User) -> dict:
    return {
        "id": u.id, "username": u.username, "email": u.email,
        "is_admin": u.is_admin, "is_active": u.is_active, "created_at": u.created_at,
    }


@router.get("/users")
async def list_users(
    _: User = Depends(require_admin),
    auth_db: AsyncSession = Depends(get_auth_session),
) -> list[dict]:
    result = await auth_db.execute(select(User).order_by(User.created_at))
    return [_user_dict(u) for u in result.scalars().all()]


@router.get("/users/{user_id}")
async def get_user(
    user_id: str,
    _: User = Depends(require_admin),
    auth_db: AsyncSession = Depends(get_auth_session),
) -> dict:
    u = await auth_db.scalar(select(User).where(User.id == user_id))
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return _user_dict(u)


@router.patch("/users/{user_id}")
async def update_user(
    user_id: str,
    body: AdminUserUpdate,
    admin: User = Depends(require_admin),
    auth_db: AsyncSession = Depends(get_auth_session),
) -> dict:
    u = await auth_db.scalar(select(User).where(User.id == user_id))
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if body.is_active is not None:
        u.is_active = body.is_active
    if body.is_admin is not None:
        u.is_admin = body.is_admin
    if body.email is not None:
        u.email = body.email
    if body.password is not None:
        u.hashed_password = hash_password(body.password)

    await auth_db.commit()
    await auth_db.refresh(u)
    return _user_dict(u)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_user(
    user_id: str,
    admin: User = Depends(require_admin),
    auth_db: AsyncSession = Depends(get_auth_session),
) -> None:
    if admin.id == user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete yourself")
    u = await auth_db.scalar(select(User).where(User.id == user_id))
    if not u:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    await auth_db.delete(u)
    await auth_db.commit()


@router.post("/reset-exhaustions", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def reset_all_exhaustions(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
) -> None:
    await db.execute(delete(ExhaustionState))
    await db.commit()
