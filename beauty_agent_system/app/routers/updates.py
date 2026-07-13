"""แจ้งเหตุการณ์ (Daily Updates) -- the founder logs whatever happened in
free text; Agent 5 (Planner) triages it into a finding + optional suggested
reply + optional task with a deadline."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents import planner_agent
from app.database import get_db
from app.models import DailyUpdate, Task

router = APIRouter(prefix="/admin/updates", tags=["admin"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
def list_updates(request: Request, db: Session = Depends(get_db)):
    updates = db.scalars(select(DailyUpdate).order_by(DailyUpdate.created_at.desc()).limit(50)).all()
    tasks_by_update_id = {
        t.source_update_id: t for t in db.scalars(select(Task).where(Task.source_update_id.isnot(None))).all()
    }
    return templates.TemplateResponse(
        request,
        "updates.html",
        {"updates": updates, "tasks_by_update_id": tasks_by_update_id, "active_nav": "updates"},
    )


@router.post("")
async def create_update(content: str = Form(...), db: Session = Depends(get_db)):
    await planner_agent.process_update(db, content)
    return RedirectResponse(url="/admin/updates", status_code=303)
