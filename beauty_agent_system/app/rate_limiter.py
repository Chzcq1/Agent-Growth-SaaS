"""Rate limiting for the GitHub Models API.

Implements, per the project spec:

1. A sliding-window limiter bounding requests/minute (``MAX_REQUESTS_PER_MINUTE``).
2. A concurrency cap so at most N requests are in flight at once.
3. A persisted "sleep mode": once the API returns 429, the whole process stops
   sending requests until ``Retry-After`` (or an exponential backoff) elapses.
   This is persisted in ``system_state`` so it survives restarts and can be
   shown on the System Health dashboard.

This module has no LLM-specific knowledge -- ``llm_client.py`` calls into it.
"""
from __future__ import annotations

import asyncio
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import ApiUsageLog, SystemState

SLEEP_STATE_KEY = "bot_sleep_state"


class RateLimitSleeping(Exception):
    """Raised when the bot is in sleep mode and a request is refused up front."""

    def __init__(self, wake_at: datetime):
        self.wake_at = wake_at
        super().__init__(f"Bot is sleeping until {wake_at.isoformat()}")


@dataclass
class _WindowState:
    timestamps: deque[float] = field(default_factory=deque)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class RateLimiter:
    """Process-wide singleton. One instance guards every GitHub Models call."""

    def __init__(self) -> None:
        settings = get_settings()
        self.max_per_minute = settings.max_requests_per_minute
        self.semaphore = asyncio.Semaphore(settings.max_concurrent_requests)
        self._window = _WindowState()
        self._consecutive_failures = 0

    # ------------------------------------------------------------------
    # Sleep mode (persisted so it survives restarts / is dashboard-visible)
    # ------------------------------------------------------------------
    def get_sleep_state(self, db: Session) -> dict:
        row = db.get(SystemState, SLEEP_STATE_KEY)
        if not row or not row.value:
            return {"sleeping": False, "wake_at": None, "reason": None}
        wake_at_raw = row.value.get("wake_at")
        if not wake_at_raw:
            return {"sleeping": False, "wake_at": None, "reason": None}
        wake_at = datetime.fromisoformat(wake_at_raw)
        sleeping = wake_at > datetime.now(timezone.utc)
        return {"sleeping": sleeping, "wake_at": wake_at, "reason": row.value.get("reason")}

    def _set_sleep_state(self, db: Session, wake_at: datetime, reason: str) -> None:
        row = db.get(SystemState, SLEEP_STATE_KEY)
        value = {"wake_at": wake_at.isoformat(), "reason": reason}
        if row:
            row.value = value
        else:
            row = SystemState(key=SLEEP_STATE_KEY, value=value)
            db.add(row)
        db.commit()

    def ensure_awake(self, db: Session) -> None:
        state = self.get_sleep_state(db)
        if state["sleeping"]:
            raise RateLimitSleeping(state["wake_at"])

    # ------------------------------------------------------------------
    # Sliding window (requests/minute)
    # ------------------------------------------------------------------
    async def _wait_for_window_slot(self) -> None:
        async with self._window.lock:
            now = time.monotonic()
            window = self._window.timestamps
            while window and now - window[0] > 60:
                window.popleft()
            if len(window) >= self.max_per_minute:
                sleep_for = 60 - (now - window[0])
            else:
                sleep_for = 0
            if sleep_for > 0:
                await asyncio.sleep(sleep_for)
            window.append(time.monotonic())

    # ------------------------------------------------------------------
    # Public API used by llm_client
    # ------------------------------------------------------------------
    async def acquire(self, db: Session) -> None:
        """Block (or raise if sleeping) until it is safe to send one request."""
        self.ensure_awake(db)
        await self.semaphore.acquire()
        try:
            await self._wait_for_window_slot()
        except Exception:
            self.semaphore.release()
            raise

    def release(self) -> None:
        self.semaphore.release()

    def record_success(
        self, db: Session, agent_name: str, model: str, tokens_used: int | None
    ) -> None:
        self._consecutive_failures = 0
        db.add(
            ApiUsageLog(
                agent_name=agent_name,
                model_used=model,
                tokens_used=tokens_used,
                status="success",
            )
        )
        db.commit()

    def record_rate_limited(
        self, db: Session, agent_name: str, model: str, retry_after_seconds: float | None
    ) -> datetime:
        settings = get_settings()
        self._consecutive_failures += 1
        backoff = retry_after_seconds
        if backoff is None:
            backoff = settings.base_backoff_seconds * (2 ** (self._consecutive_failures - 1))
        wake_at = datetime.now(timezone.utc) + timedelta(seconds=backoff)
        self._set_sleep_state(db, wake_at, reason="429 rate_limited from GitHub Models")
        db.add(
            ApiUsageLog(
                agent_name=agent_name,
                model_used=model,
                status="rate_limited",
                detail=f"sleeping {backoff:.0f}s until {wake_at.isoformat()}",
            )
        )
        db.commit()
        return wake_at

    def record_error(self, db: Session, agent_name: str, model: str, detail: str) -> None:
        db.add(
            ApiUsageLog(agent_name=agent_name, model_used=model, status="error", detail=detail[:2000])
        )
        db.commit()

    def estimate_quota_used_today(self, db: Session) -> dict:
        from sqlalchemy import func, select

        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        total = db.scalar(
            select(func.count(ApiUsageLog.id)).where(ApiUsageLog.created_at >= today_start)
        ) or 0
        rate_limited = db.scalar(
            select(func.count(ApiUsageLog.id)).where(
                ApiUsageLog.created_at >= today_start, ApiUsageLog.status == "rate_limited"
            )
        ) or 0
        errors = db.scalar(
            select(func.count(ApiUsageLog.id)).where(
                ApiUsageLog.created_at >= today_start, ApiUsageLog.status == "error"
            )
        ) or 0
        return {"total_requests_today": total, "rate_limited_today": rate_limited, "errors_today": errors}


rate_limiter = RateLimiter()
