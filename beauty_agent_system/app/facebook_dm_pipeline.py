"""AI pipeline for autonomous Facebook Messenger DM replies.

Mirrors app/chatwoot_pipeline.py's confident-vs-escalate design, adapted for
Messenger (no external inbox to hand off to -- escalation surfaces in the
founder's own "Facebook" sidebar panel as a pending reply instead of a
Chatwoot private note).

Flow for every incoming DM (called from the webhook receiver as a
BackgroundTask, so the HTTP response to Meta returns immediately):
  1. Find or create a ``Lead`` linked to this Messenger PSID.
  2. Call ``generate_reply()`` -- the same short-reply LLM prompt used for
     Chatwoot (channel-agnostic: Messenger/Instagram/Line are interchangeable
     inputs to that prompt).
  3. confidence high enough (assign_to_human == False) -> send immediately.
  4. otherwise -> create a PendingApproval row; the founder sees it, edits if
     needed, and sends it from the UI (see app/routers/facebook.py
     /facebook/dm/pending, /facebook/dm/{id}/send, /facebook/dm/{id}/dismiss).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import facebook_client
from app.agents._json_utils import parse_json_object
from app.agents.prompts import CHATWOOT_REPLY_SYSTEM_PROMPT, CHATWOOT_REPLY_USER_TEMPLATE
from app.customer_context import (
    build_customer_context,
    format_context_for_prompt,
    update_lead_stage,
    STAGE_LABELS,
)
from app.llm_client import LLMUnavailable, call_llm
from app.models import Lead, LeadStage, PendingApproval

logger = logging.getLogger("beauty_agent_system.facebook_dm_pipeline")

# Same threshold as the Chatwoot pipeline -- keeps "when does the founder get
# asked" consistent across every channel the AI replies on.
AUTO_REPLY_THRESHOLD = 0.65


# ── Lead management ───────────────────────────────────────────────────────────

def _find_or_create_lead_by_psid(db: Session, psid: str, contact_name: str) -> Lead:
    lead = db.scalars(select(Lead).where(Lead.facebook_psid == psid)).first()
    if lead:
        return lead

    lead = Lead(
        shop_name=contact_name or "ลูกค้า Facebook",
        stage="cold",
        source="facebook_dm",
        facebook_psid=psid,
        conversation_history=[],
        pain_points={},
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    logger.info("Created new lead shop_id=%s for Facebook psid=%s", lead.shop_id, psid)
    return lead


def append_to_history(db: Session, lead: Lead, role: str, content: str) -> None:
    history = list(lead.conversation_history or [])
    history.append({
        "role": role,
        "content": content,
        "ts": datetime.now(timezone.utc).isoformat(),
    })
    lead.conversation_history = history[-100:]
    lead.last_contacted_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()


# ── AI reply generation (reuses the Chatwoot reply prompt -- it's already
#    written to be channel-agnostic across Messenger/Instagram/Line) ─────────

async def generate_reply(db: Session, lead: Lead, message_text: str) -> dict:
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
            "facebook_dm_reply",
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


# ── Main handler (called from the webhook's BackgroundTask) ──────────────────

async def handle_incoming_dm(
    db: Session,
    *,
    psid: str,
    contact_name: str,
    message_text: str,
) -> None:
    lead = _find_or_create_lead_by_psid(db, psid, contact_name)
    append_to_history(db, lead, "user", message_text)

    result = await generate_reply(db, lead, message_text)
    reply_text = result.get("reply") or ""
    confidence = result.get("confidence", 0.0)
    assign_to_human = result.get("assign_to_human", True)
    suggested_stage = result.get("suggested_stage")
    reason = result.get("reason_for_handoff") or ""

    logger.info(
        "DM reply generated psid=%s confidence=%.2f assign_to_human=%s",
        psid, confidence, assign_to_human,
    )

    if not assign_to_human and reply_text:
        try:
            await facebook_client.send_dm(psid, reply_text)
            append_to_history(db, lead, "assistant", reply_text)
            logger.info("Auto-reply sent psid=%s", psid)
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to send DM psid=%s: %s", psid, exc)
            assign_to_human = True
            reason = f"ส่งข้อความล้มเหลว: {exc}"

    if assign_to_human:
        note_parts = [f"confidence={confidence:.0%}"]
        if reason:
            note_parts.append(reason)
        approval = PendingApproval(
            shop_id=lead.shop_id,
            agent_name="facebook_dm_reply",
            draft_message=reply_text or None,
            reasoning=f"ลูกค้าถาม: {message_text[:300]}\n({' / '.join(note_parts)})",
            status="pending",
        )
        db.add(approval)
        db.commit()
        logger.info("DM escalated to founder: approval_id=%s psid=%s", approval.id, psid)

    if suggested_stage and suggested_stage in {s.value for s in LeadStage}:
        changed = update_lead_stage(db, lead.shop_id, suggested_stage)
        if changed:
            logger.info("Lead shop_id=%s stage -> %s (psid=%s)", lead.shop_id, suggested_stage, psid)
