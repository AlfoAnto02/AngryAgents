from __future__ import annotations

import dataclasses
import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ...db.services import AgentContextService
from ..deps import get_db
from ..schemas import AgentContextOut

router = APIRouter()


class ContextCreate(BaseModel):
    id_agent: int = Field(..., description="Parent agent ID")
    signature_phrases: str | None = Field(None, description="JSON-encoded list of signature phrases")


class ContextPatch(BaseModel):
    signature_phrases: str | None = None


def _out(obj) -> dict:
    return dataclasses.asdict(obj)


@router.get("", response_model=list[AgentContextOut], summary="List agent contexts")
def list_contexts(
    id_agent: int | None = Query(None, description="Filter by agent ID"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: sqlite3.Connection = Depends(get_db),
) -> list:
    filters = {"id_agent": id_agent} if id_agent is not None else None
    return [_out(c) for c in AgentContextService(db).query(filters=filters, limit=limit, offset=offset)]


@router.post("", response_model=AgentContextOut, status_code=201, summary="Create an agent context")
def create_context(body: ContextCreate, db: sqlite3.Connection = Depends(get_db)) -> dict:
    return _out(
        AgentContextService(db).create(
            id_agent=body.id_agent,
            signature_phrases=body.signature_phrases,
        )
    )


@router.get("/{id}", response_model=AgentContextOut, summary="Get an agent context by ID")
def get_context(id: int, db: sqlite3.Connection = Depends(get_db)) -> dict:
    ctx = AgentContextService(db).get(id)
    if ctx is None:
        raise HTTPException(status_code=404, detail="Context not found")
    return _out(ctx)


@router.patch("/{id}", response_model=AgentContextOut, summary="Partially update an agent context")
def update_context(id: int, body: ContextPatch, db: sqlite3.Connection = Depends(get_db)) -> dict:
    svc = AgentContextService(db)
    if svc.get(id) is None:
        raise HTTPException(status_code=404, detail="Context not found")
    return _out(svc.update(id, body.model_dump(exclude_unset=True)))


@router.delete("/{id}", status_code=204, summary="Soft-delete a context (hard=true for permanent)")
def delete_context(
    id: int,
    hard: bool = Query(False, description="Set true for permanent deletion"),
    db: sqlite3.Connection = Depends(get_db),
) -> None:
    svc = AgentContextService(db)
    if svc.get(id) is None:
        raise HTTPException(status_code=404, detail="Context not found")
    svc.delete(id, hard=hard)
