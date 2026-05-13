from __future__ import annotations

import re
import sqlite3
from typing import Any

from ..models.agents import Agent
from ..repositories import agents as repo


def _make_slug(db: sqlite3.Connection, name: str, surname: str) -> str:
    base = re.sub(r"[^a-z0-9-]", "", f"{name}-{surname}".lower())
    slug, n = base, 2
    while db.execute("SELECT 1 FROM Agents WHERE Slug = ?", (slug,)).fetchone():
        slug = f"{base}-{n}"
        n += 1
    return slug


class AgentService:
    def __init__(self, db: sqlite3.Connection) -> None:
        self.db = db

    def create(
        self,
        name: str,
        surname: str,
        id_topic: int | None = None,
        summary: str | None = None,
    ) -> Agent:
        slug = _make_slug(self.db, name, surname)
        return repo.create(
            self.db,
            {"name": name, "surname": surname, "slug": slug, "id_topic": id_topic, "summary": summary},
        )

    def get(self, id: int) -> Agent | None:
        return repo.get(self.db, id)

    def get_by_slug(self, slug: str) -> Agent | None:
        row = self.db.execute(
            "SELECT * FROM Agents WHERE Slug = ? AND deleted_at IS NULL", (slug,)
        ).fetchone()
        if row is None:
            return None
        return Agent(
            id=row["ID"],
            id_topic=row["ID_topic"],
            name=row["Name"],
            surname=row["Surname"],
            slug=row["Slug"],
            summary=row["Summary"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            deleted_at=row["deleted_at"],
        )

    def update(self, id: int, patch: dict[str, Any]) -> Agent:
        return repo.update(self.db, id, patch)

    def delete(self, id: int, hard: bool = False) -> None:
        repo.delete(self.db, id, hard=hard)

    def query(
        self,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Agent]:
        return repo.query(self.db, filters, limit, offset)
