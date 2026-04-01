"""Helix platform configuration loaded from environment variables."""

from enum import StrEnum
from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings


class Environment(StrEnum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """All configuration for the Helix platform.

    Loaded from environment variables. See docs/architecture.md for full reference.
    """

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    # Core
    environment: Environment = Environment.DEVELOPMENT
    secret_key: str = Field(default="change-me-in-production", min_length=16)
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/helix"
    )
    redis_url: str = Field(default="redis://localhost:6379/0")
    debug: bool = False

    # LLM providers
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    azure_openai_endpoint: str | None = None
    azure_openai_api_key: str | None = None
    default_embedding_model: str = "text-embedding-3-large"

    # LLM gateway defaults
    default_primary_model: str = "claude-sonnet-4-6"
    default_fallback_model: str = "claude-haiku-4-5"
    compaction_threshold_pct: float = 83.5
    micro_compaction_threshold_bytes: int = 8192
    circuit_breaker_failure_threshold: int = 3

    # Identity (WorkOS)
    workos_api_key: str = ""
    workos_client_id: str = ""
    workos_webhook_secret: str = ""
    jwt_algorithm: str = "RS256"
    jwt_public_key_path: str | None = None

    # Integrations
    composio_api_key: str = ""
    nango_secret_key: str = ""
    nango_public_key: str = ""

    # Secrets management
    vault_addr: str | None = None
    vault_role_id: str | None = None
    vault_secret_id: str | None = None

    # Storage (S3 / MinIO)
    s3_bucket_sessions: str = "helix-sessions"
    s3_bucket_artifacts: str = "helix-artifacts"
    s3_endpoint_url: str | None = None
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_region: str = "us-east-1"

    # Memory / Dream Cycle
    dream_cycle_enabled: bool = True
    dream_default_min_hours: int = 24
    dream_default_min_sessions: int = 5
    dream_pii_strip_enabled: bool = True

    # Speculation
    speculation_enabled: bool = True
    speculation_default_depth: int = 2

    # CORS
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # CORS
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Observability
    log_level: str = "INFO"
    sentry_dsn: str | None = None
    otel_exporter_otlp_endpoint: str | None = None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings singleton — parsed once, reused everywhere."""
    return Settings()
