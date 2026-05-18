from __future__ import annotations

import dataclasses
import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ...db.services import TopicService
from ..deps import get_db

router = APIRouter()


class TopicCreate(BaseModel):
    title: str
    description: str | None = None


class TopicPatch(BaseModel):
    title: str | None = None
    description: str | None = None


def _out(obj) -> dict:
    return dataclasses.asdict(obj)


@router.get("")
def list_topics(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: sqlite3.Connection = Depends(get_db),
) -> list:
    return [_out(t) for t in TopicService(db).query(limit=limit, offset=offset)]


@router.post("", status_code=201)
def create_topic(body: TopicCreate, db: sqlite3.Connection = Depends(get_db)) -> dict:
    return _out(TopicService(db).create(title=body.title, description=body.description))


@router.get("/{id}")
def get_topic(id: int, db: sqlite3.Connection = Depends(get_db)) -> dict:
    topic = TopicService(db).get(id)
    if topic is None:
        raise HTTPException(status_code=404, detail="Topic not found")
    return _out(topic)


@router.patch("/{id}")
def update_topic(id: int, body: TopicPatch, db: sqlite3.Connection = Depends(get_db)) -> dict:
    svc = TopicService(db)
    if svc.get(id) is None:
        raise HTTPException(status_code=404, detail="Topic not found")
    return _out(svc.update(id, body.model_dump(exclude_unset=True)))


@router.delete("/{id}", status_code=204)
def delete_topic(
    id: int,
    hard: bool = False,
    db: sqlite3.Connection = Depends(get_db),
) -> None:
    svc = TopicService(db)
    if svc.get(id) is None:
        raise HTTPException(status_code=404, detail="Topic not found")
    svc.delete(id, hard=hard)
