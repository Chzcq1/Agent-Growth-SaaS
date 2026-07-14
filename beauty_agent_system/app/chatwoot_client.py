"""Chatwoot omni-channel client -- STUBBED until real credentials are set.

Chatwoot receives Facebook Messenger / Instagram / Line / Email and forwards
messages to us via webhook, and we send replies back through its API.

Real credentials require the founder's own Chatwoot account.  This module
ships as a working stub:

- All ``send_*`` and ``assign_*`` functions log the action and return a stub
  dict when ``CHATWOOT_ENABLED`` is false.
- ``verify_webhook_signature`` always returns True in stub mode so the
  webhook endpoint is fully testable in development.

Once the founder has a Chatwoot account:
  1. Set CHATWOOT_ENABLED=true in Replit secrets
  2. Set CHATWOOT_BASE_URL, CHATWOOT_API_ACCESS_TOKEN, CHATWOOT_ACCOUNT_ID,
     CHATWOOT_WEBHOOK_SECRET
  No code changes required.

Chatwoot API docs: https://www.chatwoot.com/developers/api/
"""
from __future__ import annotations

import hashlib
import hmac
import logging

import httpx

from app.config import get_settings

logger = logging.getLogger("beauty_agent_system.chatwoot")

_STUB = {"stub": True, "delivered": False, "note": "Chatwoot not configured yet"}


def _headers(settings) -> dict:
    return {"api_access_token": settings.chatwoot_api_access_token}


def _base(settings) -> str:
    return f"{settings.chatwoot_base_url}/api/v1/accounts/{settings.chatwoot_account_id}"


# ── Signature verification ────────────────────────────────────────────────────

def verify_webhook_signature(raw_body: bytes, signature_header: str | None) -> bool:
    settings = get_settings()
    if not settings.chatwoot_enabled:
        return True  # stub mode: accept everything
    if not settings.chatwoot_webhook_secret or not signature_header:
        return False
    expected = hmac.new(
        settings.chatwoot_webhook_secret.encode(), raw_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header)


# ── Outbound messages ─────────────────────────────────────────────────────────

async def send_message(
    *,
    conversation_id: str | None,
    shop_id: int,
    text: str,
) -> dict:
    """Send an outgoing reply in a Chatwoot conversation."""
    settings = get_settings()
    if not settings.chatwoot_enabled:
        logger.info("[CHATWOOT STUB] send to shop_id=%s conv=%s: %.120s", shop_id, conversation_id, text)
        return _STUB

    if not conversation_id:
        raise ValueError("conversation_id is required to send via Chatwoot")

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{_base(settings)}/conversations/{conversation_id}/messages",
            headers=_headers(settings),
            json={"content": text, "message_type": "outgoing"},
        )
        resp.raise_for_status()
        return resp.json()


async def add_private_note(
    *,
    conversation_id: str,
    text: str,
) -> dict:
    """Add a private note (visible only to agents, not to the customer)."""
    settings = get_settings()
    if not settings.chatwoot_enabled:
        logger.info("[CHATWOOT STUB] private note conv=%s: %.120s", conversation_id, text)
        return _STUB

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{_base(settings)}/conversations/{conversation_id}/messages",
            headers=_headers(settings),
            json={"content": text, "message_type": "activity", "private": True},
        )
        resp.raise_for_status()
        return resp.json()


# ── Conversation management ───────────────────────────────────────────────────

async def assign_to_human(
    *,
    conversation_id: str,
    reason: str = "AI ไม่มั่นใจ — ต้องการให้ทีมตรวจสอบ",
) -> dict:
    """Set conversation status to 'pending' so it surfaces in the human inbox."""
    settings = get_settings()
    if not settings.chatwoot_enabled:
        logger.info(
            "[CHATWOOT STUB] assign conv=%s to human. Reason: %s", conversation_id, reason
        )
        return _STUB

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.patch(
            f"{_base(settings)}/conversations/{conversation_id}",
            headers=_headers(settings),
            json={"status": "pending"},
        )
        resp.raise_for_status()
        return resp.json()


async def resolve_conversation(*, conversation_id: str) -> dict:
    """Mark conversation as resolved after a successful sale/care interaction."""
    settings = get_settings()
    if not settings.chatwoot_enabled:
        logger.info("[CHATWOOT STUB] resolve conv=%s", conversation_id)
        return _STUB

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.patch(
            f"{_base(settings)}/conversations/{conversation_id}",
            headers=_headers(settings),
            json={"status": "resolved"},
        )
        resp.raise_for_status()
        return resp.json()


# ── Contact management ────────────────────────────────────────────────────────

async def search_contact(*, name: str, phone: str | None = None) -> dict | None:
    """Return the first matching Chatwoot contact dict, or None."""
    settings = get_settings()
    if not settings.chatwoot_enabled:
        return None

    q = phone or name
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            f"{_base(settings)}/contacts/search",
            headers=_headers(settings),
            params={"q": q, "include_contacts": True},
        )
        if not resp.is_success:
            return None
        data = resp.json()
        contacts = data.get("payload", [])
        return contacts[0] if contacts else None


async def create_contact(
    *,
    name: str,
    phone: str | None = None,
    channel: str = "unknown",
) -> dict:
    """Create a new contact in Chatwoot and return the contact dict."""
    settings = get_settings()
    if not settings.chatwoot_enabled:
        logger.info("[CHATWOOT STUB] create contact name=%s", name)
        return {"id": "stub", "name": name}

    payload: dict = {"name": name}
    if phone:
        payload["phone_number"] = phone

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{_base(settings)}/contacts",
            headers=_headers(settings),
            json=payload,
        )
        resp.raise_for_status()
        return resp.json().get("contact", resp.json())
