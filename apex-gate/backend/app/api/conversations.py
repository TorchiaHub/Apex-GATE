"""REST API for inspecting and managing server-side conversation memory.

All endpoints are scoped to the authenticated user. Conversations belong to a
virtual key; a user can only see conversations created by their own keys.
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.auth.models import User
from app.database import get_session
from app.models.conversation import Conversation, ConversationMessage
from app.models.virtual_key import VirtualKey

router = APIRouter(prefix="/api/v1/conversations", tags=["conversations"])


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    virtual_key_id: str
    title: str | None
    message_count: int
    total_tokens: int
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    expires_at: datetime | None


class ConversationMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    role: str
    content: str
    token_count: int
    created_at: datetime


async def _get_owned_conversation(
    conversation_id: str, user_id: str, db: AsyncSession
) -> Conversation:
    conv = await db.get(Conversation, conversation_id)
    if conv is None or conv.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found"
        )
    return conv


@router.get("/", response_model=list[ConversationResponse])
async def list_conversations(
    virtual_key_id: str | None = Query(default=None),
    include_archived: bool = Query(default=False),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> list[Conversation]:
    stmt = (
        select(Conversation)
        .where(Conversation.user_id == user.id)
        .order_by(Conversation.updated_at.desc())
    )
    if virtual_key_id:
        stmt = stmt.where(Conversation.virtual_key_id == virtual_key_id)
    if not include_archived:
        stmt = stmt.where(Conversation.is_archived == False)  # noqa: E712
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> Conversation:
    return await _get_owned_conversation(conversation_id, user.id, db)


@router.get(
    "/{conversation_id}/messages", response_model=list[ConversationMessageResponse]
)
async def list_conversation_messages(
    conversation_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> list[ConversationMessage]:
    await _get_owned_conversation(conversation_id, user.id, db)
    result = await db.execute(
        select(ConversationMessage)
        .where(ConversationMessage.conversation_id == conversation_id)
        .order_by(ConversationMessage.created_at.asc())
    )
    return list(result.scalars().all())


@router.post("/{conversation_id}/archive", response_model=ConversationResponse)
async def archive_conversation(
    conversation_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> Conversation:
    conv = await _get_owned_conversation(conversation_id, user.id, db)
    conv.is_archived = True
    await db.commit()
    await db.refresh(conv)
    return conv


@router.delete(
    "/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None
)
async def delete_conversation(
    conversation_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> None:
    conv = await _get_owned_conversation(conversation_id, user.id, db)
    # Messages are removed by the ON DELETE CASCADE foreign key.
    await db.delete(conv)
    await db.commit()


@router.delete(
    "/{conversation_id}/messages",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def clear_conversation_messages(
    conversation_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> None:
    """Forget the history but keep the conversation thread alive."""
    conv = await _get_owned_conversation(conversation_id, user.id, db)
    await db.execute(
        delete(ConversationMessage).where(
            ConversationMessage.conversation_id == conversation_id
        )
    )
    conv.message_count = 0
    conv.total_tokens = 0
    await db.commit()
