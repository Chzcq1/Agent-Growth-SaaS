"""TikTok comment scan → classify → reply pipeline.

Flow (called every 10 minutes by APScheduler):
  1. List the account's recent videos via the TikTok API.
  2. For each video, fetch new comments starting from cursor=0 and stop
     early when we hit an already-processed comment_id (with a page cap of
     MAX_COMMENT_PAGES for safety).
  3. Classify each new comment (buying_signal / question / noise) via one
     LLM call that also generates a contextual reply.
  4. buying_signal → post a comment reply + create / merge Lead record.
     question     → post a comment reply only.
     noise        → skip.
  5. Mark comment processed.
  6. Threaded replies: comments with a parent_comment_id are replies to an
     existing thread; we reply with the same parent so the conversation stays
     threaded.

Reliability guarantees (same as facebook_pipeline):
  1. LLM failures return a ``_llm_error`` sentinel → comment is left
     unprocessed so the next scan retries rather than silently dropping it.
  2. Comments are marked processed only AFTER the required actions succeed:
     - noise → immediately (nothing to do).
     - question / buying_signal → after reply succeeds. If reply fails,
       comment stays unprocessed for retry.
  3. No "advance past unresolved comment" race: we use comment-ID dedup
     (not timestamp/cursor) for new-comment detection, so an LLM failure
     in the middle of a page never skips later comments.

Cross-channel lead merge (step 4):
  Before creating a new Lead for a TikTok buying_signal, we do a
  case-insensitive name lookup against existing leads. If a match is found
  we attach the TikTok comment/video IDs to that lead instead of creating
  a duplicate record.

Note: TikTok DM is out of scope — the reply text directs interested users
to Line or Facebook Messenger where the Chatwoot/Facebook pipelines take over.
"""
from __future__ import annotations

import hashlib
import logging
from collections import deque
from datetime import datetime, timezone, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import tiktok_client
from app.agents._json_utils import parse_json_object
from app.agents.prompts import (
    TIKTOK_CLASSIFY_SYSTEM_PROMPT,
    TIKTOK_CLASSIFY_USER_TEMPLATE,
)
from app.config import get_settings
from app.llm_client import LLMUnavailable, call_llm
from app.models import Lead, LeadStatus, ResearchCache

logger = logging.getLogger("beauty_agent_system.tiktok_pipeline")

# Safety cap: max comment-list pages per video per scan (50 comments/page)
MAX_COMMENT_PAGES = 5


# ── Research-cache helpers (shared pattern with facebook_pipeline) ─────────────

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
    return _get_cache(db, f"tt_comment:{comment_id}") is not None


def _mark_comment_processed(db: Session, comment_id: str, classification: str) -> None:
    _set_cache(db, f"tt_comment:{comment_id}", {
        "classification": classification,
        "processed_at": datetime.now(timezone.utc).isoformat(),
    })


# ── LLM: classify + generate reply ────────────────────────────────────────────

async def classify_and_generate(
    db: Session,
    comment_text: str,
    commenter_name: str,
    *,
    is_threaded: bool = False,
) -> dict:
    """One LLM call: classify the comment and generate a contextual reply.

    Returns:
        {
          "classification": "buying_signal" | "question" | "noise",
          "comment_reply":  str | None,
          "reasoning":      str,
        }

    On LLM/parse failure returns classification = "_llm_error" — the caller
    MUST NOT mark the comment processed so the next scan can retry.
    """
    user_prompt = TIKTOK_CLASSIFY_USER_TEMPLATE.format(
        commenter_name=commenter_name,
        comment_text=comment_text,
        thread_context="(ข้อความนี้เป็น reply ใน thread ต่อเนื่อง)" if is_threaded else "",
    )
    try:
        raw = await call_llm(
            db,
            "tiktok_classifier",
            TIKTOK_CLASSIFY_SYSTEM_PROMPT,
            user_prompt,
            temperature=0.5,   # slightly higher for reply variety per spec
        )
        data = parse_json_object(raw)
    except (LLMUnavailable, ValueError) as exc:
        logger.warning("tiktok classify_and_generate failed (will retry): %s", exc)
        return {
            "classification": "_llm_error",
            "comment_reply": None,
            "reasoning": f"AI error: {exc}",
        }

    return {
        "classification": data.get("classification", "noise"),
        "comment_reply": (data.get("comment_reply") or "").strip() or None,
        "reasoning": (data.get("reasoning") or "").strip(),
    }


# ── Cross-channel lead merge / create ─────────────────────────────────────────

