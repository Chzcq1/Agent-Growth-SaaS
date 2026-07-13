"""Agent 5: Planner.

Takes free-text notes the founder logs by hand (a customer question, a
complaint, a competitor move, a random observation -- anything) and triages
them into: a short Thai summary ("what's new"), an optional ready-to-copy
suggested reply for the founder to send manually, and an optional Task with
a deadline. Also assembles the daily briefing digest from open tasks +
recent updates.

The founder explicitly does not want any agent sending messages to
customers -- Chatwoot stays disabled. This agent only ever produces text for
a human to read and act on.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.prompts import (
    PLANNER_BRIEFING_SYSTEM_PROMPT,
    PLANNER_BRIEFING_USER_TEMPLATE,
    PLANNER_UPDATE_SYSTEM_PROMPT,
    PLANNER_UPDATE_USER_TEMPLATE,
)
from app.llm_client import LLMUnavailable, call_llm
from app.models import DailyBriefing, DailyUpdate, Task, TaskStatus

logger = logging.getLogger("beauty_agent_system.planner")

AGENT_NAME = "planner_agent"


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _parse_json_block(raw: str) -> dict:
    """Models sometimes wrap JSON in ```json fences despite instructions --
    strip those before parsing rather than failing the whole triage."""
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()
    return json.loads(text)


async def process_update(db: Session, content: str) -> dict:
    """Triage one founder note. Always creates a DailyUpdate row. Creates a
    Task row too if the model decided one is warranted. Never blocks on the
    LLM being unavailable -- falls back to a plain, un-triaged log entry so
    the founder's note is never lost."""
    analysis: dict = {}
    llm_error: str | None = None

    try:
        raw = await call_llm(
            db,
            AGENT_NAME,
            PLANNER_UPDATE_SYSTEM_PROMPT,
            PLANNER_UPDATE_USER_TEMPLATE.format(content=content),
        )
        analysis = _parse_json_block(raw)
    except LLMUnavailable as exc:
        llm_error = str(exc)
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning("planner: could not parse model JSON output: %s", exc)
        llm_error = "รูปแบบคำตอบจาก AI ไม่ถูกต้อง"

    update = DailyUpdate(
        content=content,
        update_type=analysis.get("update_type") or "other",
        summary=analysis.get("summary")
        or (f"AI ยังวิเคราะห์ไม่ได้ตอนนี้ ({llm_error}) -- บันทึกข้อความไว้แล้ว" if llm_error else None),
        needs_reply=bool(analysis.get("needs_reply")),
        suggested_reply=analysis.get("suggested_reply"),
    )
    db.add(update)
    db.flush()  # need update.id before linking a task to it

    task = None
    if analysis.get("task_title"):
        due_in_days = analysis.get("due_in_days")
        try:
            due_in_days = int(due_in_days) if due_in_days is not None else 3
        except (TypeError, ValueError):
            due_in_days = 3
        task = Task(
            title=analysis["task_title"],
            description=analysis.get("task_description"),
            category=analysis.get("category") or "other",
            due_date=_now() + timedelta(days=max(due_in_days, 0)),
            source_update_id=update.id,
        )
        db.add(task)

    db.commit()

    return {
        "status": "llm_unavailable" if llm_error else "triaged",
        "detail": llm_error,
        "update_id": update.id,
        "task_id": task.id if task else None,
    }


async def generate_daily_briefing(db: Session) -> DailyBriefing:
    now = _now()
    since = now - timedelta(hours=24)

    overdue_tasks = db.scalars(
        select(Task)
        .where(Task.status == TaskStatus.OPEN)
        .where(Task.due_date < now.replace(hour=0, minute=0, second=0, microsecond=0))
        .order_by(Task.due_date.asc())
    ).all()
    due_today_tasks = db.scalars(
        select(Task)
        .where(Task.status == TaskStatus.OPEN)
        .where(Task.due_date >= now.replace(hour=0, minute=0, second=0, microsecond=0))
        .where(Task.due_date < now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1))
        .order_by(Task.due_date.asc())
    ).all()
    recent_updates = db.scalars(
        select(DailyUpdate).where(DailyUpdate.created_at >= since).order_by(DailyUpdate.created_at.desc())
    ).all()

    def _fmt_task(t: Task) -> str:
        deadline = t.due_date.strftime("%Y-%m-%d") if t.due_date else "ไม่ระบุ"
        return f"- {t.title} (กำหนด {deadline}){f': {t.description}' if t.description else ''}"

    overdue_text = "\n".join(_fmt_task(t) for t in overdue_tasks) or "(ไม่มี)"
    due_today_text = "\n".join(_fmt_task(t) for t in due_today_tasks) or "(ไม่มี)"
    findings_text = "\n".join(f"- {u.summary}" for u in recent_updates if u.summary) or "(ไม่มี)"

    try:
        summary_text = await call_llm(
            db,
            AGENT_NAME,
            PLANNER_BRIEFING_SYSTEM_PROMPT,
            PLANNER_BRIEFING_USER_TEMPLATE.format(
                overdue_tasks=overdue_text,
                due_today_tasks=due_today_text,
                recent_findings=findings_text,
            ),
        )
    except LLMUnavailable as exc:
        # Never fail silently: assemble a plain, un-styled digest from the
        # same raw data so the founder still gets a usable summary today.
        summary_text = (
            f"(สร้างด้วย AI ไม่ได้ตอนนี้: {exc} -- นี่คือสรุปดิบจากข้อมูลที่มี)\n\n"
            f"งานที่เลยกำหนดแล้ว:\n{overdue_text}\n\n"
            f"งานที่ต้องทำวันนี้:\n{due_today_text}\n\n"
            f"สิ่งที่ AI พบใหม่ในช่วง 24 ชม. ที่ผ่านมา:\n{findings_text}"
        )

    briefing = DailyBriefing(
        summary_text=summary_text.strip(),
        tasks_due_count=len(due_today_tasks),
        tasks_overdue_count=len(overdue_tasks),
        new_findings_count=len(recent_updates),
    )
    db.add(briefing)
    db.commit()
    return briefing
