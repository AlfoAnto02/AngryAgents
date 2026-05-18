from __future__ import annotations

from dataclasses import dataclass

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS Judge_evaluation (
    ID_judge    INTEGER NOT NULL REFERENCES Judges(ID),
    ID_chat     INTEGER NOT NULL REFERENCES Group_chat(ID),
    Score       REAL,
    created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updated_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    deleted_at  TEXT,
    PRIMARY KEY (ID_judge, ID_chat)
);

CREATE TRIGGER IF NOT EXISTS judge_evaluation_updated_at
AFTER UPDATE ON Judge_evaluation
BEGIN
    UPDATE Judge_evaluation
       SET updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
     WHERE ID_judge = NEW.ID_judge AND ID_chat = NEW.ID_chat;
END;
"""


@dataclass
class JudgeEvaluation:
    id_judge: int
    id_chat: int
    score: float | None = None
    created_at: str | None = None
    updated_at: str | None = None
    deleted_at: str | None = None
