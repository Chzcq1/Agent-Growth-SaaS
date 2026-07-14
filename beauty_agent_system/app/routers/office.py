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
import os
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.graph import run_office_graph
from app.agents.supervisor import stream_run_office
from app.customer_context import STAGE_COLORS, STAGE_LABELS, update_lead_stage
from app.database import get_db
from app.models import AgentFeedback, ApiUsageLog, Conversation, Lead, LeadStage, OfficeRun, PendingApproval, SystemState
from app.rate_limiter import SLEEP_STATE_KEY, rate_limiter

logger = logging.getLogger("beauty_agent_system.office")

router = APIRouter(tags=["office"])
templates = Jinja2Templates(directory="app/templates")

UPLOAD_DIR = os.path.join("app", "static", "uploads")
ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}
MAX_IMAGE_BYTES = 8 * 1024 * 1024  # 8MB per image -- generous for a phone photo, small enough to keep LLM calls fast


def _pending_approvals(db: Session) -> list[PendingApproval]:
    return db.scalars(
        select(PendingApproval)
        .where(PendingApproval.status == "pending")
        .order_by(PendingApproval.created_at.desc())
    ).all()


HISTORY_LIMIT = 12


def _recent_runs(db: Session, conversation_id: int | None, limit: int = HISTORY_LIMIT) -> list[OfficeRun]:
    """Oldest-first slice of the most recent runs in one conversation, so the
    thread renders top-to-bottom like a growing chat instead of newest-on-top."""
    query = select(OfficeRun).order_by(OfficeRun.created_at.desc()).limit(limit)
    query = query.where(OfficeRun.conversation_id == conversation_id)
    rows = db.scalars(query).all()
    return list(reversed(rows))


def _get_or_create_default_conversation(db: Session) -> Conversation:
    """First-ever visit / no conversations yet -- give the founder one chat
    to land in instead of an empty sidebar with nowhere to type."""
    convo = db.scalars(select(Conversation).order_by(Conversation.updated_at.desc())).first()
    if convo:
        return convo
    convo = Conversation(title="แชทใหม่")
    db.add(convo)
    db.commit()
    db.refresh(convo)
    return convo


def _conversation_list(db: Session) -> list[dict]:
    convos = db.scalars(select(Conversation).order_by(Conversation.updated_at.desc())).all()
    return [
        {"id": c.id, "title": c.title, "updated_at": c.updated_at.isoformat() if c.updated_at else None}
        for c in convos
    ]


@router.get("/", response_class=HTMLResponse)
def office_home(request: Request, conversation_id: int | None = None, db: Session = Depends(get_db)):
    convo = db.get(Conversation, conversation_id) if conversation_id else None
    if not convo:
        convo = _get_or_create_default_conversation(db)
    recent_runs = _recent_runs(db, convo.id)
    return templates.TemplateResponse(
        request,
        "office.html",
        {
            "latest_run": recent_runs[-1] if recent_runs else None,
            "recent_runs": recent_runs,
            "pending_approvals": _pending_approvals(db),
            "conversation_id": convo.id,
            "conversations": _conversation_list(db),
        },
    )


@router.get("/conversations")
def list_conversations(db: Session = Depends(get_db)):
    return _conversation_list(db)


@router.post("/conversations")
def create_conversation(db: Session = Depends(get_db)):
    convo = Conversation(title="แชทใหม่")
    db.add(convo)
    db.commit()
    db.refresh(convo)
    return {"id": convo.id, "title": convo.title}


@router.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: int, db: Session = Depends(get_db)):
    convo = db.get(Conversation, conversation_id)
    if not convo:
        raise HTTPException(status_code=404, detail="not found")
    db.delete(convo)  # cascades to its office_runs
    db.commit()
    return {"ok": True}


@router.get("/runs/recent")
def runs_recent(conversation_id: int | None = None, db: Session = Depends(get_db)):
    """JSON feed of recent runs for the client to hydrate the chat-style
    history thread on load / after a refresh, using the same renderer the
    live SSE stream uses -- so refreshing the page never loses the thread."""
    runs = _recent_runs(db, conversation_id)
    return [
        {
            "run_id": r.id,
            "raw_text": r.raw_text,
            "image_urls": r.image_urls or [],
            "general_answer": r.general_answer,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "agents_run": r.agents_run or [],
            "key_findings": r.key_findings or [],
            "founder_actions": r.founder_actions or [],
            "ai_actions": r.ai_actions or [],
            "missing_info": r.missing_info or [],
            "questions": r.questions or [],
            "team_notes": r.team_notes or [],
            "outcome": r.outcome,
            "founder_note": r.founder_note,
        }
        for r in runs
    ]


