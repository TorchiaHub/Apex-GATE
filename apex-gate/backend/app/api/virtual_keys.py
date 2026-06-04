from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.virtual_key_schemas import (
    VirtualKeyCreate,
    VirtualKeyCreateResponse,
    VirtualKeyResponse,
    VirtualKeyUpdate,
)
from app.auth.deps import get_current_user
from app.auth.models import User
from app.crypto import generate_virtual_key
from app.database import get_session
from app.models.api_key import ApiKey
from app.models.virtual_key import VirtualKey
from app.models.virtual_key_assignment import VirtualKeyAssignment

router = APIRouter(prefix="/api/v1/virtual-keys", tags=["virtual-keys"])


async def _validate_assignment_ownership(
    assignments: list, user_id: str, db: AsyncSession
) -> None:
    """Ensure every referenced api_key_id belongs to the current user."""
    requested_ids = {a.api_key_id for a in assignments}
    if not requested_ids:
        return
    result = await db.execute(
        select(ApiKey.id).where(
            ApiKey.id.in_(requested_ids), ApiKey.user_id == user_id
        )
    )
    owned_ids = {row[0] for row in result.all()}
    missing = requested_ids - owned_ids
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "invalid_api_key_assignment",
                "message": "One or more api_key_id are invalid or not owned by you",
            },
        )


async def _fetch_assignments(vk_id: str, db: AsyncSession) -> list[dict]:
    result = await db.execute(
        select(VirtualKeyAssignment, ApiKey.name)
        .join(ApiKey, ApiKey.id == VirtualKeyAssignment.api_key_id)
        .where(VirtualKeyAssignment.vk_id == vk_id)
        .order_by(VirtualKeyAssignment.priority.asc())
    )
    return [
        {"id": a.id, "api_key_id": a.api_key_id, "priority": a.priority, "key_name": name}
        for a, name in result.all()
    ]


def _vk_to_dict(vk: VirtualKey, assignments: list[dict] | None = None) -> dict:
    return {
        "id": vk.id,
        "name": vk.name,
        "key_prefix": vk.key_prefix,
        "daily_token_budget": vk.daily_token_budget,
        "model_preference": vk.model_preference,
        "is_enabled": vk.is_enabled,
        "memory_mode": vk.memory_mode,
        "memory_max_messages": vk.memory_max_messages,
        "memory_max_context_tokens": vk.memory_max_context_tokens,
        "memory_ttl_hours": vk.memory_ttl_hours,
        "created_at": vk.created_at,
        "assignments": assignments or [],
    }


@router.get("/", response_model=list[VirtualKeyResponse])
async def list_virtual_keys(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> list[dict]:
    result = await db.execute(
        select(VirtualKey)
        .where(VirtualKey.user_id == user.id)
        .order_by(VirtualKey.created_at.desc())
    )
    vks = list(result.scalars().all())
    out = []
    for vk in vks:
        assignments = await _fetch_assignments(vk.id, db)
        out.append(_vk_to_dict(vk, assignments))
    return out


@router.post("/", response_model=VirtualKeyCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_virtual_key(
    body: VirtualKeyCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> dict:
    plaintext, key_hash = generate_virtual_key()
    key_prefix = plaintext[:12]

    await _validate_assignment_ownership(body.assignments, user.id, db)

    vk = VirtualKey(
        user_id=user.id,
        name=body.name,
        key_hash=key_hash,
        key_prefix=key_prefix,
        daily_token_budget=body.daily_token_budget,
        is_enabled=body.is_enabled,
        model_preference=body.model_preference,
        memory_mode=body.memory_mode,
        memory_max_messages=body.memory_max_messages,
        memory_max_context_tokens=body.memory_max_context_tokens,
        memory_ttl_hours=body.memory_ttl_hours,
    )
    db.add(vk)
    await db.flush()

    for assignment in body.assignments:
        db.add(VirtualKeyAssignment(
            vk_id=vk.id,
            api_key_id=assignment.api_key_id,
            priority=assignment.priority,
        ))

    await db.commit()
    await db.refresh(vk)
    assignments = await _fetch_assignments(vk.id, db)
    return {**_vk_to_dict(vk, assignments), "key_plaintext": plaintext}


@router.get("/{vk_id}", response_model=VirtualKeyResponse)
async def get_virtual_key(
    vk_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> dict:
    vk = await db.scalar(select(VirtualKey).where(VirtualKey.id == vk_id, VirtualKey.user_id == user.id))
    if not vk:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Virtual key not found")
    assignments = await _fetch_assignments(vk.id, db)
    return _vk_to_dict(vk, assignments)


@router.patch("/{vk_id}", response_model=VirtualKeyResponse)
async def update_virtual_key(
    vk_id: str,
    body: VirtualKeyUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> dict:
    vk = await db.scalar(select(VirtualKey).where(VirtualKey.id == vk_id, VirtualKey.user_id == user.id))
    if not vk:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Virtual key not found")

    for field in body.model_fields_set:
        val = getattr(body, field)
        if field == "assignments":
            await _validate_assignment_ownership(val or [], user.id, db)
            await db.execute(
                delete(VirtualKeyAssignment).where(VirtualKeyAssignment.vk_id == vk_id)
            )
            for assignment in (val or []):
                db.add(VirtualKeyAssignment(
                    vk_id=vk.id,
                    api_key_id=assignment.api_key_id,
                    priority=assignment.priority,
                ))
        else:
            setattr(vk, field, val)

    await db.commit()
    await db.refresh(vk)
    assignments = await _fetch_assignments(vk.id, db)
    return _vk_to_dict(vk, assignments)


@router.delete("/{vk_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_virtual_key(
    vk_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> None:
    vk = await db.scalar(select(VirtualKey).where(VirtualKey.id == vk_id, VirtualKey.user_id == user.id))
    if not vk:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Virtual key not found")
    await db.execute(delete(VirtualKeyAssignment).where(VirtualKeyAssignment.vk_id == vk_id))
    await db.delete(vk)
    await db.commit()


@router.post("/{vk_id}/rotate", response_model=VirtualKeyCreateResponse)
async def rotate_virtual_key(
    vk_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> dict:
    vk = await db.scalar(select(VirtualKey).where(VirtualKey.id == vk_id, VirtualKey.user_id == user.id))
    if not vk:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Virtual key not found")

    plaintext, key_hash = generate_virtual_key()
    vk.key_hash = key_hash
    vk.key_prefix = plaintext[:12]
    await db.commit()
    await db.refresh(vk)
    assignments = await _fetch_assignments(vk.id, db)
    return {**_vk_to_dict(vk, assignments), "key_plaintext": plaintext}
