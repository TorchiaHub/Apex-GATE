from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.key_schemas import ApiKeyCreate, ApiKeyResponse, ApiKeyTestResult, ApiKeyUpdate
from app.auth.deps import get_current_user
from app.auth.models import User
from app.crypto import decrypt_key, encrypt_key, mask_key
from app.database import get_session
from app.models.api_key import ApiKey
from app.models.exhaustion_state import ExhaustionState
from app.models.provider import Provider

router = APIRouter(prefix="/api/v1/keys", tags=["keys"])


def _build_response(ak: ApiKey, provider: Provider, exhaustion: ExhaustionState | None) -> dict:
    now = datetime.now(timezone.utc)
    if not ak.is_enabled:
        status_str = "disabled"
    elif exhaustion and exhaustion.exhausted_until > now:
        status_str = "exhausted"
    else:
        status_str = "active"

    plaintext = decrypt_key(ak.key_encrypted)
    return {
        "id": ak.id,
        "name": ak.name,
        "provider_id": ak.provider_id,
        "provider_name": provider.name,
        "provider_slug": provider.slug,
        "tier": ak.tier,
        "priority": ak.priority,
        "is_enabled": ak.is_enabled,
        "rate_limit_rpm": ak.rate_limit_rpm,
        "rate_limit_rpd": ak.rate_limit_rpd,
        "budget_daily_usd": ak.budget_daily_usd,
        "budget_monthly_usd": ak.budget_monthly_usd,
        "key_masked": mask_key(plaintext),
        "status": status_str,
        "created_at": ak.created_at,
    }


@router.get("/", response_model=list[ApiKeyResponse])
async def list_keys(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> list[dict]:
    result = await db.execute(
        select(ApiKey, Provider, ExhaustionState)
        .join(Provider, ApiKey.provider_id == Provider.id)
        .outerjoin(ExhaustionState, ApiKey.id == ExhaustionState.api_key_id)
        .where(ApiKey.user_id == user.id)
        .order_by(ApiKey.priority.asc())
    )
    return [_build_response(ak, prov, ex) for ak, prov, ex in result.all()]


@router.post("/", response_model=ApiKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_key(
    body: ApiKeyCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> dict:
    provider = await db.scalar(select(Provider).where(Provider.id == body.provider_id))
    if not provider:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")

    ak = ApiKey(
        user_id=user.id,
        provider_id=body.provider_id,
        name=body.name,
        key_encrypted=encrypt_key(body.api_key_plaintext),
        tier=body.tier,
        priority=body.priority,
        rate_limit_rpm=body.rate_limit_rpm,
        rate_limit_rpd=body.rate_limit_rpd,
        budget_daily_usd=body.budget_daily_usd,
        budget_monthly_usd=body.budget_monthly_usd,
    )
    db.add(ak)
    await db.commit()
    await db.refresh(ak)
    return _build_response(ak, provider, None)


@router.get("/{key_id}", response_model=ApiKeyResponse)
async def get_key(
    key_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> dict:
    result = await db.execute(
        select(ApiKey, Provider, ExhaustionState)
        .join(Provider, ApiKey.provider_id == Provider.id)
        .outerjoin(ExhaustionState, ApiKey.id == ExhaustionState.api_key_id)
        .where(ApiKey.id == key_id, ApiKey.user_id == user.id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key not found")
    return _build_response(*row)


@router.patch("/{key_id}", response_model=ApiKeyResponse)
async def update_key(
    key_id: str,
    body: ApiKeyUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> dict:
    result = await db.execute(
        select(ApiKey, Provider, ExhaustionState)
        .join(Provider, ApiKey.provider_id == Provider.id)
        .outerjoin(ExhaustionState, ApiKey.id == ExhaustionState.api_key_id)
        .where(ApiKey.id == key_id, ApiKey.user_id == user.id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key not found")
    ak, provider, ex = row

    for field in body.model_fields_set:
        setattr(ak, field, getattr(body, field))
    await db.commit()
    await db.refresh(ak)
    return _build_response(ak, provider, ex)


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_key(
    key_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> None:
    ak = await db.scalar(select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == user.id))
    if not ak:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key not found")
    await db.delete(ak)
    await db.commit()


@router.post("/{key_id}/test", response_model=ApiKeyTestResult)
async def test_key(
    key_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> ApiKeyTestResult:
    import time
    import litellm

    ak = await db.scalar(select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == user.id))
    if not ak:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key not found")
    provider = await db.scalar(select(Provider).where(Provider.id == ak.provider_id))

    from app.proxy.providers.registry import PROVIDER_REGISTRY
    prov = PROVIDER_REGISTRY.get(provider.slug if provider else "")
    if not prov:
        return ApiKeyTestResult(ok=False, error="Provider not supported for test")

    plaintext = decrypt_key(ak.key_encrypted)
    params = prov.get_litellm_params(plaintext, "gpt-4o-mini" if provider and provider.slug == "openai" else "auto")
    params["messages"] = [{"role": "user", "content": "Hi"}]
    params["max_tokens"] = 1

    import litellm.exceptions

    t0 = time.monotonic()
    try:
        await litellm.acompletion(**params)
        latency_ms = int((time.monotonic() - t0) * 1000)
        return ApiKeyTestResult(ok=True, latency_ms=latency_ms)
    except litellm.exceptions.AuthenticationError:
        return ApiKeyTestResult(ok=False, error="Authentication failed — check the key value")
    except litellm.exceptions.RateLimitError:
        return ApiKeyTestResult(ok=False, error="Rate limit exceeded")
    except Exception:
        return ApiKeyTestResult(ok=False, error="Connection test failed")
