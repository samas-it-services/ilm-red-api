"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "ILM Red API"
    app_version: str = "1.2.1"
    debug: bool = False
    environment: Literal["development", "staging", "production"] = "development"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Database
    database_url: PostgresDsn = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/ilmred"
    )
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_echo: bool = False

    # Redis
    redis_url: RedisDsn = Field(default="redis://localhost:6379")

    # JWT Authentication
    jwt_secret: str = Field(default="dev-secret-change-in-production")
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 7

    # API Keys
    api_key_prefix: str = "ilm_"

    # Storage
    storage_type: Literal["local", "azure", "s3"] = "local"
    local_storage_path: str = "./uploads"
    azure_storage_connection_string: str | None = None
    azure_storage_container: str = "books"

    # AI Providers (Multi-vendor support)
    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    qwen_api_key: str | None = None  # Alibaba DashScope API key
    google_api_key: str | None = None  # Google AI API key
    xai_api_key: str | None = None  # xAI/Grok API key
    deepseek_api_key: str | None = None  # DeepSeek API key

    # AI Model Defaults
    ai_default_model_public: str = "qwen-turbo"  # Cost-effective for public books
    ai_default_model_private: str = "gpt-4o-mini"  # Balanced for private books
    ai_fallback_model: str = "gpt-4o-mini"  # Fallback if primary unavailable

    # Rate Limiting (per minute)
    rate_limit_free: int = 60
    rate_limit_premium: int = 300
    rate_limit_enterprise: int = 1000

    # AI Token Limits (per day)
    token_limit_free: int = 10_000
    token_limit_premium: int = 100_000
    token_limit_enterprise: int = 10_000_000  # Effectively unlimited

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    @computed_field
    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
