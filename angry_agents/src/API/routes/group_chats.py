from __future__ import annotations

import dataclasses
import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ...db.services import GroupChatService
from ..deps import get_db

router = APIRouter()


class ChatCreate(BaseModel):
    id_topic: int


class ChatPatch(BaseModel):
    id_topic: int | None = None


def _out(obj) -> dict:
    return dataclasses.asdict(obj)


@router.get("")
def list_chats(
    id_topic: int | None = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: sqlite3.Connection = Depends(get_db),
) -> list:
    filters = {"id_topic": id_topic} if id_topic is not None else None
    return [_out(c) for c in GroupChatService(db).query(filters=filters, limit=limit, offset=offset)]


@router.post("", status_code=201)
def create_chat(body: ChatCreate, db: sqlite3.Connection = Depends(get_db)) -> dict:
    return _out(GroupChatService(db).create(id_topic=body.id_topic))


@router.get("/{id}")
def get_chat(id: int, db: sqlite3.Connection = Depends(get_db)) -> dict:
    chat = GroupChatService(db).get(id)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    return _out(chat)


@router.patch("/{id}")
def update_chat(id: int, body: ChatPatch, db: sqlite3.Connection = Depends(get_db)) -> dict:
    svc = GroupChatService(db)
    if svc.get(id) is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    return _out(svc.update(id, body.model_dump(exclude_unset=True)))


@router.delete("/{id}", status_code=204)
def delete_chat(
    id: int,
    hard: bool = False,
    db: sqlite3.Connection = Depends(get_db),
) -> None:
    svc = GroupChatService(db)
    if svc.get(id) is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    svc.delete(id, hard=hard)
