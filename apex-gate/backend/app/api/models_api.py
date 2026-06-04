from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.schemas.model_schemas import ModelCatalogResponse, ModelUpdate
from app.auth.deps import get_current_user
from app.auth.models import User
from app.database import get_session
from app.models.model_catalog import ModelCatalog
from app.models.provider import Provider

router = APIRouter(prefix="/api/v1/models", tags=["models"])


@router.get("/defaults", response_model=dict[str, ModelCatalogResponse])
async def get_default_models(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> dict:
    """Return the single default model per provider, keyed by provider slug.

    Only active defaults are included. Useful for the frontend to show which
    model is used in AUTO routing mode for each provider.
    """
    query = (
        select(ModelCatalog, Provider)
        .join(Provider, ModelCatalog.provider_id == Provider.id)
        .where(ModelCatalog.is_default == True)  # noqa: E712
        .where(ModelCatalog.is_active == True)   # noqa: E712
        .order_by(Provider.sort_order)
    )
    result = await db.execute(query)
    return {p.slug: _to_response_dict(m, p.slug) for m, p in result.all()}


@router.get("/", response_model=list[ModelCatalogResponse])
async def list_models(
    provider: str | None = Query(default=None),
    tier: str | None = Query(default=None, pattern="^(free|paid)$"),
    is_default: bool | None = Query(default=None),
    is_active: bool | None = Query(default=True),
    enabled: bool | None = Query(default=None),
    vision: bool | None = Query(default=None),
    tools: bool | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> list[dict]:
    query = (
        select(ModelCatalog, Provider)
        .join(Provider, ModelCatalog.provider_id == Provider.id)
    )
    if provider:
        query = query.where(Provider.slug == provider)
    if tier:
        query = query.where(ModelCatalog.tier == tier)
    if is_default is not None:
        query = query.where(ModelCatalog.is_default == is_default)
    if is_active is not None:
        query = query.where(ModelCatalog.is_active == is_active)
    if enabled is not None:
        query = query.where(ModelCatalog.is_enabled == enabled)
    if vision is not None:
        query = query.where(ModelCatalog.supports_vision == vision)
    if tools is not None:
        query = query.where(ModelCatalog.supports_tools == tools)

    result = await db.execute(query.order_by(Provider.sort_order, ModelCatalog.model_id))
    return [_to_response_dict(m, p.slug) for m, p in result.all()]


@router.post("/refresh")
async def refresh_models(
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> dict:
    async def _run_discovery() -> None:
        from app.database import AsyncSessionLocal
        from app.discovery.service import run_discovery

        async with AsyncSessionLocal() as session:
            await run_discovery(session)

    background_tasks.add_task(_run_discovery)
    return {"message": "Discovery started", "status": "queued"}


@router.patch("/{model_id}", response_model=ModelCatalogResponse)
async def update_model(
    model_id: str,
    body: ModelUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> dict:
    """Curate a catalog model: enable/disable it or set it as provider default.

    ``is_enabled`` controls whether the model is selectable and usable through
    the proxy. Setting ``is_default=True`` clears the default flag on the
    provider's other models so each provider has at most one default.
    """
    row = await db.execute(
        select(ModelCatalog, Provider)
        .join(Provider, ModelCatalog.provider_id == Provider.id)
        .where(ModelCatalog.id == model_id)
    )
    pair = row.first()
    if pair is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "model_not_found", "message": "Model not found"},
        )
    model, provider = pair

    if body.is_enabled is not None:
        model.is_enabled = body.is_enabled
    if body.is_default is not None:
        if body.is_default:
            # Enforce a single default per provider.
            others = await db.execute(
                select(ModelCatalog).where(
                    ModelCatalog.provider_id == model.provider_id,
                    ModelCatalog.id != model.id,
                    ModelCatalog.is_default == True,  # noqa: E712
                )
            )
            for other in others.scalars().all():
                other.is_default = False
        model.is_default = body.is_default

    await db.commit()
    await db.refresh(model)
    return _to_response_dict(model, provider.slug)


def _to_response_dict(m: ModelCatalog, provider_slug: str) -> dict:
    return {
        "id": m.id,
        "provider_id": m.provider_id,
        "provider_slug": provider_slug,
        "model_id": m.model_id,
        "display_name": m.display_name,
        "tier": m.tier,
        "is_default": m.is_default,
        "is_active": m.is_active,
        "is_enabled": m.is_enabled,
        "supports_vision": m.supports_vision,
        "supports_tools": m.supports_tools,
        "supports_streaming": m.supports_streaming,
        "context_window": m.context_window,
        "cost_input_per_1m_usd": m.cost_input_per_1m_usd,
        "cost_output_per_1m_usd": m.cost_output_per_1m_usd,
        "last_discovered_at": m.last_discovered_at,
    }
