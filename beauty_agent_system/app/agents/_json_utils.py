"""Shared helper for parsing the strict-JSON contract every worker agent
prompt requires (see prompts.py _COMMON_OUTPUT_CONTRACT)."""
from __future__ import annotations

import json


def parse_json_object(raw: str) -> dict:
    """Models sometimes wrap JSON in ```json fences despite instructions --
    strip those before parsing rather than failing the whole call."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    return json.loads(text)


def empty_result(agent_name: str, label_th: str, *, missing_info: list[str]) -> dict:
    """Fallback shape used whenever the LLM is unavailable or returns
    unparsable output -- never fabricate findings, just say what's missing."""
    return {
        "agent_name": agent_name,
        "label_th": label_th,
        "key_findings": [],
        "founder_actions": [],
        "ai_actions": [],
        "missing_info": missing_info,
        "draft_message": None,
        "draft_reasoning": None,
    }
