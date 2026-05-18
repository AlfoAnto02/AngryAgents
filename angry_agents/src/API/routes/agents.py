from __future__ import annotations

import dataclasses
import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ...db.services import AgentService
from ..deps import get_db

router = APIRouter()


class AgentCreate(BaseModel):
    name: str
    surname: str
    id_topic: int | None = None
    summary: str | None = None


class AgentPatch(BaseModel):
    name: str | None = None
    surname: str | None = None
    id_topic: int | None = None
    summary: str | None = None


def _out(obj) -> dict:
    return dataclasses.asdict(obj)


# /agents/slug/{slug} must be declared before /{id} to avoid routing conflict
@router.get("/slug/{slug}")
def get_agent_by_slug(slug: str, db: sqlite3.Connection = Depends(get_db)) -> dict:
    agent = AgentService(db).get_by_slug(slug)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return _out(agent)


@router.get("")
def list_agents(
    id_topic: int | None = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: sqlite3.Connection = Depends(get_db),
) -> list:
    filters = {"id_topic": id_topic} if id_topic is not None else None
    return [_out(a) for a in AgentService(db).query(filters=filters, limit=limit, offset=offset)]


@router.post("", status_code=201)
def create_agent(body: AgentCreate, db: sqlite3.Connection = Depends(get_db)) -> dict:
    return _out(
        AgentService(db).create(
            name=body.name,
            surname=body.surname,
            id_topic=body.id_topic,
            summary=body.summary,
        )
    )


@router.get("/{id}")
def get_agent(id: int, db: sqlite3.Connection = Depends(get_db)) -> dict:
    agent = AgentService(db).get(id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return _out(agent)


@router.patch("/{id}")
def update_agent(id: int, body: AgentPatch, db: sqlite3.Connection = Depends(get_db)) -> dict:
    svc = AgentService(db)
    if svc.get(id) is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return _out(svc.update(id, body.model_dump(exclude_unset=True)))


@router.delete("/{id}", status_code=204)
def delete_agent(
    id: int,
    hard: bool = False,
    db: sqlite3.Connection = Depends(get_db),
) -> None:
    svc = AgentService(db)
    if svc.get(id) is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    svc.delete(id, hard=hard)
