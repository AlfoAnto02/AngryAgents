from __future__ import annotations

import dataclasses
import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ...db.services import AgentContextService
from ..deps import get_db

router = APIRouter()


class ContextCreate(BaseModel):
    id_agent: int
    signature_phrases: str | None = None


class ContextPatch(BaseModel):
    signature_phrases: str | None = None


def _out(obj) -> dict:
    return dataclasses.asdict(obj)


@router.get("")
def list_contexts(
    id_agent: int | None = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: sqlite3.Connection = Depends(get_db),
) -> list:
    filters = {"id_agent": id_agent} if id_agent is not None else None
    return [_out(c) for c in AgentContextService(db).query(filters=filters, limit=limit, offset=offset)]


@router.post("", status_code=201)
def create_context(body: ContextCreate, db: sqlite3.Connection = Depends(get_db)) -> dict:
    return _out(
        AgentContextService(db).create(
            id_agent=body.id_agent,
            signature_phrases=body.signature_phrases,
        )
    )


@router.get("/{id}")
def get_context(id: int, db: sqlite3.Connection = Depends(get_db)) -> dict:
    ctx = AgentContextService(db).get(id)
    if ctx is None:
        raise HTTPException(status_code=404, detail="Context not found")
    return _out(ctx)


@router.patch("/{id}")
def update_context(id: int, body: ContextPatch, db: sqlite3.Connection = Depends(get_db)) -> dict:
    svc = AgentContextService(db)
    if svc.get(id) is None:
        raise HTTPException(status_code=404, detail="Context not found")
    return _out(svc.update(id, body.model_dump(exclude_unset=True)))


@router.delete("/{id}", status_code=204)
def delete_context(
    id: int,
    hard: bool = False,
    db: sqlite3.Connection = Depends(get_db),
) -> None:
    svc = AgentContextService(db)
    if svc.get(id) is None:
        raise HTTPException(status_code=404, detail="Context not found")
    svc.delete(id, hard=hard)
