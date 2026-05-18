from __future__ import annotations

import sqlite3
from typing import Any

from ..models.topic import Topic
from ..repositories import topic_repository as repo


class TopicService:
    def __init__(self, db: sqlite3.Connection) -> None:
        self.db = db

    def create(self, title: str, description: str | None = None) -> Topic:
        return repo.create(self.db, {"title": title, "description": description})

    def get(self, id: int) -> Topic | None:
        return repo.get(self.db, id)

    def update(self, id: int, patch: dict[str, Any]) -> Topic:
        return repo.update(self.db, id, patch)

    def delete(self, id: int, hard: bool = False) -> None:
        repo.delete(self.db, id, hard=hard)

    def query(
        self,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Topic]:
        return repo.query(self.db, filters, limit, offset)
