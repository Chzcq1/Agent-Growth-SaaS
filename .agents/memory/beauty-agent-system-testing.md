---
name: Beauty Agent System (CSC Virtual Office) testing notes
description: How to test beauty_agent_system's /run/stream endpoint without being misled by the rate limiter's sleep mode; where Facebook/TikTok scouting already lives.
---

## Rate limiter sleep mode looks like a bug but isn't
`app/rate_limiter.py` puts the whole app into a "sleep" mode after hitting GitHub Models
quota limits. While asleep, every agent call returns `missing_info: ["AI ไม่พร้อมใช้งาน:
bot is sleeping until <timestamp>"]` instead of calling the LLM at all — this happens even for
a single well-formed test request if a previous session already used up the quota.

**Why:** protects the shared GitHub Models rate limit from being exhausted by retries/dev testing.

**How to apply:** if a `/run/stream` (or `/run`) response comes back with empty `content_plan`/
`founder_actions` and a `missing_info` entry mentioning "sleeping", that's the rate limiter, not
a broken prompt or routing bug. Check `select_relevant_agents` / `plan_trace.assignments` in the
same response first — if the right agents were selected, the routing/keyword logic is fine and
you don't need to wait out the sleep timer to confirm that part.

## Facebook/TikTok scouting already has real scanning infra
`app/scheduler.py` already runs `_scan_facebook_comments` and `_scan_tiktok_comments` jobs
(gated by `settings.facebook_enabled` / `settings.tiktok_enabled`, no-op otherwise), backed by
`app/facebook_pipeline.py` and `app/tiktok_pipeline.py`. The `content_strategist` agent
(`app/agents/content_strategist_agent.py` + prompts in `app/agents/prompts.py`) is the strategy/
copy layer on top — it plans which hashtags/groups to target and what to post, it doesn't do the
actual polling itself.
