from __future__ import annotations

import sqlite3
from typing import Any

from ..models.group_chat import GroupChat

_COLS = {"id_topic": "ID_topic", "created_by": "Created_by"}


def _row(row: sqlite3.Row) -> GroupChat:
    return GroupChat(
        id=row["ID"],
        id_topic=row["ID_topic"],
        created_by=row["Created_by"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        deleted_at=row["deleted_at"],
    )


def create(db: sqlite3.Connection, data: dict[str, Any]) -> GroupChat:
    cur = db.execute(
        "INSERT INTO Group_chat (ID_topic, Created_by) VALUES (?, ?)",
        (data["id_topic"], data.get("created_by")),
    )
    db.commit()
    return get(db, cur.lastrowid)


def get(db: sqlite3.Connection, id: int) -> GroupChat | None:
    row = db.execute("SELECT * FROM Group_chat WHERE ID = ?", (id,)).fetchone()
    return _row(row) if row else None


def update(db: sqlite3.Connection, id: int, patch: dict[str, Any]) -> GroupChat:
    sets = [f"{_COLS[k]} = ?" for k in patch if k in _COLS]
    vals = [patch[k] for k in patch if k in _COLS]
    if sets:
        db.execute(
            f"UPDATE Group_chat SET {', '.join(sets)} WHERE ID = ?", (*vals, id)
        )
        db.commit()
    return get(db, id)


def delete(db: sqlite3.Connection, id: int, hard: bool = False) -> None:
    if hard:
        db.execute("DELETE FROM Group_chat WHERE ID = ?", (id,))
    else:
        db.execute(
            "UPDATE Group_chat SET deleted_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE ID = ?",
            (id,),
        )
    db.commit()


def query(
    db: sqlite3.Connection,
    filters: dict[str, Any] | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[GroupChat]:
    clauses, params = ["deleted_at IS NULL"], []
    if filters:
        for key, col in _COLS.items():
            if key in filters:
                clauses.append(f"{col} = ?")
                params.append(filters[key])
    sql = f"SELECT * FROM Group_chat WHERE {' AND '.join(clauses)} LIMIT ? OFFSET ?"
    rows = db.execute(sql, [*params, limit, offset]).fetchall()
    return [_row(r) for r in rows]
