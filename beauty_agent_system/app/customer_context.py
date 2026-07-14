"""Per-customer context for AI agents.

When an incoming message (from Chatwoot, Facebook, TikTok, or a manually
linked run) carries a lead_id, this module builds a structured context dict
that agents can use to:
  - know the customer's current stage (cold → closed → post_sale)
  - see the last N messages so they don't repeat or contradict themselves
  - know key facts (shop type, pain points, contact info)

Agents receive this via an injected text block in their user prompt.
The supervisor calls update_lead_stage() when an agent signals a transition.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import Lead, LeadStage

# How many past messages to include in context (older ones add noise)
MAX_HISTORY_MESSAGES = 20

# Human-readable labels for stage values (shown in the UI)
STAGE_LABELS: dict[str, str] = {
    "cold":        "ยังไม่เคยคุย",
    "interested":  "สนใจ/กำลังพิจารณา",
    "negotiating": "กำลังต่อรอง",
    "closed":      "ปิดการขายแล้ว",
    "post_sale":   "ดูแลหลังขาย",
    "churned":     "เลิกใช้/หายไป",
}

STAGE_COLORS: dict[str, str] = {
    "cold":        "#78716c",  # muted
    "interested":  "#b8862f",  # warm amber
    "negotiating": "#3b6fa0",  # blue
    "closed":      "#3f7d5c",  # green
    "post_sale":   "#5b4ea8",  # purple
    "churned":     "#b3564a",  # red
}


def build_customer_context(db: Session, lead_id: int) -> dict | None:
    """Return a context dict for the given lead, or None if not found."""
    lead = db.get(Lead, lead_id)
    if not lead:
        return None

    history = (lead.conversation_history or [])[-MAX_HISTORY_MESSAGES:]
    stage_val = lead.stage.value if isinstance(lead.stage, LeadStage) else (lead.stage or "cold")

    return {
        "lead_id":          lead_id,
        "shop_name":        lead.shop_name,
        "stage":            stage_val,
        "stage_label":      STAGE_LABELS.get(stage_val, stage_val),
        "facebook_url":     lead.facebook_url,
        "line_id":          lead.line_id,
        "pain_points":      lead.pain_points or {},
        "last_contacted_at": (
            lead.last_contacted_at.isoformat() if lead.last_contacted_at else None
        ),
        "recent_messages":  history,
        "total_messages":   len(lead.conversation_history or []),
    }


def format_context_for_prompt(ctx: dict | None) -> str:
    """Return a human-readable block to prepend to an agent's user prompt.

    Returns an empty string when ctx is None so callers can always do::

        prompt = format_context_for_prompt(ctx) + base_prompt
    """
    if not ctx:
        return ""

    lines = [
        "=== ข้อมูลลูกค้าคนนี้ (จากฐานข้อมูล) ===",
        f"ร้าน: {ctx['shop_name']}",
        f"สถานะปัจจุบัน: {ctx['stage_label']} ({ctx['stage']})",
    ]
    if ctx.get("facebook_url"):
        lines.append(f"Facebook: {ctx['facebook_url']}")
    if ctx.get("line_id"):
        lines.append(f"Line ID: {ctx['line_id']}")
    if ctx.get("pain_points"):
        lines.append(f"Pain points ที่รู้: {ctx['pain_points']}")
    if ctx.get("last_contacted_at"):
        lines.append(f"ติดต่อล่าสุด: {ctx['last_contacted_at'][:10]}")

    msgs = ctx.get("recent_messages") or []
    if msgs:
        lines.append(f"\nบทสนทนาล่าสุด ({len(msgs)} ข้อความ):")
        for msg in msgs:
            role_raw = msg.get("role", "")
            role = "ลูกค้า" if role_raw in ("user", "customer") else "AI"
            content = (msg.get("content") or "")[:300]
            lines.append(f"  [{role}] {content}")
    else:
        lines.append("(ยังไม่มีบทสนทนาก่อนหน้า)")

    lines.append(
        "=== ใช้ข้อมูลนี้เพื่อตอบให้ตรงบริบทลูกค้าคนนี้"
        " ไม่ต้องพูดซ้ำสิ่งที่คุยไปแล้ว และอย่าแนะนำสิ่งที่ขัดกับบทสนทนาเดิม ==="
    )
    return "\n".join(lines) + "\n\n"


def update_lead_stage(db: Session, lead_id: int, new_stage: str) -> bool:
    """Change a lead's stage.  Returns True if the stage actually changed."""
    valid = {s.value for s in LeadStage}
    if new_stage not in valid:
        return False
    lead = db.get(Lead, lead_id)
    if not lead:
        return False
    old = lead.stage.value if isinstance(lead.stage, LeadStage) else lead.stage
    if old == new_stage:
        return False
    lead.stage = LeadStage(new_stage)
    lead.last_contacted_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    return True


def touch_lead(db: Session, lead_id: int) -> None:
    """Bump last_contacted_at without changing stage."""
    lead = db.get(Lead, lead_id)
    if lead:
        lead.last_contacted_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.commit()
