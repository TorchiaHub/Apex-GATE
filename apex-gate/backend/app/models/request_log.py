from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, _now, _uuid

if TYPE_CHECKING:
    from app.models.virtual_key import VirtualKey
    from app.models.api_key import ApiKey


class RequestLog(Base):
    __tablename__ = "request_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    virtual_key_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("virtual_keys.id", ondelete="SET NULL"), nullable=True
    )
    api_key_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("api_keys.id", ondelete="SET NULL"), nullable=True
    )
    model_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cost_usd: Mapped[object] = mapped_column(Numeric(10, 6), default=0, nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Allowed values: success | rate_limited | budget_exceeded | error | all_exhausted
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Allowed values: openai | anthropic | gemini | ollama | cohere
    protocol: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )

    __table_args__ = (
        Index("idx_request_logs_user_id", "user_id"),
        Index("idx_request_logs_created", "created_at"),
        Index("idx_request_logs_vk", "virtual_key_id"),
        Index("idx_request_logs_api_key", "api_key_id"),
        Index("idx_request_logs_status", "status"),
    )

    virtual_key: Mapped[Optional["VirtualKey"]] = relationship(
        "VirtualKey", back_populates="request_logs"
    )
    api_key: Mapped[Optional["ApiKey"]] = relationship(
        "ApiKey", back_populates="request_logs"
    )

    def __repr__(self) -> str:
        return (
            f"<RequestLog id={self.id!r} user_id={self.user_id!r} "
            f"status={self.status!r} cost_usd={self.cost_usd!r}>"
        )
