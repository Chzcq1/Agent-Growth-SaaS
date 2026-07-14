"""Chatwoot webhook receiver + inbox live-feed endpoints.

Webhook flow:
  POST /webhook/chatwoot
    ↓ verify HMAC signature
    ↓ filter: only "message_created" where sender is a contact
    ↓ return 200 immediately
    ↓ BackgroundTask → chatwoot_pipeline.handle_incoming_message()

Live-feed endpoint:
  GET /chatwoot/conversations/active
    Returns leads with a linked Chatwoot conversation, sorted by most-recently
    contacted -- used by the VA sidebar "กล่องข้อความ" widget.

Take-over endpoint:
  POST /chatwoot/conversations/{conversation_id}/takeover
    Founder clicks "รับช่วงต่อ" in the live feed; sets conversation to open
    and adds a note that the founder is taking over.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import chatwoot_client, chatwoot_pipeline
from app.chatwoot_client import verify_webhook_signature
from app.customer_context import STAGE_LABELS
from app.database import get_db
from app.models import Lead

logger = logging.getLogger("beauty_agent_system.chatwoot_router")

router = APIRouter(prefix="/chatwoot", tags=["chatwoot"])


# ── Webhook receiver ──────────────────────────────────────────────────────────

@router.post("/webhook")
async def chatwoot_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Receive incoming messages from Chatwoot.

    Returns 200 immediately (Chatwoot requires < 5 s response) and dispatches
    the AI pipeline as a background task.
    """
    raw_body = await request.body()
    sig = request.headers.get("x-chatwoot-signature") or request.headers.get("x-hub-signature-256")

    if not verify_webhook_signature(raw_body, sig):
        logger.warning("Chatwoot webhook signature mismatch — rejected")
        raise HTTPException(status_code=401, detail="invalid signature")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="invalid JSON body")

    # Only process incoming messages from contacts (not our own outgoing replies
    # or bot messages -- those would create infinite loops)
    event = payload.get("event")
    if event != "message_created":
        return {"ok": True, "skipped": f"event={event}"}

    message_type = payload.get("message_type")
    sender = payload.get("sender") or {}
    if message_type != "incoming" or sender.get("type") != "contact":
        return {"ok": True, "skipped": "not an inbound contact message"}

    content = (payload.get("content") or "").strip()
    if not content:
        return {"ok": True, "skipped": "empty message"}

    # Extract conversation + contact info
    conversation = payload.get("conversation") or {}
    conv_id = str(conversation.get("id") or "")
    if not conv_id:
        return {"ok": True, "skipped": "no conversation id"}

    contact = conversation.get("contact") or sender
    contact_name = contact.get("name") or "ลูกค้าใหม่"
    contact_phone = contact.get("phone_number")
    chatwoot_contact_id = str(contact.get("id") or "")

    # Infer channel from inbox type if available
    inbox = conversation.get("inbox") or {}
    channel_type = inbox.get("channel_type") or ""
    if "facebook" in channel_type.lower():
        channel = "facebook"
    elif "line" in channel_type.lower():
        channel = "line"
    elif "instagram" in channel_type.lower():
        channel = "instagram"
    else:
        channel = "unknown"

    background_tasks.add_task(
        chatwoot_pipeline.handle_incoming_message,
        db,
        chatwoot_conversation_id=conv_id,
        chatwoot_contact_id=chatwoot_contact_id or None,
        contact_name=contact_name,
        contact_phone=contact_phone,
        message_text=content,
        channel=channel,
    )

    return {"ok": True, "queued": conv_id}


# ── Live feed ─────────────────────────────────────────────────────────────────

@router.get("/conversations/active")
def active_conversations(db: Session = Depends(get_db)):
    """Return leads with an active Chatwoot conversation, newest first.

    Used by the VA sidebar widget to show the founder which conversations
    the AI is currently handling.
    """
    leads = db.scalars(
        select(Lead)
        .where(Lead.chatwoot_conversation_id.is_not(None))
        .order_by(Lead.last_contacted_at.desc())
        .limit(20)
    ).all()

    return [
        {
            "lead_id":                l.shop_id,
            "shop_name":              l.shop_name,
            "chatwoot_conversation_id": l.chatwoot_conversation_id,
            "stage":                  l.stage or "cold",
            "stage_label":            STAGE_LABELS.get(l.stage or "cold", l.stage or "cold"),
            "last_contacted_at": (
                l.last_contacted_at.isoformat() if l.last_contacted_at else None
            ),
            "last_message": (
                (l.conversation_history or [])[-1].get("content", "")[:120]
                if l.conversation_history else ""
            ),
            "last_role": (
                (l.conversation_history or [])[-1].get("role", "")
                if l.conversation_history else ""
            ),
        }
        for l in leads
    ]


# ── Take-over ─────────────────────────────────────────────────────────────────

@router.post("/conversations/{chatwoot_conversation_id}/takeover")
async def takeover_conversation(
    chatwoot_conversation_id: str,
    db: Session = Depends(get_db),
):
    """Founder takes over an AI-handled conversation.

    Adds a private note and puts the conversation in 'open' status so it
    routes to the human inbox.
    """
    lead = db.scalars(
        select(Lead).where(Lead.chatwoot_conversation_id == chatwoot_conversation_id)
    ).first()
    if not lead:
        raise HTTPException(status_code=404, detail="conversation not found")

    try:
        await chatwoot_client.add_private_note(
            conversation_id=chatwoot_conversation_id,
            text="👤 Founder รับช่วงต่อแล้ว — AI จะหยุดตอบอัตโนมัติในบทสนทนานี้",
        )
        # Set to 'open' so it shows in the human inbox
        from app.config import get_settings
        settings = get_settings()
        if settings.chatwoot_enabled:
            import httpx
            async with httpx.AsyncClient(timeout=10) as client:
                await client.patch(
                    f"{chatwoot_client._base(settings)}/conversations/{chatwoot_conversation_id}",
                    headers=chatwoot_client._headers(settings),
                    json={"status": "open"},
                )
    except Exception as exc:  # noqa: BLE001
        logger.warning("takeover failed for conv=%s: %s", chatwoot_conversation_id, exc)

    return {"ok": True, "lead_id": lead.shop_id}
