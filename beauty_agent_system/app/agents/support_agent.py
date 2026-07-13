"""Agent 3: Support & Interactive Guide.

Answers strictly from the Knowledge Base (RAG-only, no memory answers). If no
KB match is found (or the match looks like a complex bug report), it opens a
support ticket for the admin instead of guessing.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.prompts import SUPPORT_AGENT_SYSTEM_PROMPT, SUPPORT_AGENT_USER_TEMPLATE
from app.llm_client import LLMUnavailable, call_llm
from app.models import KbArticle, SupportTicket

AGENT_NAME = "support_agent"


def _find_kb_match(db: Session, question: str) -> KbArticle | None:
    """Simple keyword-overlap match against the KB. No embeddings needed for
    the size of KB this founder will realistically maintain by hand."""
    words = {w.lower() for w in question.split() if len(w) > 2}
    if not words:
        return None
    articles = db.scalars(select(KbArticle)).all()
    best: tuple[int, KbArticle | None] = (0, None)
    for article in articles:
        haystack = f"{article.question} {article.tags or ''}".lower()
        score = sum(1 for w in words if w in haystack)
        if score > best[0]:
            best = (score, article)
    if best[0] == 0:
        return None
    return best[1]


async def answer_question(db: Session, shop_id: int | None, question: str) -> dict:
    match = _find_kb_match(db, question)

    if not match:
        ticket = SupportTicket(
            shop_id=shop_id,
            question=question,
            summary=f"No KB match found for: {question[:300]}",
            status="open",
        )
        db.add(ticket)
        db.commit()
        return {"status": "ticket_opened", "ticket_id": ticket.id, "kb_answer_found": False}

    try:
        answer = await call_llm(
            db,
            AGENT_NAME,
            SUPPORT_AGENT_SYSTEM_PROMPT,
            SUPPORT_AGENT_USER_TEMPLATE.format(question=question, kb_excerpt=match.answer),
        )
    except LLMUnavailable:
        # LLM down -- fall back to the raw KB answer verbatim rather than guessing.
        answer = match.answer

    return {"status": "answered", "kb_answer_found": True, "answer": answer, "article_id": match.id}
