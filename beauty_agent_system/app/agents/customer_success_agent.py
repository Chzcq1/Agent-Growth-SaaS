"""Agent 5: Customer Success Agent.

Checks whether shops already on the system are actually getting bookings,
and flags churn-risk shops -- based only on what the founder pasted (no
autonomous DB-wide health scan; the founder brings the signal in).
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.agents._json_utils import empty_result, parse_json_object
from app.agents.prompts import (
    CUSTOMER_SUCCESS_AGENT_SYSTEM_PROMPT,
    CUSTOMER_SUCCESS_AGENT_USER_TEMPLATE,
    REWORK_FEEDBACK_TEMPLATE,
)
from app.llm_client import LLMUnavailable, call_llm

AGENT_NAME = "customer_success_agent"
LABEL_TH = "ผู้ช่วยดูแลลูกค้าเก่า (Customer Success Agent)"

KEYWORDS = (
    "ร้านที่ใช้อยู่", "ยกเลิก", "เลิกใช้", "ไม่ได้เข้าระบบ", "หยุดใช้", "ต่ออายุ",
    "ร้านเดิม", "churn", "ไม่มีการจอง",
)


def matches(text: str) -> bool:
    lowered = text.lower()
    return any(k in lowered for k in KEYWORDS)


async def run(db: Session, raw_text: str, feedback: str | None = None) -> dict:
    user_prompt = CUSTOMER_SUCCESS_AGENT_USER_TEMPLATE.format(raw_text=raw_text)
    if feedback:
        user_prompt += REWORK_FEEDBACK_TEMPLATE.format(feedback=feedback)
    try:
        raw = await call_llm(
            db,
            AGENT_NAME,
            CUSTOMER_SUCCESS_AGENT_SYSTEM_PROMPT,
            user_prompt,
        )
        data = parse_json_object(raw)
    except (LLMUnavailable, ValueError) as exc:
        return empty_result(AGENT_NAME, LABEL_TH, missing_info=[f"AI ไม่พร้อมใช้งาน: {exc}"])

    return {
        "agent_name": AGENT_NAME,
        "label_th": LABEL_TH,
        "key_findings": data.get("key_findings") or [],
        "founder_actions": data.get("founder_actions") or [],
        "ai_actions": data.get("ai_actions") or [],
        "missing_info": data.get("missing_info") or [],
        "clarifying_question": data.get("clarifying_question"),
        "observations": data.get("observations") or [],
        "draft_message": None,
        "draft_reasoning": None,
    }
