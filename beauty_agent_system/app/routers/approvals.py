"""Pending Approvals -- Approve / Reject / Edit queue for the Founder."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.chatwoot_client import send_message
from app.database import get_db
from app.models import AgentFeedback, Lead, PendingApproval

router = APIRouter(prefix="/admin/approvals", tags=["admin"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
def list_approvals(request: Request, db: Session = Depends(get_db)):
    approvals = db.scalars(
        select(PendingApproval)
        .where(PendingApproval.status == "pending")
        .order_by(PendingApproval.created_at.asc())
    ).all()
    leads_by_id = {lead.shop_id: lead for lead in db.scalars(select(Lead)).all()}
    return templates.TemplateResponse(
        request,
        "approvals.html",
        {"approvals": approvals, "leads_by_id": leads_by_id, "active_nav": "approvals"},
    )


@router.post("/{approval_id}/approve")
async def approve(approval_id: int, db: Session = Depends(get_db)):
    approval = db.get(PendingApproval, approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="not found")
    approval.status = "approved"
    approval.reviewed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    lead = db.get(Lead, approval.shop_id)
    if lead:
        await send_message(conversation_id=None, shop_id=lead.shop_id, text=approval.draft_message or "")
        lead.conversation_history = [*(lead.conversation_history or []), {"role": "bot", "content": approval.draft_message}]
        lead.last_contacted_date = datetime.now(timezone.utc).replace(tzinfo=None)
    db.add(AgentFeedback(approval_id=approval.id, outcome="sent"))
    db.commit()
    return RedirectResponse(url="/admin/approvals", status_code=303)


@router.post("/{approval_id}/reject")
def reject(approval_id: int, founder_note: str = Form(""), db: Session = Depends(get_db)):
    approval = db.get(PendingApproval, approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="not found")
    approval.status = "rejected"
    approval.reviewed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.add(AgentFeedback(approval_id=approval.id, outcome="ignored", founder_note=founder_note or None))
    db.commit()
    return RedirectResponse(url="/admin/approvals", status_code=303)


@router.post("/{approval_id}/edit")
async def edit_and_approve(approval_id: int, edited_message: str = Form(...), db: Session = Depends(get_db)):
    approval = db.get(PendingApproval, approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="not found")
    approval.draft_message = edited_message
    approval.status = "edited"
    approval.reviewed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    lead = db.get(Lead, approval.shop_id)
    if lead:
        await send_message(conversation_id=None, shop_id=lead.shop_id, text=edited_message)
        lead.conversation_history = [*(lead.conversation_history or []), {"role": "bot", "content": edited_message}]
        lead.last_contacted_date = datetime.now(timezone.utc).replace(tzinfo=None)
    db.add(AgentFeedback(approval_id=approval.id, outcome="sent", founder_note="edited before sending"))
    db.commit()
    return RedirectResponse(url="/admin/approvals", status_code=303)
