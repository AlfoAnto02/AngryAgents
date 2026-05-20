from __future__ import annotations

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS Chat_agent (
    id_chat   INTEGER NOT NULL REFERENCES Group_chat(ID),
    id_agent  INTEGER NOT NULL REFERENCES Agents(ID),
    PRIMARY KEY (id_chat, id_agent)
);
"""
