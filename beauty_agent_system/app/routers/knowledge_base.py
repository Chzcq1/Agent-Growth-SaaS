"""Knowledge Base Manager -- what Agent 3 is allowed to answer from."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import KbArticle, SupportTicket

router = APIRouter(prefix="/admin/knowledge-base", tags=["admin"])
templates = Jinja2Templates(directory="app/templates")


@router.get("", response_class=HTMLResponse)
def list_articles(request: Request, db: Session = Depends(get_db)):
    articles = db.scalars(select(KbArticle).order_by(KbArticle.updated_at.desc())).all()
    tickets = db.scalars(
        select(SupportTicket).where(SupportTicket.status == "open").order_by(SupportTicket.created_at.desc())
    ).all()
    return templates.TemplateResponse(
        "knowledge_base.html",
        {"request": request, "articles": articles, "tickets": tickets, "active_nav": "knowledge_base"},
    )


@router.post("")
def create_article(
    question: str = Form(...), answer: str = Form(...), tags: str = Form(""), db: Session = Depends(get_db)
):
    db.add(KbArticle(question=question, answer=answer, tags=tags or None))
    db.commit()
    return RedirectResponse(url="/admin/knowledge-base", status_code=303)


@router.post("/{article_id}/delete")
def delete_article(article_id: int, db: Session = Depends(get_db)):
    article = db.get(KbArticle, article_id)
    if article:
        db.delete(article)
        db.commit()
    return RedirectResponse(url="/admin/knowledge-base", status_code=303)


@router.post("/tickets/{ticket_id}/close")
def close_ticket(ticket_id: int, db: Session = Depends(get_db)):
    ticket = db.get(SupportTicket, ticket_id)
    if ticket:
        ticket.status = "closed"
        db.commit()
    return RedirectResponse(url="/admin/knowledge-base", status_code=303)
