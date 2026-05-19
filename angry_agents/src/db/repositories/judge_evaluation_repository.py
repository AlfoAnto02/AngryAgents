from __future__ import annotations

import json
import sqlite3
from typing import Any

from ..models.judge_evaluation import JudgeEvaluation

# Composite PK: (ID_judge, ID_chat). get/update/delete take both keys.

_COLS = {"score": "Score"}


def _row(row: sqlite3.Row) -> JudgeEvaluation:
    raw = row["Score"]
    return JudgeEvaluation(
        id_judge=row["ID_judge"],
        id_chat=row["ID_chat"],
        score=json.loads(raw) if raw is not None else None,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        deleted_at=row["deleted_at"],
    )


def create(db: sqlite3.Connection, data: dict[str, Any]) -> JudgeEvaluation:
    db.execute(
        "INSERT INTO Judge_evaluation (ID_judge, ID_chat, Score) VALUES (?, ?, ?)",
        (data["id_judge"], data["id_chat"], json.dumps(data["score"]) if data.get("score") is not None else None),
    )
    db.commit()
    return get(db, data["id_judge"], data["id_chat"])


def get(
    db: sqlite3.Connection, id_judge: int, id_chat: int
) -> JudgeEvaluation | None:
    row = db.execute(
        "SELECT * FROM Judge_evaluation WHERE ID_judge = ? AND ID_chat = ?",
        (id_judge, id_chat),
    ).fetchone()
    return _row(row) if row else None


def update(
    db: sqlite3.Connection, id_judge: int, id_chat: int, patch: dict[str, Any]
) -> JudgeEvaluation:
    sets = [f"{_COLS[k]} = ?" for k in patch if k in _COLS]
    vals = [
        json.dumps(patch[k]) if k == "score" and patch[k] is not None else patch[k]
        for k in patch if k in _COLS
    ]
    if sets:
        db.execute(
            f"UPDATE Judge_evaluation SET {', '.join(sets)} WHERE ID_judge = ? AND ID_chat = ?",
            (*vals, id_judge, id_chat),
        )
        db.commit()
    return get(db, id_judge, id_chat)


def delete(
    db: sqlite3.Connection, id_judge: int, id_chat: int, hard: bool = False
) -> None:
    if hard:
        db.execute(
            "DELETE FROM Judge_evaluation WHERE ID_judge = ? AND ID_chat = ?",
            (id_judge, id_chat),
        )
    else:
        db.execute(
            "UPDATE Judge_evaluation SET deleted_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE ID_judge = ? AND ID_chat = ?",
            (id_judge, id_chat),
        )
    db.commit()


def query(
    db: sqlite3.Connection,
    filters: dict[str, Any] | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[JudgeEvaluation]:
    clauses, params = ["deleted_at IS NULL"], []
    if filters:
        if "id_judge" in filters:
            clauses.append("ID_judge = ?")
            params.append(filters["id_judge"])
        if "id_chat" in filters:
            clauses.append("ID_chat = ?")
            params.append(filters["id_chat"])
    sql = f"SELECT * FROM Judge_evaluation WHERE {' AND '.join(clauses)} LIMIT ? OFFSET ?"
    rows = db.execute(sql, [*params, limit, offset]).fetchall()
    return [_row(r) for r in rows]
