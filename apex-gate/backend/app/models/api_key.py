from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, _now, _uuid

if TYPE_CHECKING:
    from app.models.provider import Provider
    from app.models.exhaustion_state import ExhaustionState
    from app.models.request_log import RequestLog


class ApiKey(Base):
    """An encrypted LLM provider API key belonging to a user."""

    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    # Cross-DB reference — no FK constraint (user lives in Auth DB)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    provider_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("providers.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    key_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    # Allowed values: free | paid
    tier: Mapped[str] = mapped_column(String(10), default="free", nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    rate_limit_rpm: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    rate_limit_rpd: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    budget_daily_usd: Mapped[Optional[object]] = mapped_column(Numeric(10, 4), nullable=True)
    budget_monthly_usd: Mapped[Optional[object]] = mapped_column(Numeric(10, 4), nullable=True)
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False
    )

    __table_args__ = (
        Index("ix_api_keys_user_id", "user_id"),
        Index("ix_api_keys_provider_id", "provider_id"),
        Index("ix_api_keys_user_id_priority", "user_id", "priority"),
    )

    # Relationships
    provider: Mapped["Provider"] = relationship("Provider", back_populates="api_keys")
    exhaustion_state: Mapped[Optional["ExhaustionState"]] = relationship(
        "ExhaustionState", back_populates="api_key", uselist=False, passive_deletes=True
    )
    request_logs: Mapped[List["RequestLog"]] = relationship(
        "RequestLog", back_populates="api_key", passive_deletes=True
    )

    def __repr__(self) -> str:
        return (
            f"<ApiKey id={self.id!r} user_id={self.user_id!r} "
            f"provider_id={self.provider_id!r} tier={self.tier!r}>"
        )
