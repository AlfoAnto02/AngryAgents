from __future__ import annotations

from dataclasses import dataclass

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS Agent_context (
    ID_context        INTEGER PRIMARY KEY AUTOINCREMENT,
    ID_agent          INTEGER NOT NULL REFERENCES Agents(ID),
    Signature_phrases TEXT,
    created_at        TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at        TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    deleted_at        TEXT
);

CREATE TRIGGER IF NOT EXISTS agent_context_updated_at
AFTER UPDATE ON Agent_context
BEGIN
    UPDATE Agent_context
       SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
     WHERE ID_context = NEW.ID_context;
END;
"""


@dataclass
class AgentContext:
    id_agent: int
    id_context: int | None = None
    signature_phrases: str | None = None  # JSON-encoded string
    created_at: str | None = None
    updated_at: str | None = None
    deleted_at: str | None = None
