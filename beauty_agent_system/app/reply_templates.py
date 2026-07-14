"""Helpers to load / save bot reply templates from SystemState (key-value store).

Templates are stored as JSON values in the existing ``system_state`` table —
no migration required.  Each template key maps to a dict ``{"text": "..."}``
so we can add metadata fields later without changing the schema.

Keys
----
reply_tpl_fb_buying_comment   – Facebook buying_signal public comment reply
reply_tpl_fb_buying_dm        – Facebook buying_signal DM text
reply_tpl_fb_question_hint    – Facebook question style hint (optional)
reply_tpl_tt_buying_comment   – TikTok buying_signal comment reply (with link)
reply_tpl_tt_question_hint    – TikTok question style hint (optional)
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import SystemState

# ── Defaults (shown when no DB row exists yet) ──────────────────────────────

DEFAULTS: dict[str, str] = {
    "reply_tpl_fb_buying_comment": (
        "ขอบคุณที่สนใจค่ะ ส่ง DM ไปให้แล้วนะคะ 😊"
    ),
    "reply_tpl_fb_buying_dm": (
        "สวัสดีค่ะ คุณ{name} 😊 ขอบคุณที่สนใจระบบจองคิวออนไลน์ของ CSC นะคะ "
        "สมัครเปิดร้านได้เลยที่ลิงก์นี้เลยค่ะ ทดลองใช้ฟรี 30 วัน 👇\n"
        "https://nail-salon-booking-5cbr.onrender.com/register"
    ),
    "reply_tpl_fb_question_hint": "",  # empty = let LLM answer naturally
    "reply_tpl_tt_buying_comment": (
        "ขอบคุณที่สนใจนะคะ 🥰 สมัครได้เลยที่นี่เลยค่า ทดลองฟรี 30 วัน 👉 "
        "https://nail-salon-booking-5cbr.onrender.com/register"
    ),
    "reply_tpl_tt_question_hint": "",  # empty = let LLM answer naturally
}

# ── Public API ───────────────────────────────────────────────────────────────

def get_all(db: Session) -> dict[str, str]:
    """Return all template texts, falling back to defaults for missing rows."""
    rows = {
        row.key: row.value.get("text", "")
        for row in db.query(SystemState).filter(
            SystemState.key.in_(list(DEFAULTS.keys()))
        ).all()
        if row.value
    }
    return {key: rows.get(key, default) for key, default in DEFAULTS.items()}


def get(db: Session, key: str) -> str:
    """Return a single template text, falling back to default."""
    row = db.get(SystemState, key)
    if row and row.value:
        return row.value.get("text", DEFAULTS.get(key, ""))
    return DEFAULTS.get(key, "")


def save(db: Session, key: str, text: str) -> None:
    """Upsert a template text into system_state."""
    row = db.get(SystemState, key)
    if row:
        row.value = {"text": text}
    else:
        db.add(SystemState(key=key, value={"text": text}))
    db.commit()
