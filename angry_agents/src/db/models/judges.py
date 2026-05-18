from __future__ import annotations

from dataclasses import dataclass

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS Judges (
    ID          INTEGER PRIMARY KEY AUTOINCREMENT,
    Role        TEXT    NOT NULL,
    Temperature REAL,
    Guess       TEXT,
    created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    deleted_at  TEXT
);

CREATE TRIGGER IF NOT EXISTS judges_updated_at
AFTER UPDATE ON Judges
BEGIN
    UPDATE Judges
       SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
     WHERE ID = NEW.ID;
END;
"""


@dataclass
class Judge:
    role: str
    id: int | None = None
    temperature: float | None = None
    guess: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    deleted_at: str | None = None
