"""Facebook comment scan → classify → reply / DM pipeline.

Flow (called every 5 minutes by APScheduler):
  1. List recent posts on the Page (Graph API).
  2. For each post, load last_checked_at from research_cache.
  3. Fetch comments created since last_checked_at.
  4. Skip comments already processed (keyed by comment_id in research_cache).
  5. Classify the comment (buying_signal / question / noise) via one LLM call
     that also generates the public reply and DM text in one shot.
  6. buying_signal → post public reply + send DM (rate-limited) + create Lead.
     question     → post public reply only.
     noise        → skip.
  7. Mark comment processed, update last_checked_at for the post.

Rate limit: 20 DMs per rolling 60-minute window, enforced in-process via
_DM_TIMESTAMPS (a module-level list of UTC datetimes). No DB persistence
needed — the scheduler runs in the same process and a restart resets the
counter safely (Facebook won't ban for one restart-reset).
"""
from __future__ import annotations

import logging
from collections import deque
from datetime import datetime, timedelta, timezone

import hashlib

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import facebook_client, reply_templates
from app.agents._json_utils import parse_json_object
from app.agents.prompts import (
    FACEBOOK_CLASSIFY_SYSTEM_PROMPT,
    FACEBOOK_CLASSIFY_USER_TEMPLATE,
)
from app.config import get_settings
from app.llm_client import LLMUnavailable, call_llm
from app.models import Lead, LeadStatus, ResearchCache

logger = logging.getLogger("beauty_agent_system.facebook_pipeline")

# ── DM rate limiter (in-memory sliding window) ─────────────────────────────
_DM_TIMESTAMPS: deque[datetime] = deque()
_DM_WINDOW_SECONDS = 3600  # 60 minutes


def _can_send_dm() -> bool:
    limit = get_settings().facebook_dm_hourly_limit
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(seconds=_DM_WINDOW_SECONDS)
    while _DM_TIMESTAMPS and _DM_TIMESTAMPS[0] < cutoff:
        _DM_TIMESTAMPS.popleft()
    return len(_DM_TIMESTAMPS) < limit


def _record_dm() -> None:
    _DM_TIMESTAMPS.append(datetime.now(timezone.utc))


# ── Research-cache helpers ────────────────────────────────────────────────────

