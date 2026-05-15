from __future__ import annotations

import sqlite3
from typing import Any

from ..models.agent_context import AgentContext
from ..repositories import agent_context_repository as repo


class AgentContextService:
    def __init__(self, db: sqlite3.Connection) -> None:
        self.db = db

    def create(
        self,
        id_agent: int,
        signature_phrases: str | None = None,
    ) -> AgentContext:
        return repo.create(
            self.db,
            {"id_agent": id_agent, "signature_phrases": signature_phrases},
        )

    def get(self, id: int) -> AgentContext | None:
        return repo.get(self.db, id)

    def update(self, id: int, patch: dict[str, Any]) -> AgentContext:
        return repo.update(self.db, id, patch)

    def delete(self, id: int, hard: bool = False) -> None:
        repo.delete(self.db, id, hard=hard)

    def query(
        self,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[AgentContext]:
        return repo.query(self.db, filters, limit, offset)
