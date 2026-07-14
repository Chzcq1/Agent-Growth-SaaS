"""Facebook Graph API client — stub until real credentials are set.

Covers:
  - Listing recent posts on a Page
  - Listing comments on a post (since a timestamp)
  - Posting a public reply to a comment
  - Sending a Messenger DM to a user (via their PSID)

Stub mode (FACEBOOK_ENABLED=false):
  All write functions log the action and return a stub dict.
  List functions return empty lists so the scheduler is safe to run.

Once the founder has a Facebook Page:
  1. Set FACEBOOK_ENABLED=true
  2. Set FACEBOOK_PAGE_ID and FACEBOOK_PAGE_ACCESS_TOKEN
  No code changes required.

Facebook Graph API docs: https://developers.facebook.com/docs/graph-api/
Messenger Send API:       https://developers.facebook.com/docs/messenger-platform/send-messages/
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

import httpx

from app.config import get_settings

logger = logging.getLogger("beauty_agent_system.facebook")

GRAPH_BASE = "https://graph.facebook.com/v20.0"

_STUB = {"stub": True, "delivered": False, "note": "Facebook not configured yet"}


# ── Internal helpers ──────────────────────────────────────────────────────────

def _token() -> str:
    return get_settings().facebook_page_access_token


def _enabled() -> bool:
    return get_settings().facebook_enabled


# ── Posts ─────────────────────────────────────────────────────────────────────

async def list_recent_posts(
    *,
    since: datetime | None = None,
    limit: int = 10,
) -> list[dict]:
    """Return the most recent posts on the configured Page.

    Each dict contains at least: id, message, created_time.
    Returns an empty list when Facebook is not enabled.
    """
    if not _enabled():
        return []

    page_id = get_settings().facebook_page_id
    params: dict = {
        "access_token": _token(),
        "fields": "id,message,created_time",
        "limit": limit,
    }
    if since:
        params["since"] = int(since.timestamp())

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{GRAPH_BASE}/{page_id}/posts", params=params)
        resp.raise_for_status()
        return resp.json().get("data", [])


# ── Comments ──────────────────────────────────────────────────────────────────

async def list_comments(
    post_id: str,
    *,
    since: datetime | None = None,
) -> list[dict]:
    """Return all top-level comments on a post, optionally filtered by time.

    Each dict contains: id, message, from (id, name), created_time.
    Returns an empty list when Facebook is not enabled.
    """
    if not _enabled():
        return []

    params: dict = {
        "access_token": _token(),
        "fields": "id,message,from,created_time",
        "filter": "stream",
        "limit": 100,
    }
    if since:
        params["since"] = int(since.timestamp())

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{GRAPH_BASE}/{post_id}/comments", params=params)
        resp.raise_for_status()
        return resp.json().get("data", [])


# ── Comment replies (public) ──────────────────────────────────────────────────

async def post_comment_reply(comment_id: str, message: str) -> dict:
    """Post a public reply to a comment under a post."""
    if not _enabled():
        logger.info("[FB STUB] reply to comment %s: %.120s", comment_id, message)
        return _STUB

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{GRAPH_BASE}/{comment_id}/comments",
            params={"access_token": _token()},
            json={"message": message},
        )
        resp.raise_for_status()
        return resp.json()


# ── Messenger DM ──────────────────────────────────────────────────────────────

async def send_dm(psid: str, message: str) -> dict:
    """Send a private Messenger DM to a user identified by their Page-Scoped ID.

    The PSID comes from the comment's ``from.id`` field when the Page has
    the ``pages_messaging`` permission.
    """
    if not _enabled():
        logger.info("[FB STUB] DM to psid=%s: %.120s", psid, message)
        return _STUB

    page_id = get_settings().facebook_page_id
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{GRAPH_BASE}/{page_id}/messages",
            params={"access_token": _token()},
            json={
                "recipient": {"id": psid},
                "message": {"text": message},
                "messaging_type": "RESPONSE",
            },
        )
        resp.raise_for_status()
        return resp.json()


# ── Timestamp helpers ─────────────────────────────────────────────────────────

def parse_fb_time(fb_time: str) -> datetime:
    """Parse Facebook's ISO-8601 created_time into a UTC-aware datetime."""
    try:
        # Facebook returns e.g. "2026-07-14T04:30:00+0000"
        dt = datetime.fromisoformat(fb_time.replace("+0000", "+00:00"))
        return dt.astimezone(timezone.utc)
    except ValueError:
        return datetime.now(timezone.utc)
