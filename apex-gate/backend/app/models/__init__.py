"""
App DB models — single shared Base for all application tables.
Auth DB uses a separate Base defined in app/auth/models.py.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import DeclarativeBase


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Declarative base for the application database."""


# Re-export all models so alembic env.py has a single import target.
# Imports must come after Base is defined.
from app.models.provider import Provider  # noqa: E402, F401
from app.models.api_key import ApiKey  # noqa: E402, F401
from app.models.virtual_key import VirtualKey  # noqa: E402, F401
from app.models.model_catalog import ModelCatalog  # noqa: E402, F401
from app.models.request_log import RequestLog  # noqa: E402, F401
from app.models.exhaustion_state import ExhaustionState  # noqa: E402, F401
from app.models.virtual_key_assignment import VirtualKeyAssignment  # noqa: E402, F401
from app.models.conversation import Conversation, ConversationMessage  # noqa: E402, F401

__all__ = [
    "Base",
    "_uuid",
    "_now",
    "Provider",
    "ApiKey",
    "VirtualKey",
    "ModelCatalog",
    "RequestLog",
    "ExhaustionState",
    "VirtualKeyAssignment",
    "Conversation",
    "ConversationMessage",
]