@router.post("/runs/{run_id}/feedback")
def submit_run_feedback(
    run_id: int,
    outcome: str = Form(...),
    founder_note: str = Form(""),
    db: Session = Depends(get_db),
):
    """Founder marking a run's output as accepted/rejected, with an optional
    note -- the raw signal that gets folded into future runs' context (see
    supervisor._recent_feedback_note) instead of being thrown away."""
    run = db.get(OfficeRun, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="not found")
    if outcome not in ("accepted", "rejected"):
        raise HTTPException(status_code=400, detail="invalid outcome")
    run.outcome = outcome
    run.founder_note = founder_note or None
    db.commit()
    return {"ok": True}


@router.post("/images/upload")
async def upload_image(file: UploadFile, db: Session = Depends(get_db)):  # noqa: ARG001 -- db kept for consistent DI, not used
    """Saves one attached image to disk and returns its /static/uploads/...
    URL. Called before /run/stream so the SSE request body can stay a plain
    form (multipart + SSE together is awkward with the browser fetch API)."""
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="รองรับเฉพาะไฟล์รูปภาพ (PNG/JPEG/WEBP/GIF)")
    data = await file.read()
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=400, detail="ไฟล์ใหญ่เกินไป (สูงสุด 8MB ต่อรูป)")

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    ext = os.path.splitext(file.filename or "")[1].lower() or ".png"
    if ext not in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
        ext = ".png"
    filename = f"{uuid.uuid4().hex}{ext}"
    with open(os.path.join(UPLOAD_DIR, filename), "wb") as f:
        f.write(data)

    return {"url": f"/static/uploads/{filename}"}


@router.get("/leads")
def list_leads(db: Session = Depends(get_db)):
    """Return all leads with stage info for the sidebar Leads panel."""
    leads = db.scalars(select(Lead).order_by(Lead.updated_at.desc())).all()
    return [
        {
            "id":               lead.shop_id,
            "shop_name":        lead.shop_name,
            "stage":            lead.stage or "cold",
            "stage_label":      STAGE_LABELS.get(lead.stage or "cold", lead.stage or "cold"),
            "stage_color":      STAGE_COLORS.get(lead.stage or "cold", "#78716c"),
            "facebook_url":     lead.facebook_url,
            "line_id":          lead.line_id,
            "last_contacted_at": (
                lead.last_contacted_at.isoformat() if lead.last_contacted_at else None
            ),
            "status":           lead.status.value if lead.status else None,
        }
        for lead in leads
    ]


@router.patch("/leads/{lead_id}/stage")
def update_stage(
    lead_id: int,
    stage: str = Form(...),
    db: Session = Depends(get_db),
):
    """Founder manually sets a lead's funnel stage from the sidebar."""
    valid = {s.value for s in LeadStage}
    if stage not in valid:
        raise HTTPException(status_code=400, detail=f"invalid stage; valid values: {sorted(valid)}")
    changed = update_lead_stage(db, lead_id, stage)
    return {"ok": True, "changed": changed, "stage": stage, "stage_label": STAGE_LABELS.get(stage, stage)}


@router.post("/run/stream")
async def run_office_stream(
    request: Request,
    raw_text: str = Form(""),
    conversation_id: int = Form(...),
    image_urls: str = Form("[]"),
    lead_id: int | None = Form(None),
    db: Session = Depends(get_db),
):
    """Server-Sent Events endpoint: streams each pipeline stage as JSON events
    so the browser can render agent progress in real time without page freezes."""
    try:
        parsed_image_urls = json.loads(image_urls) or []
    except (TypeError, ValueError):
        parsed_image_urls = []

    async def event_generator():
        try:
            async for event in stream_run_office(
                db, raw_text,
                conversation_id=conversation_id,
                image_urls=parsed_image_urls,
                lead_id=lead_id,
            ):
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
async def run_office(
    request: Request,
    raw_text: str = Form(...),
    conversation_id: int | None = Form(None),
    db: Session = Depends(get_db),
):
    result = await run_office_graph(db, raw_text)

    run = OfficeRun(
        raw_text=raw_text,
        image_urls=[],
        conversation_id=conversation_id,
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
        general_answer=result.get("general_answer"),
    )
    db.add(run)
    db.commit()

    return templates.TemplateResponse(
        request,
        "office.html",
        {
            "latest_run": run,
            "pending_approvals": _pending_approvals(db),
            "conversation_id": conversation_id,
            "conversations": _conversation_list(db),
        },
    )


