from __future__ import annotations

import dataclasses
import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ...db.services import GroupChatService
from ..deps import get_db
from ..schemas import GroupChatOut

router = APIRouter()


class ChatCreate(BaseModel):
    id_topic: int = Field(..., description="Topic this chat belongs to")
    created_by: int | None = Field(None, description="FK to User.ID")


class ChatPatch(BaseModel):
    id_topic: int | None = None
    status: str | None = None


def _out(obj) -> dict:
    return dataclasses.asdict(obj)


@router.get("", response_model=list[GroupChatOut], summary="List group chats")
def list_chats(
    id_topic: int | None = Query(None, description="Filter by topic ID"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: sqlite3.Connection = Depends(get_db),
) -> list:
    filters = {"id_topic": id_topic} if id_topic is not None else None
    return [_out(c) for c in GroupChatService(db).query(filters=filters, limit=limit, offset=offset)]


@router.post("", response_model=GroupChatOut, status_code=201, summary="Create a group chat")
def create_chat(body: ChatCreate, db: sqlite3.Connection = Depends(get_db)) -> dict:
    return _out(GroupChatService(db).create(id_topic=body.id_topic, created_by=body.created_by))


@router.get("/{id}", response_model=GroupChatOut, summary="Get a group chat by ID")
def get_chat(id: int, db: sqlite3.Connection = Depends(get_db)) -> dict:
    chat = GroupChatService(db).get(id)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    return _out(chat)


@router.patch("/{id}", response_model=GroupChatOut, summary="Partially update a group chat")
def update_chat(id: int, body: ChatPatch, db: sqlite3.Connection = Depends(get_db)) -> dict:
    svc = GroupChatService(db)
    if svc.get(id) is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    return _out(svc.update(id, body.model_dump(exclude_unset=True)))


@router.delete("/{id}", status_code=204, summary="Soft-delete a chat (hard=true for permanent)")
def delete_chat(
    id: int,
    hard: bool = Query(False, description="Set true for permanent deletion"),
    db: sqlite3.Connection = Depends(get_db),
) -> None:
    svc = GroupChatService(db)
    if svc.get(id) is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    svc.delete(id, hard=hard)
