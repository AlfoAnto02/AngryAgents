from __future__ import annotations

import sqlite3
from typing import Any

from ..models.agent_context import AgentContext

_COLS = {
    "id_agent": "ID_agent",
    "signature_phrases": "Signature_phrases",
}


def _row(row: sqlite3.Row) -> AgentContext:
    return AgentContext(
        id_context=row["ID_context"],
        id_agent=row["ID_agent"],
        signature_phrases=row["Signature_phrases"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        deleted_at=row["deleted_at"],
    )


def create(db: sqlite3.Connection, data: dict[str, Any]) -> AgentContext:
    cur = db.execute(
        "INSERT INTO Agent_context (ID_agent, Signature_phrases) VALUES (?, ?)",
        (data["id_agent"], data.get("signature_phrases")),
    )
    db.commit()
    return get(db, cur.lastrowid)


def get(db: sqlite3.Connection, id: int) -> AgentContext | None:
    row = db.execute(
        "SELECT * FROM Agent_context WHERE ID_context = ?", (id,)
    ).fetchone()
    return _row(row) if row else None


def update(db: sqlite3.Connection, id: int, patch: dict[str, Any]) -> AgentContext:
    sets = [f"{_COLS[k]} = ?" for k in patch if k in _COLS]
    vals = [patch[k] for k in patch if k in _COLS]
    if sets:
        db.execute(
            f"UPDATE Agent_context SET {', '.join(sets)} WHERE ID_context = ?",
            (*vals, id),
        )
        db.commit()
    return get(db, id)


def delete(db: sqlite3.Connection, id: int, hard: bool = False) -> None:
    if hard:
        db.execute("DELETE FROM Agent_context WHERE ID_context = ?", (id,))
    else:
        db.execute(
            "UPDATE Agent_context SET deleted_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE ID_context = ?",
            (id,),
        )
    db.commit()


def query(
    db: sqlite3.Connection,
    filters: dict[str, Any] | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[AgentContext]:
    clauses, params = ["deleted_at IS NULL"], []
    if filters:
        for key, col in _COLS.items():
            if key in filters:
                clauses.append(f"{col} = ?")
                params.append(filters[key])
    sql = f"SELECT * FROM Agent_context WHERE {' AND '.join(clauses)} LIMIT ? OFFSET ?"
    rows = db.execute(sql, [*params, limit, offset]).fetchall()
    return [_row(r) for r in rows]
