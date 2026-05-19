from __future__ import annotations

import sqlite3
from typing import Any

from ..models.agents import Agent

_COLS = {
    "name": "Name",
    "surname": "Surname",
    "slug": "Slug",
    "summary": "Summary",
    "id_topic": "ID_topic",
    "created_by": "Created_by",
}


def _row(row: sqlite3.Row) -> Agent:
    return Agent(
        id=row["ID"],
        id_topic=row["ID_topic"],
        created_by=row["Created_by"],
        name=row["Name"],
        surname=row["Surname"],
        slug=row["Slug"],
        summary=row["Summary"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        deleted_at=row["deleted_at"],
    )


def create(db: sqlite3.Connection, data: dict[str, Any]) -> Agent:
    cur = db.execute(
        """
        INSERT INTO Agents (ID_topic, Created_by, Name, Surname, Slug, Summary)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            data.get("id_topic"),
            data.get("created_by"),
            data["name"],
            data["surname"],
            data["slug"],
            data.get("summary"),
        ),
    )
    db.commit()
    return get(db, cur.lastrowid)


def get(db: sqlite3.Connection, id: int) -> Agent | None:
    row = db.execute("SELECT * FROM Agents WHERE ID = ?", (id,)).fetchone()
    return _row(row) if row else None


def update(db: sqlite3.Connection, id: int, patch: dict[str, Any]) -> Agent:
    sets = [f"{_COLS[k]} = ?" for k in patch if k in _COLS]
    vals = [patch[k] for k in patch if k in _COLS]
    if sets:
        db.execute(f"UPDATE Agents SET {', '.join(sets)} WHERE ID = ?", (*vals, id))
        db.commit()
    return get(db, id)


def delete(db: sqlite3.Connection, id: int, hard: bool = False) -> None:
    if hard:
        db.execute("DELETE FROM Agents WHERE ID = ?", (id,))
    else:
        db.execute(
            "UPDATE Agents SET deleted_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE ID = ?",
            (id,),
        )
    db.commit()


def query(
    db: sqlite3.Connection,
    filters: dict[str, Any] | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[Agent]:
    clauses, params = ["deleted_at IS NULL"], []
    if filters:
        for key, col in _COLS.items():
            if key in filters:
                clauses.append(f"{col} = ?")
                params.append(filters[key])
    sql = f"SELECT * FROM Agents WHERE {' AND '.join(clauses)} LIMIT ? OFFSET ?"
    rows = db.execute(sql, [*params, limit, offset]).fetchall()
    return [_row(r) for r in rows]
