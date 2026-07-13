"""Agent 2: Strategic Closer.

Follows the mandatory day-based follow-up table from the spec. Every draft
this agent produces MUST be written to ``pending_approvals`` -- it never
sends anything itself, no exceptions.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.agents.prompts import STRATEGIC_CLOSER_SYSTEM_PROMPT, STRATEGIC_CLOSER_USER_TEMPLATE
from app.llm_client import LLMUnavailable, call_llm
from app.models import Lead, LeadStatus, PendingApproval
from app.research import get_verified_case_study

AGENT_NAME = "strategic_closer"


def _days_since_contact(lead: Lead) -> int:
    anchor = lead.last_contacted_date or lead.created_at
    if anchor is None:
        return 0
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    return (now - anchor).days


def determine_stage(lead: Lead) -> str:
    """Maps a lead's current state to the day-based stage from the spec table."""
    days = _days_since_contact(lead)
    if lead.status == LeadStatus.NEW:
        return "day_1"
    if days > 7:
        return "ghosted"
    if days >= 7:
        return "day_7"
    if days >= 4:
        return "day_4"
    return "day_1"


async def draft_followup(db: Session, shop_id: int) -> dict:
    lead = db.get(Lead, shop_id)
    if not lead:
        return {"status": "error", "detail": "lead not found"}

    if lead.status in (LeadStatus.GHOSTED, LeadStatus.BLOCKED):
        return {"status": "skipped", "detail": f"lead status is {lead.status}"}

    stage = determine_stage(lead)

    if stage == "ghosted":
        lead.status = LeadStatus.GHOSTED
        lead.next_followup_date = None
        db.commit()
        return {"status": "ghosted", "shop_id": shop_id}

    case_study = None
    if stage == "day_4":
        case_study = get_verified_case_study(db)

    pain_points = (lead.pain_points or {}).get("summary", "unknown -- insufficient research data")

    try:
        raw = await call_llm(
            db,
            AGENT_NAME,
            STRATEGIC_CLOSER_SYSTEM_PROMPT,
            STRATEGIC_CLOSER_USER_TEMPLATE.format(
                shop_name=lead.shop_name,
                stage=stage,
                pain_points=pain_points,
                case_study=case_study["text"] if case_study else "none",
            ),
        )
    except LLMUnavailable as exc:
        return {"status": "llm_unavailable", "shop_id": shop_id, "detail": str(exc)}

    if "---REASONING---" in raw:
        message, reasoning = raw.split("---REASONING---", 1)
    else:
        message, reasoning = raw, "(no explicit reasoning returned by model)"

    approval = PendingApproval(
        shop_id=shop_id,
        agent_name=AGENT_NAME,
        draft_message=message.strip(),
        reasoning=f"stage={stage}; " + reasoning.strip(),
        status="pending",
    )
    db.add(approval)

    next_status = {
        "day_1": LeadStatus.CONTACTED,
        "day_4": LeadStatus.FOLLOWUP_1,
        "day_7": LeadStatus.FOLLOWUP_2,
    }.get(stage, lead.status)
    lead.status = next_status
    lead.next_followup_date = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=3)
    db.commit()

    return {"status": "queued_for_approval", "shop_id": shop_id, "approval_id": approval.id, "stage": stage}
