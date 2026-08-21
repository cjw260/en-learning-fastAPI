import json
import logging
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

request_id_context: ContextVar[str | None] = ContextVar("request_id", default=None)


class JsonFormatter(logging.Formatter):
    """Small JSON formatter that never serializes settings or request bodies."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        request_id = getattr(record, "request_id", None) or request_id_context.get()
        if request_id:
            payload["requestId"] = request_id
        for key in (
            "method",
            "path",
            "statusCode",
            "durationMs",
            "service",
            "failureCount",
            "exceptionType",
            "operation",
            "userReference",
            "role",
            "deepThink",
            "webSearch",
            "chunkCount",
            "outputCharacters",
            "promptTokens",
            "completionTokens",
            "totalTokens",
            "latencyMs",
            "failureKind",
        ):
            if (value := getattr(record, key, None)) is not None:
                payload[key] = value
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def configure_logging(level: str) -> None:
    logger = logging.getLogger("en_learning")
    logger.setLevel(level)
    logger.propagate = False
    if not any(getattr(handler, "_en_learning_json", False) for handler in logger.handlers):
        json_handler = logging.StreamHandler()
        json_handler.setFormatter(JsonFormatter())
        json_handler._en_learning_json = True  # type: ignore[attr-defined]
        logger.addHandler(json_handler)
    for registered_handler in logger.handlers:
        registered_handler.setLevel(level)
