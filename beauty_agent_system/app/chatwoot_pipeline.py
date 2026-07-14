"""AI pipeline for autonomous Chatwoot inbox replies (Task #6).

Flow for every incoming customer message:
  1. Find or create a ``Lead`` record linked to this Chatwoot conversation.
  2. Load customer context (stage, history) from Task #5 infrastructure.
  3. Call ``generate_reply()`` — a dedicated lightweight LLM call that returns
     a short Thai reply plus a confidence score and optional stage suggestion.
  4. If confidence >= AUTO_REPLY_THRESHOLD → send reply via Chatwoot API.
  5. If confidence < threshold → add draft as private note + set conv to
     pending so it surfaces in the founder's human inbox.
  6. Append the exchange to the lead's ``conversation_history``.
  7. Update lead stage if the agent suggested a change.

Design choices:
- BackgroundTask is used by the webhook endpoint so the HTTP response (200)
  returns immediately without waiting for the LLM.
- A dedicated reply prompt is used instead of the full 8-agent VA pipeline:
  the VA pipeline is designed for analysis; this needs a short conversational
  reply in < 30 s.
- Auto-reply is gated behind ``chatwoot_enabled`` — when the stub is active
  the pipeline still runs (logs + DB updates) but never sends to Chatwoot.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import chatwoot_client
from app.agents.prompts import CHATWOOT_REPLY_SYSTEM_PROMPT, CHATWOOT_REPLY_USER_TEMPLATE
from app.agents._json_utils import parse_json_object
from app.customer_context import (
    build_customer_context,
    format_context_for_prompt,
    update_lead_stage,
    STAGE_LABELS,
)
from app.llm_client import LLMUnavailable, call_llm
from app.models import Lead, LeadStage

logger = logging.getLogger("beauty_agent_system.chatwoot_pipeline")

# Confidence score threshold: at or above this value the AI sends the reply
# automatically; below this it escalates to the founder.
AUTO_REPLY_THRESHOLD = 0.65


# ── Lead management ───────────────────────────────────────────────────────────

def _find_lead_by_chatwoot(db: Session, chatwoot_conversation_id: str) -> Lead | None:
    return db.scalars(
        select(Lead).where(Lead.chatwoot_conversation_id == chatwoot_conversation_id)
    ).first()


def _find_or_create_lead(
    db: Session,
    *,
    chatwoot_conversation_id: str,
    chatwoot_contact_id: str | None,
    contact_name: str,
    contact_phone: str | None,
    channel: str,
) -> Lead:
    """Return the existing lead linked to this conversation, or create one."""
    lead = _find_lead_by_chatwoot(db, chatwoot_conversation_id)
    if lead:
        return lead

    # Try to find by contact_id if present
    if chatwoot_contact_id:
        lead = db.scalars(
            select(Lead).where(Lead.chatwoot_contact_id == chatwoot_contact_id)
        ).first()
        if lead:
            # Link this conversation to the existing lead
            lead.chatwoot_conversation_id = chatwoot_conversation_id
            db.commit()
            return lead

    # Create a new Lead record
    lead = Lead(
        shop_name=contact_name or "ลูกค้าใหม่",
        stage="cold",
        chatwoot_conversation_id=chatwoot_conversation_id,
        chatwoot_contact_id=chatwoot_contact_id,
        line_id=contact_phone if channel == "line" else None,
        conversation_history=[],
        pain_points={},
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    logger.info(
        "Created new lead shop_id=%s for Chatwoot conv=%s contact=%s",
        lead.shop_id, chatwoot_conversation_id, contact_name,
    )
    return lead


def _append_to_history(db: Session, lead: Lead, role: str, content: str) -> None:
    """Append a message to the lead's conversation_history JSON array."""
    history = list(lead.conversation_history or [])
    history.append({
        "role": role,
        "content": content,
        "ts": datetime.now(timezone.utc).isoformat(),
    })
    # Keep last 100 messages to avoid unbounded growth
    lead.conversation_history = history[-100:]
    lead.last_contacted_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()


# ── AI reply generation ───────────────────────────────────────────────────────

