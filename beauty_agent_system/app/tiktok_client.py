"""TikTok for Business API client — stub until OAuth credentials are set.

Covers:
  - OAuth 2.0 access-token refresh (stored in SystemState, not config, because
    tokens change after every refresh and must be persisted across restarts)
  - Listing the account's videos (paginated via cursor)
  - Listing comments on a video (paginated via cursor)
  - Posting a comment or threaded reply on a video

Stub mode (TIKTOK_ENABLED=false):
  All write functions log the action and return a stub dict.
  List functions return empty structures so the scheduler is safe to run.

Once the founder has TikTok for Business credentials:
  1. Set TIKTOK_ENABLED=true
  2. Set TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET, TIKTOK_ACCESS_TOKEN,
     TIKTOK_REFRESH_TOKEN in Replit Secrets
  No code changes required.

TikTok for Business API docs: https://developers.tiktok.com/products/
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from sqlalchemy.orm import Session

from app.config import get_settings

logger = logging.getLogger("beauty_agent_system.tiktok")

TIKTOK_BASE = "https://open.tiktokapis.com/v2"
TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"

_STUB: dict[str, Any] = {"stub": True, "delivered": False, "note": "TikTok not configured yet"}


# ── Enabled guard ─────────────────────────────────────────────────────────────

def _enabled() -> bool:
    return get_settings().tiktok_enabled


# ── Token management (stored in SystemState so refreshes survive restarts) ────

def _load_tokens(db: Session) -> dict:
    """Load tokens from SystemState, falling back to config for the initial run."""
    from sqlalchemy import select
    from app.models import SystemState

    row = db.scalar(select(SystemState).where(SystemState.key == "tiktok_tokens"))
    if row and row.value:
        return row.value

    # First run: seed from config / Replit Secrets
    settings = get_settings()
    return {
        "access_token":  settings.tiktok_access_token,
        "refresh_token": settings.tiktok_refresh_token,
        "expires_at":    None,
    }


def _save_tokens(db: Session, tokens: dict) -> None:
    from sqlalchemy import select
    from app.models import SystemState

    row = db.scalar(select(SystemState).where(SystemState.key == "tiktok_tokens"))
    if row:
        row.value = tokens
    else:
        db.add(SystemState(key="tiktok_tokens", value=tokens))
    db.commit()


async def _refresh_access_token(db: Session, refresh_token: str) -> dict:
    """Exchange a refresh token for a new access + refresh token pair."""
    settings = get_settings()
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            TOKEN_URL,
            data={
                "client_key":    settings.tiktok_client_key,
                "client_secret": settings.tiktok_client_secret,
                "grant_type":    "refresh_token",
                "refresh_token": refresh_token,
            },
        )
        resp.raise_for_status()
        body = resp.json().get("data", resp.json())

    expires_at = (
        datetime.now(timezone.utc) + timedelta(seconds=int(body.get("expires_in", 86400)))
    ).isoformat()
    tokens = {
        "access_token":  body["access_token"],
        "refresh_token": body.get("refresh_token", refresh_token),
        "expires_at":    expires_at,
    }
    _save_tokens(db, tokens)
    logger.info("TikTok access token refreshed; new expiry=%s", expires_at)
    return tokens


async def get_access_token(db: Session) -> str:
    """Return a valid TikTok access token, refreshing it if near-expired.

    ``expires_at=None`` (first-run seeded tokens) is treated as already
    expired so an automatic refresh fires immediately rather than waiting for
    manual intervention.  If the refresh itself fails we fall back to the
    existing token and let the caller surface the 401.
    """
    tokens = _load_tokens(db)
    access_token = tokens.get("access_token") or ""
    refresh_token = tokens.get("refresh_token") or ""
    expires_at_str = tokens.get("expires_at")  # None on first run

    should_refresh = False
    if not expires_at_str:
        # No expiry recorded — treat as expired to force a refresh so the
        # token lifecycle is fully automatic from the first API call onward.
        should_refresh = bool(refresh_token)
    else:
        try:
            expires_at = datetime.fromisoformat(expires_at_str)
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            # Refresh if fewer than 5 minutes remain
            should_refresh = (
                expires_at - datetime.now(timezone.utc) < timedelta(minutes=5)
                and bool(refresh_token)
            )
        except ValueError:
            should_refresh = bool(refresh_token)

    if should_refresh:
        try:
            tokens = await _refresh_access_token(db, refresh_token)
            access_token = tokens["access_token"]
        except Exception as exc:  # noqa: BLE001
            # Refresh failed — log and fall back to the existing token.
            # The downstream API call will surface a 401 if it's also expired.
            logger.warning("TikTok token refresh failed; using existing token: %s", exc)

    return access_token


# ── Videos ────────────────────────────────────────────────────────────────────

async def list_videos(
    db: Session,
    *,
    cursor: int = 0,
    max_count: int = 10,
) -> dict:
    """List the account's own videos.

    Returns a dict with keys: videos (list), cursor (int), has_more (bool).
    Returns empty structure when TikTok is not enabled.
    """
    if not _enabled():
        return {"videos": [], "cursor": 0, "has_more": False}

    token = await get_access_token(db)
    fields = "id,title,create_time,cover_image_url,share_url"
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            f"{TIKTOK_BASE}/video/list/",
            headers={"Authorization": f"Bearer {token}"},
            params={"fields": fields},
            json={"max_count": max_count, "cursor": cursor},
        )
        resp.raise_for_status()
        body = resp.json()

    data = body.get("data", {})
    return {
        "videos":   data.get("videos") or [],
        "cursor":   data.get("cursor", 0),
        "has_more": data.get("has_more", False),
    }


# ── Comments ──────────────────────────────────────────────────────────────────

async def list_comments(
    db: Session,
    video_id: str,
    *,
    cursor: int = 0,
    count: int = 50,
) -> dict:
    """List comments on a video starting from cursor.

    Returns a dict with keys: comments (list), cursor (int), has_more (bool).
    Each comment: id, text, user.display_name, user.username, create_time,
                  parent_comment_id (if threaded reply), likes_count.
    Returns empty structure when TikTok is not enabled.
    """
    if not _enabled():
        return {"comments": [], "cursor": 0, "has_more": False}

    token = await get_access_token(db)
    fields = "id,text,user.display_name,user.username,create_time,parent_comment_id,likes_count"
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            f"{TIKTOK_BASE}/video/comment/list/",
            headers={"Authorization": f"Bearer {token}"},
            params={"fields": fields},
            json={"video_id": video_id, "cursor": cursor, "count": count},
        )
        resp.raise_for_status()
        body = resp.json()

    data = body.get("data", {})
    return {
        "comments": data.get("comments") or [],
        "cursor":   data.get("cursor", 0),
        "has_more": data.get("has_more", False),
    }


# ── Comment creation / threaded reply ─────────────────────────────────────────

async def post_comment(
    db: Session,
    video_id: str,
    text: str,
    *,
    parent_comment_id: str | None = None,
) -> dict:
    """Post a comment (or threaded reply) on a TikTok video.

    Pass ``parent_comment_id`` to reply inside an existing comment thread.
    """
    if not _enabled():
        action = "reply" if parent_comment_id else "comment"
        logger.info(
            "[TT STUB] %s on video=%s parent=%s: %.120s",
            action, video_id, parent_comment_id, text,
        )
        return _STUB

    token = await get_access_token(db)
    payload: dict[str, Any] = {"video_id": video_id, "text": text}
    if parent_comment_id:
        payload["parent_comment_id"] = parent_comment_id

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{TIKTOK_BASE}/video/comment/create/",
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
        )
        resp.raise_for_status()
        return resp.json().get("data", {})
