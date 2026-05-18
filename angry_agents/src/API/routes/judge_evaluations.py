from __future__ import annotations

import dataclasses
import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ...db.services import JudgeEvaluationService
from ..deps import get_db

router = APIRouter()


class EvaluationCreate(BaseModel):
    id_judge: int
    id_chat: int
    score: float | None = None


class EvaluationPatch(BaseModel):
    score: float | None = None


def _out(obj) -> dict:
    return dataclasses.asdict(obj)


@router.get("")
def list_evaluations(
    id_judge: int | None = None,
    id_chat: int | None = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: sqlite3.Connection = Depends(get_db),
) -> list:
    filters: dict = {}
    if id_judge is not None:
        filters["id_judge"] = id_judge
    if id_chat is not None:
        filters["id_chat"] = id_chat
    return [
        _out(e)
        for e in JudgeEvaluationService(db).query(
            filters=filters or None, limit=limit, offset=offset
        )
    ]


@router.post("", status_code=201)
def create_evaluation(body: EvaluationCreate, db: sqlite3.Connection = Depends(get_db)) -> dict:
    try:
        return _out(
            JudgeEvaluationService(db).create(
                id_judge=body.id_judge,
                id_chat=body.id_chat,
                score=body.score,
            )
        )
    except ValueError as exc:
        # max 20 evaluations per chat
        raise HTTPException(status_code=409, detail=str(exc))


@router.get("/{id_judge}/{id_chat}")
def get_evaluation(
    id_judge: int,
    id_chat: int,
    db: sqlite3.Connection = Depends(get_db),
) -> dict:
    ev = JudgeEvaluationService(db).get(id_judge, id_chat)
    if ev is None:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    return _out(ev)


@router.patch("/{id_judge}/{id_chat}")
def update_evaluation(
    id_judge: int,
    id_chat: int,
    body: EvaluationPatch,
    db: sqlite3.Connection = Depends(get_db),
) -> dict:
    svc = JudgeEvaluationService(db)
    if svc.get(id_judge, id_chat) is None:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    return _out(svc.update(id_judge, id_chat, body.model_dump(exclude_unset=True)))


@router.delete("/{id_judge}/{id_chat}", status_code=204)
def delete_evaluation(
    id_judge: int,
    id_chat: int,
    hard: bool = False,
    db: sqlite3.Connection = Depends(get_db),
) -> None:
    svc = JudgeEvaluationService(db)
    if svc.get(id_judge, id_chat) is None:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    svc.delete(id_judge, id_chat, hard=hard)
