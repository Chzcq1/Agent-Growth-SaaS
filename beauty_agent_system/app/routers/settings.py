"""Settings page — lets the founder configure bot reply templates.

GET  /settings  → render settings.html with current template values
POST /settings  → save submitted templates, redirect back
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app import reply_templates

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

_ALL_KEYS = [
    "reply_tpl_fb_buying_comment",
    "reply_tpl_fb_buying_dm",
    "reply_tpl_fb_question_hint",
    "reply_tpl_tt_buying_comment",
    "reply_tpl_tt_question_hint",
]


@router.get("/settings", response_class=HTMLResponse)
def get_settings_page(request: Request, db: Session = Depends(get_db)):
    tpls = reply_templates.get_all(db)
    return templates.TemplateResponse(request, "settings.html", {"tpls": tpls})


@router.post("/settings")
def post_settings(
    request: Request,
    db: Session = Depends(get_db),
    reply_tpl_fb_buying_comment: str = Form(""),
    reply_tpl_fb_buying_dm: str = Form(""),
    reply_tpl_fb_question_hint: str = Form(""),
    reply_tpl_tt_buying_comment: str = Form(""),
    reply_tpl_tt_question_hint: str = Form(""),
):
    values = {
        "reply_tpl_fb_buying_comment": reply_tpl_fb_buying_comment.strip(),
        "reply_tpl_fb_buying_dm": reply_tpl_fb_buying_dm.strip(),
        "reply_tpl_fb_question_hint": reply_tpl_fb_question_hint.strip(),
        "reply_tpl_tt_buying_comment": reply_tpl_tt_buying_comment.strip(),
        "reply_tpl_tt_question_hint": reply_tpl_tt_question_hint.strip(),
    }
    for key, text in values.items():
        reply_templates.save(db, key, text)
    return RedirectResponse("/settings?saved=1", status_code=303)
