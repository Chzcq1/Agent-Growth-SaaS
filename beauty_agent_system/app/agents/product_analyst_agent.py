"""Agent 6: Product Analyst Agent.

Groups feedback the founder pasted and proposes a short roadmap note --
only within Booking/Deposit/Schedule/Customer Flow scope. Must refuse
anything that drifts into POS/Stock/ERP/HR/big CRM territory.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.agents._json_utils import empty_result, parse_json_object
from app.agents.prompts import (
    PRODUCT_ANALYST_AGENT_SYSTEM_PROMPT,
    PRODUCT_ANALYST_AGENT_USER_TEMPLATE,
    REWORK_FEEDBACK_TEMPLATE,
)
from app.llm_client import LLMUnavailable, call_llm

AGENT_NAME = "product_analyst_agent"
LABEL_TH = "นักวิเคราะห์ผลิตภัณฑ์ (Product Analyst Agent)"

KEYWORDS = (
    "feedback", "ฟีดแบ็ก", "เสนอฟีเจอร์", "อยากให้เพิ่ม", "roadmap", "บั๊ก", "bug",
    "ข้อเสนอแนะ", "อยากให้ปรับ",
)


def matches(text: str) -> bool:
    lowered = text.lower()
    return any(k in lowered for k in KEYWORDS)


async def run(db: Session, raw_text: str, feedback: str | None = None) -> dict:
    user_prompt = PRODUCT_ANALYST_AGENT_USER_TEMPLATE.format(raw_text=raw_text)
    if feedback:
        user_prompt += REWORK_FEEDBACK_TEMPLATE.format(feedback=feedback)
    try:
        raw = await call_llm(
            db,
            AGENT_NAME,
            PRODUCT_ANALYST_AGENT_SYSTEM_PROMPT,
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
        "thinking": data.get("thinking"),
        "draft_message": None,
        "draft_reasoning": None,
    }
