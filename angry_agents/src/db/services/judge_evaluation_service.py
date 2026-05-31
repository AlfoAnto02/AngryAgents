from __future__ import annotations

import sqlite3
from typing import Any

from ..models.judge_evaluation import JudgeEvaluation
from ..repositories import judge_evaluation_repository as repo

MAX_EVALUATIONS_PER_CHAT = 20


class JudgeEvaluationService:
    def __init__(self, db: sqlite3.Connection) -> None:
        self.db = db

    def create(
        self,
        id_judge: int,
        id_chat: int,
        persona_identification: list[dict] | None = None,
        rag_candidates: list[str] | None = None,
    ) -> JudgeEvaluation:
        count = self.db.execute(
            "SELECT COUNT(*) FROM Judge_evaluation WHERE ID_chat = ? AND deleted_at IS NULL",
            (id_chat,),
        ).fetchone()[0]
        if count >= MAX_EVALUATIONS_PER_CHAT:
            raise ValueError(
                f"chat {id_chat} already has {MAX_EVALUATIONS_PER_CHAT} evaluations"
            )
        return repo.create(
            self.db,
            {
                "id_judge": id_judge,
                "id_chat": id_chat,
                "persona_identification": persona_identification,
                "rag_candidates": rag_candidates,
            },
        )

    def get(self, id_judge: int, id_chat: int) -> JudgeEvaluation | None:
        return repo.get(self.db, id_judge, id_chat)

    def update(
        self, id_judge: int, id_chat: int, patch: dict[str, Any]
    ) -> JudgeEvaluation:
        return repo.update(self.db, id_judge, id_chat, patch)

    def delete(self, id_judge: int, id_chat: int, hard: bool = False) -> None:
        repo.delete(self.db, id_judge, id_chat, hard=hard)

    def query(
        self,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[JudgeEvaluation]:
        return repo.query(self.db, filters, limit, offset)
