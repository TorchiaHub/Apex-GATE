"""Pydantic schemas for model catalog endpoints."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ModelCatalogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    provider_id: str
    provider_slug: str
    model_id: str
    display_name: str
    tier: str
    is_default: bool
    is_active: bool
    is_enabled: bool
    supports_vision: bool
    supports_tools: bool
    supports_streaming: bool
    context_window: int | None
    cost_input_per_1m_usd: Decimal | None
    cost_output_per_1m_usd: Decimal | None
    last_discovered_at: datetime


class ModelUpdate(BaseModel):
    """Partial update for user curation of a catalog model."""

    is_enabled: bool | None = None
    is_default: bool | None = None
