"""Founder-memory: point the team at what it already found instead of
re-deriving the same conclusion from zero every time it sees a similar
situation.

Inspired by the "query an existing knowledge structure instead of
recomputing" idea (codebase-graph tools take this approach for code; here
the equivalent knowledge store is simply the founder's own run history).

Deliberately narrow in scope: this only ever *adds a pointer* to what a past
run already concluded -- it never skips or shortcuts a current agent's own
reasoning, so it cannot make the team "dumber". A near-duplicate paste still
gets fully re-analyzed; it just isn't analyzed in a vacuum.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import OfficeRun

LOOKBACK_DAYS = 30
LOOKBACK_LIMIT = 50
# Below this, two pastes are considered unrelated -- no note.
RELATED_THRESHOLD = 0.72
# At/above this, treat it as a literal repeat -- the note calls that out
# explicitly instead of phrasing it as "similar".
EXACT_REPEAT_THRESHOLD = 0.93


def _recent_runs(db: Session) -> list[OfficeRun]:
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=LOOKBACK_DAYS)
    return list(
        db.scalars(
            select(OfficeRun)
            .where(OfficeRun.created_at >= cutoff)
            .where(OfficeRun.raw_text != "")
            .order_by(OfficeRun.created_at.desc())
            .limit(LOOKBACK_LIMIT)
        )
    )


def find_best_match(db: Session, raw_text: str, *, exclude_run_id: int | None = None) -> tuple[OfficeRun | None, float]:
    """Returns (most similar past run, similarity 0..1) or (None, 0.0)."""
    raw_text = (raw_text or "").strip()
    if not raw_text:
        return None, 0.0
    best_run, best_score = None, 0.0
    for run in _recent_runs(db):
        if run.id == exclude_run_id:
            continue
        score = SequenceMatcher(None, raw_text, run.raw_text or "").ratio()
        if score > best_score:
            best_run, best_score = run, score
    return best_run, best_score


def memory_note(db: Session, raw_text: str) -> str | None:
    """One-line pointer at the closest past run's key findings, if any past
    run is actually related. Returns None when nothing relevant exists --
    callers must not fabricate a note when this returns None."""
    run, score = find_best_match(db, raw_text)
    if not run or score < RELATED_THRESHOLD:
        return None
    findings = run.key_findings or []
    if not findings:
        return None
    when = run.created_at.strftime("%d/%m/%y") if run.created_at else "ก่อนหน้านี้"
    summary = " / ".join(f.split("] ", 1)[-1] for f in findings[:3])
    repeat_phrase = "เจอเคสนี้ซ้ำเดิมเป๊ะ" if score >= EXACT_REPEAT_THRESHOLD else "เจอสถานการณ์คล้ายกันนี้"
    return (
        f"{repeat_phrase}เมื่อ {when} สรุปไว้ว่า: {summary} -- ใช้เป็นข้อมูลอ้างอิงต่อยอด "
        f"ไม่ต้องเริ่มวิเคราะห์ใหม่จากศูนย์"
    )
