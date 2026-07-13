"""Unit tests for the rate limiter module.

These test the sliding-window + sleep-mode logic in isolation using a fake
SQLAlchemy session so no real database is required to run them.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from app.models import SystemState
from app.rate_limiter import RateLimitSleeping, RateLimiter, SLEEP_STATE_KEY


class FakeSession:
    """Minimal stand-in for a SQLAlchemy Session, just enough for RateLimiter."""

    def __init__(self) -> None:
        self._rows: dict[str, SystemState] = {}
        self.logs: list = []

    def get(self, model, pk):
        if model is SystemState:
            return self._rows.get(pk)
        return None

    def add(self, obj):
        if isinstance(obj, SystemState):
            self._rows[obj.key] = obj
        else:
            self.logs.append(obj)

    def commit(self):
        pass


@pytest.fixture
def limiter():
    return RateLimiter()


@pytest.fixture
def db():
    return FakeSession()


def test_not_sleeping_by_default(limiter, db):
    state = limiter.get_sleep_state(db)
    assert state["sleeping"] is False
    limiter.ensure_awake(db)  # should not raise


def test_record_rate_limited_sets_sleep_state(limiter, db):
    wake_at = limiter.record_rate_limited(db, "test_agent", "test-model", retry_after_seconds=30)
    assert wake_at > datetime.now(timezone.utc)

    state = limiter.get_sleep_state(db)
    assert state["sleeping"] is True

    with pytest.raises(RateLimitSleeping):
        limiter.ensure_awake(db)


def test_record_rate_limited_uses_exponential_backoff_without_retry_after(limiter, db):
    first = limiter.record_rate_limited(db, "test_agent", "test-model", retry_after_seconds=None)
    second = limiter.record_rate_limited(db, "test_agent", "test-model", retry_after_seconds=None)
    # second backoff should be strictly larger since consecutive_failures grew
    first_delta = (first - datetime.now(timezone.utc)).total_seconds()
    second_delta = (second - datetime.now(timezone.utc)).total_seconds()
    assert second_delta > first_delta


def test_sleep_state_expires(limiter, db):
    # Force a sleep state that is already in the past.
    past = datetime.now(timezone.utc) - timedelta(seconds=5)
    db.add(SystemState(key=SLEEP_STATE_KEY, value={"wake_at": past.isoformat(), "reason": "test"}))
    state = limiter.get_sleep_state(db)
    assert state["sleeping"] is False


def test_record_success_resets_consecutive_failures(limiter, db):
    limiter.record_rate_limited(db, "test_agent", "test-model", retry_after_seconds=10)
    assert limiter._consecutive_failures == 1
    limiter.record_success(db, "test_agent", "test-model", tokens_used=42)
    assert limiter._consecutive_failures == 0


@pytest.mark.asyncio
async def test_sliding_window_limits_requests_per_minute():
    limiter = RateLimiter()
    limiter.max_per_minute = 2
    start = asyncio.get_event_loop().time()
    await limiter._wait_for_window_slot()
    await limiter._wait_for_window_slot()
    assert asyncio.get_event_loop().time() - start < 0.5  # first two are immediate


@pytest.mark.asyncio
async def test_concurrency_semaphore_caps_in_flight_requests():
    limiter = RateLimiter()
    limiter.semaphore = asyncio.Semaphore(1)
    db = FakeSession()

    order: list[str] = []

    async def worker(name: str):
        await limiter.acquire(db)
        order.append(f"{name}-start")
        await asyncio.sleep(0.05)
        order.append(f"{name}-end")
        limiter.release()

    await asyncio.gather(worker("a"), worker("b"))
    # With concurrency capped at 1, "a" must fully finish before "b" starts.
    assert order == ["a-start", "a-end", "b-start", "b-end"]
