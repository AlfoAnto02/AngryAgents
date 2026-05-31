from __future__ import annotations

from dataclasses import dataclass

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS Group_chat (
    ID            INTEGER PRIMARY KEY AUTOINCREMENT,
    ID_topic      INTEGER NOT NULL REFERENCES Topic(ID),
    Created_by    INTEGER REFERENCES User(ID),
    status        TEXT    NOT NULL DEFAULT 'pending',
    author_map    TEXT,
    speaker_stats TEXT,
    is_judged     INTEGER NOT NULL DEFAULT 0,
    report        TEXT,
    created_at    TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at    TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    deleted_at    TEXT
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
    created_by: int | None = None
    status: str = "pending"
    author_map: dict | None = None    # {author_tag: persona_id} — secret, never exposed to judges
    speaker_stats: dict | None = None  # {persona_id: {name, turns, share, dirichlet_weight}}
    is_judged: bool = False
    report: dict | None = None        # flat UI report JSON — served by GET /admin/judged-chats
    created_at: str | None = None
    updated_at: str | None = None
    deleted_at: str | None = None
