"""Agent 4: Onboarding Agent.

Checks whether the info the founder pasted reveals a point where a new
shop got stuck setting up (store setup, TOTP/verification, adding
services, first real use).
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.agents._json_utils import empty_result, parse_json_object
from app.agents.prompts import ONBOARDING_AGENT_SYSTEM_PROMPT, ONBOARDING_AGENT_USER_TEMPLATE
from app.llm_client import LLMUnavailable, call_llm

AGENT_NAME = "onboarding_agent"
LABEL_TH = "ผู้ช่วยการตั้งค่าเริ่มต้น (Onboarding Agent)"

KEYWORDS = (
    "onboarding", "ตั้งค่า", "totp", "เพิ่มบริการ", "สอนใช้", "เริ่มใช้งาน",
    "สมัครสมาชิก", "ยืนยันตัวตน", "ติดขัด",
)


def matches(text: str) -> bool:
    lowered = text.lower()
    return any(k in lowered for k in KEYWORDS)


async def run(db: Session, raw_text: str) -> dict:
    try:
        raw = await call_llm(
            db,
            AGENT_NAME,
            ONBOARDING_AGENT_SYSTEM_PROMPT,
            ONBOARDING_AGENT_USER_TEMPLATE.format(raw_text=raw_text),
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
        "draft_message": None,
        "draft_reasoning": None,
    }
