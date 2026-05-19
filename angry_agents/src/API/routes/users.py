from __future__ import annotations

import sqlite3
from sqlite3 import IntegrityError

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ...db.services import UserService
from ..deps import get_db
from ..schemas import UserOut

router = APIRouter()


class UserPatch(BaseModel):
    name: str | None = None
    surname: str | None = None
    role: str | None = Field(None, description="One of: common | admin")
    password: str | None = Field(None, min_length=6, description="Replaces the current password")


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


@router.get("", response_model=list[UserOut], summary="List users")
def list_users(
    role: str | None = Query(None, description="Filter by role"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: sqlite3.Connection = Depends(get_db),
) -> list:
    filters = {"role": role} if role else None
    return [_safe_out(u) for u in UserService(db).query(filters=filters, limit=limit, offset=offset)]


@router.get("/slug/{slug}", response_model=UserOut, summary="Get a user by slug")
def get_user_by_slug(slug: str, db: sqlite3.Connection = Depends(get_db)) -> dict:
    user = UserService(db).get_by_slug(slug)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return _safe_out(user)


@router.get("/{id}", response_model=UserOut, summary="Get a user by ID")
def get_user(id: int, db: sqlite3.Connection = Depends(get_db)) -> dict:
    user = UserService(db).get(id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return _safe_out(user)


@router.patch("/{id}", response_model=UserOut, summary="Update a user")
def update_user(id: int, body: UserPatch, db: sqlite3.Connection = Depends(get_db)) -> dict:
    svc = UserService(db)
    if svc.get(id) is None:
        raise HTTPException(status_code=404, detail="User not found")
    try:
        return _safe_out(svc.update(id, body.model_dump(exclude_unset=True)))
    except (IntegrityError, ValueError) as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.delete("/{id}", status_code=204, summary="Soft-delete a user (hard=true for permanent)")
def delete_user(
    id: int,
    hard: bool = Query(False, description="Set true for permanent deletion"),
    db: sqlite3.Connection = Depends(get_db),
) -> None:
    svc = UserService(db)
    if svc.get(id) is None:
        raise HTTPException(status_code=404, detail="User not found")
    svc.delete(id, hard=hard)
