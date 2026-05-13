from __future__ import annotations

import sqlite3
from typing import Any

from ..models.judges import Judge

_COLS = {"role": "Role", "temperature": "Temperature", "guess": "Guess"}


def _row(row: sqlite3.Row) -> Judge:
    return Judge(
        id=row["ID"],
        role=row["Role"],
        temperature=row["Temperature"],
        guess=row["Guess"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        deleted_at=row["deleted_at"],
    )


def create(db: sqlite3.Connection, data: dict[str, Any]) -> Judge:
    cur = db.execute(
        "INSERT INTO Judges (Role, Temperature, Guess) VALUES (?, ?, ?)",
        (data["role"], data.get("temperature"), data.get("guess")),
    )
    db.commit()
    return get(db, cur.lastrowid)


def get(db: sqlite3.Connection, id: int) -> Judge | None:
    row = db.execute("SELECT * FROM Judges WHERE ID = ?", (id,)).fetchone()
    return _row(row) if row else None


def update(db: sqlite3.Connection, id: int, patch: dict[str, Any]) -> Judge:
    sets = [f"{_COLS[k]} = ?" for k in patch if k in _COLS]
    vals = [patch[k] for k in patch if k in _COLS]
    if sets:
        db.execute(f"UPDATE Judges SET {', '.join(sets)} WHERE ID = ?", (*vals, id))
        db.commit()
    return get(db, id)


def delete(db: sqlite3.Connection, id: int, hard: bool = False) -> None:
    if hard:
        db.execute("DELETE FROM Judges WHERE ID = ?", (id,))
    else:
        db.execute(
            "UPDATE Judges SET deleted_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE ID = ?",
            (id,),
        )
    db.commit()


def query(
    db: sqlite3.Connection,
    filters: dict[str, Any] | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Judge]:
    clauses, params = ["deleted_at IS NULL"], []
    if filters:
        for key, col in _COLS.items():
            if key in filters:
                clauses.append(f"{col} = ?")
                params.append(filters[key])
    sql = f"SELECT * FROM Judges WHERE {' AND '.join(clauses)} LIMIT ? OFFSET ?"
    rows = db.execute(sql, [*params, limit, offset]).fetchall()
    return [_row(r) for r in rows]