async def generate_reply(
    db: Session,
    lead: Lead,
    message_text: str,
) -> dict:
    """Ask the LLM for a short Thai reply plus metadata.

    Returns:
        {
          "reply": str,
          "confidence": float 0..1,
          "suggested_stage": str | None,
          "assign_to_human": bool,
          "reason_for_handoff": str | None,
        }
    """
    ctx = build_customer_context(db, lead.shop_id)
    ctx_block = format_context_for_prompt(ctx)

    current_stage = lead.stage or "cold"
    stage_label = STAGE_LABELS.get(current_stage, current_stage)

    user_prompt = ctx_block + CHATWOOT_REPLY_USER_TEMPLATE.format(
        shop_name=lead.shop_name,
        stage=current_stage,
        stage_label=stage_label,
        customer_message=message_text,
    )

    try:
        raw = await call_llm(
            db,
            "chatwoot_reply",
            CHATWOOT_REPLY_SYSTEM_PROMPT,
            user_prompt,
            temperature=0.3,
        )
        data = parse_json_object(raw)
    except (LLMUnavailable, ValueError) as exc:
        logger.warning("generate_reply failed: %s", exc)
        return {
            "reply": None,
            "confidence": 0.0,
            "suggested_stage": None,
            "assign_to_human": True,
            "reason_for_handoff": f"AI ไม่พร้อมใช้งาน: {exc}",
        }

    confidence = float(data.get("confidence") or 0.0)
    assign = bool(data.get("assign_to_human", confidence < AUTO_REPLY_THRESHOLD))

    return {
        "reply": (data.get("reply") or "").strip(),
        "confidence": confidence,
        "suggested_stage": data.get("suggested_stage"),
        "assign_to_human": assign,
        "reason_for_handoff": data.get("reason_for_handoff"),
    }


# ── Main handler (called from background task) ────────────────────────────────

async def handle_incoming_message(
    db: Session,
    *,
    chatwoot_conversation_id: str,
    chatwoot_contact_id: str | None = None,
    contact_name: str,
    contact_phone: str | None = None,
    message_text: str,
    channel: str = "unknown",
) -> None:
    """Process one incoming customer message end-to-end.

    This runs in a FastAPI BackgroundTask — the webhook endpoint has already
    returned 200 before this is called.
    """
    logger.info(
        "Incoming message conv=%s channel=%s from=%r: %.80s",
        chatwoot_conversation_id, channel, contact_name, message_text,
    )

    # ── 1. Find or create lead ───────────────────────────────────────────
    lead = _find_or_create_lead(
        db,
        chatwoot_conversation_id=chatwoot_conversation_id,
        chatwoot_contact_id=chatwoot_contact_id,
        contact_name=contact_name,
        contact_phone=contact_phone,
        channel=channel,
    )

    # Record customer message in history
    _append_to_history(db, lead, "user", message_text)

    # ── 2. Generate AI reply ─────────────────────────────────────────────
    result = await generate_reply(db, lead, message_text)

    reply_text = result.get("reply") or ""
    confidence = result.get("confidence", 0.0)
    assign_to_human = result.get("assign_to_human", True)
    suggested_stage = result.get("suggested_stage")
    reason = result.get("reason_for_handoff") or ""

    logger.info(
        "Reply generated conv=%s confidence=%.2f assign_to_human=%s",
        chatwoot_conversation_id, confidence, assign_to_human,
    )

    # ── 3. Route: auto-reply or escalate ─────────────────────────────────
    if not assign_to_human and reply_text:
        # Auto-send reply
        try:
            await chatwoot_client.send_message(
                conversation_id=chatwoot_conversation_id,
                shop_id=lead.shop_id,
                text=reply_text,
            )
            _append_to_history(db, lead, "assistant", reply_text)
            logger.info("Auto-reply sent conv=%s", chatwoot_conversation_id)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to send reply conv=%s: %s", chatwoot_conversation_id, exc)
            # Fall through to escalate
            assign_to_human = True
            reason = f"ส่ง reply ล้มเหลว: {exc}"

    if assign_to_human:
        # Add private note with draft (if we have one) so founder has context
        note_parts = [f"🤖 AI ไม่มั่นใจพอ (confidence={confidence:.0%})"]
        if reason:
            note_parts.append(f"เหตุผล: {reason}")
        if reply_text:
            note_parts.append(f"\n📝 Draft ที่ AI เตรียมไว้:\n{reply_text}")
        note_text = "\n".join(note_parts)

        try:
            await chatwoot_client.add_private_note(
                conversation_id=chatwoot_conversation_id,
                text=note_text,
            )
            await chatwoot_client.assign_to_human(
                conversation_id=chatwoot_conversation_id,
                reason=reason,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to escalate conv=%s: %s", chatwoot_conversation_id, exc)

    # ── 4. Update lead stage ─────────────────────────────────────────────
    if suggested_stage and suggested_stage in {s.value for s in LeadStage}:
        changed = update_lead_stage(db, lead.shop_id, suggested_stage)
        if changed:
            logger.info(
                "Lead shop_id=%s stage → %s (conv=%s)",
                lead.shop_id, suggested_stage, chatwoot_conversation_id,
            )
