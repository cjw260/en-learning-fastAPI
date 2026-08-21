from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field, RedisDsn, SecretStr, field_validator
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

    minio_endpoint: str = Field(validation_alias="MINIO_ENDPOINT", min_length=1)
    minio_port: int = Field(default=9000, validation_alias="MINIO_PORT", ge=1, le=65535)
    minio_use_ssl: bool = Field(default=False, validation_alias="MINIO_USE_SSL")
    minio_access_key: SecretStr = Field(validation_alias="MINIO_ACCESS_KEY")
    minio_secret_key: SecretStr = Field(validation_alias="MINIO_SECRET_KEY")
    minio_bucket: str = Field(validation_alias="MINIO_BUCKET", min_length=1)

    deepseek_base_url: AnyHttpUrl = Field(
        default=AnyHttpUrl("https://api.deepseek.com"),
        validation_alias="DEEPSEEK_BASE_URL",
    )
    deepseek_api_key: SecretStr = Field(validation_alias="DEEPSEEK_API_KEY")

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

    @field_validator("minio_access_key", "minio_secret_key", "deepseek_api_key")
    @classmethod
    def validate_non_empty_secret(cls, value: SecretStr) -> SecretStr:
        if not value.get_secret_value().strip():
            raise ValueError("must not be empty")
        return value

    @property
    def async_database_url(self) -> str:
        return self.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    @property
    def minio_host(self) -> str:
        return f"{self.minio_endpoint}:{self.minio_port}"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
