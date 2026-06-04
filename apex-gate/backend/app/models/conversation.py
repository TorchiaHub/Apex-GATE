from __future__ import annotations

from typing import TYPE_CHECKING, List

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base, _now, _uuid

if TYPE_CHECKING:
    from app.models.virtual_key import VirtualKey


class Conversation(Base):
    """A server-side conversation thread scoped to a single virtual key.

    Conversations are opt-in: they exist only when a request carries an
    ``X-Conversation-Id`` header (or when the virtual key uses memory_mode
    ``always``). They are bounded by a sliding window and expire via ``expires_at``.
    """

    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    virtual_key_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("virtual_keys.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    message_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )
    updated_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False
    )
    expires_at: Mapped[object | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        Index("idx_conversations_vk_id", "virtual_key_id"),
        Index("idx_conversations_user_id", "user_id"),
        Index("idx_conversations_expires_at", "expires_at"),
    )

    messages: Mapped[List["ConversationMessage"]] = relationship(
        "ConversationMessage",
        back_populates="conversation",
        passive_deletes=True,
        order_by="ConversationMessage.created_at",
    )

    def __repr__(self) -> str:
        return (
            f"<Conversation id={self.id!r} virtual_key_id={self.virtual_key_id!r} "
            f"message_count={self.message_count!r}>"
        )


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    conversation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    # Only "user" and "assistant" turns are stored; system prompts stay client-side.
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), default=_now, nullable=False
    )

    __table_args__ = (
        Index("idx_conversation_messages_conv_id", "conversation_id"),
    )

    conversation: Mapped["Conversation"] = relationship(
        "Conversation", back_populates="messages"
    )

    def __repr__(self) -> str:
        return (
            f"<ConversationMessage id={self.id!r} "
            f"conversation_id={self.conversation_id!r} role={self.role!r}>"
        )