def _find_or_merge_tiktok_lead(
    db: Session,
    *,
    commenter_name: str,
    comment_id: str,
    video_id: str,
    comment_text: str,
) -> tuple[Lead, bool]:
    """Find an existing lead by normalized name and merge TikTok data, or create new.

    Returns (lead, was_merged).
    """
    # 1. Already linked to this exact TikTok comment (idempotent)
    existing = db.scalar(
        select(Lead).where(Lead.tiktok_comment_id == comment_id)
    )
    if existing:
        return existing, False

    # 2. Cross-channel merge: look for existing lead with same name (case-insensitive)
    #    that does NOT yet have a TikTok comment attached.
    normalized = commenter_name.strip().lower()
    if normalized:
        same_name = db.scalar(
            select(Lead)
            .where(func.lower(Lead.shop_name) == normalized)
            .where(Lead.tiktok_comment_id.is_(None))
            .order_by(Lead.created_at.desc())
        )
        if same_name:
            same_name.tiktok_comment_id = comment_id
            same_name.tiktok_video_id = video_id
            # Preserve the existing source; annotate pain_points with TikTok context
            pain = dict(same_name.pain_points or {})
            pain["tiktok_comment_text"] = comment_text[:500]
            same_name.pain_points = pain
            db.commit()
            logger.info(
                "Merged TikTok comment=%s into existing lead shop_id=%s (cross-channel)",
                comment_id, same_name.shop_id,
            )
            return same_name, True

    # 3. Create new lead
    lead = Lead(
        shop_name=commenter_name or "TikTok Lead",
        stage="interested",
        source="tiktok_comment",
        tiktok_comment_id=comment_id,
        tiktok_video_id=video_id,
        conversation_history=[],
        pain_points={"tiktok_comment_text": comment_text[:500]},
        status=LeadStatus.CONTACTED,
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    logger.info(
        "Created TikTok lead shop_id=%s for comment=%s",
        lead.shop_id, comment_id,
    )
    return lead, False


# ── Main scanner ───────────────────────────────────────────────────────────────

async def process_new_comments(db: Session) -> int:
    """Scan the account's recent TikTok videos for new comments and process them.

    Called every 10 minutes by APScheduler. Returns the number of comments
    acted on (reply posted).

    Safe to call when TikTok is disabled: returns 0 immediately.

    Comment-discovery strategy:
      For each video, fetch comments from cursor=0 (newest first) and stop
      when we encounter a comment already in the processed cache, or after
      MAX_COMMENT_PAGES pages (safety cap). This means we always catch the
      freshest comments without relying on a time cursor (which can drift).
    """
    if not get_settings().tiktok_enabled:
        return 0

    processed = 0
    try:
        video_result = await tiktok_client.list_videos(db, cursor=0, max_count=20)
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to list TikTok videos: %s", exc)
        return 0

    for video in video_result.get("videos", []):
        video_id = video.get("id")
        if not video_id:
            continue

        cursor = 0
        pages_fetched = 0

        while pages_fetched < MAX_COMMENT_PAGES:
            try:
                result = await tiktok_client.list_comments(db, video_id, cursor=cursor, count=50)
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to list comments video=%s cursor=%s: %s", video_id, cursor, exc)
                break

            comments = result.get("comments", [])
            has_more = result.get("has_more", False)
            next_cursor = result.get("cursor", 0)
            pages_fetched += 1

            stop_early = False
            for comment in comments:
                comment_id = comment.get("id")
                if not comment_id:
                    continue

                # Stop when we reach a comment we've already processed
                if _is_comment_processed(db, comment_id):
                    stop_early = True
                    break

                comment_text = (comment.get("text") or "").strip()
                if not comment_text:
                    _mark_comment_processed(db, comment_id, "noise")
                    continue

                user = comment.get("user") or {}
                commenter_name = (
                    user.get("display_name")
                    or user.get("username")
                    or "ผู้ใช้ TikTok"
                )
                is_threaded = bool(comment.get("parent_comment_id"))

                result_cls = await classify_and_generate(
                    db, comment_text, commenter_name, is_threaded=is_threaded
                )
                classification = result_cls["classification"]
                comment_reply = result_cls["comment_reply"]

                logger.info(
                    "tt comment=%s video=%s classification=%s commenter=%r",
                    comment_id, video_id, classification, commenter_name,
                )

                # ── LLM error → leave unprocessed for retry ──────────────────
                if classification == "_llm_error":
                    logger.info(
                        "tt comment=%s deferred — LLM unavailable; will retry next scan",
                        comment_id,
                    )
                    # Do NOT advance past this comment — stop page traversal so
                    # we re-fetch it next time from cursor=0.
                    stop_early = True
                    break

                if classification == "noise" or not comment_reply:
                    _mark_comment_processed(db, comment_id, classification)
                    continue

                # ── Post comment reply (required before marking processed) ────
                parent_id = comment.get("parent_comment_id") or comment_id
                try:
                    await tiktok_client.post_comment(
                        db,
                        video_id,
                        comment_reply,
                        parent_comment_id=parent_id,
                    )
                    logger.info("Replied to tt comment=%s (threaded=%s)", comment_id, is_threaded)
                except Exception as exc:  # noqa: BLE001
                    # Transient failure — stop traversal here so this comment
                    # remains unprocessed and sits at the front of the unprocessed
                    # window. On the next scan we restart from cursor=0 and
                    # encounter it before any previously-processed comments,
                    # guaranteeing a retry. Continuing past this comment would
                    # risk hiding it behind processed-comment early-stop logic.
                    logger.warning(
                        "Failed to reply to tt comment=%s — stopping traversal for retry: %s",
                        comment_id, exc,
                    )
                    stop_early = True
                    break  # do NOT mark processed; exit comment loop for this page

                # Reply succeeded — now mark processed
                if classification == "buying_signal":
                    _find_or_merge_tiktok_lead(
                        db,
                        commenter_name=commenter_name,
                        comment_id=comment_id,
                        video_id=video_id,
                        comment_text=comment_text,
                    )
                    processed += 1
                elif classification == "question":
                    processed += 1

                _mark_comment_processed(db, comment_id, classification)

            if stop_early or not has_more:
                break

            cursor = next_cursor

    return processed
