"""Application configuration.

All runtime configuration is loaded from environment variables (and, in local
development, a ``.env`` file) and validated once at startup. Importing
``settings`` anywhere in the app yields the same validated singleton.
"""

from __future__ import annotations

from enum import Enum
from functools import lru_cache

from pydantic import AliasChoices, Field, computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_PLACEHOLDER_SECRET = "change-me-in-production-use-a-64-byte-random-value"


class Environment(str, Enum):
    """Supported runtime environments."""

    DEVELOPMENT = "development"
    TESTING = "testing"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Validated application settings sourced from the environment."""

    model_config = SettingsConfigDict(
        env_file=(".env", "../../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Runtime ---
    environment: Environment = Field(
        default=Environment.DEVELOPMENT,
        validation_alias=AliasChoices("DCIP_ENV", "ENVIRONMENT"),
    )
    app_name: str = Field(default="D-CIP", validation_alias="APP_NAME")
    app_version: str = Field(default="0.1.0", validation_alias="APP_VERSION")
    debug: bool = Field(default=False, validation_alias="DEBUG")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    log_format: str = Field(default="console", validation_alias="LOG_FORMAT")
    git_commit: str | None = Field(default=None, validation_alias="GIT_COMMIT")

    # --- API server ---
    api_host: str = Field(default="0.0.0.0", validation_alias="API_HOST")
    api_port: int = Field(default=8000, validation_alias="API_PORT")
    api_prefix: str = Field(default="/api", validation_alias="API_PREFIX")
    api_v1_prefix: str = Field(default="/api/v1", validation_alias="API_V1_PREFIX")

    # --- Security ---
    secret_key: str = Field(default=_PLACEHOLDER_SECRET, validation_alias="SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", validation_alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(
        default=15, validation_alias="ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    refresh_token_expire_minutes: int = Field(
        default=10080, validation_alias="REFRESH_TOKEN_EXPIRE_MINUTES"
    )
    auth_cookie_secure: bool = Field(default=False, validation_alias="AUTH_COOKIE_SECURE")
    auth_cookie_domain: str = Field(default="localhost", validation_alias="AUTH_COOKIE_DOMAIN")
    auth_cookie_samesite: str = Field(default="lax", validation_alias="AUTH_COOKIE_SAMESITE")

    # --- CORS ---
    cors_origins: str = Field(
        default="http://localhost:5173,http://localhost:3000",
        validation_alias="CORS_ORIGINS",
    )
    cors_allow_credentials: bool = Field(default=True, validation_alias="CORS_ALLOW_CREDENTIALS")

    # --- Rate limiting ---
    rate_limit_enabled: bool = Field(default=True, validation_alias="RATE_LIMIT_ENABLED")
    rate_limit_default: str = Field(default="120/minute", validation_alias="RATE_LIMIT_DEFAULT")
    # Storage for the limiter. Defaults to in-memory so the API and tests run
    # without Redis; point this at the Redis URL for multi-process deployments.
    rate_limit_storage_uri: str = Field(
        default="memory://", validation_alias="RATE_LIMIT_STORAGE_URI"
    )

    # --- PostgreSQL ---
    postgres_host: str = Field(default="localhost", validation_alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, validation_alias="POSTGRES_PORT")
    postgres_user: str = Field(default="dcip", validation_alias="POSTGRES_USER")
    postgres_password: str = Field(default="dcip", validation_alias="POSTGRES_PASSWORD")
    postgres_db: str = Field(default="dcip", validation_alias="POSTGRES_DB")
    database_url_override: str | None = Field(default=None, validation_alias="DATABASE_URL")
    db_pool_size: int = Field(default=10, validation_alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=20, validation_alias="DB_MAX_OVERFLOW")
    db_echo: bool = Field(default=False, validation_alias="DB_ECHO")

    # --- Neo4j ---
    neo4j_uri: str = Field(default="bolt://localhost:7687", validation_alias="NEO4J_URI")
    neo4j_user: str = Field(default="neo4j", validation_alias="NEO4J_USER")
    neo4j_password: str = Field(default="neo4j", validation_alias="NEO4J_PASSWORD")
    neo4j_database: str = Field(default="neo4j", validation_alias="NEO4J_DATABASE")

    # --- Redis ---
    redis_host: str = Field(default="localhost", validation_alias="REDIS_HOST")
    redis_port: int = Field(default=6379, validation_alias="REDIS_PORT")
    redis_db: int = Field(default=0, validation_alias="REDIS_DB")
    redis_password: str | None = Field(default=None, validation_alias="REDIS_PASSWORD")
    redis_url_override: str | None = Field(default=None, validation_alias="REDIS_URL")

    # --- OpenSearch ---
    opensearch_host: str = Field(default="localhost", validation_alias="OPENSEARCH_HOST")
    opensearch_port: int = Field(default=9200, validation_alias="OPENSEARCH_PORT")
    opensearch_user: str = Field(default="admin", validation_alias="OPENSEARCH_USER")
    opensearch_password: str = Field(default="admin", validation_alias="OPENSEARCH_PASSWORD")
    opensearch_use_ssl: bool = Field(default=False, validation_alias="OPENSEARCH_USE_SSL")
    opensearch_verify_certs: bool = Field(
        default=False, validation_alias="OPENSEARCH_VERIFY_CERTS"
    )

    # --- Uploads / Evidence ---
    upload_dir: str = Field(default="uploads", validation_alias="UPLOAD_DIR")
    max_evidence_size_mb: int = Field(
        default=500, validation_alias="MAX_EVIDENCE_SIZE_MB"
    )

    # --- AI Provider ---
    ai_provider: str = Field(default="none", validation_alias="AI_PROVIDER")
    ai_api_key: str = Field(default="", validation_alias="AI_API_KEY")
    ai_api_base: str = Field(
        default="https://api.openai.com/v1", validation_alias="AI_API_BASE"
    )
    ai_model: str = Field(default="gpt-4o-mini", validation_alias="AI_MODEL")
    ai_embedding_model: str = Field(
        default="text-embedding-3-small", validation_alias="AI_EMBEDDING_MODEL"
    )
    ai_max_tokens: int = Field(default=2048, validation_alias="AI_MAX_TOKENS")
    ai_temperature: float = Field(default=0.1, validation_alias="AI_TEMPERATURE")

    # --- OCR ---
    ocr_enabled: bool = Field(default=True, validation_alias="OCR_ENABLED")
    tesseract_cmd: str = Field(default="", validation_alias="TESSERACT_CMD")

    # --- OpenSearch indexing ---
    opensearch_enabled: bool = Field(default=False, validation_alias="OPENSEARCH_ENABLED")

    # --- Celery ---
    celery_broker_url: str = Field(
        default="redis://localhost:6379/1", validation_alias="CELERY_BROKER_URL"
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/2", validation_alias="CELERY_RESULT_BACKEND"
    )
    celery_task_always_eager: bool = Field(
        default=False, validation_alias="CELERY_TASK_ALWAYS_EAGER"
    )

    # --- Derived values -------------------------------------------------------
    @computed_field  # type: ignore[prop-decorator]
    @property
    def database_url(self) -> str:
        """SQLAlchemy connection URL (psycopg v3 driver)."""
        if self.database_url_override:
            return self.database_url_override
        return (
            f"postgresql+psycopg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def redis_url(self) -> str:
        """Redis connection URL used for caching and sessions."""
        if self.redis_url_override:
            return self.redis_url_override
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def cors_origin_list(self) -> list[str]:
        """CORS origins parsed into a clean list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment is Environment.PRODUCTION

    @property
    def docs_enabled(self) -> bool:
        """Expose the OpenAPI docs UI everywhere except production."""
        return not self.is_production

    @model_validator(mode="after")
    def _enforce_production_secrets(self) -> Settings:
        """Refuse to boot in production with insecure settings."""
        if self.is_production:
            if self.secret_key == _PLACEHOLDER_SECRET:
                raise ValueError(
                    "SECRET_KEY must be set to a strong random value in production."
                )
            if not self.auth_cookie_secure:
                raise ValueError(
                    "AUTH_COOKIE_SECURE must be true in production to prevent cookie theft."
                )
        return self


@lru_cache
def get_settings() -> Settings:
    """Return the cached settings singleton."""
    return Settings()


settings = get_settings()
