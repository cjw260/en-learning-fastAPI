from functools import lru_cache
from typing import Literal, Self

from pydantic import AnyHttpUrl, Field, RedisDsn, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed process settings with secret-safe validation errors."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
        hide_input_in_errors=True,
        populate_by_name=True,
    )

    environment: Literal["development", "test", "production"] = Field(
        default="development",
        validation_alias="ENVIRONMENT",
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        validation_alias="LOG_LEVEL",
    )

    database_url: str = Field(validation_alias="DATABASE_URL", min_length=1)
    database_pool_size: int = Field(
        default=5,
        validation_alias="DATABASE_POOL_SIZE",
        ge=1,
        le=100,
    )
    database_max_overflow: int = Field(
        default=5,
        validation_alias="DATABASE_MAX_OVERFLOW",
        ge=0,
        le=100,
    )

    redis_url: RedisDsn = Field(validation_alias="REDIS_URL")

    jwt_secret: SecretStr = Field(validation_alias="SECRET_KEY")
    jwt_access_ttl_seconds: int = Field(
        default=300,
        validation_alias="JWT_ACCESS_TTL_SECONDS",
        ge=60,
        le=86_400,
    )
    jwt_refresh_ttl_seconds: int = Field(
        default=604_800,
        validation_alias="JWT_REFRESH_TTL_SECONDS",
        ge=300,
        le=2_592_000,
    )

    minio_endpoint: str = Field(validation_alias="MINIO_ENDPOINT", min_length=1)
    minio_port: int = Field(default=9000, validation_alias="MINIO_PORT", ge=1, le=65535)
    minio_use_ssl: bool = Field(default=False, validation_alias="MINIO_USE_SSL")
    minio_access_key: SecretStr = Field(validation_alias="MINIO_ACCESS_KEY")
    minio_secret_key: SecretStr = Field(validation_alias="MINIO_SECRET_KEY")
    minio_bucket: str = Field(validation_alias="MINIO_BUCKET", min_length=1)
    avatar_max_bytes: int = Field(
        default=5 * 1024 * 1024,
        validation_alias="AVATAR_MAX_BYTES",
        ge=1024,
        le=10 * 1024 * 1024,
    )

    tracker_max_body_bytes: int = Field(
        default=64 * 1024,
        validation_alias="TRACKER_MAX_BODY_BYTES",
        ge=1024,
        le=1024 * 1024,
    )
    tracker_rate_limit: int = Field(
        default=120,
        validation_alias="TRACKER_RATE_LIMIT",
        ge=1,
        le=10_000,
    )
    tracker_rate_window_seconds: int = Field(
        default=60,
        validation_alias="TRACKER_RATE_WINDOW_SECONDS",
        ge=1,
        le=3600,
    )

    deepseek_base_url: AnyHttpUrl = Field(
        default=AnyHttpUrl("https://api.deepseek.com"),
        validation_alias="DEEPSEEK_BASE_URL",
    )
    deepseek_api_key: SecretStr = Field(validation_alias="DEEPSEEK_API_KEY")
    deepseek_chat_model: str = Field(
        default="deepseek-chat",
        validation_alias="DEEPSEEK_CHAT_MODEL",
        min_length=1,
    )
    deepseek_reasoner_model: str = Field(
        default="deepseek-reasoner",
        validation_alias="DEEPSEEK_REASONER_MODEL",
        min_length=1,
    )
    bocha_search_url: AnyHttpUrl | None = Field(
        default=None,
        validation_alias="BOCHA_SEARCH_URL",
    )
    bocha_api_key: SecretStr | None = Field(
        default=None,
        validation_alias="BOCHA_API_KEY",
    )

    llm_connect_timeout_seconds: float = Field(
        default=5,
        validation_alias="LLM_CONNECT_TIMEOUT_SECONDS",
        gt=0,
        le=60,
    )
    llm_first_token_timeout_seconds: float = Field(
        default=30,
        validation_alias="LLM_FIRST_TOKEN_TIMEOUT_SECONDS",
        gt=0,
        le=180,
    )
    llm_total_timeout_seconds: float = Field(
        default=120,
        validation_alias="LLM_TOTAL_TIMEOUT_SECONDS",
        gt=0,
        le=600,
    )
    llm_max_retries: int = Field(
        default=1,
        validation_alias="LLM_MAX_RETRIES",
        ge=0,
        le=3,
    )
    ai_max_input_characters: int = Field(
        default=4_000,
        validation_alias="AI_MAX_INPUT_CHARACTERS",
        ge=100,
        le=20_000,
    )
    ai_history_message_limit: int = Field(
        default=40,
        validation_alias="AI_HISTORY_MESSAGE_LIMIT",
        ge=2,
        le=200,
    )
    ai_sse_heartbeat_seconds: float = Field(
        default=10,
        validation_alias="AI_SSE_HEARTBEAT_SECONDS",
        gt=0,
        le=30,
    )
    ai_conversation_lock_ttl_seconds: int = Field(
        default=150,
        validation_alias="AI_CONVERSATION_LOCK_TTL_SECONDS",
        ge=10,
        le=900,
    )
    ai_search_result_limit: int = Field(
        default=5,
        validation_alias="AI_SEARCH_RESULT_LIMIT",
        ge=1,
        le=10,
    )
    ai_search_context_characters: int = Field(
        default=8_000,
        validation_alias="AI_SEARCH_CONTEXT_CHARACTERS",
        ge=500,
        le=20_000,
    )

    http_timeout_seconds: float = Field(
        default=10,
        validation_alias="HTTP_TIMEOUT_SECONDS",
        gt=0,
        le=120,
    )
    health_check_timeout_seconds: float = Field(
        default=2,
        validation_alias="HEALTH_CHECK_TIMEOUT_SECONDS",
        gt=0,
        le=30,
    )

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        if not value.startswith(("postgresql+asyncpg://", "postgresql://")):
            raise ValueError("must be a PostgreSQL URL")
        return value

    @field_validator(
        "jwt_secret",
        "minio_access_key",
        "minio_secret_key",
        "deepseek_api_key",
    )
    @classmethod
    def validate_non_empty_secret(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value().strip():
            raise ValueError("must not be empty")
        return value

    @field_validator("bocha_api_key")
    @classmethod
    def validate_optional_secret(cls, value: SecretStr | None) -> SecretStr | None:
        if value is not None and not value.get_secret_value().strip():
            raise ValueError("must not be empty")
        return value

    @model_validator(mode="after")
    def validate_ai_timeouts(self) -> Self:
        if self.llm_first_token_timeout_seconds > self.llm_total_timeout_seconds:
            raise ValueError("LLM first-token timeout must not exceed total timeout")
        if self.ai_conversation_lock_ttl_seconds <= self.llm_total_timeout_seconds:
            raise ValueError("AI conversation lock TTL must exceed LLM total timeout")
        if (self.bocha_search_url is None) != (self.bocha_api_key is None):
            raise ValueError("BOCHA_SEARCH_URL and BOCHA_API_KEY must be configured together")
        return self

    @property
    def async_database_url(self) -> str:
        return self.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    @property
    def minio_host(self) -> str:
        return f"{self.minio_endpoint}:{self.minio_port}"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
