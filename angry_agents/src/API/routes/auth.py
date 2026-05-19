from __future__ import annotations

import os
import sqlite3

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, EmailStr, Field
from sqlite3 import IntegrityError

from ...db.services import UserService
from ..deps import get_db
from ..schemas import UserOut

router = APIRouter()

_AUTH_DISABLED = os.getenv("AUTH_DISABLED", "0") == "1"


class RegisterBody(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=6)
    name: str
    surname: str
    email: str = Field(..., description="Must be unique")
    role: str = Field("common", description="One of: common | admin")


class LoginBody(BaseModel):
    email: str
    password: str


def _safe_out(user) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "name": user.name,
        "surname": user.surname,
        "email": user.email,
        "role": user.role,
        "slug": user.slug,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
        "deleted_at": user.deleted_at,
    }


@router.post(
    "/register",
    response_model=UserOut,
    status_code=201,
    summary="Register a new user",
    description="Creates a new `common` user by default. Password is stored hashed (PBKDF2-SHA256).",
)
def register(body: RegisterBody, db: sqlite3.Connection = Depends(get_db)) -> dict:
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
    return _safe_out(user)


@router.post(
    "/login",
    response_model=UserOut,
    summary="Login",
    description=(
        "Returns user info including `slug` and `role`. "
        "Store the slug and send it as `X-User-Slug` on subsequent requests. "
        "If `AUTH_DISABLED=1`, password check is skipped."
    ),
)
def login(body: LoginBody, db: sqlite3.Connection = Depends(get_db)) -> dict:
    svc = UserService(db)
    if _AUTH_DISABLED:
        user = svc.get_by_email(body.email)
        if user is None:
            raise HTTPException(status_code=404, detail="User not found")
    else:
        user = svc.authenticate(body.email, body.password)
        if user is None:
            raise HTTPException(status_code=401, detail="Invalid email or password")
    return _safe_out(user)


@router.get(
    "/me",
    response_model=UserOut,
    summary="Get current user",
    description="Reads `X-User-Slug` header and returns the corresponding user.",
)
def me(
    x_user_slug: str | None = Header(None, alias="X-User-Slug"),
    db: sqlite3.Connection = Depends(get_db),
) -> dict:
    if not x_user_slug:
        raise HTTPException(status_code=401, detail="X-User-Slug header required")
    user = UserService(db).get_by_slug(x_user_slug)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return _safe_out(user)
