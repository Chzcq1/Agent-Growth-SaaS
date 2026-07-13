"""Shared LangGraph state passed between Supervisor and worker agents."""
from __future__ import annotations

from typing import Any, Literal, TypedDict

Intent = Literal["lead_analysis", "sales_followup", "support_question", "unknown"]


class AgentState(TypedDict, total=False):
    shop_id: int | None
    conversation_id: str | None
    incoming_message: str | None
    channel: str | None

    intent: Intent
    agent_name: str | None

    draft_message: str | None
    reasoning: str | None
    kb_answer_found: bool
    requires_approval: bool
    auto_send: bool

    validated: bool
    validation_notes: list[str]

    error: str | None
    extra: dict[str, Any]
