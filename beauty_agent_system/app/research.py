"""Research-first helper.

Non-negotiable rule from the spec: no agent may state a marketing fact,
customer case, or statistic that wasn't actually retrieved from somewhere
real. This module is the single gate for that -- every "fact" that ends up
in a prompt must have flowed through here and be traceable back to a source
URL + timestamp in ``research_cache``.

Real web search is not wired into this backend by default (no search API key
was requested). The default provider fetches a lead's own public Facebook
page URL over HTTP and extracts visible text. If that fails, or turns up
nothing substantive, the result is marked ``insufficient_data`` -- callers
must never fall back to inventing content.

To use a real search API later, implement another provider and swap it in
`fetch_research` (see README "Wiring in a real search API").
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import ResearchCache

INSUFFICIENT_DATA = "insufficient_data"


def _hash(query_text: str) -> str:
    return hashlib.sha256(query_text.encode("utf-8")).hexdigest()


def get_cached(db: Session, query_text: str) -> dict | None:
    row = db.scalar(select(ResearchCache).where(ResearchCache.query_hash == _hash(query_text)))
    if not row:
        return None
    if row.expires_at and row.expires_at < datetime.now(timezone.utc).replace(tzinfo=None):
        return None
    return row.result


def _store(db: Session, query_text: str, result: dict, verified: bool) -> None:
    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.research_cache_ttl_days)
    query_hash = _hash(query_text)
    row = db.scalar(select(ResearchCache).where(ResearchCache.query_hash == query_hash))
    if row:
        row.result = result
        row.verified = verified
        row.expires_at = expires_at.replace(tzinfo=None)
    else:
        db.add(
            ResearchCache(
                query_hash=query_hash,
                query_text=query_text,
                result=result,
                verified=verified,
                expires_at=expires_at.replace(tzinfo=None),
            )
        )
    db.commit()


def _strip_html(html: str) -> str:
    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


async def fetch_public_page(url: str) -> tuple[str | None, str]:
    """Best-effort fetch of a public page. Returns (text_or_None, note)."""
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0 (research-bot)"})
        if resp.status_code >= 400:
            return None, f"http_{resp.status_code}"
        text = _strip_html(resp.text)
        if len(text) < 80:
            return None, "page_too_thin"
        return text[:6000], "ok"
    except Exception as exc:  # noqa: BLE001
        return None, f"fetch_error:{exc}"


async def research_lead(db: Session, shop_id: int, facebook_url: str | None) -> dict:
    """Research-before-generate for Agent 1 (Lead Scraper).

    Returns a dict always containing ``status`` (``ok`` or ``insufficient_data``),
    ``source`` (the URL used, if any), ``fetched_at``, and ``text`` (raw
    extracted text, only present when status == ok).
    """
    query_text = f"lead_research:{shop_id}:{facebook_url or ''}"
    cached = get_cached(db, query_text)
    if cached is not None:
        return cached

    if not facebook_url:
        result = {"status": INSUFFICIENT_DATA, "source": None, "fetched_at": None}
        _store(db, query_text, result, verified=False)
        return result

    text, note = await fetch_public_page(facebook_url)
    now_iso = datetime.now(timezone.utc).isoformat()
    if text is None:
        result = {"status": INSUFFICIENT_DATA, "source": facebook_url, "fetched_at": now_iso, "note": note}
        _store(db, query_text, result, verified=False)
        return result

    result = {"status": "ok", "source": facebook_url, "fetched_at": now_iso, "text": text}
    _store(db, query_text, result, verified=True)
    return result


def get_verified_case_study(db: Session) -> dict | None:
    """Return one verified case-study entry from the cache, or None.

    Agent 2's Day-4 follow-up step is only allowed to cite a case study if one
    exists here with ``verified = True`` -- see models.ResearchCache.
    """
    row = db.scalar(
        select(ResearchCache)
        .where(ResearchCache.verified.is_(True))
        .where(ResearchCache.query_text.like("case_study:%"))
        .order_by(ResearchCache.created_at.desc())
    )
    if not row:
        return None
    return row.result


def store_verified_case_study(db: Session, name: str, result: dict) -> None:
    """Admin/ops helper: record a verified case study Agent 2 may cite later."""
    _store(db, f"case_study:{name}", result, verified=True)
