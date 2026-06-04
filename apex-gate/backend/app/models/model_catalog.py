from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, _now, _uuid

if TYPE_CHECKING:
    from app.models.provider import Provider


class ModelCatalog(Base):
    __tablename__ = "model_catalog"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    provider_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("providers.id", ondelete="CASCADE"), nullable=False
    )
    model_id: Mapped[str] = mapped_column(String(200), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    context_window: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Allowed values: free | paid
    tier: Mapped[str] = mapped_column(String(10), default="free", nullable=False)
    cost_input_per_1m_usd: Mapped[object | None] = mapped_column(Numeric(10, 6), nullable=True)
    cost_output_per_1m_usd: Mapped[object | None] = mapped_column(Numeric(10, 6), nullable=True)
    supports_vision: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    supports_tools: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    supports_streaming: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # is_active: model still exists at the provider (set by discovery).
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # is_enabled: user curation — whether this model is selectable/usable.
    # Discovery never overwrites this, so the user's choice persists across refreshes.
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_discovered_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )

    __table_args__ = (
        UniqueConstraint("provider_id", "model_id", name="uq_model_catalog_provider_model"),
        Index("idx_model_catalog_provider", "provider_id"),
        Index("idx_model_catalog_tier", "tier"),
        Index("idx_model_catalog_active", "is_active"),
        Index("ix_model_catalog_default", "provider_id", "is_default"),
    )

    provider: Mapped["Provider"] = relationship(
        "Provider", back_populates="model_catalog_entries"
    )

    def __repr__(self) -> str:
        return (
            f"<ModelCatalog id={self.id!r} model_id={self.model_id!r} "
            f"tier={self.tier!r} is_active={self.is_active!r}>"
        )
