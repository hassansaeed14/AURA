from __future__ import annotations

import base64
import hashlib
import hmac
import secrets


PBKDF2_ROUNDS = 120_000


def hash_secret(value: str, *, salt: str | None = None) -> str:
    raw_salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", value.encode("utf-8"), raw_salt.encode("utf-8"), PBKDF2_ROUNDS)
    return f"{raw_salt}${base64.b64encode(digest).decode('utf-8')}"


def verify_secret(value: str, hashed_value: str) -> bool:
    try:
        salt, encoded = hashed_value.split("$", 1)
    except ValueError:
        return False
    expected = hash_secret(value, salt=salt)
    return hmac.compare_digest(expected, f"{salt}${encoded}")


def generate_token(length: int = 24) -> str:
    return secrets.token_urlsafe(length)
