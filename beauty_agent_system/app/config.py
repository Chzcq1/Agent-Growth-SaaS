"""Central configuration, loaded from environment variables (.env in dev).

Every tunable that touches rate limiting, LLM provider, or external services
lives here so it can be changed without touching agent logic.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Database -----------------------------------------------------
    # NOTE: intentionally NOT named DATABASE_URL. This project targets an
    # external Neon Postgres instance, not the Replit-managed database, so a
    # distinct name avoids any collision with Replit's runtime-managed key.
    neon_database_url: str = ""

    # --- GitHub Models (LLM provider) ----------------------------------
    github_models_token: str = ""
    github_models_base_url: str = "https://models.github.ai/inference"
    github_models_model: str = "openai/gpt-4o-mini"

    # --- Rate limiting ---------------------------------------------------
    max_requests_per_minute: int = 10
    max_concurrent_requests: int = 2
    max_retries: int = 3
    base_backoff_seconds: float = 5.0

    # --- Follow-up scheduler ---------------------------------------------
    followup_batch_delay_seconds: float = 3.0
    followup_scan_hour_utc: int = 3  # runs once a day at this UTC hour

    # --- Research cache ---------------------------------------------------
    research_cache_ttl_days: int = 7

    # --- Chatwoot (omni-channel hub) -------------------------------------
    chatwoot_enabled: bool = False
    chatwoot_base_url: str = ""
    chatwoot_api_access_token: str = ""
    chatwoot_account_id: str = ""
    chatwoot_webhook_secret: str = ""

    # --- App ---------------------------------------------------------------
    admin_session_secret: str = "dev-only-change-me"
    environment: str = "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()
