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


def _to_persona_identification(result: PersonaIdentificationResult) -> list[dict]:
    """
    Convert author-centric AuthorMatch list to the persona-centric format
    expected by metrics_persona_id.py and metrics_fidelity.py:

      [{persona_name, predicted, scores: [{author, score}]}]

    Input (base_judge):  per author → scores for each persona
    Output (metrics):    per persona → scores from each author
    """
    persona_scores: dict[str, list[dict]] = {}
    for match in result.matches:
        for ps in match.scores:
            persona_scores.setdefault(ps.persona_name, []).append(
                {"author": match.author, "score": ps.score}
            )
    return [
        {
            "persona_name": persona_name,
            "predicted": max(scores, key=lambda x: x["score"])["author"],
            "scores": scores,
        }
        for persona_name, scores in persona_scores.items()
    ]


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
    - Creates or updates a Judge_evaluation row with the full persona_identification
      output (persona-centric format consumed by metrics modules).
    - Returns the full PersonaIdentificationResult for the caller to inspect or log.

    Raises ValueError if chat_id already has 20 active evaluations.
    """
    result = judge.persona_identification(chat, personas)

    JudgeService(db).update(judge_db_id, {"guess": _top_predicted(result)})

    pi = _to_persona_identification(result)
    svc = JudgeEvaluationService(db)
    if svc.get(judge_db_id, chat_id) is None:
        svc.create(judge_db_id, chat_id, persona_identification=pi)
    else:
        svc.update(judge_db_id, chat_id, {"persona_identification": pi})

    return result
