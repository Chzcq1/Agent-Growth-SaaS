"""Agent 3: Demo Agent.

Prepares the founder to answer a prospect's feature/package questions --
selling the strengths (self-booking, deposits, less chat load, 24h booking),
not a laundry list of minor features. Explicitly flags anything out of
scope (POS/Stock/ERP/HR/big CRM) if the customer asked about it.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.agents._json_utils import empty_result, parse_json_object
from app.agents.prompts import DEMO_AGENT_SYSTEM_PROMPT, DEMO_AGENT_USER_TEMPLATE
from app.llm_client import LLMUnavailable, call_llm

AGENT_NAME = "demo_agent"
LABEL_TH = "ผู้ช่วยสาธิตสินค้า (Demo Agent)"

KEYWORDS = (
    "ฟีเจอร์", "feature", "เทียบแพ็กเกจ", "แพ็กเกจ", "package", "demo", "สาธิต",
    "เปรียบเทียบ", "ราคาแพ็กเกจ",
)


def matches(text: str) -> bool:
    lowered = text.lower()
    return any(k in lowered for k in KEYWORDS)


async def run(db: Session, raw_text: str) -> dict:
    try:
        raw = await call_llm(
            db,
            AGENT_NAME,
            DEMO_AGENT_SYSTEM_PROMPT,
            DEMO_AGENT_USER_TEMPLATE.format(raw_text=raw_text),
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
