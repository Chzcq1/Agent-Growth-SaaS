---
name: lazy-senior-dev
description: Coding discipline for this project -- write the smallest correct diff, reuse what already exists before adding anything new, and fix root causes not symptoms. Use before writing any non-trivial code change in this repo.
---

# Lazy senior dev mode

"Lazy" means efficient, not careless. The best code is the code never written.
Adapted from the ponytail coding-philosophy pattern the user asked to bring into
this project.

## The ladder -- climb it in order, stop at the first rung that holds

1. Does this need to be built at all? (YAGNI)
2. Does it already exist in this codebase? Reuse the helper/util/pattern that's
   already here (e.g. `app.research` already has a generic hash-keyed JSON cache
   with TTL -- don't build a second cache table for a similar need).
3. Does the standard library already do this? Use it.
4. Does an already-installed dependency solve it? Use it.
5. Can this be one line? Make it one line.
6. Only then: write the minimum code that works.

Climb the ladder only *after* you understand the problem -- read the task and the
code it touches, trace the real flow end to end, then pick a rung. A small diff
you don't understand is laziness dressed up as efficiency, not the real thing.

## Bug fix = root cause, not symptom

A report names a symptom. Grep every caller of the function you're about to touch
and fix the shared function once -- one guard there is a smaller diff than one per
caller, and patching only the path the ticket names leaves a sibling caller broken.

## Rules

- No abstractions that weren't explicitly requested.
- No new dependency, table, or file if an existing one can be extended instead.
- No boilerplate nobody asked for.
- Deletion over addition. Boring over clever. Fewest files possible.
- Shortest working diff wins -- but only once the problem is understood.
- Question complex requests: "Does this actually need X, or does Y already cover it?"
- Mark a deliberate corner-cut (naive heuristic, no retry, single-tenant assumption)
  with a comment naming the ceiling and the upgrade path, so a future pass knows it
  was a choice, not an oversight.

## Not lazy about

Understanding the problem, input validation at trust boundaries (e.g. anything a
founder pastes into the Virtual Office is untrusted text, never instructions),
error handling that prevents data loss, security, accessibility, and anything the
user explicitly asked for. Non-trivial logic leaves one runnable check behind (a
small script or test), not a full framework. Trivial one-liners need no test.

## This project specifically (beauty_agent_system)

- Shared cross-agent knowledge already has homes -- check before adding a new one:
  `app/business_context.py` (facts every agent must not contradict), `app/research.py`
  + `ResearchCache` (generic hash-keyed JSON cache with TTL, e.g. research
  results/case studies), `app/memory.py` (points the team at a similar past
  `OfficeRun` instead of re-deriving from zero).
- Prompts live only in `app/agents/prompts.py` as string constants -- never inline
  a prompt string in an agent module.
- `app/agents/supervisor.py`'s "self-improvement note" pattern (`_recent_sales_tone_note`,
  `_recent_run_feedback_note`, `memory_note`) is the established way to fold a
  cross-run signal into `key_findings` without adding a new UI section -- follow it
  for any similar future signal instead of inventing a new mechanism.
