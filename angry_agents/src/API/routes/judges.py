from __future__ import annotations

import dataclasses
import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ...db.services import JudgeService
from ..deps import get_db
from ..schemas import JudgeOut

router = APIRouter()


class JudgeCreate(BaseModel):
    role: str = Field(
        ...,
        description="One of: style | ideology | general | behavioral",
        examples=["style"],
    )
    temperature: float | None = Field(None, ge=0.0, le=2.0, description="LLM sampling temperature")
    guess: str | None = Field(None, description="Initial persona guess")


class JudgePatch(BaseModel):
    role: str | None = Field(None, description="One of: style | ideology | general | behavioral")
    temperature: float | None = Field(None, ge=0.0, le=2.0)
    guess: str | None = None


def _out(obj) -> dict:
    return dataclasses.asdict(obj)


@router.get("", response_model=list[JudgeOut], summary="List judges")
def list_judges(
    role: str | None = Query(None, description="Filter by role (style|ideology|general|behavioral)"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: sqlite3.Connection = Depends(get_db),
) -> list:
    filters = {"role": role} if role is not None else None
    return [_out(j) for j in JudgeService(db).query(filters=filters, limit=limit, offset=offset)]


@router.post(
    "",
    response_model=JudgeOut,
    status_code=201,
    summary="Create a judge",
    description="Returns HTTP 422 if `role` is not one of the four valid values.",
)
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


@router.get("/{id}", response_model=JudgeOut, summary="Get a judge by ID")
def get_judge(id: int, db: sqlite3.Connection = Depends(get_db)) -> dict:
    judge = JudgeService(db).get(id)
    if judge is None:
        raise HTTPException(status_code=404, detail="Judge not found")
    return _out(judge)


@router.patch("/{id}", response_model=JudgeOut, summary="Partially update a judge")
def update_judge(id: int, body: JudgePatch, db: sqlite3.Connection = Depends(get_db)) -> dict:
    svc = JudgeService(db)
    if svc.get(id) is None:
        raise HTTPException(status_code=404, detail="Judge not found")
    try:
        return _out(svc.update(id, body.model_dump(exclude_unset=True)))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.delete("/{id}", status_code=204, summary="Soft-delete a judge (hard=true for permanent)")
def delete_judge(
    id: int,
    hard: bool = Query(False, description="Set true for permanent deletion"),
    db: sqlite3.Connection = Depends(get_db),
) -> None:
    svc = JudgeService(db)
    if svc.get(id) is None:
        raise HTTPException(status_code=404, detail="Judge not found")
    svc.delete(id, hard=hard)
