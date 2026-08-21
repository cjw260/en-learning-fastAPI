from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import math
import time
from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from en_learning.common.config import Settings
from en_learning.common.errors import AppError

bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True, slots=True)
class Principal:
    user_id: str


def _decode_segment(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    try:
        return base64.urlsafe_b64decode(value + padding)
    except (ValueError, binascii.Error) as exception:
        raise ValueError("invalid JWT encoding") from exception


def _json_object(value: str) -> dict[str, Any]:
    try:
        decoded = json.loads(_decode_segment(value))
    except (UnicodeDecodeError, json.JSONDecodeError) as exception:
        raise ValueError("invalid JWT JSON") from exception
    if not isinstance(decoded, dict):
        raise ValueError("JWT segment must be an object")
    return decoded


def _numeric_date(payload: dict[str, Any], claim: str) -> float | None:
    value = payload.get(claim)
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"invalid {claim} claim")
    return float(value)


def decode_access_token(token: str, settings: Settings, *, now: float | None = None) -> Principal:
    try:
        header_segment, payload_segment, signature_segment = token.split(".")
    except ValueError as exception:
        raise ValueError("JWT must contain three segments") from exception

    header = _json_object(header_segment)
    payload = _json_object(payload_segment)
    if header.get("alg") != "HS256":
        raise ValueError("unsupported JWT algorithm")

    signed = f"{header_segment}.{payload_segment}".encode()
    expected = hmac.new(
        settings.jwt_secret.get_secret_value().encode(),
        signed,
        hashlib.sha256,
    ).digest()
    actual = _decode_segment(signature_segment)
    if not hmac.compare_digest(expected, actual):
        raise ValueError("invalid JWT signature")

    current_time = time.time() if now is None else now
    expires_at = _numeric_date(payload, "exp")
    not_before = _numeric_date(payload, "nbf")
    if expires_at is None or current_time >= expires_at:
        raise ValueError("expired JWT")
    if not_before is not None and current_time < not_before:
        raise ValueError("JWT is not active")
    if payload.get("tokenType") != "access":
        raise ValueError("JWT is not an access token")

    user_id = payload.get("userId")
    if not isinstance(user_id, str) or not user_id.strip() or len(user_id) > 128:
        raise ValueError("invalid userId claim")
    return Principal(user_id=user_id)


async def get_current_principal(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> Principal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise AppError("请先登录", status_code=401)
    settings: Settings = request.app.state.settings
    try:
        return decode_access_token(credentials.credentials, settings)
    except ValueError as exception:
        raise AppError("token已失效", status_code=401) from exception
