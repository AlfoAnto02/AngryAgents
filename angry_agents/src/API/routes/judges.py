from __future__ import annotations

import dataclasses
import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ...db.services import JudgeService
from ..deps import get_db

router = APIRouter()

VALID_ROLES = ("style", "ideology", "general", "behavioral")


class JudgeCreate(BaseModel):
    role: str
    temperature: float | None = None
    guess: str | None = None


class JudgePatch(BaseModel):
    role: str | None = None
    temperature: float | None = None
    guess: str | None = None


def _out(obj) -> dict:
    return dataclasses.asdict(obj)


@router.get("")
def list_judges(
    role: str | None = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: sqlite3.Connection = Depends(get_db),
) -> list:
    filters = {"role": role} if role is not None else None
    return [_out(j) for j in JudgeService(db).query(filters=filters, limit=limit, offset=offset)]


@router.post("", status_code=201)
def create_judge(body: JudgeCreate, db: sqlite3.Connection = Depends(get_db)) -> dict:
    try:
        return _out(
            JudgeService(db).create(
                role=body.role,
                temperature=body.temperature,
                guess=body.guess,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/{id}")
def get_judge(id: int, db: sqlite3.Connection = Depends(get_db)) -> dict:
    judge = JudgeService(db).get(id)
    if judge is None:
        raise HTTPException(status_code=404, detail="Judge not found")
    return _out(judge)


@router.patch("/{id}")
def update_judge(id: int, body: JudgePatch, db: sqlite3.Connection = Depends(get_db)) -> dict:
    svc = JudgeService(db)
    if svc.get(id) is None:
        raise HTTPException(status_code=404, detail="Judge not found")
    try:
        return _out(svc.update(id, body.model_dump(exclude_unset=True)))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.delete("/{id}", status_code=204)
def delete_judge(
    id: int,
    hard: bool = False,
    db: sqlite3.Connection = Depends(get_db),
) -> None:
    svc = JudgeService(db)
    if svc.get(id) is None:
        raise HTTPException(status_code=404, detail="Judge not found")
    svc.delete(id, hard=hard)
