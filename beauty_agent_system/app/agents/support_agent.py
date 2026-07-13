"""Agent 3: Support & Interactive Guide.

Answers strictly from the Knowledge Base (RAG-only, no memory answers). If no
KB match is found (or the match looks like a complex bug report), it opens a
support ticket for the admin instead of guessing.
"""
from __future__ import annotations

import difflib
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.prompts import SUPPORT_AGENT_SYSTEM_PROMPT, SUPPORT_AGENT_USER_TEMPLATE
from app.llm_client import LLMUnavailable, call_llm
from app.models import KbArticle, SupportTicket

AGENT_NAME = "support_agent"

# Matching is deliberately NOT whitespace-tokenized: Thai script has no
# spaces between words, so `question.split()` would never find overlap for
# Thai input. Instead we combine (a) whole-string similarity against the
# article's question via difflib, which works character-by-character and is
# language-agnostic, with (b) substring containment for comma-separated tags
# (English shorthand keywords the founder writes deliberately).
_MATCH_THRESHOLD = 0.28


def _normalize(text: str) -> str:
    return re.sub(r"\s+", "", text.lower())


def _find_kb_match(db: Session, question: str) -> KbArticle | None:
    normalized_question = _normalize(question)
    if not normalized_question:
        return None

    articles = db.scalars(select(KbArticle)).all()
    best: tuple[float, KbArticle | None] = (0.0, None)
    for article in articles:
        similarity = difflib.SequenceMatcher(
            None, normalized_question, _normalize(article.question)
        ).ratio()

        tag_hit = 0.0
        for tag in (article.tags or "").split(","):
            tag = tag.strip().lower()
            if tag and tag in question.lower():
                tag_hit = 0.5
                break

        score = max(similarity, tag_hit)
        if score > best[0]:
            best = (score, article)

    if best[0] < _MATCH_THRESHOLD:
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
