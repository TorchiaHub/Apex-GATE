from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings

logger = logging.getLogger(__name__)

_scheduler = AsyncIOScheduler()


async def _job_reset_exhaustions() -> None:
    from app.database import AsyncSessionLocal
    from app.proxy.manager import provider_manager

    try:
        async with AsyncSessionLocal() as db:
            await provider_manager.reset_expired_exhaustions(db)
    except Exception:
        logger.exception("reset_exhaustions job failed")


async def _job_cleanup_logs() -> None:
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import delete

    from app.database import AsyncSessionLocal
    from app.models.request_log import RequestLog

    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=settings.LOG_RETENTION_DAYS)
        async with AsyncSessionLocal() as db:
            await db.execute(delete(RequestLog).where(RequestLog.created_at < cutoff))
            await db.commit()
    except Exception:
        logger.exception("cleanup_logs job failed")


async def _job_discovery() -> None:
    from app.database import AsyncSessionLocal
    from app.discovery.service import run_discovery

    try:
        async with AsyncSessionLocal() as db:
            await run_discovery(db)
    except Exception:
        logger.exception("discovery job failed")


async def _job_cleanup_conversations() -> None:
    from datetime import datetime, timezone

    from sqlalchemy import delete

    from app.database import AsyncSessionLocal
    from app.models.conversation import Conversation

    try:
        now = datetime.now(timezone.utc)
        async with AsyncSessionLocal() as db:
            await db.execute(
                delete(Conversation).where(
                    Conversation.expires_at.is_not(None),
                    Conversation.expires_at < now,
                )
            )
            await db.commit()
    except Exception:
        logger.exception("cleanup_conversations job failed")


async def start_scheduler() -> None:
    _scheduler.add_job(_job_reset_exhaustions, "interval", seconds=60, id="reset_exhaustions")
    _scheduler.add_job(_job_cleanup_logs, "cron", hour=3, minute=0, id="cleanup_logs")
    _scheduler.add_job(
        _job_cleanup_conversations, "cron", hour=3, minute=30, id="cleanup_conversations"
    )
    _scheduler.add_job(
        _job_discovery,
        "interval",
        hours=settings.DISCOVERY_INTERVAL_HOURS,
        id="discovery",
    )
    # Run an initial discovery shortly after startup so the catalog is
    # refreshed automatically without waiting for the first interval.
    _scheduler.add_job(
        _job_discovery,
        "date",
        run_date=datetime.now(timezone.utc) + timedelta(seconds=5),
        id="discovery_startup",
    )
    _scheduler.start()
