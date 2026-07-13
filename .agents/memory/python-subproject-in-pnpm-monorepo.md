---
name: Python subproject inside a pnpm monorepo
description: How to add a standalone Python/FastAPI app when the repo is otherwise a Node/TS pnpm workspace and the user wants it isolated (different deploy target, different DB, different LLM provider).
---

When a user explicitly wants a Python service kept separate from the repo's
native Node/pnpm stack (different deploy target like Render, different DB
like Neon instead of the Replit-managed DB, different LLM provider like
GitHub Models instead of Replit AI Integrations):

- Put it in its own top-level directory (e.g. `beauty_agent_system/`), not
  under `artifacts/` and not listed in `pnpm-workspace.yaml` packages. It is
  not a Replit "artifact" (no Python artifact kind exists) and is not meant
  to be deployed via Replit.
- Installing a Python toolchain via the language installer runs `uv init` at
  the *workspace root*, creating a root-level `pyproject.toml` / `uv.lock` /
  `.pythonlibs/` virtualenv shared across the repo — this is separate from
  the app subdirectory's own `requirements.txt` (kept for portability to the
  external deploy target, e.g. Render's `pip install -r requirements.txt`).
- Give it its own hand-configured Replit workflow (`configureWorkflow`) to
  run the dev server locally — it has no `artifact.toml`, so it isn't
  eligible for `WorkflowsRestart` on an artifact-managed name.
- Name secrets to avoid colliding with Replit-managed keys the platform
  already reserves, e.g. `NEON_DATABASE_URL` instead of `DATABASE_URL`,
  `GITHUB_MODELS_TOKEN` instead of `GITHUB_TOKEN`.

**Why:** the project's actual product is a Node/TS pnpm workspace with
Replit-managed artifacts and DB; mixing an unrelated Python service into that
structure would break workspace tooling assumptions and Replit's deploy
story for a stack the user deliberately chose to host elsewhere.

**How to apply:** whenever a request calls for a language/stack that
conflicts with the repo's existing workspace tooling AND the user confirms
they want it isolated (different deploy target/DB/provider), scaffold it as
a sibling top-level directory with its own lockfile/venv, its own
requirements file for the external host, and its own manually configured
workflow -- do not try to fold it into the existing workspace.
