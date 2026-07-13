# [Project name]

_Replace the heading above with the project's name, and this line with one sentence describing what this app does for users._

## Run & Operate

- `pnpm --filter @workspace/api-server run dev` — run the API server (port 5000)
- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from the OpenAPI spec
- `pnpm --filter @workspace/db run push` — push DB schema changes (dev only)
- Required env: `DATABASE_URL` — Postgres connection string

## Stack

- pnpm workspaces, Node.js 24, TypeScript 5.9
- API: Express 5
- DB: PostgreSQL + Drizzle ORM
- Validation: Zod (`zod/v4`), `drizzle-zod`
- API codegen: Orval (from OpenAPI spec)
- Build: esbuild (CJS bundle)

## Where things live

- `beauty_agent_system/` — standalone FastAPI + LangGraph multi-agent app (Beauty SaaS Growth & Support System). Not part of the pnpm workspace, not a Replit artifact. See `beauty_agent_system/README.md` for architecture, env vars, and deploy (Render + Neon).

_Populate as you build — short repo map plus pointers to the source-of-truth file for DB schema, API contracts, theme files, etc._

## Architecture decisions

- `beauty_agent_system/` is intentionally isolated from the Node/pnpm stack: it's Python/FastAPI, deployed to Render (not Replit), backed by Neon Postgres (not the Replit DB), and uses GitHub Models (not Replit AI Integrations) per explicit user choice. Its DB secret is `NEON_DATABASE_URL` and its LLM secret is `GITHUB_MODELS_TOKEN` — deliberately not named `DATABASE_URL`/`GITHUB_TOKEN` to avoid colliding with Replit-managed keys.
- Its dev workflow (`Beauty Agent System`, port 8000) runs `python run.py` directly; it is a hand-configured workflow, not an artifact-managed one.

_Populate as you build — non-obvious choices a reader couldn't infer from the code (3-5 bullets)._

## Product

_Describe the high-level user-facing capabilities of this app once they exist._

## User preferences

_Populate as you build — explicit user instructions worth remembering across sessions._

## Gotchas

- `beauty_agent_system/` has its own Python env, separate from the pnpm workspace. After a fresh import/clone (or if the `Beauty Agent System` workflow fails with `.pythonlibs/bin/python: No such file or directory`), run `uv sync` from the repo root to (re)install it, then `cd beauty_agent_system && /home/runner/workspace/.pythonlibs/bin/python -m alembic upgrade head` to apply DB migrations to `NEON_DATABASE_URL` before restarting the workflow.
- Verify the service is actually healthy (not just "port open") with `beauty_agent_system/scripts/health_check.sh` — it checks `/admin/system-health` and exercises the `/webhooks/chatwoot` intent-routing path end to end.

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details
