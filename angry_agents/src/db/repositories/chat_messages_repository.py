from __future__ import annotations

import sqlite3
from typing import Any

from ..models.chat_messages import ChatMessage

_COLS = {"id_chat": "ID_Chat", "author": "author", "created_by": "Created_by"}


def _row(row: sqlite3.Row) -> ChatMessage:
    return ChatMessage(
        id=row["ID"],
        id_chat=row["ID_Chat"],
        message=row["message"],
        author=row["author"],
        created_by=row["Created_by"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        deleted_at=row["deleted_at"],
    )


def create(db: sqlite3.Connection, data: dict[str, Any]) -> ChatMessage:
    cur = db.execute(
        "INSERT INTO Chat_messages (ID_Chat, message, author, Created_by) VALUES (?, ?, ?, ?)",
        (data["id_chat"], data["message"], data.get("author"), data.get("created_by")),
    )
    db.commit()
    return get(db, cur.lastrowid)


def get(db: sqlite3.Connection, id: int) -> ChatMessage | None:
    row = db.execute("SELECT * FROM Chat_messages WHERE ID = ?", (id,)).fetchone()
    return _row(row) if row else None


def update(db: sqlite3.Connection, id: int, patch: dict[str, Any]) -> ChatMessage:
    editable = {"message": "message"}
    sets = [f"{editable[k]} = ?" for k in patch if k in editable]
    vals = [patch[k] for k in patch if k in editable]
    if sets:
        db.execute(
            f"UPDATE Chat_messages SET {', '.join(sets)} WHERE ID = ?", (*vals, id)
        )
        db.commit()
    return get(db, id)


def delete(db: sqlite3.Connection, id: int, hard: bool = False) -> None:
    if hard:
        db.execute("DELETE FROM Chat_messages WHERE ID = ?", (id,))
    else:
        db.execute(
            "UPDATE Chat_messages SET deleted_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE ID = ?",
            (id,),
        )
    db.commit()


def query(
    db: sqlite3.Connection,
    filters: dict[str, Any] | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[ChatMessage]:
    clauses, params = ["deleted_at IS NULL"], []
    if filters:
        for key, col in _COLS.items():
            if key in filters:
                clauses.append(f"{col} = ?")
                params.append(filters[key])
    sql = f"SELECT * FROM Chat_messages WHERE {' AND '.join(clauses)} ORDER BY ID ASC LIMIT ? OFFSET ?"
    rows = db.execute(sql, [*params, limit, offset]).fetchall()
    return [_row(r) for r in rows]
