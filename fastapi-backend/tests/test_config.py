import json
import logging

import pytest
from pydantic import ValidationError

from en_learning.common.config import Settings
from en_learning.common.logging import JsonFormatter
from tests.conftest import settings_values


def test_missing_required_configuration_fails_without_values() -> None:
    with pytest.raises(ValidationError) as captured:
        Settings(_env_file=None)

    rendered = str(captured.value)
    for field in (
        "DATABASE_URL",
        "REDIS_URL",
        "MINIO_ENDPOINT",
        "MINIO_ACCESS_KEY",
        "MINIO_SECRET_KEY",
        "MINIO_BUCKET",
        "DEEPSEEK_API_KEY",
    ):
        assert field in rendered


def test_configuration_repr_and_validation_hide_secrets() -> None:
    sentinel = "never-log-this-secret"
    settings = Settings(
        _env_file=None,
        **settings_values(
            minio_access_key=sentinel,
            minio_secret_key=sentinel,
            deepseek_api_key=sentinel,
        ),
    )
    assert sentinel not in repr(settings)

    with pytest.raises(ValidationError) as captured:
        Settings(_env_file=None, **settings_values(database_url=sentinel))
    assert sentinel not in str(captured.value)


def test_json_log_formatter_includes_request_id_without_secrets() -> None:
    record = logging.LogRecord(
        name="en_learning.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="request.completed",
        args=(),
        exc_info=None,
    )
    record.request_id = "request-123"
    record.path = "/health/live"
    rendered = JsonFormatter().format(record)
    payload = json.loads(rendered)
    assert payload["requestId"] == "request-123"
    assert payload["path"] == "/health/live"
    assert "secret" not in rendered.lower()
