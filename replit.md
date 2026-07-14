# CSC Virtual Office — Beauty Agent System

A single-page "virtual office" for the founder of CSC (an online booking SaaS for beauty salons). Paste raw text — Facebook comments, lead conversations, feature questions, shop feedback — and the AI team analyses it and returns one synthesized action plan in real time.

## Stack

- **Backend**: FastAPI + Python 3.11 (Uvicorn, SQLAlchemy, Alembic)
- **Database**: Neon Postgres (falls back to local SQLite when `NEON_DATABASE_URL` is not set)
- **AI**: GitHub Models API (OpenAI-compatible; gpt-4o-mini by default)
- **Frontend**: Server-rendered Jinja2 + vanilla JS (SSE streaming)

All code lives in `beauty_agent_system/`.

## Running on Replit

The **Beauty Agent System** workflow starts the server automatically. It runs:

```
cd beauty_agent_system && python3 run.py
```

The server listens on `$PORT` (default 8000).

To apply DB migrations manually:

```bash
cd beauty_agent_system
python3 -m alembic upgrade head
```

## Required Secrets

Set these in Replit Secrets (already configured):

| Secret | Purpose |
|--------|---------|
| `NEON_DATABASE_URL` | Neon Postgres connection string |
| `GITHUB_MODELS_TOKEN` | GitHub fine-grained PAT with "Models" permission |
| `FACEBOOK_APP_SECRET` | Meta App secret — verifies the `X-Hub-Signature-256` header on incoming webhook calls |

Plus one plain env var: `FACEBOOK_WEBHOOK_VERIFY_TOKEN` — an arbitrary shared string that must match the "Verify Token" entered in Meta's webhook setup screen (a value has already been generated and set here; reuse the same value in Meta's dashboard).

Without `NEON_DATABASE_URL` the app falls back to a local SQLite file and creates all tables automatically — useful for dev/testing.

## Facebook Messenger DM auto-reply + real-time webhook

The bot now replies to Messenger DMs, not just public comments, and reacts to
Facebook events in real time via a webhook instead of relying only on a
5-minute poll (which never fires while a free-tier Render dyno is asleep).

- `POST /facebook/webhook` — receives Meta's push events. New DM → AI drafts
  a reply; if confident, sends it immediately; if not, holds it for founder
  review (see below). New Page comment → immediately re-runs the same
  classify/reply job the 5-minute poller uses, instead of waiting.
- `GET /facebook/webhook` — Meta's one-time verification handshake.
- The 5-minute poller (`app/scheduler.py`) still runs as a safety net in
  case a webhook event is ever missed.
- Founder review queue: DMs the AI wasn't confident enough to send land in
  the sidebar **Facebook** panel ("รอตอบ DM") with an editable draft, a
  "ส่ง" button (sends via Messenger) and "ข้าม" (dismiss, founder replies
  manually outside the app). Logic lives in `app/facebook_dm_pipeline.py`,
  reusing the same confidence-threshold prompt as `app/chatwoot_pipeline.py`.
- **To activate in production**: in the Meta App dashboard, add a webhook
  subscription pointing to `https://<your-render-domain>/facebook/webhook`,
  enter the `FACEBOOK_WEBHOOK_VERIFY_TOKEN` value as the Verify Token, and
  subscribe the Page to the `messages` and `feed` fields. Requires the
  `pages_messaging` permission (already needed for the existing DM-on-comment
  feature).

## Architecture

```
Founder pastes text → Supervisor selects relevant agents (0–8) →
    agents run concurrently → Supervisor synthesises ONE answer:
        Key Findings + Action Plan (Founder must do / AI will do)
        + inline draft approval (when Sales Assistant produced one)
```

### The 8 specialist agents (`beauty_agent_system/app/agents/`)

| Key | File | Role |
|-----|------|------|
| `lead_hunter` | `lead_hunter.py` | Extracts pain points from Facebook/lead text |
| `sales_assistant` | `sales_assistant.py` | Drafts one Messenger opening line |
| `demo_agent` | `demo_agent.py` | Preps feature/package Q&A |
| `onboarding_agent` | `onboarding_agent.py` | Flags setup / verification issues |
| `customer_success_agent` | `customer_success_agent.py` | Churn-risk signals for live shops |
| `product_analyst_agent` | `product_analyst_agent.py` | Groups feedback into a roadmap note |
| `content_strategist` | `content_strategist_agent.py` | Step-by-step target-audience scouting + content plan on Facebook and TikTok, through to closing the sale |
| `general_assistant` | `general_assistant.py` | Fallback for anything outside the above; also handles attached images |

### Key files

- `app/agents/supervisor.py` — orchestrator: routing → dispatch → QA review → synthesis
- `app/agents/prompts.py` — all LLM prompts (edit here to change agent behaviour)
- `app/business_context.py` — CSC stage, pain points, off-limits scope (single source of truth)
- `app/routers/office.py` — HTTP routes (`/`, `/run/stream`, `/run/continue`, etc.)
- `app/static/js/app.js` — streaming UI (SSE reader, sidebar, chat thread)
- `app/rate_limiter.py` — GitHub Models rate-limit enforcement

## Deployment

The app is designed to be deployed to **Render** (see README in `beauty_agent_system/`) backed by a Neon Postgres database. Production start command:

```
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## User Preferences

- Keep the existing Python/FastAPI structure; do not migrate to Node/TypeScript.
- All prompts live in `app/agents/prompts.py` and `app/business_context.py` — edit there, not inline in agent files.
- The app intentionally has no separate Approvals/Leads/System Health pages — everything goes through the single `/` page.
