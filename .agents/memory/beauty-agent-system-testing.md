---
name: Beauty Agent System testing notes
description: Quirks found while testing/extending the beauty_agent_system FastAPI app (rate limiter, FB/TikTok infra, DM pipeline reuse).
---

- Rate-limiter "sleep mode" can look like a broken prompt when testing; FB/TikTok scanning infra already exists separately from content_strategist.
- `app/chatwoot_pipeline.py`'s confidence-threshold reply pattern (generate_reply → auto-send if confident, else escalate) is written channel-agnostically
  (`CHATWOOT_REPLY_SYSTEM_PROMPT` explicitly covers "Facebook Messenger, Instagram DM, Line"). Reused verbatim for `app/facebook_dm_pipeline.py` instead of
  writing a new prompt — same threshold (0.65), same JSON shape (`reply`, `confidence`, `assign_to_human`, `suggested_stage`, `reason_for_handoff`).
- The `PendingApproval` model + `/approvals/{id}/approve|reject|edit` routes in `app/routers/office.py` are legacy/orphaned — nothing in office.html or
  app.js renders `pending_approvals` or calls those routes. Don't assume they're wired to any visible UI; check before building on them. New founder-facing
  approval queues (e.g. Facebook DM review) need their own dedicated endpoints + sidebar panel wiring, not a resurrection of that dead path.
- In this dev sandbox `FACEBOOK_ENABLED=true` is set but `FACEBOOK_PAGE_ID`/`FACEBOOK_PAGE_ACCESS_TOKEN` are not (real creds live only on the Render
  production deploy) — any live Graph API call here 400s. That's expected, not a regression; don't "fix" it by disabling the flag.
- Local dev DB is SQLite auto-created via `Base.metadata.create_all()` (no Alembic in this environment since `NEON_DATABASE_URL` is unset). That only
  creates missing tables, not new columns on existing tables — after adding a column via Alembic migration, must also delete the local
  `_unconfigured.db` file and restart so create_all rebuilds the full current schema, or the dev server crashes/mismatches on the stale schema.
