"""งานที่ต้องทำ (Tasks) -- every task always has a deadline, whether the
founder typed it in by hand or Agent 5 created it from a logged update."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Task, TaskStatus

router = APIRouter(prefix="/admin/tasks", tags=["admin"])
templates = Jinja2Templates(directory="app/templates")


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


@router.get("", response_class=HTMLResponse)
def list_tasks(request: Request, db: Session = Depends(get_db)):
    today_start = _now().replace(hour=0, minute=0, second=0, microsecond=0)
    open_tasks = db.scalars(
        select(Task).where(Task.status == TaskStatus.OPEN).order_by(Task.due_date.asc())
    ).all()
    overdue = [t for t in open_tasks if t.due_date and t.due_date < today_start]
    today = [t for t in open_tasks if t.due_date and today_start <= t.due_date < today_start + timedelta(days=1)]
    upcoming = [t for t in open_tasks if not t.due_date or t.due_date >= today_start + timedelta(days=1)]
    done = db.scalars(
        select(Task).where(Task.status == TaskStatus.DONE).order_by(Task.completed_at.desc()).limit(20)
    ).all()
    return templates.TemplateResponse(
        request,
        "tasks.html",
        {"overdue": overdue, "today": today, "upcoming": upcoming, "done": done, "active_nav": "tasks"},
    )


@router.post("")
def create_task(
    title: str = Form(...),
    description: str = Form(""),
    due_in_days: int = Form(3),
    db: Session = Depends(get_db),
):
    db.add(
        Task(
            title=title,
            description=description or None,
            category="other",
            due_date=_now() + timedelta(days=max(due_in_days, 0)),
        )
    )
    db.commit()
    return RedirectResponse(url="/admin/tasks", status_code=303)


@router.post("/{task_id}/complete")
def complete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if task:
        task.status = TaskStatus.DONE
        task.completed_at = _now()
        db.commit()
    return RedirectResponse(url="/admin/tasks", status_code=303)
