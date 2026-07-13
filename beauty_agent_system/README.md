# CSC Virtual Office

A private single-page "virtual office" for one founder running CSC, an
online booking SaaS for beauty salons (early PMF, 3 paying shops). The
founder pastes ONE blob of raw information -- a Facebook comment, a lead
conversation, a feature question, a note about an existing shop, feedback
-- and gets back ONE synthesized answer: what was found, what the founder
must do himself, and what the AI will keep doing on its own. It stays
inside GitHub Models' rate limits automatically.

This is a standalone FastAPI service. It lives in this directory
(`beauty_agent_system/`) and does not use the Node/TypeScript tooling in the
rest of this repo -- it is meant to be deployed to **Render**, backed by a
**Neon** Postgres database.

## Architecture

```
Founder pastes raw text -> Supervisor selects relevant agents (0-6) ->
    selected agents run concurrently -> Supervisor synthesizes ONE answer:
        Key Findings + Action Plan (Founder must do / AI will do) +
        inline draft approval (if Sales Assistant produced one)
```

There is no more multi-page admin dashboard (no separate Approvals / Leads /
System Health / Weekly Insights / Knowledge Base pages) -- everything
happens on the single page at `/`.

### The 6 specialist agents (`app/agents/`)

- **Lead Hunter** (`lead_hunter.py`) -- extracts pain points from pasted
  Facebook group/comment/lead-conversation text, matched against CSC's
  ranked pain-point list in `app/business_context.py`.
- **Sales Assistant** (`sales_assistant.py`) -- drafts ONE Messenger opening
  line for an interested lead, anchored on their pain point. Never pitches
  price on day one. Every draft always goes to `pending_approvals` -- this
  agent never sends anything itself.
- **Demo Agent** (`demo_agent.py`) -- preps the founder to answer feature/
  package questions from a prospect, selling CSC's strengths (self-booking,
  deposits, less chat load, 24h booking) rather than a feature laundry list.
- **Onboarding Agent** (`onboarding_agent.py`) -- flags where a new shop got
  stuck during setup/verification/first use, from whatever signal the
  founder pasted.
- **Customer Success Agent** (`customer_success_agent.py`) -- flags shops
  that are live but not actually booking, or show churn-risk signals.
- **Product Analyst Agent** (`product_analyst_agent.py`) -- groups feedback
  into a short roadmap note, but only within Booking/Deposit/Schedule/
  Customer Flow scope; explicitly refuses anything drifting into
  POS/Stock/ERP/HR/big CRM territory (see `app/business_context.py`).

### Supervisor (`app/agents/supervisor.py`)

The single entry point and the only router. Routing is a cheap keyword
heuristic per agent first (protects the LLM quota); only when nothing
matches does it fall back to one LLM classification call. Selected agents
run concurrently (`asyncio.gather`), then the Supervisor merges their
`key_findings` / `founder_actions` / `ai_actions` / `missing_info` into one
answer -- no LLM "synthesis" call, just deterministic merging, so the
combined answer can't drift or reformat inconsistently.

All prompts are constants in `app/agents/prompts.py`, all built on top of
the shared `BUSINESS_CONTEXT` string in `app/business_context.py` -- edit
that one file to change CSC's stage/priorities/off-limits list and every
agent picks it up.

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

Unit tests: `beauty_agent_system/tests/test_rate_limiter.py`.

## Research-first (`app/research.py`)

No agent may cite a stat, quote, or case study that wasn't actually
verified. Sales Assistant only cites a case study via
`get_verified_case_study()`, which only ever returns a row explicitly
marked `verified=True` in `research_cache` -- there is no path for an
unverified case study to reach a customer message.

## Self-improvement

Folded directly into the next synthesized answer instead of a separate
"Weekly Insights" page: `supervisor._recent_sales_tone_note()` checks the
last 7 days of `agent_feedback` tied to Sales Assistant drafts, and if the
rejection rate is high, adds a Key Finding suggesting a tone change on the
very next submission -- no separate page, no scheduled job required.

## The single page (`/`, `app/routers/office.py`)

- A textarea to paste raw text + "ส่งให้ Virtual Office วิเคราะห์".
- The latest synthesized result (Key Findings / Action Plan / missing info),
  persisted in `office_runs` so a page reload doesn't lose it.
- "ข้อความร่างที่รอตรวจ" -- any pending Sales Assistant draft, with inline
  Approve / Edit+use / Reject buttons (writes to `pending_approvals` +
  `agent_feedback`, same tables the self-improvement note reads from).

## Environment variables

Copy `.env.example` to `.env` for local runs outside Replit. Inside this
Replit project, the two secrets below are managed as Replit Secrets instead
(ask the agent to change them, never edit them here):

- `NEON_DATABASE_URL` -- your Neon Postgres connection string
- `GITHUB_MODELS_TOKEN` -- a GitHub token with the "Models" permission

## Running locally in Replit (for development/testing)

```bash
cd beauty_agent_system
alembic upgrade head          # creates/updates all tables in Neon
python run.py                 # starts the API on $PORT (defaults to 8000)
```

Try it:

```bash
curl -X POST localhost:8000/run --data-urlencode \
  "raw_text=มีคนคอมเมนต์ในกลุ่ม Facebook ร้านทำเล็บว่าเทลูกค้าประจำเพราะตอบแชทไม่ทัน ทักมาถามราคาแพ็กเกจด้วย"
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
   - Add `NEON_DATABASE_URL` and `GITHUB_MODELS_TOKEN` under Render's
     Environment tab.

A `requirements.txt` is included alongside this README for Render's build
step; if you add a dependency locally, regenerate it with
`pip freeze > requirements.txt` from inside an activated virtualenv for this
project (or ask the agent to do it).
