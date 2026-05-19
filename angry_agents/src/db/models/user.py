from __future__ import annotations

from dataclasses import dataclass

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS User (
    ID          INTEGER PRIMARY KEY AUTOINCREMENT,
    Username    TEXT    NOT NULL UNIQUE,
    Password    TEXT    NOT NULL,
    Name        TEXT    NOT NULL,
    Surname     TEXT    NOT NULL,
    Role        TEXT    NOT NULL DEFAULT 'common',
    Email       TEXT    NOT NULL UNIQUE,
    Slug        TEXT    NOT NULL UNIQUE,
    created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    deleted_at  TEXT
);

CREATE TRIGGER IF NOT EXISTS user_updated_at
AFTER UPDATE ON User
BEGIN
    UPDATE User
       SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
     WHERE ID = NEW.ID;
END;
"""


@dataclass
class User:
    username: str
    password: str  # stored as pbkdf2 hash, never plaintext
    name: str
    surname: str
    email: str
    slug: str
    id: int | None = None
    role: str = "common"
    created_at: str | None = None
    updated_at: str | None = None
    deleted_at: str | None = None
