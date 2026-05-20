from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import jwt

_ALGORITHM = "HS256"


def create_access_token(user_id: int, slug: str, role: str) -> str:
    from .config import get_settings
    settings = get_settings()
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode(
        {"sub": str(user_id), "slug": slug, "role": role, "exp": exp},
        settings.jwt_secret,
        algorithm=_ALGORITHM,
    )


def create_refresh_token() -> tuple[str, str]:
    """Return (plaintext_token, sha256_hex_hash). Store only the hash."""
    plain = secrets.token_urlsafe(32)
    hashed = hashlib.sha256(plain.encode()).hexdigest()
    return plain, hashed


def decode_access_token(token: str) -> dict | None:
    """Return payload dict or None on expiry / invalid signature."""
    from .config import get_settings
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[_ALGORITHM])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
