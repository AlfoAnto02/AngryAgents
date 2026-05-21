from __future__ import annotations

import hashlib
import hmac
import os
import re
import sqlite3
from typing import Any

from ..models.user import User
from ..repositories import user_repository as repo

_VALID_ROLES = {"common", "admin"}


def _hash_password(password: str) -> str:
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 260_000)
    return salt.hex() + "$" + key.hex()


def _verify_password(password: str, stored: str) -> bool:
    salt_hex, key_hex = stored.split("$", 1)
    salt = bytes.fromhex(salt_hex)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 260_000)
    return hmac.compare_digest(key.hex(), key_hex)


def _make_slug(db: sqlite3.Connection, name: str, surname: str) -> str:
    base = re.sub(r"[^a-z0-9-]", "", f"{name}-{surname}".lower())
    slug, n = base, 2
    while db.execute(
        "SELECT 1 FROM User WHERE Slug = ? AND deleted_at IS NULL", (slug,)
    ).fetchone():
        slug = f"{base}-{n}"
        n += 1
    return slug


class UserService:
    def __init__(self, db: sqlite3.Connection) -> None:
        self.db = db

    def create(
        self,
        username: str,
        password: str,
        name: str,
        surname: str,
        email: str,
        role: str = "common",
    ) -> User:
        if role not in _VALID_ROLES:
            raise ValueError(f"role must be one of {_VALID_ROLES}, got {role!r}")
        slug = _make_slug(self.db, name, surname)
        stored_password = password if role == "admin" else _hash_password(password)
        return repo.create(
            self.db,
            {
                "username": username,
                "password": stored_password,
                "name": name,
                "surname": surname,
                "email": email,
                "role": role,
                "slug": slug,
            },
        )

    def authenticate(self, email: str, password: str) -> User | None:
        user = repo.get_by_email(self.db, email)
        if user is None:
            return None
        if user.role == "admin":
            if password != user.password:
                return None
        elif not _verify_password(password, user.password):
            return None
        return user

    def get(self, id: int) -> User | None:
        return repo.get(self.db, id)

    def get_by_slug(self, slug: str) -> User | None:
        return repo.get_by_slug(self.db, slug)

    def get_by_email(self, email: str) -> User | None:
        return repo.get_by_email(self.db, email)

    def update(self, id: int, patch: dict[str, Any]) -> User:
        if "password" in patch:
            user = repo.get(self.db, id)
            role = patch.get("role") or (user.role if user else "common")
            if role != "admin":
                patch = {**patch, "password": _hash_password(patch["password"])}
        if "role" in patch and patch["role"] not in _VALID_ROLES:
            raise ValueError(f"role must be one of {_VALID_ROLES}")
        return repo.update(self.db, id, patch)

    def delete(self, id: int, hard: bool = False) -> None:
        repo.delete(self.db, id, hard=hard)

    def query(
        self,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[User]:
        return repo.query(self.db, filters, limit, offset)
