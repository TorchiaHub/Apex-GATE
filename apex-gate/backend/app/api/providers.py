from __future__ import annotations

import re
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.provider_schemas import ProviderCreate, ProviderDetailResponse, ProviderResponse
from app.auth.deps import get_current_user
from app.auth.models import User
from app.database import get_session
from app.models.api_key import ApiKey
from app.models.model_catalog import ModelCatalog
from app.models.provider import Provider

router = APIRouter(prefix="/api/v1/providers", tags=["providers"])


@router.get("/", response_model=list[ProviderResponse])
async def list_providers(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_session)) -> list[dict]:
    result = await db.execute(select(Provider).where(Provider.is_active == True).order_by(Provider.sort_order))  # noqa: E712
    providers = result.scalars().all()

    counts_result = await db.execute(
        select(ApiKey.provider_id, func.count(ApiKey.id)).where(ApiKey.user_id == user.id).group_by(ApiKey.provider_id)
    )
    counts = {row[0]: row[1] for row in counts_result.all()}

    return [{"id": p.id, "slug": p.slug, "name": p.name, "protocol": p.protocol,
             "supports_free_tier": p.supports_free_tier, "is_active": p.is_active,
             "key_count": counts.get(p.id, 0),
             "sort_order": p.sort_order, "logo_url": p.logo_url,
             "litellm_prefix": p.litellm_prefix} for p in providers]


@router.post("/", response_model=ProviderDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_provider(
    body: ProviderCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> dict:
    # auto-generate slug: sanitize name + short uuid suffix to avoid collisions
    base_slug = re.sub(r"[^a-z0-9]+", "_", body.name.lower()).strip("_")
    slug = f"custom_{base_slug}_{str(uuid.uuid4())[:8]}"

    p = Provider(
        slug=slug,
        name=body.name,
        protocol=body.protocol,
        api_base_url=body.api_base_url,
        supports_free_tier=body.supports_free_tier,
        litellm_prefix="openai/",
        is_active=True,
        sort_order=99,
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return {
        "id": p.id, "slug": p.slug, "name": p.name, "protocol": p.protocol,
        "supports_free_tier": p.supports_free_tier, "key_count": 0,
        "sort_order": p.sort_order, "logo_url": p.logo_url,
        "api_base_url": p.api_base_url, "litellm_prefix": p.litellm_prefix,
        "is_active": p.is_active,
    }


@router.get("/{slug}", response_model=ProviderDetailResponse)
async def get_provider(slug: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_session)) -> dict:
    p = await db.scalar(select(Provider).where(Provider.slug == slug))
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")

    count = await db.scalar(select(func.count(ApiKey.id)).where(ApiKey.provider_id == p.id, ApiKey.user_id == user.id))
    return {"id": p.id, "slug": p.slug, "name": p.name, "protocol": p.protocol,
            "supports_free_tier": p.supports_free_tier, "key_count": count or 0,
            "sort_order": p.sort_order, "logo_url": p.logo_url,
            "api_base_url": p.api_base_url, "litellm_prefix": p.litellm_prefix, "is_active": p.is_active}


@router.get("/{slug}/models")
async def get_provider_models(slug: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_session)) -> list[dict]:
    p = await db.scalar(select(Provider).where(Provider.slug == slug))
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider not found")

    result = await db.execute(select(ModelCatalog).where(ModelCatalog.provider_id == p.id).order_by(ModelCatalog.model_id))
    return [{"id": m.id, "model_id": m.model_id, "display_name": m.display_name, "tier": m.tier,
             "context_window": m.context_window, "is_active": m.is_active} for m in result.scalars().all()]
