import logging
import secrets
from functools import lru_cache
from typing import List

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_logger = logging.getLogger("rolecraft.config")

# ── Known-weak / placeholder secrets that MUST be rejected in production ──
_WEAK_SECRETS: set[str] = {
    "change-me",
    "change-me-to-a-long-random-secret",
    "secret",
    "supersecret",
    "dev-secret-change-me",
    "your-secret-key",
    "mysecret",
    "password",
    "jwt-secret",
    "test-secret",
}

# ── Known-placeholder database URLs ──
_PLACEHOLDER_DB_URLS: set[str] = {
    "postgresql+asyncpg://postgres:postgres@localhost:5432/rolecraft",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Override via DATABASE_URL in .env — prefer Neon pooled URL (see .env.example).
    database_url: str = ""
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30  # 30 minutes
    refresh_token_expire_days: int = 14     # 14 days
    gcs_bucket_name: str = "rolecraft-uploads"
    gcs_project_id: str = ""
    groq_api_key: str = ""
    groq_model: str = "openai/gpt-oss-20b"
    groq_ats_model: str = "openai/gpt-oss-20b"
    fitment_llm_rationales: bool = True
    embedding_api_key: str = ""
    embedding_model: str = "text-embedding-3-small"
    embedding_api_base: str = "https://api.openai.com/v1"
    resume_max_fix_iterations: int = 3
    # When true, skip Groq and always use deterministic resume generation (API-key backup).
    force_deterministic_resumes: bool = False
    cors_origins: str = ""
    environment: str = "development"
    storage_backend: str = "local"  # local | gcs

    # ── Rate limiting (see core/rate_limit.py for limit values) ────────────
    rate_limit_enabled: bool = True
    # memory:// = single process only; redis://host:6379/0 for multi-worker
    rate_limit_storage_uri: str = "memory://"
    # When true, client IP is taken from X-Forwarded-For (set only behind a known proxy)
    trusted_proxy: bool = False

    # ── Messaging Policy ────────────────────────────────────────────────
    # "applicants_only": Company can only message candidates who applied to their jobs or shortlisted
    # "any_candidate_with_plan": Company can message any candidate if they have active plan (requires active subscription)
    messaging_policy: str = "applicants_only"  # applicants_only | any_candidate_with_plan

    # ── Razorpay Payment Configuration (Step 6D) ────────────────────────────
    razorpay_key_id: str = ""
    razorpay_key_secret: str = ""
    razorpay_webhook_secret: str = ""
    payments_mode: str = "disabled"  # disabled | test | live

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip(' "\'') for o in self.cors_origins.split(",") if o.strip(' "\'')]

    @property
    def is_production(self) -> bool:
        """True when the environment is anything other than explicit 'development'."""
        return self.environment.lower() != "development"

    # ── Startup validation ────────────────────────────────────────────────
    @model_validator(mode="after")
    def _validate_critical_settings(self) -> "Settings":
        errors: list[str] = []

        # ---- JWT_SECRET ----
        if self.is_production:
            if not self.jwt_secret:
                errors.append(
                    "JWT_SECRET is required in production. "
                    "Set it to a cryptographically random string (≥ 32 characters)."
                )
            elif self.jwt_secret.lower() in _WEAK_SECRETS:
                errors.append(
                    f"JWT_SECRET is a known placeholder ('{self.jwt_secret}'). "
                    "Replace it with a strong random secret (≥ 32 characters)."
                )
            elif len(self.jwt_secret) < 32:
                errors.append(
                    f"JWT_SECRET is too short ({len(self.jwt_secret)} chars). "
                    "Use at least 32 characters."
                )
        else:
            # Development mode: generate a random per-process secret if unset.
            if not self.jwt_secret or self.jwt_secret.lower() in _WEAK_SECRETS:
                self.jwt_secret = secrets.token_urlsafe(48)
                _logger.warning(
                    "DEVELOPMENT MODE: Generated a random JWT_SECRET for this process. "
                    "Tokens will NOT survive restarts. "
                    "Set JWT_SECRET in .env for persistence."
                )

        # ---- DATABASE_URL ----
        if self.is_production:
            if not self.database_url:
                errors.append(
                    "DATABASE_URL is required in production. "
                    "Point it at your Neon/Postgres pooled connection string."
                )
            elif self.database_url in _PLACEHOLDER_DB_URLS:
                errors.append(
                    "DATABASE_URL is still the local placeholder. "
                    "Set it to your production database URL."
                )
        else:
            # In development, default to localhost if not set.
            if not self.database_url:
                self.database_url = (
                    "postgresql+asyncpg://postgres:postgres@localhost:5432/rolecraft"
                )

        # ---- CORS_ORIGINS ----
        if self.is_production:
            if not self.cors_origins:
                errors.append(
                    "CORS_ORIGINS is required in production. "
                    "Set it to a comma-separated list of allowed origins."
                )
            elif "*" in self.cors_origin_list:
                errors.append(
                    "CORS_ORIGINS must not contain '*' in production."
                )
        else:
            if not self.cors_origins:
                self.cors_origins = "http://localhost:3000,http://127.0.0.1:3000"

        # ---- Fail hard ----
        if errors:
            msg = (
                "\n\n🚨 FATAL: Critical configuration errors — "
                "the application CANNOT start.\n\n"
                + "\n".join(f"  • {e}" for e in errors)
                + "\n"
            )
            raise ValueError(msg)

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
