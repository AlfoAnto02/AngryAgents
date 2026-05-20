from __future__ import annotations

from dataclasses import dataclass

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS RefreshToken (
    ID          INTEGER PRIMARY KEY AUTOINCREMENT,
    User_ID     INTEGER NOT NULL REFERENCES User(ID),
    Token_Hash  TEXT    NOT NULL UNIQUE,
    Expires_At  TEXT    NOT NULL,
    Created_At  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    Revoked_At  TEXT
);
"""


@dataclass
class RefreshToken:
    user_id: int
    token_hash: str
    expires_at: str
    id: int | None = None
    created_at: str | None = None
    revoked_at: str | None = None
