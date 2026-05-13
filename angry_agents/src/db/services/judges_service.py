from __future__ import annotations

import sqlite3
from typing import Any

from ..models.judges import Judge
from ..models.roles import JudgeRole
from ..repositories import judges as repo


class JudgeService:
    def __init__(self, db: sqlite3.Connection) -> None:
        self.db = db

    def create(
        self,
        role: str,
        temperature: float | None = None,
        guess: str | None = None,
    ) -> Judge:
        JudgeRole(role)  # raises ValueError if role is not one of the 4 valid values
        return repo.create(
            self.db,
            {"role": role, "temperature": temperature, "guess": guess},
        )

    def get(self, id: int) -> Judge | None:
        return repo.get(self.db, id)

    def update(self, id: int, patch: dict[str, Any]) -> Judge:
        if "role" in patch:
            JudgeRole(patch["role"])
        return repo.update(self.db, id, patch)

    def delete(self, id: int, hard: bool = False) -> None:
        repo.delete(self.db, id, hard=hard)

    def query(
        self,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Judge]:
        return repo.query(self.db, filters, limit, offset)
