"""Chatwoot webhook -- the single entry point for Facebook/Line/Email chat."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.graph import run_graph
from app.chatwoot_client import send_message, verify_webhook_signature
from app.database import get_db
from app.models import Lead

logger = logging.getLogger("beauty_agent_system.webhook")
router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _get_or_create_lead(db: Session, *, shop_name: str, facebook_url: str | None, line_id: str | None) -> Lead:
    query = select(Lead)
    if facebook_url:
        query = query.where(Lead.facebook_url == facebook_url)
    elif line_id:
        query = query.where(Lead.line_id == line_id)
    lead = db.scalar(query)
    if lead:
        return lead
    lead = Lead(shop_name=shop_name, facebook_url=facebook_url, line_id=line_id)
    db.add(lead)
    db.commit()
    return lead


@router.post("/chatwoot")
async def chatwoot_webhook(request: Request, db: Session = Depends(get_db)) -> dict:
    raw_body = await request.body()
    signature = request.headers.get("X-Chatwoot-Signature")
    if not verify_webhook_signature(raw_body, signature):
        raise HTTPException(status_code=401, detail="invalid webhook signature")

    payload = await request.json()

    # Chatwoot's real payload shape is deeper; this pulls the fields this
    # system needs and degrades gracefully if the shape differs (stub mode).
    content = payload.get("content") or payload.get("message", {}).get("content") or ""
    sender = payload.get("sender") or {}
    shop_name = sender.get("name") or "Unknown shop"
    conversation_id = str(payload.get("conversation", {}).get("id") or payload.get("conversation_id") or "")
    channel = payload.get("channel") or "unknown"

    lead = _get_or_create_lead(db, shop_name=shop_name, facebook_url=sender.get("facebook_url"), line_id=sender.get("line_id"))
    lead.conversation_history = [*(lead.conversation_history or []), {"role": "customer", "content": content}]
    db.commit()

    state = await run_graph(
        db,
        {
            "shop_id": lead.shop_id,
            "conversation_id": conversation_id,
            "incoming_message": content,
            "channel": channel,
            "extra": {},
        },
    )

    if state.get("auto_send") and state.get("draft_message"):
        await send_message(conversation_id=conversation_id, shop_id=lead.shop_id, text=state["draft_message"])
        lead.conversation_history = [*(lead.conversation_history or []), {"role": "bot", "content": state["draft_message"]}]
        db.commit()

    return {
        "shop_id": lead.shop_id,
        "intent": state.get("intent"),
        "agent_name": state.get("agent_name"),
        "auto_sent": bool(state.get("auto_send")),
        "requires_approval": bool(state.get("requires_approval")),
        "validation_notes": state.get("validation_notes"),
    }
