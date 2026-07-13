"""Agent 4: Supervisor.

Routes incoming work to the right worker agent and validates every output
before it leaves the graph. The Supervisor is the ONLY decision-maker on
routing and final validation -- worker agents never talk to each other or
argue; they only report back to the Supervisor.
"""
from __future__ import annotations

from app.agents.state import AgentState

SALES_KEYWORDS = ("ราคา", "สนใจ", "trial", "ทดลอง", "สมัคร", "โปรโมชั่น")
SUPPORT_KEYWORDS = ("ใช้งานยังไง", "error", "บั๊ก", "bug", "ไม่ทำงาน", "help", "วิธี")


def classify_intent(state: AgentState) -> AgentState:
    """Cheap heuristic classification -- deliberately NOT an LLM call.

    The spec's #1 priority is protecting GitHub Models quota, so routing
    (which happens on every single inbound message) is done with keyword
    heuristics rather than spending a model call on every classification.
    """
    message = (state.get("incoming_message") or "").lower()

    if state.get("intent") == "lead_analysis":
        state["agent_name"] = "lead_scraper"
        return state

    if any(k in message for k in SUPPORT_KEYWORDS):
        state["intent"] = "support_question"
        state["agent_name"] = "support_agent"
    elif any(k in message for k in SALES_KEYWORDS) or state.get("intent") == "sales_followup":
        state["intent"] = "sales_followup"
        state["agent_name"] = "strategic_closer"
    elif message.strip():
        # Default unclear inbound chat messages to support -- never guess a
        # sales pitch out of an ambiguous message.
        state["intent"] = "support_question"
        state["agent_name"] = "support_agent"
    else:
        state["intent"] = "unknown"
        state["agent_name"] = None

    return state


def validate_output(state: AgentState) -> AgentState:
    """Final gate before anything leaves the graph. Enforces the
    non-negotiable rules from the spec regardless of what a worker agent
    returned."""
    notes: list[str] = []

    if state.get("agent_name") == "strategic_closer":
        # Sales/follow-up drafts must ALWAYS require approval.
        state["requires_approval"] = True
        state["auto_send"] = False
        notes.append("sales/follow-up draft forced into approval queue")
    elif state.get("agent_name") == "support_agent":
        if state.get("kb_answer_found"):
            state["requires_approval"] = False
            state["auto_send"] = True
            notes.append("KB match found -- auto-send allowed")
        else:
            state["requires_approval"] = False
            state["auto_send"] = False
            notes.append("no KB match -- routed to a support ticket instead of guessing")
    else:
        state["requires_approval"] = True
        state["auto_send"] = False
        notes.append("unrecognized agent output -- defaulting to human review")

    state["validated"] = True
    state["validation_notes"] = notes
    return state
