from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.auth.models import User
from app.database import get_session
from app.models.request_log import RequestLog

router = APIRouter(prefix="/api/v1/logs", tags=["logs"])


@router.get("/")
async def list_logs(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    status: str | None = Query(default=None),
    virtual_key_id: str | None = Query(default=None),
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> list[dict]:
    query = select(RequestLog).where(RequestLog.user_id == user.id)
    if status:
        query = query.where(RequestLog.status == status)
    if virtual_key_id:
        query = query.where(RequestLog.virtual_key_id == virtual_key_id)
    if date_from:
        query = query.where(RequestLog.created_at >= date_from)
    if date_to:
        query = query.where(RequestLog.created_at <= date_to)

    query = query.order_by(RequestLog.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)

    return [{
        "id": r.id, "model_id": r.model_id, "input_tokens": r.input_tokens,
        "output_tokens": r.output_tokens, "cost_usd": str(r.cost_usd),
        "latency_ms": r.latency_ms, "status": r.status,
        "protocol": r.protocol, "created_at": r.created_at,
        "virtual_key_id": r.virtual_key_id, "api_key_id": r.api_key_id,
        "error_message": r.error_message,
    } for r in result.scalars().all()]
