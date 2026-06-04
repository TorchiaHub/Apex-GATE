"""Pydantic schemas for virtual key endpoints."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class KeyAssignment(BaseModel):
    api_key_id: str
    priority: int = Field(default=10, ge=1, le=99)


class VirtualKeyBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    daily_token_budget: int | None = Field(default=None, ge=0)
    assignments: list[KeyAssignment] = Field(default_factory=list)
    is_enabled: bool = True
    model_preference: str | None = None
    memory_mode: Literal["off", "optional", "always"] = "off"
    memory_max_messages: int = Field(default=50, ge=1, le=500)
    memory_max_context_tokens: int = Field(default=8000, ge=256, le=200000)
    memory_ttl_hours: int = Field(default=720, ge=1, le=8760)


class VirtualKeyCreate(VirtualKeyBase):
    pass


class VirtualKeyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    daily_token_budget: int | None = Field(default=None, ge=0)
    assignments: list[KeyAssignment] | None = None
    is_enabled: bool | None = None
    model_preference: str | None = None
    memory_mode: Literal["off", "optional", "always"] | None = None
    memory_max_messages: int | None = Field(default=None, ge=1, le=500)
    memory_max_context_tokens: int | None = Field(default=None, ge=256, le=200000)
    memory_ttl_hours: int | None = Field(default=None, ge=1, le=8760)


class VirtualKeyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    key_prefix: str
    daily_token_budget: int | None
    is_enabled: bool
    model_preference: str | None = None
    memory_mode: str = "off"
    memory_max_messages: int = 50
    memory_max_context_tokens: int = 8000
    memory_ttl_hours: int = 720
    created_at: datetime
    assignments: list[dict] = []


class VirtualKeyCreateResponse(VirtualKeyResponse):
    key_plaintext: str
