from __future__ import annotations

import sqlite3
from typing import Any

from ..models.user import User

_COLS = {
    "username": "Username",
    "name": "Name",
    "surname": "Surname",
    "role": "Role",
    "email": "Email",
    "slug": "Slug",
    "password": "Password",
}


def _row(row: sqlite3.Row) -> User:
    return User(
        id=row["ID"],
        username=row["Username"],
        password=row["Password"],
        name=row["Name"],
        surname=row["Surname"],
        role=row["Role"],
        email=row["Email"],
        slug=row["Slug"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        deleted_at=row["deleted_at"],
    )


def create(db: sqlite3.Connection, data: dict[str, Any]) -> User:
    cur = db.execute(
        """
        INSERT INTO User (Username, Password, Name, Surname, Role, Email, Slug)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data["username"],
            data["password"],
            data["name"],
            data["surname"],
            data.get("role", "common"),
            data["email"],
            data["slug"],
        ),
    )
    db.commit()
    return get(db, cur.lastrowid)


def get(db: sqlite3.Connection, id: int) -> User | None:
    row = db.execute("SELECT * FROM User WHERE ID = ?", (id,)).fetchone()
    return _row(row) if row else None


def get_by_slug(db: sqlite3.Connection, slug: str) -> User | None:
    row = db.execute(
        "SELECT * FROM User WHERE Slug = ? AND deleted_at IS NULL", (slug,)
    ).fetchone()
    return _row(row) if row else None


def get_by_email(db: sqlite3.Connection, email: str) -> User | None:
    row = db.execute(
        "SELECT * FROM User WHERE Email = ? AND deleted_at IS NULL", (email,)
    ).fetchone()
    return _row(row) if row else None


def get_by_username(db: sqlite3.Connection, username: str) -> User | None:
    row = db.execute(
        "SELECT * FROM User WHERE Username = ? AND deleted_at IS NULL", (username,)
    ).fetchone()
    return _row(row) if row else None


def update(db: sqlite3.Connection, id: int, patch: dict[str, Any]) -> User:
    sets = [f"{_COLS[k]} = ?" for k in patch if k in _COLS]
    vals = [patch[k] for k in patch if k in _COLS]
    if sets:
        db.execute(
            f"UPDATE User SET {', '.join(sets)} WHERE ID = ?", (*vals, id)
        )
        db.commit()
    return get(db, id)


def delete(db: sqlite3.Connection, id: int, hard: bool = False) -> None:
    if hard:
        db.execute("DELETE FROM User WHERE ID = ?", (id,))
    else:
        db.execute(
            "UPDATE User SET deleted_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE ID = ?",
            (id,),
        )
    db.commit()


def query(
    db: sqlite3.Connection,
    filters: dict[str, Any] | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[User]:
    clauses, params = ["deleted_at IS NULL"], []
    if filters:
        for key, col in _COLS.items():
            if key in filters:
                clauses.append(f"{col} = ?")
                params.append(filters[key])
    sql = f"SELECT * FROM User WHERE {' AND '.join(clauses)} LIMIT ? OFFSET ?"
    rows = db.execute(sql, [*params, limit, offset]).fetchall()
    return [_row(r) for r in rows]
