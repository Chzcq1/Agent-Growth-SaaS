"""Agent 1: Lead Scraper & Analyst.

Research-first, always. Never calls the LLM unless real page text was
fetched -- if research turned up nothing, the lead is marked
``insufficient_data`` and no LLM call happens at all (saves quota and avoids
hallucination by construction).
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.agents.prompts import LEAD_SCRAPER_SYSTEM_PROMPT, LEAD_SCRAPER_USER_TEMPLATE
from app.llm_client import LLMUnavailable, call_llm
from app.models import Lead
from app.research import INSUFFICIENT_DATA, research_lead

AGENT_NAME = "lead_scraper"


async def analyze_lead(db: Session, shop_id: int) -> dict:
    lead = db.get(Lead, shop_id)
    if not lead:
        return {"status": "error", "detail": "lead not found"}

    research = await research_lead(db, shop_id, lead.facebook_url)

    if research["status"] == INSUFFICIENT_DATA:
        lead.pain_points = {
            "status": INSUFFICIENT_DATA,
            "source": research.get("source"),
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
        db.commit()
        return {"status": INSUFFICIENT_DATA, "shop_id": shop_id}

    try:
        summary = await call_llm(
            db,
            AGENT_NAME,
            LEAD_SCRAPER_SYSTEM_PROMPT,
            LEAD_SCRAPER_USER_TEMPLATE.format(
                shop_name=lead.shop_name,
                source_url=research["source"],
                fetched_at=research["fetched_at"],
                page_text=research["text"],
            ),
        )
    except LLMUnavailable as exc:
        return {"status": "llm_unavailable", "shop_id": shop_id, "detail": str(exc)}

    lead.pain_points = {
        "status": "ok",
        "summary": summary,
        "source": research["source"],
        "fetched_at": research["fetched_at"],
    }
    db.commit()
    return {"status": "ok", "shop_id": shop_id, "pain_points": lead.pain_points}
