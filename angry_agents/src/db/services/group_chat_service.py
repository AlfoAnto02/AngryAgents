from __future__ import annotations

import sqlite3
from typing import Any

from ..models.group_chat import GroupChat
from ..repositories import group_chat_repository as repo


class GroupChatService:
    def __init__(self, db: sqlite3.Connection) -> None:
        self.db = db

    def create(self, id_topic: int, created_by: int | None = None) -> GroupChat:
        return repo.create(self.db, {"id_topic": id_topic, "created_by": created_by})

    def get(self, id: int) -> GroupChat | None:
        return repo.get(self.db, id)

    def update(self, id: int, patch: dict[str, Any]) -> GroupChat:
        return repo.update(self.db, id, patch)

    def delete(self, id: int, hard: bool = False) -> None:
        repo.delete(self.db, id, hard=hard)

    def query(
        self,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[GroupChat]:
        return repo.query(self.db, filters, limit, offset)
