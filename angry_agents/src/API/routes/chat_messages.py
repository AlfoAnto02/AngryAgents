from __future__ import annotations

import dataclasses
import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from ...db.services import ChatMessageService
from ..config import Settings, get_settings
from ..deps import get_db
from ..schemas import ChatMessageOut

router = APIRouter()


class MessageCreate(BaseModel):
    agent_name: str = Field(..., description="Real agent first name (used to compute anonymised author token)")
    agent_surname: str = Field(..., description="Real agent surname (used to compute anonymised author token)")
    message: str


class MessagePatch(BaseModel):
    message: str | None = None


def _svc(db: sqlite3.Connection, settings: Settings) -> ChatMessageService:
    return ChatMessageService(db, settings.author_secret)


def _out(obj) -> dict:
    return dataclasses.asdict(obj)


@router.get(
    "/chats/{chat_id}/messages",
    response_model=list[ChatMessageOut],
    summary="List messages in a chat",
)
def list_messages(
    chat_id: int,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: sqlite3.Connection = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> list:
    return [
        _out(m)
        for m in _svc(db, settings).query(
            filters={"id_chat": chat_id}, limit=limit, offset=offset
        )
    ]


@router.post(
    "/chats/{chat_id}/messages",
    response_model=ChatMessageOut,
    status_code=201,
    summary="Post a message to a chat",
    description=(
        "The `author` field in the response is an anonymised HMAC token. "
        "Judges see it for source-diversity tracking but cannot identify the real agent."
    ),
)
def create_message(
    chat_id: int,
    body: MessageCreate,
    db: sqlite3.Connection = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    return _out(
        _svc(db, settings).create(
            id_chat=chat_id,
            message=body.message,
            agent_name=body.agent_name,
            agent_surname=body.agent_surname,
        )
    )


@router.get("/messages/{id}", response_model=ChatMessageOut, summary="Get a message by ID")
def get_message(
    id: int,
    db: sqlite3.Connection = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    msg = _svc(db, settings).get(id)
    if msg is None:
        raise HTTPException(status_code=404, detail="Message not found")
    return _out(msg)


@router.patch("/messages/{id}", response_model=ChatMessageOut, summary="Update message text")
def update_message(
    id: int,
    body: MessagePatch,
    db: sqlite3.Connection = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    svc = _svc(db, settings)
    if svc.get(id) is None:
        raise HTTPException(status_code=404, detail="Message not found")
    return _out(svc.update(id, body.model_dump(exclude_unset=True)))


@router.delete("/messages/{id}", status_code=204, summary="Soft-delete a message (hard=true for permanent)")
def delete_message(
    id: int,
    hard: bool = Query(False, description="Set true for permanent deletion"),
    db: sqlite3.Connection = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> None:
    svc = _svc(db, settings)
    if svc.get(id) is None:
        raise HTTPException(status_code=404, detail="Message not found")
    svc.delete(id, hard=hard)
