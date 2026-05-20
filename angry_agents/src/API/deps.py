from __future__ import annotations

import sqlite3
from typing import Generator

from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..db.models.base import get_connection
from ..db.models.user import User
from ..db.services.user_service import UserService
from .config import Settings, get_settings
from .jwt_utils import decode_access_token

_bearer = HTTPBearer(auto_error=False)


def get_db(settings: Settings = Depends(get_settings)) -> Generator[sqlite3.Connection, None, None]:
    conn = get_connection(settings.db_path)
    try:
        yield conn
    finally:
        conn.close()


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
    db: sqlite3.Connection = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = UserService(db).get(int(payload["sub"]))
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user
