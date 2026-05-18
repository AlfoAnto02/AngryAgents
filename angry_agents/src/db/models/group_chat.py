from __future__ import annotations

from dataclasses import dataclass

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS Group_chat (
    ID          INTEGER PRIMARY KEY AUTOINCREMENT,
    ID_topic    INTEGER NOT NULL REFERENCES Topic(ID),
    created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    deleted_at  TEXT
);

CREATE TRIGGER IF NOT EXISTS group_chat_updated_at
AFTER UPDATE ON Group_chat
BEGIN
    UPDATE Group_chat
       SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
     WHERE ID = NEW.ID;
END;
"""


@dataclass
class GroupChat:
    id_topic: int
    id: int | None = None
    created_at: str | None = None
    updated_at: str | None = None
    deleted_at: str | None = None