def _cache_key(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _get_cache(db: Session, key_text: str) -> dict | None:
    row = db.scalar(
        select(ResearchCache).where(ResearchCache.query_hash == _cache_key(key_text))
    )
    if not row:
        return None
    if row.expires_at and row.expires_at < datetime.now(timezone.utc).replace(tzinfo=None):
        return None
    return row.result


def _set_cache(db: Session, key_text: str, result: dict, ttl_days: int = 30) -> None:
    h = _cache_key(key_text)
    expires = (datetime.now(timezone.utc) + timedelta(days=ttl_days)).replace(tzinfo=None)
    row = db.scalar(select(ResearchCache).where(ResearchCache.query_hash == h))
    if row:
        row.result = result
        row.expires_at = expires
    else:
        db.add(ResearchCache(
            query_hash=h,
            query_text=key_text,
            result=result,
            verified=False,
            expires_at=expires,
        ))
    db.commit()


def _is_comment_processed(db: Session, comment_id: str) -> bool:
    return _get_cache(db, f"fb_comment:{comment_id}") is not None


def _mark_comment_processed(
    db: Session,
    comment_id: str,
    classification: str,
    *,
    commenter_name: str = "",
    comment_text: str = "",
    reply_text: str = "",
) -> None:
    _set_cache(db, f"fb_comment:{comment_id}", {
        "classification": classification,
        "processed_at": datetime.now(timezone.utc).isoformat(),
        "commenter_name": commenter_name,
        "comment_text": comment_text[:300] if comment_text else "",
        "reply_text": reply_text[:500] if reply_text else "",
    })


def _get_post_last_checked(db: Session, post_id: str) -> datetime | None:
    cached = _get_cache(db, f"fb_post_checked:{post_id}")
    if not cached or not cached.get("last_checked_at"):
        return None
    try:
        return datetime.fromisoformat(cached["last_checked_at"])
    except (ValueError, KeyError):
        return None


def _set_post_last_checked(db: Session, post_id: str, ts: datetime | None = None) -> None:
    """Store the scan-cursor for a post.

    ``ts`` should be the timestamp captured BEFORE the list_comments call so
    that comments arriving during processing are not permanently missed.
    Defaults to now (safe for ad-hoc / test calls).
    """
    checkpoint = (ts or datetime.now(timezone.utc)).isoformat()
    _set_cache(db, f"fb_post_checked:{post_id}", {"last_checked_at": checkpoint})


# ── LLM: classify + generate ─────────────────────────────────────────────────

async def classify_and_generate(
    db: Session,
    comment_text: str,
    commenter_name: str,
) -> dict:
    """One LLM call: classify the comment and pre-generate reply + DM text.

    Returns:
        {
          "classification": "buying_signal" | "question" | "noise",
          "comment_reply":  str | None,   # public comment reply (short)
          "dm_text":        str | None,   # DM for buying_signal only
          "reasoning":      str,
        }
    """
    # Load founder-configurable templates from DB (falls back to defaults)
    tpls = reply_templates.get_all(db)
    tpl_lines = [
        "---",
        "Template ที่ต้องใช้ (ปรับถ้อยคำให้เข้ากับคอมเมนต์ได้ แต่รักษาโครงสร้างไว้):",
        f'buying_signal → comment_reply: "{tpls["reply_tpl_fb_buying_comment"]}"',
        f'buying_signal → dm_text: "{tpls["reply_tpl_fb_buying_dm"]}"',
    ]
    hint = tpls.get("reply_tpl_fb_question_hint", "").strip()
    if hint:
        tpl_lines.append(f'question → สไตล์/แนวทาง: "{hint}"')
    tpl_block = "\n".join(tpl_lines)

    user_prompt = FACEBOOK_CLASSIFY_USER_TEMPLATE.format(
        commenter_name=commenter_name,
        comment_text=comment_text,
    ) + "\n\n" + tpl_block
    try:
        raw = await call_llm(
            db,
            "facebook_classifier",
            FACEBOOK_CLASSIFY_SYSTEM_PROMPT,
            user_prompt,
            temperature=0.3,
        )
        data = parse_json_object(raw)
    except (LLMUnavailable, ValueError) as exc:
        # Return a sentinel so the caller can leave this comment unprocessed
        # and retry on the next scan rather than silently dropping it.
        logger.warning("classify_and_generate failed (will retry): %s", exc)
        return {
            "classification": "_llm_error",
            "comment_reply": None,
            "dm_text": None,
            "reasoning": f"AI error: {exc}",
        }

    return {
        "classification": data.get("classification", "noise"),
        "comment_reply": (data.get("comment_reply") or "").strip() or None,
        "dm_text": (data.get("dm_text") or "").strip() or None,
        "reasoning": (data.get("reasoning") or "").strip(),
    }


# ── Lead creation ─────────────────────────────────────────────────────────────

def _find_or_create_facebook_lead(
    db: Session,
    *,
    psid: str,
    commenter_name: str,
    comment_id: str,
    comment_text: str,
) -> Lead:
    """Find an existing lead for this PSID or create a new one."""
    # Try to find by facebook_comment_id first, then by shop_name + source
    existing = db.scalar(
        select(Lead).where(Lead.facebook_comment_id == comment_id)
    )
    if existing:
        return existing

    lead = Lead(
        shop_name=commenter_name or "Facebook Lead",
        stage="interested",
        source="facebook_comment",
        facebook_comment_id=comment_id,
        facebook_url=f"https://www.facebook.com/{psid}",
        conversation_history=[],
        pain_points={"comment_text": comment_text[:500]},
        status=LeadStatus.CONTACTED,
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    logger.info("Created Facebook lead shop_id=%s for comment=%s", lead.shop_id, comment_id)
    return lead


# ── Main scanner ──────────────────────────────────────────────────────────────

async def process_new_comments(db: Session) -> int:
    """Scan recent Page posts and process new comments.

    Called every 5 minutes by APScheduler. Returns the number of comments
    that were acted on (reply sent or DM sent).

    Safe to call when Facebook is disabled: returns 0 immediately.

    Reliability guarantees
    ─────────────────────
    1. Comments are marked processed only AFTER required actions succeed:
       - noise / empty message → immediate (nothing to do).
       - question → after public reply succeeds; failure leaves comment
         unprocessed so the next scan retries.
       - buying_signal → after public reply succeeds; the DM attempt (or
         explicit rate-limit skip) then determines the final mark.
         If the public reply itself fails the whole comment is left for retry.
         Once the reply is out we always mark processed (avoid duplicate
         replies) and record whether the DM was sent or skipped.

    2. Checkpoint race-window fix: ``scan_start`` is captured ONCE before any
       Graph API calls and stored as the cursor for every post processed in
       this run.  Comments that arrive DURING this scan will be fetched on the
       next run (since we start from scan_start, not "now at loop end") and
       processed then.  The processed-comment cache handles the small overlap
       efficiently.
    """
    settings = get_settings()
    if not settings.facebook_enabled:
        return 0

    # Capture scan start BEFORE any Graph API calls to avoid race window
    # (see docstring point 2).
    scan_start = datetime.now(timezone.utc)

    processed = 0
    try:
        posts = await facebook_client.list_recent_posts(limit=10)
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to list Facebook posts: %s", exc)
        return 0

    for post in posts:
        post_id = post.get("id")
        if not post_id:
            continue

        since = _get_post_last_checked(db, post_id)
        try:
            comments = await facebook_client.list_comments(post_id, since=since)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to list comments for post %s: %s", post_id, exc)
            continue

        # Track the earliest timestamp of any comment left unprocessed (LLM
        # error) so we can set the cursor conservatively and re-fetch it next
        # scan instead of advancing past it.
        earliest_deferred: datetime | None = None

        for comment in comments:
            comment_id = comment.get("id")
            if not comment_id:
                continue

            if _is_comment_processed(db, comment_id):
                continue

            comment_text = (comment.get("message") or "").strip()
            if not comment_text:
                # Nothing to act on — safe to mark immediately.
                _mark_comment_processed(db, comment_id, "noise")
                continue

            sender = comment.get("from") or {}
            commenter_name = sender.get("name") or "ลูกค้า"
            psid = sender.get("id") or ""

            result = await classify_and_generate(db, comment_text, commenter_name)
            classification = result["classification"]
            comment_reply = result["comment_reply"]
            dm_text = result["dm_text"]

            logger.info(
                "comment=%s classification=%s commenter=%r",
                comment_id, classification, commenter_name,
            )

            if classification == "_llm_error":
                # LLM temporarily unavailable — leave comment unprocessed so
                # the next scan retries classification rather than silently
                # dropping a potential lead.
                created_str = comment.get("created_time", "")
                if created_str:
                    ct = facebook_client.parse_fb_time(created_str)
                    if earliest_deferred is None or ct < earliest_deferred:
                        earliest_deferred = ct
                logger.info(
                    "comment=%s deferred (LLM unavailable); cursor will not advance past %s",
                    comment_id,
                    earliest_deferred.isoformat() if earliest_deferred else "unknown",
                )
                continue  # do NOT mark processed

            if classification == "noise" or not comment_reply:
                # No public action needed.
                _mark_comment_processed(db, comment_id, classification,
                                        commenter_name=commenter_name,
                                        comment_text=comment_text)
                continue

            # ── Public reply (required before marking processed) ──────────────
            try:
                await facebook_client.post_comment_reply(comment_id, comment_reply)
                logger.info("Replied to comment %s", comment_id)
            except Exception as exc:  # noqa: BLE001
                # Transient failure — leave comment unprocessed so next scan
                # retries the full action (reply + DM).
                logger.warning(
                    "Reply failed for comment %s — will retry next scan: %s",
                    comment_id, exc,
                )
                continue  # do NOT mark processed

            # Public reply succeeded.  From here we always mark processed
            # (even on DM failure) to prevent duplicate public replies.

            # ── DM for buying signals ─────────────────────────────────────────
            dm_outcome = "skipped"
            if classification == "buying_signal" and dm_text and psid:
                if _can_send_dm():
                    try:
                        await facebook_client.send_dm(psid, dm_text)
                        _record_dm()
                        _find_or_create_facebook_lead(
                            db,
                            psid=psid,
                            commenter_name=commenter_name,
                            comment_id=comment_id,
                            comment_text=comment_text,
                        )
                        logger.info("DM sent to psid=%s comment=%s", psid, comment_id)
                        dm_outcome = "sent"
                        processed += 1
                    except Exception as exc:  # noqa: BLE001
                        # DM failed after reply — log and accept; the public
                        # reply is already visible so we must not retry.
                        logger.warning(
                            "DM failed for comment %s (reply already sent): %s",
                            comment_id, exc,
                        )
                        dm_outcome = "dm_failed"
                else:
                    logger.warning(
                        "DM rate limit reached — reply sent but DM skipped for comment=%s",
                        comment_id,
                    )
                    dm_outcome = "rate_limited"
            elif classification == "question":
                processed += 1

            _mark_comment_processed(db, comment_id, f"{classification}:{dm_outcome}",
                                    commenter_name=commenter_name,
                                    comment_text=comment_text,
                                    reply_text=comment_reply or "")

        # Checkpoint: if any comments were deferred due to LLM errors, set
        # the cursor to just before the earliest deferred comment's created_time
        # so the next scan re-fetches them for retry.  Otherwise use scan_start
        # (pre-captured to avoid the race window where comments arrive during
        # processing and get missed permanently).
        if earliest_deferred is not None:
            checkpoint = earliest_deferred - timedelta(seconds=1)
            logger.info(
                "post=%s cursor set to %s (deferred comments present; scan_start=%s)",
                post_id, checkpoint.isoformat(), scan_start.isoformat(),
            )
        else:
            checkpoint = scan_start
        _set_post_last_checked(db, post_id, checkpoint)

    return processed
