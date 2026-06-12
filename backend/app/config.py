"""Central application configuration, loaded from environment variables."""
from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Core ---
    PROJECT_NAME: str = "SUBRECO"
    API_V1_PREFIX: str = "/api"
    ENVIRONMENT: str = "development"
    SECRET_KEY: str = "change-me-in-production-use-openssl-rand-hex-32"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    ALGORITHM: str = "HS256"

    # --- Database ---
    POSTGRES_USER: str = "subreco"
    POSTGRES_PASSWORD: str = "subreco"
    POSTGRES_DB: str = "subreco"
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432

    # --- Redis / Celery ---
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    CELERY_BROKER_URL: str = ""
    CELERY_RESULT_BACKEND: str = ""

    # --- CORS ---
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost"]

    # --- External API keys (optional; passive sources still work without them) ---
    SECURITYTRAILS_API_KEY: str = ""
    CHAOS_API_KEY: str = ""
    OTX_API_KEY: str = ""

    # --- Notification channels (optional) ---
    DISCORD_WEBHOOK_URL: str = ""
    SLACK_WEBHOOK_URL: str = ""
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "subreco@localhost"
    SMTP_TO: str = ""

    # --- Recon tuning ---
    RECON_HTTP_TIMEOUT: int = 15
    RECON_MAX_CONCURRENCY: int = 50
    RECON_TOOL_TIMEOUT: int = 600  # per-tool subprocess timeout (seconds)
    SCREENSHOT_DIR: str = "/data/screenshots"

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def _split_origins(cls, v):
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def broker_url(self) -> str:
        return self.CELERY_BROKER_URL or f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/0"

    @property
    def result_backend(self) -> str:
        return self.CELERY_RESULT_BACKEND or f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/1"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
