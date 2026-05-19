from __future__ import annotations

import dataclasses
import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ...db.services import JudgeEvaluationService
from ..deps import get_db
from ..schemas import JudgeEvaluationOut

router = APIRouter()


_Score = Annotated[float, Field(ge=1.0, le=5.0)]


class EvaluationCreate(BaseModel):
    id_judge: int = Field(..., description="FK to Judges")
    id_chat: int = Field(..., description="FK to Group_chat")
    score: list[_Score] | None = Field(None, description="Fidelity scores 1–5")


class EvaluationPatch(BaseModel):
    score: list[_Score] | None = Field(None, description="Fidelity scores 1–5")


def _out(obj) -> dict:
    return dataclasses.asdict(obj)


@router.get("", response_model=list[JudgeEvaluationOut], summary="List evaluations")
def list_evaluations(
    id_judge: int | None = Query(None, description="Filter by judge ID"),
    id_chat: int | None = Query(None, description="Filter by chat ID"),
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


@router.post(
    "",
    response_model=JudgeEvaluationOut,
    status_code=201,
    summary="Create a judge evaluation",
    description="Returns HTTP 409 if the chat already has 20 evaluations (the maximum).",
)
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
        raise HTTPException(status_code=409, detail=str(exc))


@router.get(
    "/{id_judge}/{id_chat}",
    response_model=JudgeEvaluationOut,
    summary="Get an evaluation by composite key",
)
def get_evaluation(
    id_judge: int,
    id_chat: int,
    db: sqlite3.Connection = Depends(get_db),
) -> dict:
    ev = JudgeEvaluationService(db).get(id_judge, id_chat)
    if ev is None:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    return _out(ev)


@router.patch(
    "/{id_judge}/{id_chat}",
    response_model=JudgeEvaluationOut,
    summary="Update an evaluation score",
)
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


@router.delete(
    "/{id_judge}/{id_chat}",
    status_code=204,
    summary="Soft-delete an evaluation (hard=true for permanent)",
)
def delete_evaluation(
    id_judge: int,
    id_chat: int,
    hard: bool = Query(False, description="Set true for permanent deletion"),
    db: sqlite3.Connection = Depends(get_db),
) -> None:
    svc = JudgeEvaluationService(db)
    if svc.get(id_judge, id_chat) is None:
        raise HTTPException(status_code=404, detail="Evaluation not found")
    svc.delete(id_judge, id_chat, hard=hard)
