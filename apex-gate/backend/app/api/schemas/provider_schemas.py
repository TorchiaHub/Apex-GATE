"""Pydantic schemas for provider endpoints."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ProviderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    slug: str
    name: str
    protocol: str
    supports_free_tier: bool
    is_active: bool
    key_count: int
    sort_order: int
    logo_url: str | None = None
    litellm_prefix: str | None = None


class ProviderDetailResponse(ProviderResponse):
    api_base_url: str | None


class ProviderCreate(BaseModel):
    name: str
    api_base_url: str
    protocol: str = "openai"
    supports_free_tier: bool = False
