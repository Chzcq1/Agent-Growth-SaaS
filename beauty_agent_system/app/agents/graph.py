"""LangGraph state machine wiring Supervisor + the three worker agents.

Graph shape (matches the spec's diagram):

    classify (Supervisor) -> run_worker_agent -> validate_output (Supervisor) -> END

The Supervisor is the only router/validator; worker agents never call each
other and never loop -- this graph has no cycles, which is what prevents the
"agents arguing forever" failure mode called out in the spec.
"""
from __future__ import annotations

from typing import Any

from langgraph.graph import END, StateGraph
from sqlalchemy.orm import Session

from app.agents import lead_scraper, strategic_closer, support_agent
from app.agents.state import AgentState
from app.agents.supervisor import classify_intent, validate_output


def _make_graph():
    graph = StateGraph(AgentState)

    graph.add_node("classify", classify_intent)
    graph.add_node("run_worker_agent", _run_worker_agent_node)
    graph.add_node("validate_output", validate_output)

    graph.set_entry_point("classify")
    graph.add_edge("classify", "run_worker_agent")
    graph.add_edge("run_worker_agent", "validate_output")
    graph.add_edge("validate_output", END)

    return graph.compile()


def _run_worker_agent_node(state: AgentState) -> AgentState:
    # Worker agents are async + need a DB session, both of which are threaded
    # through ``state["extra"]`` by the caller (routers/webhook.py) rather
    # than through LangGraph's sync node signature.
    return state


_COMPILED_GRAPH = _make_graph()


async def run_graph(db: Session, initial_state: AgentState) -> AgentState:
    """Runs classify -> worker agent -> validate, doing the actual async DB/LLM
    work for the worker step outside of LangGraph's sync node call (LangGraph
    nodes here are pure state transforms; the actual agent call happens here
    so we can await it)."""
    state = classify_intent(dict(initial_state))  # type: ignore[arg-type]

    agent_name = state.get("agent_name")
    shop_id = state.get("shop_id")

    if agent_name == "lead_scraper" and shop_id is not None:
        result = await lead_scraper.analyze_lead(db, shop_id)
        state["extra"] = {**state.get("extra", {}), "lead_scraper_result": result}
    elif agent_name == "strategic_closer" and shop_id is not None:
        result = await strategic_closer.draft_followup(db, shop_id)
        state["extra"] = {**state.get("extra", {}), "strategic_closer_result": result}
    elif agent_name == "support_agent":
        result = await support_agent.answer_question(db, shop_id, state.get("incoming_message") or "")
        state["kb_answer_found"] = bool(result.get("kb_answer_found"))
        state["draft_message"] = result.get("answer")
        state["extra"] = {**state.get("extra", {}), "support_agent_result": result}
    else:
        state["error"] = "no agent could handle this input"

    state = validate_output(state)
    return state
