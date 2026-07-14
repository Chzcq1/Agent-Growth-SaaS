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

import hashlib
import hmac
import logging
from datetime import datetime, timezone

import httpx

from app.config import get_settings

logger = logging.getLogger("beauty_agent_system.facebook")

GRAPH_BASE = "https://graph.facebook.com/v20.0"

_STUB = {"stub": True, "delivered": False, "note": "Facebook not configured yet"}

# Cache for the resolved Page-scoped access token (see _resolve_page_token below).
# Keyed by the configured token so a credential rotation invalidates the cache.
_resolved_token_cache: dict[str, str] = {}


# ── Internal helpers ──────────────────────────────────────────────────────────

def _enabled() -> bool:
    return get_settings().facebook_enabled


async def _resolve_page_token() -> str:
    """Return a Page-scoped access token usable for Page API calls.

    Meta issues several token "shapes" depending on how it was generated:
    a User token, a Business System User token, or a genuine Page token.
    Pages migrated to Meta's "New Pages Experience" reject the first two for
    Page-level calls (error code 190 / subcode 2069032) — only a true Page
    token works. Since a System User/User token can list every Page it has
    access to via ``/me/accounts`` (each entry embeds that Page's own token),
    we resolve the real Page token once per configured credential and cache
    it, instead of requiring the operator to manually extract it.
    """
    configured = get_settings().facebook_page_access_token
    page_id = get_settings().facebook_page_id

    cached = _resolved_token_cache.get(configured)
    if cached:
        return cached

    resolved = configured  # fall back to the configured token as-is
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{GRAPH_BASE}/me/accounts",
                params={"access_token": configured, "fields": "id,access_token"},
            )
            resp.raise_for_status()
            for page in resp.json().get("data", []):
                if page.get("id") == page_id and page.get("access_token"):
                    resolved = page["access_token"]
                    break
    except httpx.HTTPError:
        logger.warning(
            "Could not resolve a Page-scoped token via /me/accounts; "
            "using the configured token as-is.",
            exc_info=True,
        )

    _resolved_token_cache[configured] = resolved
    return resolved


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
        "access_token": await _resolve_page_token(),
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
        "access_token": await _resolve_page_token(),
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
            params={"access_token": await _resolve_page_token()},
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
            params={"access_token": await _resolve_page_token()},
            json={
                "recipient": {"id": psid},
                "message": {"text": message},
                "messaging_type": "RESPONSE",
            },
        )
        resp.raise_for_status()
        return resp.json()


# ── Webhook signature verification ───────────────────────────────────────────

def verify_webhook_signature(raw_body: bytes, signature_header: str | None) -> bool:
    """Verify Meta's X-Hub-Signature-256 header against the raw request body.

    Meta signs every webhook POST with HMAC-SHA256 using the App Secret.
    Returns True (accepts unsigned bodies) only when no app secret is
    configured yet -- e.g. before the founder has copied it in -- so local
    testing isn't blocked, but this must never be true once configured.
    """
    secret = get_settings().facebook_app_secret
    if not secret:
        return True
    if not signature_header or not signature_header.startswith("sha256="):
        return False
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    provided = signature_header.removeprefix("sha256=")
    return hmac.compare_digest(expected, provided)


# ── Timestamp helpers ─────────────────────────────────────────────────────────

def parse_fb_time(fb_time: str) -> datetime:
    """Parse Facebook's ISO-8601 created_time into a UTC-aware datetime."""
    try:
        # Facebook returns e.g. "2026-07-14T04:30:00+0000"
        dt = datetime.fromisoformat(fb_time.replace("+0000", "+00:00"))
        return dt.astimezone(timezone.utc)
    except ValueError:
        return datetime.now(timezone.utc)
