"""APScheduler jobs.

The Virtual Office is a synchronous, founder-triggered flow (paste -> one
combined answer) -- there is no more daily follow-up batching or a
scheduled daily briefing to generate, since nothing runs on a schedule
against leads anymore. Self-improvement (what used to be a weekly digest
page) is now computed on demand inside app.agents.supervisor.run_office
each time the founder submits something, using the last 7 days of
agent_feedback directly -- see _recent_sales_tone_note there.

This module is kept as the place to add any future scheduled job (e.g. a
periodic Customer Success health scan). It currently runs exactly one job:
pruning old ApiUsageLog rows (see _prune_old_api_usage_log below) -- pure
housekeeping of a diagnostic table, never touches OfficeRun/leads/approvals,
so it cannot lose anything the founder cares about or change any agent's
behavior/output.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import delete

logger = logging.getLogger("beauty_agent_system.scheduler")

# How long ApiUsageLog rows (one per LLM call, used only for the
# rate-limiter's quota dashboard/debugging) are kept. This table grows by a
# few rows on every single founder message (one per agent dispatched, plus
# the review pass) and has no product value once it's old -- left unpruned
# it's the single biggest source of ever-growing Neon storage as usage
# accumulates over weeks.
API_USAGE_LOG_RETENTION_DAYS = 14


def _prune_old_api_usage_log() -> None:
    from app.database import get_session_factory
    from app.models import ApiUsageLog

    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(
        days=API_USAGE_LOG_RETENTION_DAYS
    )
    session_factory = get_session_factory()
    db = session_factory()
    try:
        result = db.execute(delete(ApiUsageLog).where(ApiUsageLog.created_at < cutoff))
        db.commit()
        if result.rowcount:
            logger.info("pruned %s ApiUsageLog rows older than %sd", result.rowcount, API_USAGE_LOG_RETENTION_DAYS)
    except Exception:  # noqa: BLE001 -- housekeeping must never crash the app
        logger.exception("ApiUsageLog pruning failed")
        db.rollback()
    finally:
        db.close()


async def _scan_facebook_comments() -> None:
    """Poll Facebook Page for new comments and process them (Task #6).

    Runs every N minutes (FACEBOOK_POLL_INTERVAL_MINUTES, default 5).
    Safe no-op when FACEBOOK_ENABLED=false.
    """
    from app.config import get_settings
    settings = get_settings()
    if not settings.facebook_enabled:
        return

    from app.database import get_session_factory
    from app.facebook_pipeline import process_new_comments

    session_factory = get_session_factory()
    db = session_factory()
    try:
        count = await process_new_comments(db)
        if count:
            logger.info("Facebook scan: %s comment(s) acted on", count)
    except Exception:  # noqa: BLE001
        logger.exception("Facebook comment scan failed")
        db.rollback()
    finally:
        db.close()


async def _scan_tiktok_comments() -> None:
    """Poll TikTok account videos for new comments and process them (Task #7).

    Runs every N minutes (TIKTOK_POLL_INTERVAL_MINUTES, default 10).
    Safe no-op when TIKTOK_ENABLED=false.
    """
    from app.config import get_settings
    settings = get_settings()
    if not settings.tiktok_enabled:
        return

    from app.database import get_session_factory
    from app.tiktok_pipeline import process_new_comments

    session_factory = get_session_factory()
    db = session_factory()
    try:
        count = await process_new_comments(db)
        if count:
            logger.info("TikTok scan: %s comment(s) acted on", count)
    except Exception:  # noqa: BLE001
        logger.exception("TikTok comment scan failed")
        db.rollback()
    finally:
        db.close()


def start_scheduler() -> AsyncIOScheduler:
    from app.config import get_settings
    settings = get_settings()

    scheduler = AsyncIOScheduler()
    scheduler.add_job(_prune_old_api_usage_log, "interval", hours=24, next_run_time=datetime.now())
    scheduler.add_job(
        _scan_facebook_comments,
        "interval",
        minutes=settings.facebook_poll_interval_minutes,
        id="scan_facebook_comments",
    )
    scheduler.add_job(
        _scan_tiktok_comments,
        "interval",
        minutes=settings.tiktok_poll_interval_minutes,
        id="scan_tiktok_comments",
    )
    scheduler.start()
    return scheduler
