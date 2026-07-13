"""Supervisor Agent -- the single entry point of the Virtual Office.

Reads whatever raw blob the founder pasted, decides which of the 6 worker
agents are relevant (never all 6 by default -- only the ones the input
actually touches), runs them, and synthesizes ONE combined answer: Key
Findings + a two-bucket Action Plan (Founder must do / AI will do next).

Routing is a cheap keyword heuristic first (protects the GitHub Models
quota, same philosophy as the old classify_intent) and only falls back to
one LLM call when no keyword matched anything -- free text from a founder
won't always contain an obvious keyword.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents import (
    customer_success_agent,
    demo_agent,
    lead_hunter,
    onboarding_agent,
    product_analyst_agent,
    sales_assistant,
)
from app.agents._json_utils import parse_json_object
from app.agents.prompts import SUPERVISOR_ROUTE_SYSTEM_PROMPT, SUPERVISOR_ROUTE_USER_TEMPLATE
from app.llm_client import LLMUnavailable, call_llm
from app.models import AgentFeedback, PendingApproval

logger = logging.getLogger("beauty_agent_system.supervisor")

AGENT_MODULES = {
    "lead_hunter": lead_hunter,
    "sales_assistant": sales_assistant,
    "demo_agent": demo_agent,
    "onboarding_agent": onboarding_agent,
    "customer_success_agent": customer_success_agent,
    "product_analyst_agent": product_analyst_agent,
}


async def select_relevant_agents(db: Session, raw_text: str) -> list[str]:
    """Returns the list of agent keys (from AGENT_MODULES) relevant to
    raw_text. Keyword heuristics first; LLM fallback only if none matched."""
    matched = [name for name, module in AGENT_MODULES.items() if module.matches(raw_text)]
    if matched:
        return matched

    try:
        raw = await call_llm(
            db,
            "supervisor",
            SUPERVISOR_ROUTE_SYSTEM_PROMPT,
            SUPERVISOR_ROUTE_USER_TEMPLATE.format(raw_text=raw_text),
        )
        selected = parse_json_object(raw) if raw.strip().startswith("{") else __import__("json").loads(raw)
    except Exception as exc:  # noqa: BLE001 -- routing failure must not crash the request
        logger.warning("supervisor routing LLM call failed: %s", exc)
        return []

    if not isinstance(selected, list):
        return []
    return [name for name in selected if name in AGENT_MODULES]


def _recent_sales_tone_note(db: Session) -> str | None:
    """Self-improvement, folded into the next round's Key Findings instead
    of a separate 'Weekly Insights' page: if sales_assistant drafts have
    been rejected a lot in the last 7 days, surface that pattern now."""
    week_ago = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=7)
    rows = db.scalars(
        select(AgentFeedback)
        .join(PendingApproval, AgentFeedback.approval_id == PendingApproval.id)
        .where(PendingApproval.agent_name == "sales_assistant")
        .where(AgentFeedback.created_at >= week_ago)
    ).all()
    if len(rows) < 3:
        return None
    rejected = sum(1 for r in rows if r.outcome in ("ignored", "rejected", "blocked"))
    if rejected / len(rows) > 0.5:
        return (
            f"ข้อสังเกตจาก 7 วันที่ผ่านมา: ข้อความร่างของ Sales Assistant ถูกปฏิเสธ/ไม่ส่ง "
            f"{rejected}/{len(rows)} ครั้ง -- ควรลองปรับโทนให้เปิดด้วยคำถาม Pain Point ล้วนๆ "
            f"และตัดทุกคำที่ฟังดูเหมือนขายทิ้งไปอีก"
        )
    return None


async def run_office(db: Session, raw_text: str) -> dict:
    """Main entry point: classify -> run relevant agents -> synthesize.

    Returns a dict with keys: agents_run, key_findings, founder_actions,
    ai_actions, missing_info, draft (optional), approval_id (optional).
    """
    raw_text = (raw_text or "").strip()
    if not raw_text:
        return {
            "agents_run": [],
            "key_findings": [],
            "founder_actions": [],
            "ai_actions": [],
            "missing_info": ["ยังไม่ได้แปะข้อมูลอะไรเข้ามา"],
            "draft": None,
            "approval_id": None,
        }

    selected = await select_relevant_agents(db, raw_text)
    if not selected:
        return {
            "agents_run": [],
            "key_findings": [],
            "founder_actions": [],
            "ai_actions": [],
            "missing_info": [
                "ข้อมูลนี้ไม่เข้าเงื่อนไขของ Agent ตัวใดใน Virtual Office (Lead/Sales/Demo/"
                "Onboarding/Customer Success/Product) -- ลองระบุให้ชัดเจนขึ้นว่าเป็นเรื่องอะไร"
            ],
            "draft": None,
            "approval_id": None,
        }

    import asyncio

    results = await asyncio.gather(
        *(AGENT_MODULES[name].run(db, raw_text) for name in selected)
    )

    key_findings: list[str] = []
    founder_actions: list[str] = []
    ai_actions: list[str] = []
    missing_info: list[str] = []
    draft: dict | None = None
    approval_id: int | None = None

    for result in results:
        label = result["label_th"]
        for finding in result["key_findings"]:
            key_findings.append(f"[{label}] {finding}")
        founder_actions.extend(result["founder_actions"])
        ai_actions.extend(result["ai_actions"])
        for missing in result["missing_info"]:
            missing_info.append(f"[{label}] {missing}")

        if result["agent_name"] == "sales_assistant" and result.get("draft_message"):
            approval = PendingApproval(
                agent_name="sales_assistant",
                draft_message=result["draft_message"],
                reasoning=result.get("draft_reasoning") or "(ไม่มีคำอธิบายเพิ่มเติม)",
                status="pending",
            )
            db.add(approval)
            db.commit()
            draft = {
                "message": result["draft_message"],
                "reasoning": result.get("draft_reasoning"),
                "approval_id": approval.id,
            }
            approval_id = approval.id
            founder_actions.append("ตรวจ/แก้/อนุมัติข้อความร่างจาก Sales Assistant ก่อนส่งลูกค้าจริง")

    tone_note = _recent_sales_tone_note(db)
    if tone_note:
        key_findings.append(f"[Supervisor] {tone_note}")

    return {
        "agents_run": [AGENT_MODULES[name].LABEL_TH for name in selected],
        "key_findings": key_findings,
        "founder_actions": founder_actions,
        "ai_actions": ai_actions,
        "missing_info": missing_info,
        "draft": draft,
        "approval_id": approval_id,
    }
