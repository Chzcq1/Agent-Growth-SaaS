---
name: Multi-agent synthesis without an LLM merge step
description: How beauty_agent_system's Virtual Office combines several worker-agent outputs into one founder-facing answer, plus its bounded review/rework loop.
---

When a Supervisor needs to combine N worker-agent outputs into one
synthesized response (e.g. "Key Findings" + "Action Plan" sections), prefer
having each worker agent return a small fixed-shape JSON (key_findings,
founder_actions, ai_actions, missing_info) and merge those lists in plain
Python, rather than making one more LLM call to "write the combined
summary."

**Why:** an LLM synthesis step adds cost/latency/rate-limit pressure and
risks inconsistent formatting or dropped items across runs. Deterministic
list-concatenation is trivially correct and traceable back to which agent
said what (prefix each finding with `[Agent Label]`).

**How to apply:** give every worker agent the same strict JSON output
contract in its system prompt, validate/parse defensively (strip ``` json
fences), and do the merge in the Supervisor with plain dict/list ops. Same
philosophy for routing: try cheap keyword heuristics per agent first, and
only fall back to one LLM classification call when heuristics find nothing
-- keeps quota usage low on a system with strict per-minute LLM limits.

## Making coordination visible + one bounded review/rework round

A founder explicitly complained that parallel keyword-routed agents felt
like they "didn't talk to each other" -- just dumped independent, often
duplicate restatements with no visible plan or self-check. Fixed by adding
two more stages around the same deterministic-merge core:

1. **Plan trace** -- before running agents, build and show a short shared
   goal statement + a one-line task assignment per selected agent. Purely
   templated from a static per-agent description dict; no extra LLM call.
2. **Review/rework** -- exactly ONE extra LLM call after the first-round
   merge: ask a Supervisor "QA" prompt whether the combined draft is
   complete/non-redundant/actionable against the original input, returning
   `{sufficient, rework: [{agent, feedback}], note}`. If any agent is
   flagged, re-run only those agents once with the feedback appended to
   their user prompt, re-merge, done -- never loop further.

**Why:** this gives the "we have a goal, here's who's doing what, here's
what QA found and sent back for rework" experience the founder wanted,
without an unbounded critique loop that would blow through the LLM rate
limit or hang the request. A broken/unavailable review call must fail open
(treat as "sufficient", show the first-round draft) rather than block the
founder from seeing anything.

Near-duplicate findings across agents (same fact restated with different
wording) are also worth deduping with a cheap `difflib.SequenceMatcher`
ratio threshold (~0.7) on the text after the `[Agent Label] ` prefix --
catches verbatim/near-verbatim repeats, but is not true semantic dedup, so
some paraphrased overlap across agents will still get through.

## Feeding real founder feedback back into future runs

The founder wants the system to "grow" from real accepted/rejected outcomes
instead of resetting every time. Pattern used: store outcome ("accepted"/
"rejected") + an optional free-text note directly on the run record itself
(not a separate table), then at synthesis time query the last 7 days of
outcomes and, if rejections are the majority of a large-enough sample,
append one more `[Supervisor] ...` line to key_findings summarizing the
rejection rate plus the founder's own notes verbatim (not re-summarized by
an LLM -- the founder's literal wording carries the real "why").

**Why:** folding the lesson into the next round's Key Findings (rather than
a separate "Weekly Insights" page or a fine-tune/RAG pipeline) means every
future run's own LLM calls see the recent feedback as ordinary context with
no new infra, and it's exactly the same trick already used for the
narrower Sales-Assistant-draft-approval feedback loop -- keeping both
consistent matters more than inventing a fancier mechanism.

**How to apply:** when adding a new feedback surface to this app, prefer
adding outcome/note columns to the existing per-interaction record over a
new join table, and prefer folding a "recent pattern" note into
key_findings over building a separate learning/analytics page.
