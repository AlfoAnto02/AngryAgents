from __future__ import annotations

from dataclasses import dataclass

# author = name + surname + DIGEST — no FK to Agents by design (judge anonymity).
# author is NULL for user-posted messages (Created_by is set instead).
CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS Chat_messages (
    ID          INTEGER PRIMARY KEY AUTOINCREMENT,
    ID_Chat     INTEGER NOT NULL REFERENCES Group_chat(ID),
    message     TEXT    NOT NULL,
    author      TEXT,
    Created_by  INTEGER REFERENCES User(ID),
    created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    deleted_at  TEXT
);

CREATE TRIGGER IF NOT EXISTS chat_messages_updated_at
AFTER UPDATE ON Chat_messages
BEGIN
    UPDATE Chat_messages
       SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
     WHERE ID = NEW.ID;
END;
"""


@dataclass
class ChatMessage:
    id_chat: int
    message: str
    id: int | None = None
    author: str | None = None
    created_by: int | None = None
    created_at: str | None = None
    updated_at: str | None = None
    deleted_at: str | None = None
