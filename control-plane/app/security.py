"""Auth helpers: password hashing, JWT, enrollment codes, config signing."""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import get_settings

pwd_context = CryptContext(schemes=["argon2", "scrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_access_token(
    subject: str,
    *,
    token_type: str = "admin",
    extra: Optional[dict[str, Any]] = None,
    expires_minutes: Optional[int] = None,
) -> str:
    settings = get_settings()
    ttl = expires_minutes or settings.access_token_ttl_minutes
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=ttl)).timestamp()),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.token_signing_key, algorithm="HS256")


def decode_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    return jwt.decode(token, settings.token_signing_key, algorithms=["HS256"])


def try_decode_token(token: str) -> Optional[dict[str, Any]]:
    try:
        return decode_token(token)
    except JWTError:
        return None


def generate_enrollment_code() -> str:
    return secrets.token_urlsafe(12)


def generate_short_id(length: int = 8) -> str:
    if length % 2:
        length += 1
    return secrets.token_hex(length // 2)


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def new_uuid() -> UUID:
    from uuid import uuid4

    return uuid4()
