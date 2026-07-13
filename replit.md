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

Without `NEON_DATABASE_URL` the app falls back to a local SQLite file and creates all tables automatically — useful for dev/testing.

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
| `content_strategist` | `content_strategist_agent.py` | Step-by-step Facebook content plan |
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
