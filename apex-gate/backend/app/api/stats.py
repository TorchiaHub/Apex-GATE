from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.deps import get_current_user
from app.auth.models import User
from app.database import get_session
from app.models.request_log import RequestLog

router = APIRouter(prefix="/api/v1/stats", tags=["stats"])


@router.get("/overview")
async def stats_overview(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_session)) -> dict:
    today_start = datetime.combine(date.today(), datetime.min.time()).replace(tzinfo=timezone.utc)

    result = await db.execute(
        select(
            func.count(RequestLog.id),
            func.coalesce(func.sum(RequestLog.input_tokens + RequestLog.output_tokens), 0),
            func.coalesce(func.sum(RequestLog.cost_usd), 0),
        ).where(RequestLog.user_id == user.id, RequestLog.created_at >= today_start)
    )
    calls, tokens, cost = result.one()
    return {"calls_today": calls, "tokens_today": tokens, "cost_today": str(cost)}


@router.get("/by-provider")
async def stats_by_provider(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_session)) -> list[dict]:
    from app.models.api_key import ApiKey
    from app.models.provider import Provider

    result = await db.execute(
        select(
            func.coalesce(Provider.slug, "unknown"),
            func.count(RequestLog.id),
            func.coalesce(func.sum(RequestLog.cost_usd), 0),
            func.sum(case((RequestLog.status == "rate_limited", 1), else_=0)),
        )
        .outerjoin(ApiKey, RequestLog.api_key_id == ApiKey.id)
        .outerjoin(Provider, ApiKey.provider_id == Provider.id)
        .where(RequestLog.user_id == user.id)
        .group_by(func.coalesce(Provider.slug, "unknown"))
    )
    return [{"provider": row[0], "calls": row[1], "cost": str(row[2]), "rate_limits": row[3]} for row in result.all()]


@router.get("/by-model")
async def stats_by_model(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_session)) -> list[dict]:
    result = await db.execute(
        select(RequestLog.model_id, func.count(RequestLog.id), func.avg(RequestLog.latency_ms), func.coalesce(func.sum(RequestLog.cost_usd), 0))
        .where(RequestLog.user_id == user.id, RequestLog.model_id != None)  # noqa: E711
        .group_by(RequestLog.model_id)
        .order_by(func.count(RequestLog.id).desc())
        .limit(20)
    )
    return [{"model_id": r[0], "calls": r[1], "avg_latency_ms": r[2], "cost_usd": str(r[3])} for r in result.all()]


@router.get("/by-day")
async def stats_by_day(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_session)) -> list[dict]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    result = await db.execute(
        select(func.date(RequestLog.created_at), func.count(RequestLog.id), func.coalesce(func.sum(RequestLog.cost_usd), 0))
        .where(RequestLog.user_id == user.id, RequestLog.created_at >= cutoff)
        .group_by(func.date(RequestLog.created_at))
        .order_by(func.date(RequestLog.created_at))
    )
    return [{"date": str(r[0]), "calls": r[1], "cost": str(r[2])} for r in result.all()]


@router.get("/costs")
async def stats_costs(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_session)) -> list[dict]:
    from app.models.api_key import ApiKey

    result = await db.execute(
        select(ApiKey.name, func.coalesce(func.sum(RequestLog.cost_usd), 0))
        .join(ApiKey, RequestLog.api_key_id == ApiKey.id)
        .where(RequestLog.user_id == user.id, ApiKey.tier == "paid")
        .group_by(ApiKey.id, ApiKey.name)
        .order_by(func.sum(RequestLog.cost_usd).desc())
    )
    return [{"key_name": r[0], "total_cost": str(r[1])} for r in result.all()]
