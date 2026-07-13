---
name: Multi-agent synthesis without an LLM merge step
description: How beauty_agent_system's Virtual Office combines several worker-agent outputs into one founder-facing answer.
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
