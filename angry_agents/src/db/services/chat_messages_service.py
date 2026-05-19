from __future__ import annotations

import hashlib
import hmac
import sqlite3
from typing import Any

from ..models.chat_messages import ChatMessage
from ..repositories import agents_repository as agents_repo
from ..repositories import chat_messages_repository as repo

# author = "{name} {surname} {digest}"
# The digest lets judges distinguish sources without knowing the real agent identity.
# Name and surname are always fetched from the DB — never trusted from the caller.


def _make_author(name: str, surname: str, secret: str) -> str:
    return hmac.new(
        secret.encode(),
        f"{name}:{surname}".encode(),
        hashlib.sha256,
    ).hexdigest()


class ChatMessageService:
    def __init__(self, db: sqlite3.Connection, author_secret: str) -> None:
        self.db = db
        self._secret = author_secret

    def create(
        self,
        id_chat: int,
        message: str,
        agent_id: int | None = None,
        created_by: int | None = None,
    ) -> ChatMessage:
        author: str | None = None
        if agent_id is not None:
            agent = agents_repo.get(self.db, agent_id)
            if agent is None:
                raise ValueError(f"Agent {agent_id} not found")
            author = _make_author(agent.name, agent.surname, self._secret)
        return repo.create(
            self.db,
            {"id_chat": id_chat, "message": message, "author": author, "created_by": created_by},
        )

    def get(self, id: int) -> ChatMessage | None:
        return repo.get(self.db, id)

    def update(self, id: int, patch: dict[str, Any]) -> ChatMessage:
        return repo.update(self.db, id, patch)

    def delete(self, id: int, hard: bool = False) -> None:
        repo.delete(self.db, id, hard=hard)

    def query(
        self,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ChatMessage]:
        return repo.query(self.db, filters, limit, offset)
