"""Leads Overview -- browse and filter all leads."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Lead, LeadStatus

router = APIRouter(prefix="/admin/leads", tags=["admin"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
def list_leads(request: Request, status: str = "", db: Session = Depends(get_db)):
    query = select(Lead).order_by(Lead.created_at.desc())
    if status:
        query = query.where(Lead.status == LeadStatus(status))
    leads = db.scalars(query).all()
    return templates.TemplateResponse(
        request,
        "leads.html",
        {
            "leads": leads,
            "statuses": [s.value for s in LeadStatus],
            "active_status": status,
            "active_nav": "leads",
        },
    )


@router.post("")
def create_lead(
    shop_name: str = Form(...),
    facebook_url: str = Form(""),
    line_id: str = Form(""),
    db: Session = Depends(get_db),
):
    lead = Lead(shop_name=shop_name, facebook_url=facebook_url or None, line_id=line_id or None)
    db.add(lead)
    db.commit()
    return RedirectResponse(url="/admin/leads", status_code=303)
