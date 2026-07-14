"""Content Strategist Agent — วางแผนหากลุ่มเป้าหมาย+คอนเทนต์ Facebook/TikTok แบบครบวงจร step-by-step."""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.agents._json_utils import empty_result, parse_json_object
from app.agents.prompts import (
    CONTENT_STRATEGIST_SYSTEM_PROMPT,
    CONTENT_STRATEGIST_USER_TEMPLATE,
    REWORK_FEEDBACK_TEMPLATE,
)
from app.llm_client import LLMUnavailable, call_llm

logger = logging.getLogger("beauty_agent_system.content_strategist")

LABEL_TH = "นักวางแผนคอนเทนต์ (Content Strategist)"

_KEYWORDS = [
    # เฉพาะ keyword ที่บ่งบอกว่า Founder ต้องการวางแผนคอนเทนต์/หากลุ่มเป้าหมายจริงๆ
    # ห้ามใส่ keyword กว้างๆ ที่แชร์กับ sales_assistant/lead_hunter
    "โพสต์", "คอนเทนต์", "content", "วางแผนคอนเทนต์", "แผนโพสต์",
    "facebook", "marketing", "มาร์เก็ต", "ประชาสัมพันธ์",
    "โปรโมท", "promotion", "กลยุทธ์คอนเทนต์", "engagement",
    "ฟีด", "reach", "caption", "ไอเดียโพสต์", "สร้างคอนเทนต์",
    "tiktok", "ติ๊กต็อก", "ติ้กต๊อก", "คลิป", "แฮชแท็ก", "hashtag",
    "สอดส่อง", "หากลุ่มเป้าหมาย", "ระบุกลุ่มเป้าหมาย", "ปิดการขาย",
]


def matches(raw_text: str) -> bool:
    low = raw_text.lower()
    return any(kw in low for kw in _KEYWORDS)


async def run(db: Session, raw_text: str, *, feedback: str | None = None) -> dict:
    user_prompt = CONTENT_STRATEGIST_USER_TEMPLATE.format(raw_text=raw_text)
    if feedback:
        user_prompt += REWORK_FEEDBACK_TEMPLATE.format(feedback=feedback)

    try:
        raw = await call_llm(
            db, "content_strategist",
            CONTENT_STRATEGIST_SYSTEM_PROMPT,
            user_prompt,
        )
        data = parse_json_object(raw)
    except (LLMUnavailable, ValueError, Exception) as exc:  # noqa: BLE001
        logger.warning("content_strategist failed: %s", exc)
        return empty_result(
            "content_strategist", LABEL_TH,
            missing_info=[f"AI ไม่พร้อมใช้งาน: {exc}"],
        )

    def safe_list(val) -> list:
        return val if isinstance(val, list) else []

    return {
        "agent_name": "content_strategist",
        "label_th": LABEL_TH,
        "thinking": data.get("thinking"),
        "key_findings": safe_list(data.get("key_findings")),
        "content_ideas": safe_list(data.get("content_ideas")),
        "founder_actions": safe_list(data.get("founder_actions")),
        "ai_actions": safe_list(data.get("ai_actions")),
        "missing_info": safe_list(data.get("missing_info")),
        "clarifying_question": data.get("clarifying_question"),
        "observations": safe_list(data.get("observations")),
        "draft_message": None,
        "draft_reasoning": None,
        # Fields specific to this agent (extracted by supervisor)
        "content_plan": safe_list(data.get("content_plan")),
        "target_profile": data.get("target_profile") or "",
        "pitch_timing": data.get("pitch_timing") or "",
        "product_pitch": data.get("product_pitch") or "",
    }
