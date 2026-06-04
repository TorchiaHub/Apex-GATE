"""Server-side conversation memory.

Opt-in, virtual-key scoped, bounded conversation history. A virtual key declares
its ``memory_mode`` (off | optional | always); a request opts in by sending an
``X-Conversation-Id`` header. When active, the proxy reconstructs prior history
from the database and prepends it to the incoming message(s) before calling the
model (the client only needs to send the latest user turn).

Growth is bounded three ways:
  * sliding window of the last ``memory_max_messages`` stored messages,
  * a ``memory_max_context_tokens`` budget applied at read time,
  * a TTL (``memory_ttl_hours``) after which the conversation expires and is
    cleaned up by the scheduler.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import _now
from app.models.conversation import Conversation, ConversationMessage
from app.models.virtual_key import VirtualKey


def _estimate_tokens(content: Any) -> int:
    """Cheap, dependency-free token estimate (~4 chars/token)."""
    text = content if isinstance(content, str) else json.dumps(content, default=str)
    return max(1, len(text) // 4)


def _content_to_text(content: Any) -> str:
    return content if isinstance(content, str) else json.dumps(content, default=str)


@dataclass
class MemoryDecision:
    active: bool
    conversation_id: str | None


def resolve(vk: VirtualKey, requested_id: str | None) -> MemoryDecision:
    """Decide whether memory applies for this request.

    * ``off``      -> never active, conversation id ignored.
    * ``optional`` -> active only when the client supplies a conversation id.
    * ``always``   -> always active; a missing id is generated server-side.
    """
    mode = getattr(vk, "memory_mode", "off") or "off"
    if mode == "off":
        return MemoryDecision(active=False, conversation_id=None)
    if mode == "optional":
        if requested_id:
            return MemoryDecision(active=True, conversation_id=requested_id)
        return MemoryDecision(active=False, conversation_id=None)
    if mode == "always":
        from app.models import _uuid

        return MemoryDecision(active=True, conversation_id=requested_id or _uuid())
    return MemoryDecision(active=False, conversation_id=None)


async def _get_or_create(
    db: AsyncSession, vk: VirtualKey, conversation_id: str
) -> Conversation:
    conv = await db.get(Conversation, conversation_id)
    if conv is not None:
        # Isolation: a conversation belongs to the virtual key that created it.
        if conv.virtual_key_id != vk.id:
            raise PermissionError("conversation_id does not belong to this virtual key")
        return conv

    ttl_hours = getattr(vk, "memory_ttl_hours", 720) or 720
    conv = Conversation(
        id=conversation_id,
        user_id=vk.user_id,
        virtual_key_id=vk.id,
        expires_at=_now() + timedelta(hours=ttl_hours),
    )
    db.add(conv)
    await db.flush()
    return conv


async def prepare_messages(
    db: AsyncSession,
    vk: VirtualKey,
    conversation_id: str,
    incoming: list[dict],
) -> tuple[list[dict], Conversation]:
    """Load bounded history and merge it with the incoming request messages.

    System messages from the incoming request are preserved at the front; stored
    history (user/assistant turns only) is inserted between them and the new turn.
    """
    conv = await _get_or_create(db, vk, conversation_id)

    max_messages = getattr(vk, "memory_max_messages", 50) or 50
    max_tokens = getattr(vk, "memory_max_context_tokens", 8000) or 8000

    rows = (
        await db.execute(
            select(ConversationMessage)
            .where(ConversationMessage.conversation_id == conv.id)
            .order_by(ConversationMessage.created_at.desc())
            .limit(max_messages)
        )
    ).scalars().all()

    # rows are newest-first; walk backwards in time accumulating a token budget.
    history: list[dict] = []
    budget = 0
    for msg in rows:
        budget += msg.token_count or _estimate_tokens(msg.content)
        if budget > max_tokens and history:
            break
        history.append({"role": msg.role, "content": msg.content})
    history.reverse()  # back to chronological order

    system_msgs = [m for m in incoming if m.get("role") == "system"]
    turn_msgs = [m for m in incoming if m.get("role") != "system"]

    merged = system_msgs + history + turn_msgs
    return merged, conv


async def persist_turn(
    db: AsyncSession,
    vk: VirtualKey,
    conv: Conversation,
    incoming: list[dict],
    assistant_content: Any,
) -> None:
    """Store the new user turn(s) + assistant reply and enforce the window."""
    new_msgs: list[ConversationMessage] = []
    total_new_tokens = 0

    for m in incoming:
        if m.get("role") == "system":
            continue  # system prompts stay client-side
        text = _content_to_text(m.get("content", ""))
        tokens = _estimate_tokens(text)
        total_new_tokens += tokens
        new_msgs.append(
            ConversationMessage(
                conversation_id=conv.id,
                role=str(m.get("role", "user")),
                content=text,
                token_count=tokens,
            )
        )

    assistant_text = _content_to_text(assistant_content)
    if assistant_text:
        tokens = _estimate_tokens(assistant_text)
        total_new_tokens += tokens
        new_msgs.append(
            ConversationMessage(
                conversation_id=conv.id,
                role="assistant",
                content=assistant_text,
                token_count=tokens,
            )
        )

    if not new_msgs:
        return

    db.add_all(new_msgs)

    conv.message_count = (conv.message_count or 0) + len(new_msgs)
    conv.total_tokens = (conv.total_tokens or 0) + total_new_tokens
    conv.updated_at = _now()
    ttl_hours = getattr(vk, "memory_ttl_hours", 720) or 720
    conv.expires_at = _now() + timedelta(hours=ttl_hours)  # refresh on activity
    await db.flush()

    # Hard-trim stored messages to the sliding window so storage stays bounded.
    max_messages = getattr(vk, "memory_max_messages", 50) or 50
    keep_ids = (
        await db.execute(
            select(ConversationMessage.id)
            .where(ConversationMessage.conversation_id == conv.id)
            .order_by(ConversationMessage.created_at.desc())
            .limit(max_messages)
        )
    ).scalars().all()
    if keep_ids:
        await db.execute(
            delete(ConversationMessage).where(
                ConversationMessage.conversation_id == conv.id,
                ConversationMessage.id.notin_(keep_ids),
            )
        )
    await db.commit()
