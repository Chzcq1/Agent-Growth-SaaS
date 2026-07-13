"""สรุปประจำวัน (Daily Summary) -- Agent 5's digest of overdue/due-today
tasks plus new findings from the last 24 hours. Generated automatically
every morning by the scheduler; the founder can also regenerate on demand."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents import planner_agent
from app.database import get_db
from app.models import DailyBriefing

router = APIRouter(prefix="/admin/daily-summary", tags=["admin"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
def show_daily_summary(request: Request, db: Session = Depends(get_db)):
    briefings = db.scalars(select(DailyBriefing).order_by(DailyBriefing.created_at.desc()).limit(14)).all()
    return templates.TemplateResponse(
        request,
        "daily_summary.html",
        {"latest": briefings[0] if briefings else None, "history": briefings[1:], "active_nav": "daily_summary"},
    )


@router.post("/generate")
async def generate_now(db: Session = Depends(get_db)):
    await planner_agent.generate_daily_briefing(db)
    return RedirectResponse(url="/admin/daily-summary", status_code=303)
