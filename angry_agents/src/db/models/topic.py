from __future__ import annotations

from dataclasses import dataclass

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS Topic (
    ID          INTEGER PRIMARY KEY AUTOINCREMENT,
    Title       TEXT    NOT NULL UNIQUE,
    Description TEXT,
    created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    deleted_at  TEXT
);

CREATE TRIGGER IF NOT EXISTS topic_updated_at
AFTER UPDATE ON Topic
BEGIN
    UPDATE Topic
       SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
     WHERE ID = NEW.ID;
END;
"""


@dataclass
class Topic:
    title: str
    id: int | None = None
    description: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    deleted_at: str | None = None
