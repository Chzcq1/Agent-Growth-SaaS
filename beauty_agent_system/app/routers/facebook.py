"""Facebook prospecting log + webhook + DM approval endpoints.

GET /facebook/leads
  Returns leads that were created by the Facebook comment scanner
  (source = "facebook_comment"), ordered by most recently contacted.
  Used by the sidebar "Facebook" panel in the Virtual Office.

GET /facebook/webhook
  Meta's one-time verification handshake when the webhook subscription is
  set up in the App dashboard.

POST /facebook/webhook
  Real-time push from Meta for new Messenger DMs and new Page comments.
  Verifies the request signature, then returns 200 immediately and does the
  actual work in a BackgroundTask (Meta requires a fast response).
  This is what keeps the bot responsive even if Render's free-tier dyno was
  asleep -- the incoming request itself wakes the process, instead of
  waiting for the next 5-minute poll (which never fires while asleep).

GET /facebook/dm/pending, POST /facebook/dm/{id}/send, /dismiss
  The founder's review queue for DMs the AI wasn't confident enough to send
  on its own -- rendered in the sidebar "Facebook" panel.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import facebook_client
from app.config import get_settings
from app.customer_context import STAGE_COLORS, STAGE_LABELS
from app.database import get_db, get_session_factory
from app.models import Lead, PendingApproval

logger = logging.getLogger("beauty_agent_system.facebook_router")

router = APIRouter(prefix="/facebook", tags=["facebook"])


@router.get("/leads")
def facebook_leads(db: Session = Depends(get_db)):
    """Prospecting log: leads sourced from Facebook comments, newest first."""
    leads = db.scalars(
        select(Lead)
        .where(Lead.source == "facebook_comment")
        .order_by(Lead.last_contacted_at.desc(), Lead.created_at.desc())
        .limit(50)
    ).all()

    return [
        {
            "id":                  lead.shop_id,
            "shop_name":           lead.shop_name,
            "stage":               lead.stage or "interested",
            "stage_label":         STAGE_LABELS.get(lead.stage or "interested", lead.stage or "interested"),
            "stage_color":         STAGE_COLORS.get(lead.stage or "interested", "#78716c"),
            "facebook_url":        lead.facebook_url,
            "facebook_comment_id": lead.facebook_comment_id,
            "comment_snippet":     (
                (lead.pain_points or {}).get("comment_text", "")[:120]
                if lead.pain_points else ""
            ),
            "last_contacted_at":   (
                lead.last_contacted_at.isoformat() if lead.last_contacted_at else None
            ),
            "created_at":          lead.created_at.isoformat() if lead.created_at else None,
        }
        for lead in leads
    ]


# ── Webhook: verification handshake ──────────────────────────────────────────

@router.get("/webhook")
async def verify_webhook_handshake(request: Request):
    """Meta calls this once, with query params using dots (hub.mode etc.,
    which FastAPI can't bind to a Python identifier directly -- read raw
    query params instead), when the founder saves the webhook subscription
    in the App dashboard."""
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    expected = get_settings().facebook_webhook_verify_token
    if mode == "subscribe" and expected and token == expected:
        logger.info("Facebook webhook verification succeeded")
        return PlainTextResponse(challenge or "")

    logger.warning("Facebook webhook verification failed (mode=%s, token matched=%s)", mode, token == expected)
    raise HTTPException(status_code=403, detail="verification failed")


# ── Webhook: real-time events ────────────────────────────────────────────────

async def _handle_dm_background(psid: str, contact_name: str, message_text: str) -> None:
    from app import facebook_client
    from app.facebook_dm_pipeline import handle_incoming_dm

    # Try to get the real sender name from the Graph API; fall back to the
    # name passed in (usually "ลูกค้า Facebook") if the profile call fails.
    profile = await facebook_client.get_user_profile(psid)
    resolved_name = profile.get("name") or contact_name

    session_factory = get_session_factory()
    db = session_factory()
    try:
        await handle_incoming_dm(db, psid=psid, contact_name=resolved_name, message_text=message_text)
    except Exception:  # noqa: BLE001
        logger.exception("Facebook DM handling failed for psid=%s", psid)
        db.rollback()
    finally:
        db.close()


async def _trigger_immediate_comment_scan() -> None:
    from app.scheduler import _scan_facebook_comments

    try:
        await _scan_facebook_comments()
    except Exception:  # noqa: BLE001
        logger.exception("Immediate Facebook comment scan (webhook-triggered) failed")


@router.post("/webhook")
async def receive_webhook(request: Request, background_tasks: BackgroundTasks):
    raw_body = await request.body()
    signature = request.headers.get("x-hub-signature-256")

    if not facebook_client.verify_webhook_signature(raw_body, signature):
        logger.warning("Facebook webhook signature mismatch — rejected")
        raise HTTPException(status_code=401, detail="invalid signature")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="invalid JSON body")

    if payload.get("object") != "page":
        return {"ok": True, "skipped": "not a page object"}

    saw_message = False
    saw_comment = False

    for entry in payload.get("entry", []):
        for msg_event in entry.get("messaging", []) or []:
            message = msg_event.get("message") or {}
            if message.get("is_echo"):
                continue  # our own outgoing message being echoed back -- not a customer reply
            text = (message.get("text") or "").strip()
            psid = (msg_event.get("sender") or {}).get("id")
            if text and psid:
                saw_message = True
                background_tasks.add_task(_handle_dm_background, psid, "ลูกค้า Facebook", text)

        for change in entry.get("changes", []) or []:
            value = change.get("value") or {}
            if change.get("field") == "feed" and value.get("item") == "comment" and value.get("verb") == "add":
                saw_comment = True

    if saw_comment:
        # Re-run the same classify/reply logic the poller uses, right now,
        # instead of waiting for the next scheduled scan.
        background_tasks.add_task(_trigger_immediate_comment_scan)

    return {"ok": True, "message": saw_message, "comment": saw_comment}


# ── DM health / diagnostics ──────────────────────────────────────────────────

@router.get("/dm/health")
async def dm_health():
    """Diagnostic endpoint that tells the founder exactly what is missing for
    Messenger DM replies to work.

    Returns a JSON object with:
      - configured: dict of which settings are set (not their values)
      - pages_messaging_granted: whether the token has the pages_messaging scope
      - checklist: ordered list of human-readable steps still needed
    """
    settings = get_settings()

    configured = {
        "FACEBOOK_ENABLED":               settings.facebook_enabled,
        "FACEBOOK_PAGE_ID":               bool(settings.facebook_page_id),
        "FACEBOOK_PAGE_ACCESS_TOKEN":     bool(settings.facebook_page_access_token),
        "FACEBOOK_APP_SECRET":            bool(settings.facebook_app_secret),
        "FACEBOOK_WEBHOOK_VERIFY_TOKEN":  bool(settings.facebook_webhook_verify_token),
    }

    pages_messaging_granted: bool | None = None
    if settings.facebook_enabled and settings.facebook_page_access_token:
        pages_messaging_granted = await facebook_client.check_pages_messaging_permission()

    checklist = []

    if not settings.facebook_enabled:
        checklist.append(
            "ตั้ง FACEBOOK_ENABLED=true ใน Replit Secrets"
        )
    if not settings.facebook_page_id:
        checklist.append(
            "ตั้ง FACEBOOK_PAGE_ID — ID ของ Facebook Page ของคุณ "
            "(เช่น 123456789)"
        )
    if not settings.facebook_page_access_token:
        checklist.append(
            "ตั้ง FACEBOOK_PAGE_ACCESS_TOKEN — Page Access Token จาก "
            "Meta for Developers → Your App → Facebook Login → Settings → "
            "Token Generation; ใช้ User Token ก็ได้แล้ว code จะ resolve เป็น Page Token เอง"
        )
    if not settings.facebook_app_secret:
        checklist.append(
            "ตั้ง FACEBOOK_APP_SECRET — App Secret จาก "
            "Meta for Developers → Your App → Settings → Basic"
        )
    if not settings.facebook_webhook_verify_token:
        checklist.append(
            "ตั้ง FACEBOOK_WEBHOOK_VERIFY_TOKEN — ตั้งเป็นอะไรก็ได้ เช่น 'my-verify-token-2026' "
            "แล้วใส่ค่าเดียวกันใน Meta App Dashboard → Webhooks → Verify Token"
        )

    if settings.facebook_enabled and settings.facebook_page_access_token:
        if pages_messaging_granted is False:
            checklist.append(
                "เพิ่ม pages_messaging permission ให้ Page Token: "
                "Meta App Dashboard → App Review → Permissions → ขอ pages_messaging "
                "(หรือเปิด Advanced Access ถ้า App ยัง Development Mode อยู่)"
            )
        elif pages_messaging_granted:
            checklist.append("✅ pages_messaging permission: granted")

    if settings.facebook_enabled:
        checklist.append(
            "ตั้งค่า Webhook ใน Meta App Dashboard: "
            "Webhooks → Page → Subscribe → ติ๊กทั้ง 'feed' (สำหรับ comment) "
            "และ 'messages' (สำหรับ DM/Messenger) — "
            "ถ้าติ๊กแค่ feed อยู่ DM จะไม่เข้ามาที่ server เลย"
        )

    return {
        "configured": configured,
        "pages_messaging_granted": pages_messaging_granted,
        "checklist": checklist,
        "webhook_url_hint": "POST /facebook/webhook (ต้องเป็น HTTPS public URL, Render URL ก็ใช้ได้)",
    }


# ── DM founder-review queue ──────────────────────────────────────────────────

@router.get("/dm/pending")
def pending_dm_replies(db: Session = Depends(get_db)):
    """DMs the AI wasn't confident enough to send on its own -- rendered in
    the sidebar 'Facebook' panel so the founder can edit/send or dismiss."""
    approvals = db.scalars(
        select(PendingApproval)
        .where(PendingApproval.agent_name == "facebook_dm_reply", PendingApproval.status == "pending")
        .order_by(PendingApproval.created_at.desc())
    ).all()

    return [
        {
            "id": a.id,
            "shop_name": a.lead.shop_name if a.lead else "ลูกค้า",
            "draft_message": a.draft_message,
            "reasoning": a.reasoning,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in approvals
    ]


@router.post("/dm/{approval_id}/send")
async def send_dm_reply(approval_id: int, message: str = Form(...), db: Session = Depends(get_db)):
    approval = db.get(PendingApproval, approval_id)
    if not approval or approval.status != "pending":
        raise HTTPException(status_code=404, detail="approval not found or already handled")
    if not approval.lead or not approval.lead.facebook_psid:
        raise HTTPException(status_code=400, detail="no Facebook contact linked to this approval")

    from app.facebook_dm_pipeline import append_to_history

    message = message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="message is empty")

    try:
        await facebook_client.send_dm(approval.lead.facebook_psid, message)
    except Exception as exc:  # noqa: BLE001
        logger.error("Manual DM send failed approval_id=%s: %s", approval_id, exc)
        raise HTTPException(status_code=502, detail=f"ส่งข้อความไปยัง Facebook ไม่สำเร็จ: {exc}") from exc
    append_to_history(db, approval.lead, "assistant", message)

    approval.status = "sent"
    approval.reviewed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    return {"ok": True}


@router.post("/dm/{approval_id}/dismiss")
def dismiss_dm_reply(approval_id: int, db: Session = Depends(get_db)):
    approval = db.get(PendingApproval, approval_id)
    if not approval or approval.status != "pending":
        raise HTTPException(status_code=404, detail="approval not found or already handled")

    approval.status = "dismissed"
    approval.reviewed_at = datetime.now(timezone.utc).replace(tzinfo=None)
    db.commit()
    return {"ok": True}
