from __future__ import annotations

from typing import TYPE_CHECKING, List

from sqlalchemy import Boolean, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, _now, _uuid

if TYPE_CHECKING:
    from app.models.request_log import RequestLog


class VirtualKey(Base):
    __tablename__ = "virtual_keys"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(20), nullable=False)
    daily_token_budget: Mapped[int | None] = mapped_column(Integer, nullable=True)
    allowed_providers: Mapped[str | None] = mapped_column(Text, nullable=True)
    model_preference: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Conversation memory. Off by default: a request stays stateless unless the
    # key opts in. Allowed values: off | optional | always.
    memory_mode: Mapped[str] = mapped_column(
        String(10), default="off", server_default="off", nullable=False
    )
    # Sliding-window limits applied whenever memory is active.
    memory_max_messages: Mapped[int] = mapped_column(
        Integer, default=50, server_default="50", nullable=False
    )
    memory_max_context_tokens: Mapped[int] = mapped_column(
        Integer, default=8000, server_default="8000", nullable=False
    )
    memory_ttl_hours: Mapped[int] = mapped_column(
        Integer, default=720, server_default="720", nullable=False
    )
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )

    __table_args__ = (
        Index("idx_virtual_keys_user_id", "user_id"),
        Index("idx_virtual_keys_hash", "key_hash"),
    )

    request_logs: Mapped[List["RequestLog"]] = relationship(
        "RequestLog", back_populates="virtual_key", passive_deletes=True
    )

    def __repr__(self) -> str:
        return (
            f"<VirtualKey id={self.id!r} user_id={self.user_id!r} "
            f"key_prefix={self.key_prefix!r} is_enabled={self.is_enabled!r}>"
        )
