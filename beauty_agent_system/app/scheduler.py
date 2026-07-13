"""APScheduler jobs.

The Virtual Office is a synchronous, founder-triggered flow (paste -> one
combined answer) -- there is no more daily follow-up batching or a
scheduled daily briefing to generate, since nothing runs on a schedule
against leads anymore. Self-improvement (what used to be a weekly digest
page) is now computed on demand inside app.agents.supervisor.run_office
each time the founder submits something, using the last 7 days of
agent_feedback directly -- see _recent_sales_tone_note there.

This module is kept as the place to add any future scheduled job (e.g. a
periodic Customer Success health scan), but currently starts no jobs.
"""
from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = logging.getLogger("beauty_agent_system.scheduler")


def start_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.start()
    return scheduler
