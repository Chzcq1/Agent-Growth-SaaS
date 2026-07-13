"""System Health -- token/rate-limit status for the Admin dashboard."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.rate_limiter import rate_limiter

router = APIRouter(prefix="/admin/system-health", tags=["admin"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
def system_health(request: Request, db: Session = Depends(get_db)):
    settings = get_settings()
    sleep_state = rate_limiter.get_sleep_state(db)
    quota = rate_limiter.estimate_quota_used_today(db)
    return templates.TemplateResponse(
        "system_health.html",
        {
            "request": request,
            "sleep_state": sleep_state,
            "quota": quota,
            "max_per_minute": settings.max_requests_per_minute,
            "max_concurrency": settings.max_concurrent_requests,
            "active_nav": "system_health",
        },
    )


@router.get("/api", response_class=None)
def system_health_json(db: Session = Depends(get_db)):
    sleep_state = rate_limiter.get_sleep_state(db)
    quota = rate_limiter.estimate_quota_used_today(db)
    return {
        "sleeping": sleep_state["sleeping"],
        "wake_at": sleep_state["wake_at"].isoformat() if sleep_state["wake_at"] else None,
        **quota,
    }
