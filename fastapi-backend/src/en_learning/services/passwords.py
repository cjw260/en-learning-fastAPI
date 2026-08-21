from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from dataclasses import dataclass

SCHEME = "scrypt"
VERSION = "1"
N = 2**14
R = 8
P = 1
DKLEN = 64
SALT_BYTES = 16


@dataclass(frozen=True, slots=True)
class PasswordCheck:
    valid: bool
    needs_upgrade: bool


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _derive(password: str, salt: bytes) -> bytes:
    return hashlib.scrypt(password.encode(), salt=salt, n=N, r=R, p=P, dklen=DKLEN)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(SALT_BYTES)
    digest = _derive(password, salt)
    return f"{SCHEME}${VERSION}${N}${R}${P}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, stored: str) -> PasswordCheck:
    if not stored.startswith(f"{SCHEME}$"):
        return PasswordCheck(
            valid=hmac.compare_digest(password.encode(), stored.encode()),
            needs_upgrade=True,
        )
    try:
        scheme, version, n, r, p, salt_value, digest_value = stored.split("$")
        if (scheme, version, int(n), int(r), int(p)) != (SCHEME, VERSION, N, R, P):
            return PasswordCheck(valid=False, needs_upgrade=False)
        salt = _decode(salt_value)
        expected = _decode(digest_value)
        if len(salt) != SALT_BYTES or len(expected) != DKLEN:
            return PasswordCheck(valid=False, needs_upgrade=False)
        actual = _derive(password, salt)
    except (ValueError, TypeError):
        return PasswordCheck(valid=False, needs_upgrade=False)
    return PasswordCheck(valid=hmac.compare_digest(actual, expected), needs_upgrade=False)
