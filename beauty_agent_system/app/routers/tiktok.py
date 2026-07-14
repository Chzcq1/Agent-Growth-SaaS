"""TikTok prospecting log endpoint.

GET /tiktok/leads
  Returns leads that have a tiktok_comment_id set (sourced from or merged
  with TikTok activity), ordered by most recently created.
  Used by the sidebar "TikTok" panel in the Virtual Office.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.customer_context import STAGE_COLORS, STAGE_LABELS
from app.database import get_db
from app.models import Lead

logger = logging.getLogger("beauty_agent_system.tiktok_router")

router = APIRouter(prefix="/tiktok", tags=["tiktok"])


@router.get("/leads")
def tiktok_leads(db: Session = Depends(get_db)):
    """Prospecting log: leads sourced from or merged with TikTok comments."""
    leads = db.scalars(
        select(Lead)
        .where(Lead.tiktok_comment_id.is_not(None))
        .order_by(Lead.created_at.desc())
        .limit(50)
    ).all()

    return [
        {
            "id":                 lead.shop_id,
            "shop_name":          lead.shop_name,
            "stage":              lead.stage or "interested",
            "stage_label":        STAGE_LABELS.get(lead.stage or "interested", lead.stage or "interested"),
            "stage_color":        STAGE_COLORS.get(lead.stage or "interested", "#78716c"),
            "source":             lead.source or "tiktok_comment",
            "tiktok_comment_id":  lead.tiktok_comment_id,
            "tiktok_video_id":    lead.tiktok_video_id,
            "tiktok_video_url":   (
                f"https://www.tiktok.com/video/{lead.tiktok_video_id}"
                if lead.tiktok_video_id else None
            ),
            "comment_snippet":    (
                (lead.pain_points or {}).get("tiktok_comment_text", "")[:120]
                or (lead.pain_points or {}).get("comment_text", "")[:120]
            ),
            "merged":             lead.source != "tiktok_comment" and lead.tiktok_comment_id is not None,
            "created_at":         lead.created_at.isoformat() if lead.created_at else None,
            "last_contacted_at":  (
                lead.last_contacted_at.isoformat() if lead.last_contacted_at else None
            ),
        }
        for lead in leads
    ]
