"""Agent 1: Lead Hunter.

Analyzes whatever raw text the founder pasted (a Facebook group post, a
comment, a snippet of a lead conversation) and extracts pain points that
match the 5 ranked pain points in the business context. Never fetches
anything itself -- the founder pastes the content directly.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.agents._json_utils import empty_result, parse_json_object
from app.agents.prompts import (
    LEAD_HUNTER_SYSTEM_PROMPT,
    LEAD_HUNTER_USER_TEMPLATE,
    REWORK_FEEDBACK_TEMPLATE,
)
from app.llm_client import LLMUnavailable, call_llm

AGENT_NAME = "lead_hunter"
LABEL_TH = "นักล่าลีด (Lead Hunter)"

KEYWORDS = (
    "กลุ่ม", "เพจ", "คอมเมนต์", "comment", "ลีด", "lead", "โพสต์", "post",
    "facebook", "เฟซบุ๊ก", "สนใจ", "ทักมา", "ลูกค้าใหม่", "ร้านใหม่",
)


def matches(text: str) -> bool:
    lowered = text.lower()
    return any(k in lowered for k in KEYWORDS)


async def run(db: Session, raw_text: str, feedback: str | None = None) -> dict:
    user_prompt = LEAD_HUNTER_USER_TEMPLATE.format(raw_text=raw_text)
    if feedback:
        user_prompt += REWORK_FEEDBACK_TEMPLATE.format(feedback=feedback)
    try:
        raw = await call_llm(
            db,
            AGENT_NAME,
            LEAD_HUNTER_SYSTEM_PROMPT,
            user_prompt,
        )
        data = parse_json_object(raw)
    except (LLMUnavailable, ValueError) as exc:
        result = empty_result(AGENT_NAME, LABEL_TH, missing_info=[f"AI ไม่พร้อมใช้งาน: {exc}"])
        return result

    return {
        "agent_name": AGENT_NAME,
        "label_th": LABEL_TH,
        "key_findings": data.get("key_findings") or [],
        "content_ideas": data.get("content_ideas") or [],
        "founder_actions": data.get("founder_actions") or [],
        "ai_actions": data.get("ai_actions") or [],
        "missing_info": data.get("missing_info") or [],
        "clarifying_question": data.get("clarifying_question"),
        "observations": data.get("observations") or [],
        "thinking": data.get("thinking"),
        "draft_message": None,
        "draft_reasoning": None,
    }
