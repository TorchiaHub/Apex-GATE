from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, _now, _uuid

if TYPE_CHECKING:
    from app.models.api_key import ApiKey


class ExhaustionState(Base):
    __tablename__ = "exhaustion_state"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    api_key_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("api_keys.id", ondelete="CASCADE"), nullable=False
    )
    exhausted_until: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    # Allowed values: rate_limit | budget_daily | budget_monthly | error_429 | auth_error
    reason: Mapped[str] = mapped_column(String(30), nullable=False)
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )

    __table_args__ = (
        UniqueConstraint("api_key_id", name="uq_exhaustion_state_api_key_id"),
        Index("idx_exhaustion_until", "exhausted_until"),
    )

    api_key: Mapped["ApiKey"] = relationship(
        "ApiKey", back_populates="exhaustion_state"
    )

    def __repr__(self) -> str:
        return (
            f"<ExhaustionState id={self.id!r} api_key_id={self.api_key_id!r} "
            f"reason={self.reason!r} exhausted_until={self.exhausted_until!r}>"
        )
