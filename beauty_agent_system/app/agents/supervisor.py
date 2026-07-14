"""Supervisor Agent -- the single entry point of the Virtual Office.

Reads whatever raw blob the founder pasted, decides which of the 6 worker
agents are relevant (never all 6 by default -- only the ones the input
actually touches), runs them, reviews their combined draft against the
shared goal, and synthesizes ONE combined answer: Key Findings + a
two-bucket Action Plan (Founder must do / AI will do next).

Four stages, each shown to the founder as a "trace" so the coordination is
visible instead of implicit (see run_office's plan_trace/review_trace):

1. plan       -- state the shared goal + what each selected agent is doing.
2. dispatch   -- run the selected agents concurrently.
3. review     -- one QA pass: is the combined draft complete/non-redundant/
                 actionable? If not, feed specific gaps back to only the
                 agent(s) that need it for exactly ONE rework round (never
                 unbounded -- protects the GitHub Models quota/latency).
4. synthesize -- dedupe findings and merge into the final answer.

Routing (which agents to run at all) is a cheap keyword heuristic first
(protects the GitHub Models quota) and only falls back to one LLM call when
no keyword matched anything -- free text from a founder won't always
contain an obvious keyword.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents import (
    content_strategist_agent,
    customer_success_agent,
    demo_agent,
    general_assistant,
    lead_hunter,
    onboarding_agent,
    product_analyst_agent,
    sales_assistant,
)
from app.agents._json_utils import empty_result, empty_review, parse_json_object
from app.agents.prompts import (
    SUPERVISOR_REVIEW_SYSTEM_PROMPT,
    SUPERVISOR_REVIEW_USER_TEMPLATE,
    SUPERVISOR_ROUTE_SYSTEM_PROMPT,
    SUPERVISOR_ROUTE_USER_TEMPLATE,
)
from app.business_context import AGENT_TASK_TH, CSC_GOAL_TH
from app.customer_context import build_customer_context, touch_lead
from app.llm_client import LLMUnavailable, call_llm
from app.memory import memory_note as _memory_note
from app.models import AgentFeedback, Conversation, OfficeRun, PendingApproval

logger = logging.getLogger("beauty_agent_system.supervisor")

AGENT_MODULES = {
    "lead_hunter": lead_hunter,
    "sales_assistant": sales_assistant,
    "demo_agent": demo_agent,
    "onboarding_agent": onboarding_agent,
    "customer_success_agent": customer_success_agent,
    "product_analyst_agent": product_analyst_agent,
    "content_strategist": content_strategist_agent,
    "general_assistant": general_assistant,
}


async def _run_agent(
    name: str,
    db: Session,
    raw_text: str,
    *,
    feedback: str | None = None,
    image_urls: list[str] | None = None,
    customer_context: dict | None = None,
) -> dict:
    """Thin dispatch wrapper that passes customer_context to agents that
    support it (sales_assistant, customer_success_agent, general_assistant)
    and image_urls only to general_assistant."""
    module = AGENT_MODULES[name]
    kwargs: dict = {}
    if feedback:
        kwargs["feedback"] = feedback
    if image_urls and getattr(module, "SUPPORTS_IMAGES", False):
        kwargs["image_urls"] = image_urls
    # Pass customer context to agents whose run() accepts it
    if customer_context and name in ("sales_assistant", "customer_success_agent", "general_assistant"):
        kwargs["customer_context"] = customer_context
    return await module.run(db, raw_text, **kwargs)


async def select_relevant_agents(db: Session, raw_text: str, *, has_images: bool = False) -> list[str]:
    """Returns the list of agent keys (from AGENT_MODULES) relevant to
    raw_text. Keyword heuristics first; LLM fallback only if none matched.
    general_assistant is never keyword-matched -- it's added explicitly
    below as the catch-all for anything outside CSC's 7 specialized agents,
    and always runs when an image is attached (it's the only one that can
    see it)."""
    matched = [
        name for name, module in AGENT_MODULES.items()
        if name != "general_assistant" and module.matches(raw_text)
    ]
    if matched:
        if has_images:
            matched.append("general_assistant")
        return matched

    if has_images:
        return ["general_assistant"]

    try:
        raw = await call_llm(
            db,
            "supervisor",
            SUPERVISOR_ROUTE_SYSTEM_PROMPT,
            SUPERVISOR_ROUTE_USER_TEMPLATE.format(raw_text=raw_text),
        )
        selected = parse_json_object(raw) if raw.strip().startswith("{") else __import__("json").loads(raw)
    except Exception as exc:  # noqa: BLE001 -- routing failure must not crash the request
        logger.warning("supervisor routing LLM call failed: %s", exc)
        return []

    if not isinstance(selected, list):
        selected = []
    selected = [name for name in selected if name in AGENT_MODULES and name != "general_assistant"]
    if not selected:
        selected = ["general_assistant"]
    elif has_images:
        selected.append("general_assistant")
    return selected


def _dedupe_findings(findings: list[str], *, threshold: float = 0.72) -> list[str]:
    """Drops findings that are near-duplicates of one already kept (same
    idea restated by a different agent) instead of showing the same
    sentence 4-5 times with only the agent tag changed."""
    kept: list[str] = []
    for finding in findings:
        # Compare only the text after the "[Agent Label] " prefix so two
        # agents phrasing the same fact aren't kept just because their tags differ.
        body = finding.split("] ", 1)[-1]
        if any(SequenceMatcher(None, body, k.split("] ", 1)[-1]).ratio() >= threshold for k in kept):
            continue
        kept.append(finding)
    return kept


async def _review_draft(
    db: Session,
    raw_text: str,
    selected: list[str],
    key_findings: list[str],
    founder_actions: list[str],
    ai_actions: list[str],
    missing_info: list[str],
) -> dict:
    """One QA pass over the team's first-round draft. Falls back to
    'sufficient' (no rework) if the LLM is unavailable -- a broken review
    step must never block the founder from seeing the draft output."""
    try:
        raw = await call_llm(
            db,
            "supervisor",
            SUPERVISOR_REVIEW_SYSTEM_PROMPT,
            SUPERVISOR_REVIEW_USER_TEMPLATE.format(
                raw_text=raw_text,
                selected_agents=", ".join(selected),
                key_findings=key_findings or "(ไม่มี)",
                founder_actions=founder_actions or "(ไม่มี)",
                ai_actions=ai_actions or "(ไม่มี)",
                missing_info=missing_info or "(ไม่มี)",
            ),
        )
        review = parse_json_object(raw)
    except (LLMUnavailable, ValueError) as exc:
        logger.warning("supervisor review LLM call failed: %s", exc)
        return empty_review()

    if not isinstance(review, dict):
        return empty_review()

    rework = [
        item
        for item in (review.get("rework") or [])
        if isinstance(item, dict) and item.get("agent") in selected and item.get("feedback")
    ]
    return {
        "sufficient": bool(review.get("sufficient", True)) and not rework,
        "rework": rework,
        "note": review.get("note"),
    }


def _recent_sales_tone_note(db: Session) -> str | None:
    """Self-improvement, folded into the next round's Key Findings instead
    of a separate 'Weekly Insights' page: if sales_assistant drafts have
    been rejected a lot in the last 7 days, surface that pattern now."""
    week_ago = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=7)
    rows = db.scalars(
        select(AgentFeedback)
        .join(PendingApproval, AgentFeedback.approval_id == PendingApproval.id)
        .where(PendingApproval.agent_name == "sales_assistant")
        .where(AgentFeedback.created_at >= week_ago)
    ).all()
    if len(rows) < 3:
        return None
    rejected = sum(1 for r in rows if r.outcome in ("ignored", "rejected", "blocked"))
    if rejected / len(rows) > 0.5:
        return (
            f"ข้อสังเกตจาก 7 วันที่ผ่านมา: ข้อความร่างของ Sales Assistant ถูกปฏิเสธ/ไม่ส่ง "
            f"{rejected}/{len(rows)} ครั้ง -- ควรลองปรับโทนให้เปิดด้วยคำถาม Pain Point ล้วนๆ "
            f"และตัดทุกคำที่ฟังดูเหมือนขายทิ้งไปอีก"
        )
    return None


def _recent_run_feedback_note(db: Session) -> str | None:
    """General self-improvement across ALL agents, not just Sales Assistant
    drafts: the founder can mark any run's whole output as 'accepted' or
    'rejected' (with an optional note) straight from the result card. This
    folds recent rejections -- with their notes, which carry the real
    'why' -- into the next round's Key Findings, the same way
    _recent_sales_tone_note already does for the narrower approval flow.
    Both notes can appear together; they cover different signals."""
    week_ago = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=7)
    rows = db.scalars(
        select(OfficeRun)
        .where(OfficeRun.outcome.is_not(None))
        .where(OfficeRun.created_at >= week_ago)
    ).all()
    if len(rows) < 3:
        return None
    rejected = [r for r in rows if r.outcome == "rejected"]
    if len(rejected) / len(rows) <= 0.5:
        return None
    notes = [r.founder_note for r in rejected if r.founder_note]
    notes_text = "; ".join(notes[-3:]) if notes else "(ผู้ก่อตั้งไม่ได้ระบุเหตุผลเพิ่มเติม)"
    return (
        f"ข้อสังเกตจาก 7 วันที่ผ่านมา: ผลลัพธ์ของทีม AI ถูกผู้ก่อตั้งบอกว่า 'ไม่เวิร์ก' "
        f"{len(rejected)}/{len(rows)} ครั้ง -- เหตุผลที่ผู้ก่อตั้งให้ไว้: {notes_text} "
        f"-- ควรนำเหตุผลนี้มาปรับแนวคิด/มุมมองก่อนตอบครั้งนี้"
    )


def _merge_results(results: list[dict]) -> tuple[list[str], list[str], list[str], list[str], list[str]]:
    key_findings: list[str] = []
    content_ideas: list[str] = []
    founder_actions: list[str] = []
    ai_actions: list[str] = []
    missing_info: list[str] = []
    for result in results:
        label = result["label_th"]
        for finding in result["key_findings"]:
            key_findings.append(f"[{label}] {finding}")
        content_ideas.extend(result.get("content_ideas") or [])
        founder_actions.extend(result["founder_actions"])
        ai_actions.extend(result["ai_actions"])
        for missing in result["missing_info"]:
            missing_info.append(f"[{label}] {missing}")
    return key_findings, content_ideas, founder_actions, ai_actions, missing_info


def _collect_questions_and_notes(results: list[dict]) -> tuple[list[dict], list[dict]]:
    """Pulls out each agent's clarifying_question (if it truly couldn't
    proceed confidently) and observations (proactive ideas/signals outside
    its own task) so they can be shown separately and prominently, instead
    of getting buried inside key_findings/missing_info."""
    questions: list[dict] = []
    notes: list[dict] = []
    for result in results:
        label = result["label_th"]
        if result.get("clarifying_question"):
            questions.append({"agent": result["agent_name"], "label": label, "question": result["clarifying_question"]})
        for note in result.get("observations") or []:
            notes.append({"label": label, "note": note})
    return questions, notes


async def run_office(db: Session, raw_text: str, *, image_urls: list[str] | None = None) -> dict:
    """Main entry point: plan -> dispatch -> review -> (rework once) ->
    synthesize.

    Returns a dict with keys: agents_run, plan_trace, review_trace,
    key_findings, founder_actions, ai_actions, missing_info, draft
    (optional), approval_id (optional).
    """
    raw_text = (raw_text or "").strip()
    if not raw_text and not image_urls:
        return {
            "agents_run": [],
            "plan_trace": None,
            "review_trace": None,
            "questions": [],
            "team_notes": [],
            "key_findings": [],
            "founder_actions": [],
            "ai_actions": [],
            "missing_info": ["ยังไม่ได้แปะข้อมูลอะไรเข้ามา"],
            "draft": None,
            "approval_id": None,
        }

    selected = await select_relevant_agents(db, raw_text, has_images=bool(image_urls))

    # --- Stage 1: plan -- state the shared goal + each agent's assignment,
    # shown to the founder so the division of labor is visible up front. ---
    plan_trace = {
        "goal": CSC_GOAL_TH,
        "assignments": [
            {"label": AGENT_MODULES[name].LABEL_TH, "task": AGENT_TASK_TH.get(name, "")}
            for name in selected
        ],
    }

    # --- Stage 2: dispatch -- run every selected agent concurrently. ---
    results = await asyncio.gather(
        *(_run_agent(name, db, raw_text, image_urls=image_urls) for name in selected)
    )
    results_by_agent = {r["agent_name"]: r for r in results}
    key_findings, content_ideas, founder_actions, ai_actions, missing_info = _merge_results(results)

    # --- Stage 3: review -- one QA pass; rework exactly the agents flagged,
    # exactly once, then re-merge. Skipped for a pure general_assistant reply --
    # a freeform chat answer has nothing to QA against the CSC action-plan shape.
    review = (
        {"sufficient": True, "rework": [], "note": None}
        if selected == ["general_assistant"]
        else await _review_draft(
            db, raw_text, selected, key_findings, founder_actions, ai_actions, missing_info
        )
    )
    review_trace = {"note": review.get("note"), "rework": []}

    if review["rework"]:
        rework_map = {item["agent"]: item["feedback"] for item in review["rework"]}
        reworked = await asyncio.gather(
            *(
                _run_agent(name, db, raw_text, feedback=feedback)
                for name, feedback in rework_map.items()
            )
        )
        for name, new_result in zip(rework_map.keys(), reworked):
            results_by_agent[name] = new_result
            review_trace["rework"].append(
                {"label": AGENT_MODULES[name].LABEL_TH, "feedback": rework_map[name]}
            )
        key_findings, content_ideas, founder_actions, ai_actions, missing_info = _merge_results(
            list(results_by_agent.values())
        )

    # --- Stage 4: synthesize -- dedupe near-identical findings, pick up any
    # Sales Assistant draft, fold in the self-improvement note. ---
    key_findings = _dedupe_findings(key_findings)
    draft: dict | None = None
    approval_id: int | None = None

    sales_result = results_by_agent.get("sales_assistant")
    if sales_result and sales_result.get("draft_message"):
        approval = PendingApproval(
            agent_name="sales_assistant",
            draft_message=sales_result["draft_message"],
            reasoning=sales_result.get("draft_reasoning") or "(ไม่มีคำอธิบายเพิ่มเติม)",
            status="pending",
        )
        db.add(approval)
        db.commit()
        draft = {
            "message": sales_result["draft_message"],
            "reasoning": sales_result.get("draft_reasoning"),
            "approval_id": approval.id,
        }
        approval_id = approval.id

    tone_note = _recent_sales_tone_note(db)
    if tone_note:
        key_findings.append(f"[Supervisor] {tone_note}")
    feedback_note = _recent_run_feedback_note(db)
    if feedback_note:
        key_findings.append(f"[Supervisor] {feedback_note}")
    mem_note = _memory_note(db, raw_text)
    if mem_note:
        key_findings.append(f"[Supervisor] {mem_note}")

    questions, team_notes = _collect_questions_and_notes(list(results_by_agent.values()))

    # Extract Content Strategist specific structured fields
    cs_result = results_by_agent.get("content_strategist")
    content_plan = cs_result.get("content_plan") or [] if cs_result else []
    target_profile = cs_result.get("target_profile") or "" if cs_result else ""
    pitch_timing = cs_result.get("pitch_timing") or "" if cs_result else ""
    product_pitch = cs_result.get("product_pitch") or "" if cs_result else ""

    ga_result = results_by_agent.get("general_assistant")
    general_answer = ga_result.get("answer_text") if ga_result else None

    return {
        "agents_run": [AGENT_MODULES[name].LABEL_TH for name in selected],
        "plan_trace": plan_trace,
        "review_trace": review_trace,
        "questions": questions,
        "team_notes": team_notes,
        "key_findings": key_findings,
        "content_ideas": content_ideas,
        "content_plan": content_plan,
        "target_profile": target_profile,
        "pitch_timing": pitch_timing,
        "product_pitch": product_pitch,
        "founder_actions": founder_actions,
        "ai_actions": ai_actions,
        "missing_info": missing_info,
        "draft": draft,
        "approval_id": approval_id,
        "general_answer": general_answer,
    }


# ---------------------------------------------------------------------------
# Streaming variant -- yields SSE-ready event dicts as work progresses.
# The router wraps each with `data: ...\n\n` and saves the OfficeRun to DB
# once the "final" event is yielded.
# ---------------------------------------------------------------------------

AGENT_EMOJI = {
    "lead_hunter": "lead_hunter",
    "sales_assistant": "sales_assistant",
    "demo_agent": "demo_agent",
    "onboarding_agent": "onboarding_agent",
    "customer_success_agent": "customer_success_agent",
    "product_analyst_agent": "product_analyst_agent",
    "content_strategist": "content_strategist",
    "general_assistant": "general_assistant",
}


async def stream_run_office(
    db: Session,
    raw_text: str,
    *,
    conversation_id: int | None = None,
    image_urls: list[str] | None = None,
    lead_id: int | None = None,
):
    """Async generator that yields event dicts representing each stage of the
    Virtual Office pipeline.  The caller (SSE router) serialises them as
    `data: <json>\n\n` and pipes to the browser.  The OfficeRun DB record is
    created here at the very end so run_id can be included in "final".

    When lead_id is provided (e.g. from an incoming Chatwoot message or a
    manually linked run), the supervisor builds a customer_context dict and
    injects it into supporting agents so they don't start blind."""

    raw_text = (raw_text or "").strip()
    image_urls = image_urls or []

    # ── Customer context (if a specific lead is linked to this run) ──────
    customer_context = build_customer_context(db, lead_id) if lead_id else None

    # ── Stage 0: supervisor selects agents ──────────────────────────────
    yield {"type": "supervisor_thinking", "text": "กำลังอ่านและเลือก Agent ที่เหมาะสม..."}

    if not raw_text and not image_urls:
        run = OfficeRun(
            raw_text="", conversation_id=conversation_id, image_urls=[],
            agents_run=[], plan_trace=None, review_trace=None,
            questions=[], team_notes=[], key_findings=[],
            founder_actions=[], ai_actions=[],
            missing_info=["ยังไม่ได้แปะข้อมูลอะไรเข้ามา"], approval_id=None,
        )
        db.add(run); db.commit()
        yield {"type": "final", "run_id": run.id, "key_findings": [],
               "founder_actions": [], "ai_actions": [],
               "missing_info": ["ยังไม่ได้แปะข้อมูลอะไรเข้ามา"],
               "questions": [], "team_notes": [], "draft": None, "agents_run": []}
        return

    selected = await select_relevant_agents(db, raw_text, has_images=bool(image_urls))

    plan_trace = {
        "goal": CSC_GOAL_TH,
        "assignments": [
            {
                "agent": name,
                "label": AGENT_MODULES[name].LABEL_TH,
                "emoji": AGENT_EMOJI.get(name, "🤖"),
                "task": AGENT_TASK_TH.get(name, ""),
            }
            for name in selected
        ],
    }
    yield {"type": "planning", "plan_trace": plan_trace, "selected": selected}

    # ── Stage 1: dispatch agents ──────────────────────────────────────────
    # general_assistant gets a special streaming path so the founder sees
    # its plain-text answer arriving token by token instead of all at once.
    # All other agents (JSON-returning) run concurrently first, then GA
    # streams last.  Because the rate-limiter semaphore serialises calls
    # anyway this doesn't increase total latency but dramatically improves
    # perceived responsiveness.
    ga_selected = "general_assistant" in selected
    other_agents = [n for n in selected if n != "general_assistant"]

    # Signal start for all non-GA agents up front
    for name in other_agents:
        yield {"type": "agent_start", "agent": name,
               "label": AGENT_MODULES[name].LABEL_TH,
               "emoji": AGENT_EMOJI.get(name, "🤖")}

    # Run non-GA agents concurrently (rate-limiter serialises internally)
    name_to_task = {
        name: asyncio.create_task(
            _run_agent(name, db, raw_text, image_urls=image_urls, customer_context=customer_context)
        )
        for name in other_agents
    }
    task_to_name = {v: k for k, v in name_to_task.items()}
    pending = set(name_to_task.values())

    results_by_agent: dict = {}
    while pending:
        done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
        for task in done:
            name = task_to_name[task]
            try:
                result = task.result()
            except Exception as exc:  # noqa: BLE001
                logger.warning("agent %s raised: %s", name, exc)
                result = empty_result(name, AGENT_MODULES[name].LABEL_TH,
                                      missing_info=[f"ข้อผิดพลาด: {exc}"])
            results_by_agent[name] = result
            yield {
                "type": "agent_done",
                "agent": name,
                "label": result["label_th"],
                "emoji": AGENT_EMOJI.get(name, "🤖"),
                "thinking": result.get("thinking"),
                "findings": result.get("key_findings") or [],
                "question": result.get("clarifying_question"),
                "observations": result.get("observations") or [],
                "draft_message": result.get("draft_message"),
                "answer_text": result.get("answer_text"),
            }

    # ── general_assistant: stream tokens live ────────────────────────────
    if ga_selected:
        yield {"type": "agent_start", "agent": "general_assistant",
               "label": AGENT_MODULES["general_assistant"].LABEL_TH,
               "emoji": AGENT_EMOJI.get("general_assistant", "🤖")}
        ga_result: dict = {}
        try:
            async for chunk, result in general_assistant.run_stream(
                db, raw_text, image_urls=image_urls, customer_context=customer_context
            ):
                if chunk is not None:
                    yield {"type": "token", "text": chunk}
                else:
                    ga_result = result or {}
        except Exception as exc:  # noqa: BLE001
            logger.warning("general_assistant stream raised: %s", exc)
            ga_result = empty_result(
                "general_assistant", AGENT_MODULES["general_assistant"].LABEL_TH,
                missing_info=[f"ข้อผิดพลาด: {exc}"]
            )
        results_by_agent["general_assistant"] = ga_result
        yield {
            "type": "agent_done",
            "agent": "general_assistant",
            "label": ga_result.get("label_th", AGENT_MODULES["general_assistant"].LABEL_TH),
            "emoji": AGENT_EMOJI.get("general_assistant", "🤖"),
            "thinking": ga_result.get("thinking"),
            "findings": ga_result.get("key_findings") or [],
            "question": ga_result.get("clarifying_question"),
            "observations": ga_result.get("observations") or [],
            "draft_message": ga_result.get("draft_message"),
            "answer_text": ga_result.get("answer_text"),
        }

    # ── Stage 2: QA review + rework (silent — no UI events) ─────────────
    # Skipped for a pure general_assistant reply -- a freeform chat answer
    # has nothing to QA against the CSC action-plan shape.
    key_findings, content_ideas, founder_actions, ai_actions, missing_info = _merge_results(
        [results_by_agent[n] for n in selected if n in results_by_agent]
    )
    review = (
        {"sufficient": True, "rework": [], "note": None}
        if selected == ["general_assistant"]
        else await _review_draft(db, raw_text, selected,
                                 key_findings, founder_actions, ai_actions, missing_info)
    )

    review_trace = {"note": review.get("note"), "rework": []}
    if review.get("rework"):
        rework_map = {
            item["agent"]: item["feedback"]
            for item in review["rework"]
            if item.get("agent") in AGENT_MODULES
        }
        rework_name_to_task = {
            name: asyncio.create_task(_run_agent(name, db, raw_text, feedback=fb, image_urls=image_urls))
            for name, fb in rework_map.items()
        }
        rework_task_to_name = {v: k for k, v in rework_name_to_task.items()}
        pending_rework = set(rework_name_to_task.values())
        while pending_rework:
            done, pending_rework = await asyncio.wait(
                pending_rework, return_when=asyncio.FIRST_COMPLETED
            )
            for task in done:
                name = rework_task_to_name[task]
                try:
                    result = task.result()
                except Exception as exc:  # noqa: BLE001
                    result = results_by_agent.get(
                        name, empty_result(name, AGENT_MODULES[name].LABEL_TH,
                                           missing_info=[str(exc)])
                    )
                results_by_agent[name] = result
                review_trace["rework"].append(
                    {"label": AGENT_MODULES[name].LABEL_TH, "feedback": rework_map[name]}
                )
        key_findings, content_ideas, founder_actions, ai_actions, missing_info = _merge_results(
            [results_by_agent[n] for n in selected if n in results_by_agent]
        )

    # ── Stage 4: synthesize ──────────────────────────────────────────────
    key_findings = _dedupe_findings(key_findings)
    draft: dict | None = None
    approval_id: int | None = None

    sales_result = results_by_agent.get("sales_assistant")
    if sales_result and sales_result.get("draft_message"):
        approval = PendingApproval(
            agent_name="sales_assistant",
            draft_message=sales_result["draft_message"],
            reasoning=sales_result.get("draft_reasoning") or "(ไม่มีคำอธิบายเพิ่มเติม)",
            status="pending",
        )
        db.add(approval)
        db.commit()
        draft = {
            "message": sales_result["draft_message"],
            "reasoning": sales_result.get("draft_reasoning"),
            "approval_id": approval.id,
        }
        approval_id = approval.id
        founder_actions.append({
            "action": "ตรวจ/แก้/อนุมัติข้อความร่างจาก Sales Assistant ก่อนส่งลูกค้าจริง",
            "goal_metric": "",
            "target_audience": "",
            "where_and_how_many": "",
            "reasoning": "ข้อความร่างต้องผ่านสายตา Founder ก่อนเสมอ เพื่อให้น้ำเสียงตรงกับที่ต้องการและไม่มีข้อผิดพลาด",
            "engagement_tactic": "",
        })

    tone_note = _recent_sales_tone_note(db)
    if tone_note:
        key_findings.append(f"[Supervisor] {tone_note}")
    feedback_note = _recent_run_feedback_note(db)
    if feedback_note:
        key_findings.append(f"[Supervisor] {feedback_note}")
    mem_note = _memory_note(db, raw_text)
    if mem_note:
        key_findings.append(f"[Supervisor] {mem_note}")

    questions, team_notes = _collect_questions_and_notes(
        list(results_by_agent.values())
    )

    # Extract Content Strategist structured fields
    cs_result = results_by_agent.get("content_strategist")
    content_plan = cs_result.get("content_plan") or [] if cs_result else []
    target_profile = cs_result.get("target_profile") or "" if cs_result else ""
    pitch_timing = cs_result.get("pitch_timing") or "" if cs_result else ""
    product_pitch = cs_result.get("product_pitch") or "" if cs_result else ""

    ga_result = results_by_agent.get("general_assistant")
    general_answer = ga_result.get("answer_text") if ga_result else None

    # Save OfficeRun to DB so the static fallback (/GET) still works
    run = OfficeRun(
        raw_text=raw_text,
        conversation_id=conversation_id,
        image_urls=image_urls,
        agents_run=[AGENT_MODULES[n].LABEL_TH for n in selected],
        plan_trace={
            "goal": CSC_GOAL_TH,
            "assignments": [
                {"label": AGENT_MODULES[n].LABEL_TH, "task": AGENT_TASK_TH.get(n, "")}
                for n in selected
            ],
        },
        review_trace=review_trace,
        questions=questions,
        team_notes=team_notes,
        key_findings=key_findings,
        founder_actions=founder_actions,
        ai_actions=ai_actions,
        missing_info=missing_info,
        approval_id=approval_id,
        general_answer=general_answer,
    )
    db.add(run)
    db.commit()

    if conversation_id:
        convo = db.get(Conversation, conversation_id)
        if convo and convo.title == "แชทใหม่":
            convo.title = (raw_text or "รูปภาพที่แนบมา")[:60]
            db.commit()

    # Bump last_contacted_at for linked lead so the Leads panel stays fresh
    if lead_id:
        touch_lead(db, lead_id)

    yield {
        "type": "final",
        "run_id": run.id,
        "agents_run": [AGENT_MODULES[n].LABEL_TH for n in selected],
        "key_findings": key_findings,
        "content_ideas": content_ideas,
        "content_plan": content_plan,
        "target_profile": target_profile,
        "pitch_timing": pitch_timing,
        "product_pitch": product_pitch,
        "founder_actions": founder_actions,
        "ai_actions": ai_actions,
        "missing_info": missing_info,
        "questions": questions,
        "team_notes": team_notes,
        "draft": draft,
        "general_answer": general_answer,
    }
