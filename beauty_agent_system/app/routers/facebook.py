"""Facebook prospecting log endpoint.

GET /facebook/leads
  Returns leads that were created by the Facebook comment scanner
  (source = "facebook_comment"), ordered by most recently contacted.
  Used by the sidebar "Facebook" panel in the Virtual Office.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.customer_context import STAGE_COLORS, STAGE_LABELS
from app.database import get_db
from app.models import Lead

logger = logging.getLogger("beauty_agent_system.facebook_router")

router = APIRouter(prefix="/facebook", tags=["facebook"])


@router.get("/leads")
def facebook_leads(db: Session = Depends(get_db)):
    """Prospecting log: leads sourced from Facebook comments, newest first."""
    leads = db.scalars(
        select(Lead)
        .where(Lead.source == "facebook_comment")
        .order_by(Lead.last_contacted_at.desc(), Lead.created_at.desc())
        .limit(50)
    ).all()

    return [
        {
            "id":                  lead.shop_id,
            "shop_name":           lead.shop_name,
            "stage":               lead.stage or "interested",
            "stage_label":         STAGE_LABELS.get(lead.stage or "interested", lead.stage or "interested"),
            "stage_color":         STAGE_COLORS.get(lead.stage or "interested", "#78716c"),
            "facebook_url":        lead.facebook_url,
            "facebook_comment_id": lead.facebook_comment_id,
            "comment_snippet":     (
                (lead.pain_points or {}).get("comment_text", "")[:120]
                if lead.pain_points else ""
            ),
            "last_contacted_at":   (
                lead.last_contacted_at.isoformat() if lead.last_contacted_at else None
            ),
            "created_at":          lead.created_at.isoformat() if lead.created_at else None,
        }
        for lead in leads
    ]
