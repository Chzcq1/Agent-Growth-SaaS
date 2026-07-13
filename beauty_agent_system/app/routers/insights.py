"""Weekly Insights -- self-improvement summaries, Founder applies manually."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import WeeklyInsight

router = APIRouter(prefix="/admin/insights", tags=["admin"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
def list_insights(request: Request, db: Session = Depends(get_db)):
    insights = db.scalars(select(WeeklyInsight).order_by(WeeklyInsight.week_start.desc())).all()
    return templates.TemplateResponse(
        request, "insights.html", {"insights": insights, "active_nav": "insights"}
    )


@router.post("/{insight_id}/apply")
def mark_applied(insight_id: int, db: Session = Depends(get_db)):
    insight = db.get(WeeklyInsight, insight_id)
    if insight:
        insight.applied = True
        db.commit()
    return RedirectResponse(url="/admin/insights", status_code=303)
