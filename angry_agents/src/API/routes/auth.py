from __future__ import annotations

import hashlib
import os
import sqlite3
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from pydantic import BaseModel, EmailStr, Field
from sqlite3 import IntegrityError

from ...db.repositories import refresh_token_repository as rt_repo
from ...db.services.user_service import UserService
from ..config import get_settings
from ..deps import get_db, get_current_user
from ..jwt_utils import create_access_token, create_refresh_token
from ..schemas import AccessTokenOut, TokenOut, UserOut

router = APIRouter()

_AUTH_DISABLED = os.getenv("AUTH_DISABLED", "0") == "1"


class RegisterBody(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=6)
    name: str
    surname: str
    email: EmailStr
    role: str = Field("common", description="One of: common | admin")


class LoginBody(BaseModel):
    email: EmailStr
    password: str


class RefreshBody(BaseModel):
    refresh_token: str | None = Field(None, description="Supply if not using httpOnly cookie")


def _user_out(user) -> UserOut:
    return UserOut(
        id=user.id,
        username=user.username,
        name=user.name,
        surname=user.surname,
        email=user.email,
        role=user.role,
        slug=user.slug,
        created_at=user.created_at,
        updated_at=user.updated_at,
        deleted_at=user.deleted_at,
    )


def _issue_tokens(response: Response, user, db: sqlite3.Connection) -> TokenOut:
    """Generate access + refresh tokens, persist hash, set httpOnly cookie."""
    settings = get_settings()
    access_token = create_access_token(user.id, user.slug, user.role)
    plain_refresh, hash_refresh = create_refresh_token()
    if settings.refresh_token_expire_minutes > 0:
        refresh_delta = timedelta(minutes=settings.refresh_token_expire_minutes)
        cookie_max_age = settings.refresh_token_expire_minutes * 60
    else:
        refresh_delta = timedelta(days=settings.refresh_token_expire_days)
        cookie_max_age = settings.refresh_token_expire_days * 86_400
    expires_at = (datetime.now(timezone.utc) + refresh_delta).strftime("%Y-%m-%dT%H:%M:%S.000Z")

    rt_repo.create(db, user.id, hash_refresh, expires_at)

    response.set_cookie(
        key="refresh_token",
        value=plain_refresh,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        max_age=cookie_max_age,
        path="/auth",
    )
    return TokenOut(access_token=access_token, token_type="bearer", user=_user_out(user), refresh_token=plain_refresh)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

@router.post(
    "/register",
    response_model=UserOut,
    status_code=201,
    summary="Register a new user",
    description="Creates a new `common` user. Password is hashed with PBKDF2-SHA256 (260k iterations).",
)
def register(body: RegisterBody, db: sqlite3.Connection = Depends(get_db)) -> UserOut:
    try:
        user = UserService(db).create(
            username=body.username,
            password=body.password,
            name=body.name,
            surname=body.surname,
            email=body.email,
            role=body.role,
        )
    except IntegrityError:
        raise HTTPException(status_code=409, detail="Username or email already in use")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return _user_out(user)


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

@router.post(
    "/login",
    response_model=TokenOut,
    summary="Login",
    description=(
        "Returns a short-lived **access token** (Bearer JWT) and sets an httpOnly "
        "`refresh_token` cookie valid for 7 days. "
        "If `AUTH_DISABLED=1`, password check is skipped."
    ),
)
def login(body: LoginBody, response: Response, db: sqlite3.Connection = Depends(get_db)) -> TokenOut:
    svc = UserService(db)
    if _AUTH_DISABLED:
        user = svc.get_by_email(body.email)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
    else:
        user = svc.authenticate(body.email, body.password)
        if user is None:
            raise HTTPException(status_code=401, detail="Invalid email or password")
    return _issue_tokens(response, user, db)


# ---------------------------------------------------------------------------
# Current user
# ---------------------------------------------------------------------------

@router.get(
    "/me",
    response_model=UserOut,
    summary="Get current user",
    description="Reads the `Authorization: Bearer <token>` header and returns the authenticated user.",
)
def me(current_user=Depends(get_current_user)) -> UserOut:
    return _user_out(current_user)


# ---------------------------------------------------------------------------
# Refresh
# ---------------------------------------------------------------------------

@router.post(
    "/refresh",
    response_model=AccessTokenOut,
    summary="Refresh access token",
    description=(
        "Exchange a valid refresh token for a new access token. "
        "Supply via the httpOnly cookie **or** the JSON body field `refresh_token`."
    ),
)
def refresh(
    response: Response,
    body: RefreshBody = RefreshBody(),
    cookie_token: str | None = Cookie(None, alias="refresh_token"),
    db: sqlite3.Connection = Depends(get_db),
) -> AccessTokenOut:
    plain = body.refresh_token or cookie_token
    if not plain:
        raise HTTPException(status_code=401, detail="Refresh token required")

    token_hash = hashlib.sha256(plain.encode()).hexdigest()
    stored = rt_repo.get_by_hash(db, token_hash)

    if stored is None or stored.revoked_at is not None:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    if stored.expires_at < datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"):
        raise HTTPException(status_code=401, detail="Refresh token expired")

    user = UserService(db).get(stored.user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    new_access = create_access_token(user.id, user.slug, user.role)
    return AccessTokenOut(access_token=new_access, token_type="bearer")


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------

@router.post(
    "/logout",
    status_code=204,
    summary="Logout",
    description="Revokes the refresh token. Pass it via cookie or body field `refresh_token`.",
)
def logout(
    response: Response,
    body: RefreshBody = RefreshBody(),
    cookie_token: str | None = Cookie(None, alias="refresh_token"),
    db: sqlite3.Connection = Depends(get_db),
) -> None:
    plain = body.refresh_token or cookie_token
    if plain:
        token_hash = hashlib.sha256(plain.encode()).hexdigest()
        rt_repo.revoke(db, token_hash)
    response.delete_cookie(key="refresh_token", path="/auth")
