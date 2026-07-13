# CSC Virtual Office

A private single-page tool for the CSC founder: paste a Facebook comment, lead conversation, feature question, or any raw note — six AI specialist agents analyse it concurrently and return one synthesised answer (key findings + action plan + any draft messages awaiting approval).

## Run & Operate

### Required secrets (add via Replit Secrets before starting)
- `NEON_DATABASE_URL` — Neon Postgres connection string (`postgresql://user:pass@ep-xxx.neon.tech/dbname?sslmode=require`). Create a free project at [neon.tech](https://neon.tech).
- `GITHUB_MODELS_TOKEN` — GitHub fine-grained PAT with the "Models" permission. Create at [github.com/settings/tokens](https://github.com/settings/tokens).

### Starting the app
1. Add both secrets above via Replit Secrets.
2. Apply DB migrations (first time, or after schema changes):
   ```bash
   cd beauty_agent_system && /home/runner/workspace/.pythonlibs/bin/python -m alembic upgrade head
   ```
3. Start via the **Beauty Agent System** workflow in the UI, or:
   ```bash
   cd beauty_agent_system && PORT=8000 /home/runner/workspace/.pythonlibs/bin/python run.py
   ```

### Other commands
- `cd beauty_agent_system && pytest tests/test_rate_limiter.py -v` — run rate-limiter unit tests

## Stack

- **Beauty Agent System** (`beauty_agent_system/`): Python, FastAPI, LangGraph, SQLAlchemy + Alembic, Neon Postgres, GitHub Models (GPT-4o-mini)
- pnpm workspaces, Node.js 24, TypeScript 5.9 (scaffolding only — no Node app built yet)

## Where things live

- `beauty_agent_system/` — standalone FastAPI + LangGraph multi-agent app. Not part of the pnpm workspace. See `beauty_agent_system/README.md` for full architecture details.
- `beauty_agent_system/app/agents/` — the six specialist agents (Lead Hunter, Sales Assistant, Demo Agent, Onboarding, Customer Success, Product Analyst)
- `beauty_agent_system/app/agents/supervisor.py` — routes input, runs agents concurrently, merges results
- `beauty_agent_system/app/business_context.py` — single source of truth for CSC's stage, priorities, and off-limits scope
- `beauty_agent_system/app/agents/prompts.py` — all LLM prompt constants

## Architecture decisions

- `beauty_agent_system/` is intentionally isolated from the Node/pnpm stack: it's Python/FastAPI, deployed to Render (not Replit), backed by Neon Postgres (not the Replit DB), and uses GitHub Models per explicit design. Its secrets are `NEON_DATABASE_URL` and `GITHUB_MODELS_TOKEN` — deliberately not named `DATABASE_URL`/`GITHUB_TOKEN` to avoid colliding with Replit-managed keys.
- Agent synthesis is deterministic Python merging (no LLM "synthesis" call) so combined answers can't drift.
- Keyword-heuristic routing first, LLM classification only as fallback — protects GitHub Models rate limits.

## Gotchas

- The `Beauty Agent System` workflow will fail until both `NEON_DATABASE_URL` and `GITHUB_MODELS_TOKEN` secrets are set.
- After adding secrets, run `alembic upgrade head` (step 2 above) before starting — the app expects all tables to exist.
- If the workflow fails with `.pythonlibs/bin/python: No such file or directory` after a fresh clone, run `uv sync` from the repo root to reinstall the Python env (this is expected right after an import/clone — `.pythonlibs` is gitignored and not checked in).

## Setup status (last verified 2026-07-13)

- Ran `uv sync` from the repo root to (re)create `.pythonlibs` after the import — required every time the project is freshly cloned since the venv isn't committed.
- Re-collected `NEON_DATABASE_URL` and `GITHUB_MODELS_TOKEN` via Replit Secrets (they don't carry over on re-import) and confirmed both are set.
- Ran `cd beauty_agent_system && /home/runner/workspace/.pythonlibs/bin/python -m alembic upgrade head` — schema is current.
- Restarted the `Beauty Agent System` workflow; verified `GET /` returns 200.
- Two unrelated scaffold artifacts (`artifacts/api-server`, `artifacts/mockup-sandbox`) exist in this repo but were not created for this project and are not part of the Beauty Agent System — they have no installed dependencies and are out of scope for this app.

## User preferences

_Populate as you build — explicit user instructions worth remembering across sessions._
