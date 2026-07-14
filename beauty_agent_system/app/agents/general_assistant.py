"""Agent 8: General Assistant -- fallback for anything outside the 7
CSC-specific agents' scope, and the only agent that can see attached images.

Used by the Supervisor when no beauty-agent keyword matched at all, or when
the founder attached an image (vision needs a dedicated call regardless of
which other agents also ran). Returns a single freeform reply in
`answer_text` instead of the structured key_findings/founder_actions shape
-- a general question doesn't fit that mold.
"""
from __future__ import annotations

import base64
import mimetypes
import os

from sqlalchemy.orm import Session

from app.agents.prompts import (
    GENERAL_ASSISTANT_SYSTEM_PROMPT,
    GENERAL_ASSISTANT_USER_TEMPLATE,
    REWORK_FEEDBACK_TEMPLATE,
)
from app.customer_context import format_context_for_prompt
from app.llm_client import LLMUnavailable, call_llm, call_llm_stream

AGENT_NAME = "general_assistant"
LABEL_TH = "ผู้ช่วยทั่วไป (General Assistant)"

# Marker used by supervisor.py so this module gets special handling
# (always eligible as a fallback, and the only one offered image_urls).
SUPPORTS_IMAGES = True

# Any non-empty text/image always "matches" -- this agent is only ever
# selected explicitly by the Supervisor's fallback logic, never by keyword.
KEYWORDS: tuple[str, ...] = ()


def matches(text: str) -> bool:  # noqa: ARG001 -- never keyword-routed
    return False


def _to_data_url(relative_path: str) -> str | None:
    """Reads an uploaded image off disk and returns a base64 data: URL --
    GitHub Models can't reach our localhost, so we can't just pass the URL."""
    abs_path = os.path.join("app", relative_path.lstrip("/"))
    if not os.path.isfile(abs_path):
        return None
    mime, _ = mimetypes.guess_type(abs_path)
    mime = mime or "image/png"
    with open(abs_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


async def run(
    db: Session,
    raw_text: str,
    feedback: str | None = None,
    image_urls: list[str] | None = None,
    *,
    customer_context: dict | None = None,
) -> dict:
    ctx_block = format_context_for_prompt(customer_context)
    user_prompt = ctx_block + GENERAL_ASSISTANT_USER_TEMPLATE.format(
        raw_text=raw_text or "(ไม่มีข้อความ ดูจากรูปที่แนบมาแทน)"
    )
    if feedback:
        user_prompt += REWORK_FEEDBACK_TEMPLATE.format(feedback=feedback)

    data_urls = [u for u in (_to_data_url(p) for p in (image_urls or [])) if u]

    try:
        answer = await call_llm(
            db,
            AGENT_NAME,
            GENERAL_ASSISTANT_SYSTEM_PROMPT,
            user_prompt,
            image_data_urls=data_urls or None,
        )
    except LLMUnavailable as exc:
        return {
            "agent_name": AGENT_NAME,
            "label_th": LABEL_TH,
            "key_findings": [],
            "content_ideas": [],
            "founder_actions": [],
            "ai_actions": [],
            "missing_info": [f"AI ไม่พร้อมใช้งาน: {exc}"],
            "clarifying_question": None,
            "observations": [],
            "thinking": None,
            "draft_message": None,
            "draft_reasoning": None,
            "answer_text": None,
        }

    return {
        "agent_name": AGENT_NAME,
        "label_th": LABEL_TH,
        "key_findings": [],
        "content_ideas": [],
        "founder_actions": [],
        "ai_actions": [],
        "missing_info": [],
        "clarifying_question": None,
        "observations": [],
        "thinking": None,
        "draft_message": None,
        "draft_reasoning": None,
        "answer_text": answer.strip(),
    }


def _empty_result(error_msg: str) -> dict:
    return {
        "agent_name": AGENT_NAME, "label_th": LABEL_TH,
        "key_findings": [], "content_ideas": [], "founder_actions": [], "ai_actions": [],
        "missing_info": [error_msg], "clarifying_question": None, "observations": [],
        "thinking": None, "draft_message": None, "draft_reasoning": None, "answer_text": None,
    }


async def run_stream(
    db: Session,
    raw_text: str,
    *,
    image_urls: list[str] | None = None,
    customer_context: dict | None = None,
):
    """Async generator — streams the plain-text answer token by token.

    Yields ``(chunk: str, result: None)`` for each token chunk, then
    ``(None, result: dict)`` as the very last item once the LLM is done.
    The caller (supervisor) forwards chunk events to SSE and uses the final
    result dict to build the OfficeRun record.
    """
    ctx_block = format_context_for_prompt(customer_context)
    user_prompt = ctx_block + GENERAL_ASSISTANT_USER_TEMPLATE.format(
        raw_text=raw_text or "(ไม่มีข้อความ ดูจากรูปที่แนบมาแทน)"
    )
    data_urls = [u for u in (_to_data_url(p) for p in (image_urls or [])) if u]

    accumulated: list[str] = []
    try:
        async for chunk in call_llm_stream(
            db, AGENT_NAME, GENERAL_ASSISTANT_SYSTEM_PROMPT, user_prompt,
            image_data_urls=data_urls or None,
        ):
            accumulated.append(chunk)
            yield (chunk, None)
    except LLMUnavailable as exc:
        yield (None, _empty_result(f"AI ไม่พร้อมใช้งาน: {exc}"))
        return

    answer = "".join(accumulated).strip()
    yield (None, {
        "agent_name": AGENT_NAME, "label_th": LABEL_TH,
        "key_findings": [], "content_ideas": [], "founder_actions": [], "ai_actions": [],
        "missing_info": [], "clarifying_question": None, "observations": [],
        "thinking": None, "draft_message": None, "draft_reasoning": None,
        "answer_text": answer,
    })
