from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Override via DATABASE_URL in .env — prefer Neon pooled URL (see .env.example).
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/rolecraft"
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7
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
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    environment: str = "development"
    storage_backend: str = "local"  # local | gcs

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
