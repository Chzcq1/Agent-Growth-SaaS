"""GitHub Models client wrapper.

Every LLM call in the whole system MUST go through ``call_llm`` -- this is
what makes rate limiting enforceable. GitHub Models exposes an
OpenAI-compatible Chat Completions API, so we reuse the official OpenAI SDK
with a custom base_url + the user's GitHub token as the bearer credential.
"""
from __future__ import annotations

import asyncio
import logging

from openai import APIStatusError, AsyncOpenAI
from sqlalchemy.orm import Session

from app.config import get_settings
from app.rate_limiter import RateLimitSleeping, rate_limiter

logger = logging.getLogger("beauty_agent_system.llm")


class LLMUnavailable(Exception):
    """Raised when the LLM could not be called (sleeping, or exhausted retries)."""


def _client(settings) -> AsyncOpenAI:
    return AsyncOpenAI(api_key=settings.github_models_token, base_url=settings.github_models_base_url)


async def call_llm(
    db: Session,
    agent_name: str,
    system_prompt: str,
    user_prompt: str,
    *,
    temperature: float = 0.4,
) -> str:
    """Rate-limited, retried call to GitHub Models. Returns the assistant text.

    Raises ``LLMUnavailable`` if the bot is asleep or retries are exhausted --
    callers must treat this as "no answer available", never fabricate one.
    """
    settings = get_settings()
    if not settings.github_models_token:
        raise LLMUnavailable("GITHUB_MODELS_TOKEN is not configured")

    try:
        rate_limiter.ensure_awake(db)
    except RateLimitSleeping as exc:
        raise LLMUnavailable(f"bot is sleeping until {exc.wake_at.isoformat()}") from exc

    client = _client(settings)
    attempt = 0
    while attempt < settings.max_retries:
        attempt += 1
        try:
            await rate_limiter.acquire(db)
        except RateLimitSleeping as exc:
            raise LLMUnavailable(f"bot is sleeping until {exc.wake_at.isoformat()}") from exc

        try:
            response = await client.chat.completions.create(
                model=settings.github_models_model,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            tokens_used = getattr(response.usage, "total_tokens", None) if response.usage else None
            rate_limiter.record_success(db, agent_name, settings.github_models_model, tokens_used)
            return response.choices[0].message.content or ""
        except APIStatusError as exc:
            if exc.status_code == 429:
                retry_after = None
                header_val = exc.response.headers.get("retry-after") if exc.response else None
                if header_val:
                    try:
                        retry_after = float(header_val)
                    except ValueError:
                        retry_after = None
                wake_at = rate_limiter.record_rate_limited(
                    db, agent_name, settings.github_models_model, retry_after
                )
                logger.warning("GitHub Models 429 -- sleeping until %s", wake_at.isoformat())
                # Do not retry immediately; the caller should treat this run as
                # failed. The next scheduled/incoming request will respect sleep mode.
                raise LLMUnavailable(f"rate limited, sleeping until {wake_at.isoformat()}") from exc
            rate_limiter.record_error(db, agent_name, settings.github_models_model, str(exc))
            if attempt >= settings.max_retries:
                raise LLMUnavailable(f"GitHub Models error after {attempt} attempts: {exc}") from exc
            await asyncio.sleep(settings.base_backoff_seconds * attempt)
        except Exception as exc:  # noqa: BLE001 -- log then decide retry/raise
            rate_limiter.record_error(db, agent_name, settings.github_models_model, str(exc))
            if attempt >= settings.max_retries:
                raise LLMUnavailable(f"GitHub Models error after {attempt} attempts: {exc}") from exc
            await asyncio.sleep(settings.base_backoff_seconds * attempt)
        finally:
            rate_limiter.release()

    raise LLMUnavailable("exhausted retries without a response")