@router.post("/run/continue")
async def continue_office_run(
    previous_run_id: int = Form(...),
    answer: str = Form(...),
    db: Session = Depends(get_db),
):
    """Founder answering a clarifying_question a worker agent asked.

    Returns JSON with the combined raw_text the client should stream through
    /run/stream so the founder sees real-time SSE progress instead of a
    full-page reload.  Folds the answer into the original raw_text so every
    agent has full context (same approach as before, just returned as JSON
    instead of an HTML page redirect).
    """
    previous = db.get(OfficeRun, previous_run_id)
    if not previous:
        raise HTTPException(status_code=404, detail="not found")

    combined_text = (
        f"{previous.raw_text}\n\n[คำตอบเพิ่มเติมจาก Founder ต่อคำถามของทีม AI]\n{answer.strip()}"
    )
    return {
        "combined_text": combined_text,
        "conversation_id": previous.conversation_id,
    }


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


# ---------------------------------------------------------------------------
# Usage / quota monitoring page
# ---------------------------------------------------------------------------

@router.get("/usage", response_class=HTMLResponse)
def usage_page(request: Request, db: Session = Depends(get_db)):
    """Dashboard showing GitHub Models API quota, sleep state, and recent logs."""
    from sqlalchemy import func, select
    from datetime import date

    sleep_state = rate_limiter.get_sleep_state(db)
    today_quota = rate_limiter.estimate_quota_used_today(db)

    # Last 7 days daily breakdown
    from sqlalchemy import cast, Date
    daily_rows = db.execute(
        select(
            cast(ApiUsageLog.created_at, Date).label("day"),
            ApiUsageLog.status,
            func.count(ApiUsageLog.id).label("cnt"),
        )
        .group_by("day", ApiUsageLog.status)
        .order_by("day")
    ).all()

    # Per-agent breakdown (all time, last 7 days)
    from datetime import timedelta
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    agent_rows = db.execute(
        select(
            ApiUsageLog.agent_name,
            ApiUsageLog.status,
            func.count(ApiUsageLog.id).label("cnt"),
        )
        .where(ApiUsageLog.created_at >= week_ago)
        .group_by(ApiUsageLog.agent_name, ApiUsageLog.status)
        .order_by(ApiUsageLog.agent_name)
    ).all()

    # Recent log entries (last 60)
    recent_logs = db.scalars(
        select(ApiUsageLog).order_by(ApiUsageLog.created_at.desc()).limit(60)
    ).all()

    # Token totals today
    tokens_today = db.scalar(
        select(func.sum(ApiUsageLog.tokens_used)).where(
            ApiUsageLog.created_at >= datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        )
    ) or 0

    return templates.TemplateResponse(
        request,
        "usage.html",
        {
            "sleep_state": sleep_state,
            "today": today_quota,
            "tokens_today": tokens_today,
            "daily_rows": daily_rows,
            "agent_rows": agent_rows,
            "recent_logs": recent_logs,
            "now": datetime.now(timezone.utc),
        },
    )


@router.post("/usage/wake")
def wake_bot(db: Session = Depends(get_db)):
    """Clear sleep mode immediately so the bot can make LLM calls again."""
    row = db.get(SystemState, SLEEP_STATE_KEY)
    if row:
        db.delete(row)
        db.commit()
    logger.info("Sleep mode cleared manually via /usage/wake")
    return RedirectResponse(url="/usage", status_code=303)


@router.get("/usage/stats")
def usage_stats_api(db: Session = Depends(get_db)):
    """JSON endpoint for live-refresh of the usage widget without a full page reload."""
    sleep_state = rate_limiter.get_sleep_state(db)
    today = rate_limiter.estimate_quota_used_today(db)
    return {
        "sleep_state": {
            "sleeping": sleep_state["sleeping"],
            "wake_at": sleep_state["wake_at"].isoformat() if sleep_state.get("wake_at") else None,
            "reason": sleep_state.get("reason"),
        },
        **today,
    }
