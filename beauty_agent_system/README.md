# Beauty SaaS Growth & Support System

A private multi-agent "virtual office" for one founder: it researches leads,
drafts and queues outbound sales/follow-up messages for approval, answers
support questions strictly from a knowledge base, and stays inside GitHub
Models' rate limits automatically.

This is a standalone FastAPI service. It lives in this directory
(`beauty_agent_system/`) and does not use the Node/TypeScript tooling in the
rest of this repo -- it is meant to be deployed to **Render**, backed by a
**Neon** Postgres database, exactly as specified.

## Architecture

```
Chatwoot webhook -> Supervisor (classify) -> worker agent -> Supervisor (validate) ->
    -> KB-answered support question -> auto-sent via Chatwoot
    -> everything else (sales/follow-up, unclear cases) -> pending_approvals (Founder reviews)
```

- **Agent 1 -- Lead Scraper & Analyst** (`app/agents/lead_scraper.py`): fetches
  a lead's public Facebook page text before ever calling the LLM. If nothing
  usable was fetched, the lead is marked `insufficient_data` and the LLM is
  never called for that lead.
- **Agent 2 -- Strategic Closer** (`app/agents/strategic_closer.py`): drafts
  Day 1 / Day 4 / Day 7 / Ghosted follow-ups per the required table. Every
  draft goes to `pending_approvals` -- this agent never sends anything itself.
- **Agent 3 -- Support & Interactive Guide** (`app/agents/support_agent.py`):
  answers only from `kb_articles` (RAG-only). No match -> opens a
  `support_tickets` row instead of guessing.
- **Agent 4 -- Supervisor** (`app/agents/supervisor.py`): the only router and
  the only validator. Workers never talk to each other; there are no cycles
  in the graph (`app/agents/graph.py`), so there is no infinite-loop failure
  mode.

All prompts are constants in `app/agents/prompts.py` -- editable without
touching any logic.

## Rate limiting (`app/rate_limiter.py`)

Every LLM call goes through `app/llm_client.py`, which enforces, in order:

1. **Sleep-mode check** -- if the bot is asleep (see below), the call is
   refused immediately, no network request is made.
2. **Concurrency cap** -- `asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)`.
3. **Sliding window** -- no more than `MAX_REQUESTS_PER_MINUTE` requests in
   any rolling 60s window.
4. On a `429` from GitHub Models: reads `Retry-After` (falls back to
   exponential backoff), persists a `wake_at` timestamp in `system_state`,
   and logs `status=rate_limited` to `api_usage_log`. No immediate retry.
   Every route into the system respects this sleep state, including the
   daily follow-up scheduler.

Unit tests: `beauty_agent_system/tests/test_rate_limiter.py`.

## Research-first (`app/research.py`)

No agent may cite a stat, quote, or case study that wasn't actually fetched.
`research_lead()` fetches a lead's own Facebook page URL and caches the
result (with source + timestamp) in `research_cache`; on failure it returns
`insufficient_data` and the caller must not fabricate a substitute. Agent 2's
Day-4 case-study mention only fires if `get_verified_case_study()` finds a
row explicitly marked `verified=True` -- there is no path for an unverified
case study to reach a customer message.

**Wiring in a real search API:** the default provider only fetches a lead's
own page. To add real web search (e.g. for market research beyond the lead's
own page), implement a new function in `app/research.py` that calls your
search API of choice, cache its result the same way, and mark it
`verified=True` only when you're confident in the source.

## Self-improvement (`app/scheduler.py`, Weekly Insights page)

Every Monday, `run_weekly_insights()` aggregates the last 7 days of
`agent_feedback` into a plain-language summary + one recommendation, written
to `weekly_insights`. Per the spec, **nothing is ever auto-applied** -- the
Founder reviews the recommendation on the dashboard and clicks "Mark as
applied" by hand, which only records that they saw it; changing an actual
prompt still means editing `app/agents/prompts.py` yourself.

## Admin Dashboard

Server-rendered (Jinja2) at `/admin/*`, responsive for phone and desktop:

- `/admin/approvals` -- Pending Approvals queue (Approve / Edit+Send / Reject, shows AI reasoning)
- `/admin/leads` -- Leads Overview with status filter
- `/admin/system-health` -- Active/Sleeping status, today's request/error/rate-limit counts
- `/admin/insights` -- Weekly Insights
- `/admin/knowledge-base` -- Knowledge Base Manager + open support tickets

## Environment variables

Copy `.env.example` to `.env` for local runs outside Replit. Inside this
Replit project, the two secrets below are managed as Replit Secrets instead
(ask the agent to change them, never edit them here):

- `NEON_DATABASE_URL` -- your Neon Postgres connection string
- `GITHUB_MODELS_TOKEN` -- a GitHub token with the "Models" permission

Chatwoot is **stubbed** until you have an account (`CHATWOOT_ENABLED=false`).
While stubbed, outbound sends are logged and appended to
`leads.conversation_history` instead of calling the real API, so the whole
approve -> send flow is testable end-to-end today. Flip
`CHATWOOT_ENABLED=true` and fill in the four `CHATWOOT_*` values once you
have a Chatwoot account -- no code changes needed.

## Running locally in Replit (for development/testing)

```bash
cd beauty_agent_system
alembic upgrade head          # creates all tables in Neon
python run.py                 # starts the API on $PORT (defaults to 8000)
```

Send a test webhook:

```bash
curl -X POST localhost:8000/webhooks/chatwoot \
  -H "Content-Type: application/json" \
  -d '{"content": "ราคาเท่าไหร่คะ", "sender": {"name": "ร้านเล็บทดสอบ"}, "conversation": {"id": "1"}}'
```

Run the rate limiter unit tests:

```bash
cd beauty_agent_system
pytest tests/test_rate_limiter.py -v
```

## Deploying to Render + Neon DB

1. **Neon**: create a project at neon.tech, copy its connection string into
   `NEON_DATABASE_URL`.
2. **GitHub Models token**: create a fine-grained GitHub PAT with the
   "Models" permission at github.com/settings/tokens, put it in
   `GITHUB_MODELS_TOKEN`.
3. **Render**: create a new Web Service pointing at this repo.
   - Root directory: `beauty_agent_system`
   - Build command: `pip install -r requirements.txt`
   - Start command: `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - Add all variables from `.env.example` under Render's Environment tab
     (set `CHATWOOT_ENABLED=true` once you have a Chatwoot account).
4. **Chatwoot**: point your Chatwoot inbox's webhook URL at
   `https://<your-render-service>.onrender.com/webhooks/chatwoot`, and set
   `CHATWOOT_WEBHOOK_SECRET` to match Chatwoot's webhook signing secret.
5. Render's free/starter tiers spin down when idle, which will pause the
   scheduler (daily follow-ups, weekly insights) until the next request wakes
   the service -- use a paid always-on instance if follow-up timing needs to
   be exact.

A `requirements.txt` is included alongside this README for Render's build
step; if you add a dependency locally, regenerate it with
`pip freeze > requirements.txt` from inside an activated virtualenv for this
project (or ask the agent to do it).
