import base64
import hashlib
import hmac
import json
import time
from typing import Any

import pytest

from en_learning.common.auth import decode_access_token
from en_learning.common.config import Settings


def encode_token(
    settings: Settings,
    *,
    user_id: str = "user-1",
    token_type: str = "access",
    expires_at: float | None = None,
    algorithm: str = "HS256",
    secret: str | None = None,
) -> str:
    def segment(value: dict[str, Any]) -> str:
        raw = json.dumps(value, separators=(",", ":")).encode()
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

    header = segment({"alg": algorithm, "typ": "JWT"})
    payload = segment(
        {
            "userId": user_id,
            "name": "test",
            "tokenType": token_type,
            "iat": int(time.time()),
            "exp": int(expires_at if expires_at is not None else time.time() + 300),
        }
    )
    signing_input = f"{header}.{payload}".encode()
    signature = hmac.new(
        (secret or settings.jwt_secret.get_secret_value()).encode(),
        signing_input,
        hashlib.sha256,
    ).digest()
    encoded_signature = base64.urlsafe_b64encode(signature).rstrip(b"=").decode()
    return f"{header}.{payload}.{encoded_signature}"


def test_access_token_matches_legacy_hs256_claims(settings: Settings) -> None:
    token = encode_token(settings)
    assert decode_access_token(token, settings).user_id == "user-1"


@pytest.mark.parametrize(
    "token",
    [
        "not-a-jwt",
        "e30.e30.invalid",
    ],
)
def test_malformed_tokens_are_rejected(settings: Settings, token: str) -> None:
    with pytest.raises(ValueError, match=r"JWT|signature"):
        decode_access_token(token, settings)


def test_refresh_expired_wrong_algorithm_and_wrong_signature_are_rejected(
    settings: Settings,
) -> None:
    invalid_tokens = (
        encode_token(settings, token_type="refresh"),
        encode_token(settings, expires_at=time.time() - 1),
        encode_token(settings, algorithm="none"),
        encode_token(settings, secret="wrong-secret"),
    )
    for token in invalid_tokens:
        with pytest.raises(ValueError, match=r"JWT|token|signature|algorithm|expired|access"):
            decode_access_token(token, settings)
