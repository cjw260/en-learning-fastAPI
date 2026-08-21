from __future__ import annotations

import math
import re
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from en_learning.common.errors import AppError

SENSITIVE_KEY_PARTS = (
    "authorization",
    "cookie",
    "password",
    "passwd",
    "secret",
    "token",
    "credential",
)
BEARER_PATTERN = re.compile(r"(?i)bearer\s+[a-z0-9._~+\-/]+=*")
EMAIL_PATTERN = re.compile(r"(?<![\w.+-])[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}(?![\w.-])")
PHONE_PATTERN = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
MAX_DEPTH = 8
MAX_ITEMS = 50
MAX_KEY_LENGTH = 64
MAX_STRING_LENGTH = 1024


def sanitize_text(value: str) -> str:
    value = BEARER_PATTERN.sub("[REDACTED_TOKEN]", value)
    value = EMAIL_PATTERN.sub("[REDACTED_EMAIL]", value)
    value = PHONE_PATTERN.sub("[REDACTED_PHONE]", value)
    return value[:MAX_STRING_LENGTH]


def sanitize_url(value: str | None) -> str | None:
    if value is None or not value:
        return value
    parts = urlsplit(value)
    query = []
    for key, item in parse_qsl(parts.query, keep_blank_values=True):
        if any(part in key.lower() for part in SENSITIVE_KEY_PARTS):
            query.append((key, "[REDACTED]"))
        else:
            query.append((key, sanitize_text(item)))
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), ""))[:2048]


def sanitize_payload(value: Any, *, depth: int = 0) -> Any:
    if depth > MAX_DEPTH:
        raise AppError("埋点 payload 嵌套过深", status_code=422)
    if isinstance(value, float) and not math.isfinite(value):
        raise AppError("埋点 payload 数值无效", status_code=422)
    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, str):
        return sanitize_text(value)
    if isinstance(value, list):
        if len(value) > MAX_ITEMS:
            raise AppError("埋点 payload 项目过多", status_code=422)
        return [sanitize_payload(item, depth=depth + 1) for item in value]
    if isinstance(value, dict):
        if len(value) > MAX_ITEMS:
            raise AppError("埋点 payload 项目过多", status_code=422)
        sanitized: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str) or len(key) > MAX_KEY_LENGTH:
                raise AppError("埋点 payload key 无效", status_code=422)
            if any(part in key.lower() for part in SENSITIVE_KEY_PARTS):
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = sanitize_payload(item, depth=depth + 1)
        return sanitized
    raise AppError("埋点 payload 类型无效", status_code=422)
