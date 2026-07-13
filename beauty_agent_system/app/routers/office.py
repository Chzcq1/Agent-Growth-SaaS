"""Virtual Office -- the single page of this app.

One textarea in, one synthesized answer out: Key Findings + a two-bucket
Action Plan (Founder must do / AI will do next), with an inline
approve/edit/reject box when Sales Assistant produced a draft. Replaces the
old multi-page admin dashboard (Approvals/Leads/System Health/Weekly
Insights/Knowledge Base) entirely -- see README for the rationale.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.graph import run_office_graph
from app.agents.supervisor import stream_run_office
from app.database import get_db
from app.models import AgentFeedback, OfficeRun, PendingApproval

logger = logging.getLogger("beauty_agent_system.office")

router = APIRouter(tags=["office"])
templates = Jinja2Templates(directory="app/templates")


def _pending_approvals(db: Session) -> list[PendingApproval]:
    return db.scalars(
        select(PendingApproval)
        .where(PendingApproval.status == "pending")
        .order_by(PendingApproval.created_at.desc())
    ).all()


@router.get("/", response_class=HTMLResponse)
def office_home(request: Request, db: Session = Depends(get_db)):
    latest_run = db.scalar(select(OfficeRun).order_by(OfficeRun.created_at.desc()))
    return templates.TemplateResponse(
        request,
        "office.html",
        {
            "latest_run": latest_run,
            "pending_approvals": _pending_approvals(db),
        },
    )


@router.post("/run/stream")
async def run_office_stream(
    request: Request,
    raw_text: str = Form(...),
    db: Session = Depends(get_db),
):
    """Server-Sent Events endpoint: streams each pipeline stage as JSON events
    so the browser can render agent progress in real time without page freezes."""

    async def event_generator():
        try:
            async for event in stream_run_office(db, raw_text):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as exc:
            logger.exception("SSE stream error")
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)}, ensure_ascii=False)}\n\n"
        finally:
            yield 'data: {"type":"stream_end"}\n\n'

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.post("/run", response_class=HTMLResponse)
async def run_office(request: Request, raw_text: str = Form(...), db: Session = Depends(get_db)):
    result = await run_office_graph(db, raw_text)

    run = OfficeRun(
        raw_text=raw_text,
        agents_run=result["agents_run"],
        plan_trace=result.get("plan_trace"),
        review_trace=result.get("review_trace"),
        questions=result.get("questions") or [],
        team_notes=result.get("team_notes") or [],
        key_findings=result["key_findings"],
        founder_actions=result["founder_actions"],
        ai_actions=result["ai_actions"],
        missing_info=result["missing_info"],
        approval_id=result.get("approval_id"),
    )
    db.add(run)
    db.commit()

    return templates.TemplateResponse(
        request,
        "office.html",
        {
            "latest_run": run,
            "pending_approvals": _pending_approvals(db),
        },
    )


@router.post("/run/continue", response_class=HTMLResponse)
async def continue_office_run(
    request: Request,
    previous_run_id: int = Form(...),
    answer: str = Form(...),
    db: Session = Depends(get_db),
):
    """Founder answering a clarifying_question a worker agent asked. Folds
    the answer into the original raw_text as extra context and re-runs the
    whole office -- simplest way to keep it a single append-only "thread"
    rather than building a separate half-finished conversation model."""
    previous = db.get(OfficeRun, previous_run_id)
    if not previous:
        raise HTTPException(status_code=404, detail="not found")

    combined_text = (
        f"{previous.raw_text}\n\n[คำตอบเพิ่มเติมจาก Founder ต่อคำถามของทีม AI]\n{answer.strip()}"
    )
    return await run_office(request, raw_text=combined_text, db=db)


@router.post("/approvals/{approval_id}/approve")
def approve(approval_id: int, db: Session = Depends(get_db)):
    approval = db.get(PendingApproval, approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="not found")
    approval.status = "approved"
    approval.reviewed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.add(AgentFeedback(approval_id=approval.id, outcome="sent", founder_note="approved as-is"))
    db.commit()
    return RedirectResponse(url="/", status_code=303)


@router.post("/approvals/{approval_id}/reject")
def reject(approval_id: int, founder_note: str = Form(""), db: Session = Depends(get_db)):
    approval = db.get(PendingApproval, approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="not found")
    approval.status = "rejected"
    approval.reviewed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.add(AgentFeedback(approval_id=approval.id, outcome="ignored", founder_note=founder_note or None))
    db.commit()
    return RedirectResponse(url="/", status_code=303)


@router.post("/approvals/{approval_id}/edit")
def edit_and_approve(approval_id: int, edited_message: str = Form(...), db: Session = Depends(get_db)):
    approval = db.get(PendingApproval, approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="not found")
    approval.draft_message = edited_message
    approval.status = "edited"
    approval.reviewed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.add(AgentFeedback(approval_id=approval.id, outcome="sent", founder_note="edited before use"))
    db.commit()
    return RedirectResponse(url="/", status_code=303)
