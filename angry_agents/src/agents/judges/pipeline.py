from __future__ import annotations

import sqlite3
from collections import Counter

from ...db.services.judge_evaluation_service import JudgeEvaluationService
from ...db.services.judges_service import JudgeService
from .base_judge import BaseJudge, PersonaIdentificationResult


def _top_predicted(result: PersonaIdentificationResult) -> str | None:
    """Most frequently predicted persona across all author matches in this result."""
    predictions = [m.predicted for m in result.matches if m.scores]
    if not predictions:
        return None
    return Counter(predictions).most_common(1)[0][0]


def run_and_persist(
    db: sqlite3.Connection,
    judge_db_id: int,
    chat_id: int,
    judge: BaseJudge,
    chat: dict,
    personas: list[dict],
) -> PersonaIdentificationResult:
    """
    Run persona identification for one judge and persist results to the DB.

    - Calls judge.persona_identification(chat, personas).
    - Writes the top predicted persona to Judges.Guess.
    - Creates a Judge_evaluation row (score=None until fidelity methods are implemented).
    - Returns the full PersonaIdentificationResult for the caller to inspect or log.

    Raises ValueError if chat_id already has 20 active evaluations.
    """
    result = judge.persona_identification(chat, personas)

    JudgeService(db).update(judge_db_id, {"guess": _top_predicted(result)})

    svc = JudgeEvaluationService(db)
    if svc.get(judge_db_id, chat_id) is None:
        svc.create(judge_db_id, chat_id)

    return result
