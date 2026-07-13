"""LangGraph state machine for the Virtual Office.

Graph shape:

    select_agents (Supervisor) -> dispatch_agents -> synthesize (Supervisor) -> END

The Supervisor is the single entry point: it decides which of the 6 worker
agents are relevant to the raw text the founder pasted, they run
concurrently in ``dispatch_agents``, and the Supervisor synthesizes their
individual outputs into ONE combined answer. No cycles, no agent-to-agent
calls -- same acyclic shape as before, now with a dynamic (0-6 agent) fan
out instead of a fixed 1-of-3 classification.

LangGraph nodes here are pure state transforms; the actual async DB/LLM
work happens in ``run_office_graph`` below (same pattern the old graph.py
used), since LangGraph node signatures in this version are sync.
"""
from __future__ import annotations

from typing import TypedDict

from langgraph.graph import END, StateGraph
from sqlalchemy.orm import Session


class OfficeState(TypedDict, total=False):
    raw_text: str
    selected_agents: list[str]
    result: dict


def _select_node(state: OfficeState) -> OfficeState:
    return state


def _dispatch_node(state: OfficeState) -> OfficeState:
    return state


def _synthesize_node(state: OfficeState) -> OfficeState:
    return state


def _make_graph():
    graph = StateGraph(OfficeState)
    graph.add_node("select_agents", _select_node)
    graph.add_node("dispatch_agents", _dispatch_node)
    graph.add_node("synthesize", _synthesize_node)

    graph.set_entry_point("select_agents")
    graph.add_edge("select_agents", "dispatch_agents")
    graph.add_edge("dispatch_agents", "synthesize")
    graph.add_edge("synthesize", END)

    return graph.compile()


_COMPILED_GRAPH = _make_graph()


async def run_office_graph(db: Session, raw_text: str) -> dict:
    """Runs the Virtual Office graph for one founder submission. Delegates
    the actual routing/execution/synthesis to app.agents.supervisor.run_office
    -- see that module's docstring for the routing + synthesis rules."""
    from app.agents.supervisor import run_office

    return await run_office(db, raw_text)
