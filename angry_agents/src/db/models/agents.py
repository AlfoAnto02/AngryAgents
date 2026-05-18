from __future__ import annotations

from dataclasses import dataclass

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS Agents (
    ID          INTEGER PRIMARY KEY AUTOINCREMENT,
    ID_topic    INTEGER REFERENCES Topic(ID),
    Name        TEXT    NOT NULL,
    Surname     TEXT    NOT NULL,
    Slug        TEXT    NOT NULL UNIQUE,
    Summary     TEXT,
    created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    deleted_at  TEXT
);

CREATE TRIGGER IF NOT EXISTS agents_updated_at
AFTER UPDATE ON Agents
BEGIN
    UPDATE Agents
       SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
     WHERE ID = NEW.ID;
END;
"""


@dataclass
class Agent:
    name: str
    surname: str
    slug: str
    id: int | None = None
    id_topic: int | None = None
    summary: str | None = None  # JSON-encoded string
    created_at: str | None = None
    updated_at: str | None = None
    deleted_at: str | None = None
