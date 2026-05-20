from __future__ import annotations

import sqlite3

from ..models.refresh_token import RefreshToken


def create(
    db: sqlite3.Connection,
    user_id: int,
    token_hash: str,
    expires_at: str,
) -> RefreshToken:
    db.execute(
        "INSERT INTO RefreshToken (User_ID, Token_Hash, Expires_At) VALUES (?, ?, ?)",
        (user_id, token_hash, expires_at),
    )
    db.commit()
    row = db.execute(
        "SELECT * FROM RefreshToken WHERE Token_Hash = ?", (token_hash,)
    ).fetchone()
    return _from_row(row)


def get_by_hash(db: sqlite3.Connection, token_hash: str) -> RefreshToken | None:
    row = db.execute(
        "SELECT * FROM RefreshToken WHERE Token_Hash = ?", (token_hash,)
    ).fetchone()
    return _from_row(row) if row else None


def revoke(db: sqlite3.Connection, token_hash: str) -> None:
    db.execute(
        "UPDATE RefreshToken"
        " SET Revoked_At = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')"
        " WHERE Token_Hash = ? AND Revoked_At IS NULL",
        (token_hash,),
    )
    db.commit()


def revoke_all_for_user(db: sqlite3.Connection, user_id: int) -> None:
    db.execute(
        "UPDATE RefreshToken"
        " SET Revoked_At = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')"
        " WHERE User_ID = ? AND Revoked_At IS NULL",
        (user_id,),
    )
    db.commit()


def _from_row(row: sqlite3.Row) -> RefreshToken:
    return RefreshToken(
        id=row["ID"],
        user_id=row["User_ID"],
        token_hash=row["Token_Hash"],
        expires_at=row["Expires_At"],
        created_at=row["Created_At"],
        revoked_at=row["Revoked_At"],
    )
