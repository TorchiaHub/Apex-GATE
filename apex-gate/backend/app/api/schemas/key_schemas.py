"""Pydantic schemas for API key endpoints."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ApiKeyBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    tier: str = Field(default="free", pattern="^(free|paid)$")
    priority: int = Field(default=10, ge=1, le=99)
    rate_limit_rpm: int | None = Field(default=None, ge=0)
    rate_limit_rpd: int | None = Field(default=None, ge=0)
    budget_daily_usd: Decimal | None = Field(default=None, ge=0)
    budget_monthly_usd: Decimal | None = Field(default=None, ge=0)


class ApiKeyCreate(ApiKeyBase):
    provider_id: str
    api_key_plaintext: str = Field(..., min_length=1)


class ApiKeyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    priority: int | None = Field(default=None, ge=1, le=99)
    is_enabled: bool | None = None
    rate_limit_rpm: int | None = Field(default=None, ge=0)
    rate_limit_rpd: int | None = Field(default=None, ge=0)
    budget_daily_usd: Decimal | None = Field(default=None, ge=0)
    budget_monthly_usd: Decimal | None = Field(default=None, ge=0)
    tier: str | None = Field(default=None, pattern="^(free|paid)$")


class ApiKeyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    provider_id: str
    provider_name: str
    provider_slug: str
    tier: str
    priority: int
    is_enabled: bool
    rate_limit_rpm: int | None
    rate_limit_rpd: int | None
    budget_daily_usd: Decimal | None
    budget_monthly_usd: Decimal | None
    key_masked: str
    status: str  # 'active' | 'exhausted' | 'disabled'
    created_at: datetime


class ApiKeyTestResult(BaseModel):
    ok: bool
    error: str | None = None
    latency_ms: int | None = None
