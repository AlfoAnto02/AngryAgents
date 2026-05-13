from __future__ import annotations

import hashlib
import hmac
import sqlite3
from typing import Any

from ..models.chat_messages import ChatMessage
from ..repositories import chat_messages as repo

# author = "{name} {surname} {digest}"
# The digest lets judges distinguish sources without knowing the real agent identity.


def _make_author(name: str, surname: str, secret: str) -> str:
    digest = hmac.new(
        secret.encode(),
        f"{name}:{surname}".encode(),
        hashlib.sha256,
    ).hexdigest()[:12]
    return f"{name} {surname} {digest}"


class ChatMessageService:
    def __init__(self, db: sqlite3.Connection, author_secret: str) -> None:
        self.db = db
        self._secret = author_secret

    def create(
        self,
        id_chat: int,
        message: str,
        agent_name: str,
        agent_surname: str,
    ) -> ChatMessage:
        author = _make_author(agent_name, agent_surname, self._secret)
        return repo.create(
            self.db,
            {"id_chat": id_chat, "message": message, "author": author},
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
