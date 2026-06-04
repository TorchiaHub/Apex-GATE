from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, _now, _uuid

if TYPE_CHECKING:
    from app.models.api_key import ApiKey
    from app.models.model_catalog import ModelCatalog


class Provider(Base):
    """LLM provider configuration (OpenAI, Anthropic, Gemini, Ollama, Cohere, …)."""

    __tablename__ = "providers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # Allowed values: openai | anthropic | gemini | ollama | cohere
    protocol: Mapped[str] = mapped_column(String(20), nullable=False)
    api_base_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    supports_free_tier: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    litellm_prefix: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=99, nullable=False)
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )

    # Relationships
    api_keys: Mapped[List["ApiKey"]] = relationship(
        "ApiKey", back_populates="provider", passive_deletes=True
    )
    model_catalog_entries: Mapped[List["ModelCatalog"]] = relationship(
        "ModelCatalog", back_populates="provider", passive_deletes=True
    )

    def __repr__(self) -> str:
        return f"<Provider id={self.id!r} slug={self.slug!r} protocol={self.protocol!r}>"
