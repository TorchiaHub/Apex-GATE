from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.discovery.base import AbstractScraper, ModelData
from app.discovery.gemini import GeminiScraper
from app.discovery.groq import GroqScraper
from app.discovery.nvidia import NvidiaScraper
from app.discovery.openrouter import OpenRouterScraper
from app.models.model_catalog import ModelCatalog
from app.models.provider import Provider

_SCRAPERS: list[AbstractScraper] = [
    NvidiaScraper(),
    OpenRouterScraper(),
    GroqScraper(),
    GeminiScraper(),
]


async def run_discovery(db: AsyncSession) -> None:
    for scraper in _SCRAPERS:
        prov = await db.scalar(select(Provider).where(Provider.slug == scraper.provider_slug))
        if not prov:
            continue
        try:
            models = await scraper.fetch_models()
        except Exception:
            continue

        discovered_ids: set[str] = set()
        for md in models:
            if not md.model_id:
                continue
            discovered_ids.add(md.model_id)
            existing = await db.scalar(
                select(ModelCatalog).where(
                    ModelCatalog.provider_id == prov.id,
                    ModelCatalog.model_id == md.model_id,
                )
            )
            if existing:
                _update_catalog(existing, md)
            else:
                db.add(_to_catalog(md, prov.id))

        await _deactivate_missing(prov.id, discovered_ids, db)
        await db.commit()


def _to_catalog(md: ModelData, provider_id: str) -> ModelCatalog:
    return ModelCatalog(
        provider_id=provider_id,
        model_id=md.model_id,
        display_name=md.display_name,
        context_window=md.context_window,
        tier=md.tier,
        cost_input_per_1m_usd=md.cost_input_per_1m_usd,
        cost_output_per_1m_usd=md.cost_output_per_1m_usd,
        supports_vision=md.supports_vision,
        supports_tools=md.supports_tools,
        supports_streaming=md.supports_streaming,
        is_active=True,
        last_discovered_at=datetime.now(timezone.utc),
    )


def _update_catalog(existing: ModelCatalog, md: ModelData) -> None:
    existing.display_name = md.display_name
    existing.context_window = md.context_window
    existing.tier = md.tier
    existing.cost_input_per_1m_usd = md.cost_input_per_1m_usd
    existing.cost_output_per_1m_usd = md.cost_output_per_1m_usd
    existing.supports_vision = md.supports_vision
    existing.supports_tools = md.supports_tools
    existing.supports_streaming = md.supports_streaming
    existing.is_active = True
    existing.last_discovered_at = datetime.now(timezone.utc)


async def _deactivate_missing(provider_id: str, discovered_ids: set[str], db: AsyncSession) -> None:
    result = await db.execute(
        select(ModelCatalog).where(
            ModelCatalog.provider_id == provider_id,
            ModelCatalog.is_active == True,  # noqa: E712
        )
    )
    for mc in result.scalars().all():
        if mc.model_id not in discovered_ids:
            mc.is_active = False
