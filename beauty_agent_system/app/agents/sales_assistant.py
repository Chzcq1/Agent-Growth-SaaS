"""Agent 2: Sales Assistant.

Drafts ONE Messenger opening line for a lead/interested customer, anchored
on their pain point. Never sends anything itself -- the draft always waits
for the founder in the "รอตรวจ" section of the single-page office view.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.agents._json_utils import empty_result, parse_json_object
from app.agents.prompts import (
    REWORK_FEEDBACK_TEMPLATE,
    SALES_ASSISTANT_SYSTEM_PROMPT,
    SALES_ASSISTANT_USER_TEMPLATE,
)
from app.llm_client import LLMUnavailable, call_llm
from app.research import get_verified_case_study

AGENT_NAME = "sales_assistant"
LABEL_TH = "ผู้ช่วยขาย (Sales Assistant)"

KEYWORDS = (
    "ทักมา", "ราคา", "สนใจ", "สมัคร", "จองคิว", "เปิดร้าน", "แชท", "messenger",
    "คุยกับลูกค้า", "อยากรู้เพิ่ม", "ลูกค้าถาม",
)


def matches(text: str) -> bool:
    lowered = text.lower()
    return any(k in lowered for k in KEYWORDS)


async def run(db: Session, raw_text: str, feedback: str | None = None) -> dict:
    case_study = get_verified_case_study(db)
    user_prompt = SALES_ASSISTANT_USER_TEMPLATE.format(
        raw_text=raw_text,
        case_study=case_study["text"] if case_study else "ไม่มี",
    )
    if feedback:
        user_prompt += REWORK_FEEDBACK_TEMPLATE.format(feedback=feedback)
    try:
        raw = await call_llm(
            db,
            AGENT_NAME,
            SALES_ASSISTANT_SYSTEM_PROMPT,
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
        "draft_message": data.get("draft_message"),
        "draft_reasoning": data.get("draft_reasoning"),
    }
