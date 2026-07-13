"""APScheduler jobs: daily follow-up batching + weekly self-improvement.

Both jobs deliberately process leads/feedback ONE AT A TIME with a delay in
between (``FOLLOWUP_BATCH_DELAY_SECONDS``) instead of firing every request
at once -- this is the "Batching Follow-up" requirement from the spec.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.agents import strategic_closer
from app.config import get_settings
from app.database import get_session_factory
from app.models import AgentFeedback, Lead, LeadStatus, PendingApproval, WeeklyInsight

logger = logging.getLogger("beauty_agent_system.scheduler")


async def run_daily_followups() -> None:
    settings = get_settings()
    db = get_session_factory()()
    try:
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        due_leads = db.scalars(
            select(Lead)
            .where(Lead.status.in_([LeadStatus.CONTACTED, LeadStatus.FOLLOWUP_1, LeadStatus.FOLLOWUP_2]))
            .where((Lead.next_followup_date.is_(None)) | (Lead.next_followup_date <= now))
        ).all()
        logger.info("daily follow-up scan: %s leads due", len(due_leads))
        for lead in due_leads:
            try:
                result = await strategic_closer.draft_followup(db, lead.shop_id)
                logger.info("follow-up for shop_id=%s -> %s", lead.shop_id, result.get("status"))
            except Exception:  # noqa: BLE001
                logger.exception("follow-up failed for shop_id=%s", lead.shop_id)
            await asyncio.sleep(settings.followup_batch_delay_seconds)
    finally:
        db.close()


async def run_weekly_insights() -> None:
    """Aggregates the last 7 days of agent_feedback into a plain-language
    summary. No auto-apply -- this only ever writes a suggestion row that the
    Founder can mark 'applied' from the dashboard."""
    db = get_session_factory()()
    try:
        week_start = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=7)
        feedback_rows = db.scalars(
            select(AgentFeedback)
            .join(PendingApproval, AgentFeedback.approval_id == PendingApproval.id)
            .where(AgentFeedback.created_at >= week_start)
        ).all()

        sent = sum(1 for f in feedback_rows if f.outcome == "sent")
        ignored = sum(1 for f in feedback_rows if f.outcome == "ignored")
        converted = sum(1 for f in feedback_rows if f.outcome == "converted")

        total = len(feedback_rows) or 1
        summary = (
            f"Last 7 days: {len(feedback_rows)} reviewed drafts -- "
            f"{sent} sent, {ignored} rejected, {converted} converted "
            f"({converted / total:.0%} conversion of reviewed drafts)."
        )
        recommendation = (
            "Not enough reviewed drafts yet to recommend a tone/length change."
            if len(feedback_rows) < 5
            else (
                "Rejection rate is high -- consider shortening Day-1 messages and "
                "removing any remaining sales language from the first outreach."
                if ignored / total > 0.5
                else "Approval rate looks healthy -- no changes recommended this week."
            )
        )

        db.add(WeeklyInsight(week_start=week_start, summary_text=summary, recommendation=recommendation))
        db.commit()
        logger.info("weekly insight generated: %s", summary)
    finally:
        db.close()


def start_scheduler() -> AsyncIOScheduler:
    settings = get_settings()
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_daily_followups,
        "cron",
        hour=settings.followup_scan_hour_utc,
        id="daily_followups",
        replace_existing=True,
    )
    scheduler.add_job(
        run_weekly_insights,
        "cron",
        day_of_week="mon",
        hour=4,
        id="weekly_insights",
        replace_existing=True,
    )
    scheduler.start()
    return scheduler
