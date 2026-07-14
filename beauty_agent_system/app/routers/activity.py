"""Activity feed — shows every Facebook/TikTok comment the bot has acted on.

GET /activity
  Full-page activity feed with today's summary metrics and a reverse-
  chronological list of every comment the pipeline processed (buying_signal,
  question, noise) with the commenter name, comment snippet, bot reply, and
  result badge.

Data source: ResearchCache rows whose query_text starts with 'fb_comment:'
or 'tt_comment:'.  The pipeline now stores commenter_name, comment_text,
and reply_text in the result JSON for every processed comment.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ResearchCache

logger = logging.getLogger("beauty_agent_system.activity")

router = APIRouter(tags=["activity"])
templates = Jinja2Templates(directory="app/templates")


@router.get("/activity")
def activity_page(request: Request, db: Session = Depends(get_db)):
    """Render the bot reply activity feed."""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)

    rows = db.scalars(
        select(ResearchCache)
        .where(
            or_(
                ResearchCache.query_text.like("fb_comment:%"),
                ResearchCache.query_text.like("tt_comment:%"),
            )
        )
        .order_by(ResearchCache.created_at.desc())
        .limit(200)
    ).all()

    activities = []
    for row in rows:
        result = row.result or {}
        platform = "facebook" if (row.query_text or "").startswith("fb_") else "tiktok"
        classification_raw = result.get("classification", "")
        parts = classification_raw.split(":", 1)
        classification = parts[0]
        dm_outcome = parts[1] if len(parts) > 1 else ""

        activities.append({
            "platform": platform,
            "commenter_name": result.get("commenter_name") or "",
            "comment_text": result.get("comment_text") or "",
            "reply_text": result.get("reply_text") or "",
            "classification": classification,
            "dm_outcome": dm_outcome,
            "created_at": row.created_at,
        })

    # Today's metrics (created_at stored as naive UTC)
    today = [a for a in activities if a["created_at"] and a["created_at"] >= today_start]
    replied = [a for a in today if a["reply_text"]]

    metrics = {
        "total_today": len(today),
        "buying_signals": sum(1 for a in today if a["classification"] == "buying_signal"),
        "questions": sum(1 for a in today if a["classification"] == "question"),
        "noise": sum(1 for a in today if a["classification"] == "noise"),
        "replied": len(replied),
        "dms_sent": sum(1 for a in today if a["dm_outcome"] == "sent"),
    }

    return templates.TemplateResponse(request, "activity.html", {
        "request": request,
        "activities": activities,
        "metrics": metrics,
        "now": now,
    })
