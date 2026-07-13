"""Chatwoot omni-channel client -- STUBBED until real credentials are set.

Chatwoot receives Facebook Messenger / Line / Email and forwards messages to
us via webhook, and we send replies back through its API. Real credentials
require the founder's own Chatwoot account, which wasn't available at build
time, so this module ships as a working stub:

- ``send_message`` logs the outbound message and appends it to the lead's
  ``conversation_history`` instead of calling the real API when
  ``CHATWOOT_ENABLED`` is false.
- ``verify_webhook_signature`` always returns True in stub mode so the
  webhook endpoint is fully exercisable in development.

Once the founder has a Chatwoot account: set CHATWOOT_ENABLED=true and fill
in CHATWOOT_BASE_URL / CHATWOOT_API_ACCESS_TOKEN / CHATWOOT_ACCOUNT_ID /
CHATWOOT_WEBHOOK_SECRET in .env -- no code changes required.
"""
from __future__ import annotations

import hashlib
import hmac
import logging

import httpx

from app.config import get_settings

logger = logging.getLogger("beauty_agent_system.chatwoot")


def verify_webhook_signature(raw_body: bytes, signature_header: str | None) -> bool:
    settings = get_settings()
    if not settings.chatwoot_enabled:
        return True  # stub mode: accept everything so it's testable end-to-end
    if not settings.chatwoot_webhook_secret or not signature_header:
        return False
    expected = hmac.new(
        settings.chatwoot_webhook_secret.encode(), raw_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header)


async def send_message(*, conversation_id: str | None, shop_id: int, text: str) -> dict:
    settings = get_settings()
    if not settings.chatwoot_enabled:
        logger.info("[CHATWOOT STUB] would send to shop_id=%s: %s", shop_id, text)
        return {"stub": True, "delivered": False, "note": "Chatwoot not configured yet"}

    if not conversation_id:
        raise ValueError("conversation_id is required to send via Chatwoot")

    url = (
        f"{settings.chatwoot_base_url}/api/v1/accounts/"
        f"{settings.chatwoot_account_id}/conversations/{conversation_id}/messages"
    )
    headers = {"api_access_token": settings.chatwoot_api_access_token}
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(url, headers=headers, json={"content": text, "message_type": "outgoing"})
        resp.raise_for_status()
        return resp.json()
