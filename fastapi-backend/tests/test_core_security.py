import time

import pytest

from en_learning.common.auth import decode_access_token, decode_token, encode_token
from en_learning.services.passwords import hash_password, verify_password
from en_learning.services.tracker_privacy import sanitize_payload, sanitize_text, sanitize_url


def test_password_hash_is_salted_and_legacy_values_upgrade() -> None:
    first = hash_password("legacy-md5-value")
    second = hash_password("legacy-md5-value")

    assert first.startswith("scrypt$1$")
    assert second.startswith("scrypt$1$")
    assert first != second
    assert verify_password("legacy-md5-value", first).valid
    assert not verify_password("wrong", first).valid

    legacy = verify_password("legacy-md5-value", "legacy-md5-value")
    assert legacy.valid
    assert legacy.needs_upgrade


def test_access_and_refresh_tokens_are_typed_and_expire(settings) -> None:  # type: ignore[no-untyped-def]
    access = encode_token(
        settings,
        user_id="user-1",
        name="Tester",
        email=None,
        token_type="access",
        refresh_version=4,
    )
    refresh = encode_token(
        settings,
        user_id="user-1",
        name="Tester",
        email=None,
        token_type="refresh",
        refresh_version=4,
    )

    assert decode_access_token(access, settings).user_id == "user-1"
    assert decode_token(refresh, settings, expected_type="refresh").refresh_version == 4
    with pytest.raises(ValueError, match="refresh"):
        decode_token(access, settings, expected_type="refresh")
    with pytest.raises(ValueError, match="access"):
        decode_access_token(refresh, settings)

    expired = encode_token(
        settings,
        user_id="user-1",
        name="Tester",
        email=None,
        token_type="access",
        refresh_version=4,
        now=time.time() - settings.jwt_access_ttl_seconds - 1,
    )
    with pytest.raises(ValueError, match="expired"):
        decode_access_token(expired, settings)


def test_tracker_privacy_redacts_nested_secrets_and_url_queries() -> None:
    secret = "Bearer abc.def.ghi"
    payload = sanitize_payload(
        {
            "password": "visible",
            "nested": {
                "email": "person@example.test",
                "phone": "13800138000",
                "text": secret,
            },
        }
    )
    assert payload == {
        "password": "[REDACTED]",
        "nested": {
            "email": "[REDACTED_EMAIL]",
            "phone": "[REDACTED_PHONE]",
            "text": "[REDACTED_TOKEN]",
        },
    }
    assert sanitize_text(secret) == "[REDACTED_TOKEN]"
    assert sanitize_url("https://example.test/page?token=abc&view=person@example.test#secret") == (
        "https://example.test/page?token=%5BREDACTED%5D&view=%5BREDACTED_EMAIL%5D"
    )


def test_tracker_privacy_rejects_unbounded_payloads() -> None:
    with pytest.raises(Exception, match="嵌套过深"):
        sanitize_payload({"a": {"b": {"c": {"d": {"e": {"f": {"g": {"h": {"i": 1}}}}}}}}})
    with pytest.raises(Exception, match="项目过多"):
        sanitize_payload({str(index): index for index in range(51)})
