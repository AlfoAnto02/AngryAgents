from __future__ import annotations

import json
import sqlite3
from typing import Any

# rel_type registry — what src and tgt mean per type:
#   "agent_topic"  : src=agent_id,  tgt=topic_id   (nullable FK on Agents)
#   "judge_chat"   : src=judge_id,  tgt=chat_id    (row in Judge_evaluation)
#
# rel_id is a (rel_type, src, tgt) tuple returned by add() and consumed by remove().

RelId = tuple[str, int, int]


def add(
    db: sqlite3.Connection,
    src: int,
    tgt: int,
    rel_type: str,
    details: dict[str, Any] | None = None,
) -> RelId:
    if rel_type == "agent_topic":
        db.execute("UPDATE Agents SET ID_topic = ? WHERE ID = ?", (tgt, src))

    elif rel_type == "judge_chat":
        pi = (details or {}).get("persona_identification")
        db.execute(
            "INSERT INTO Judge_evaluation (ID_judge, ID_chat, persona_identification) VALUES (?, ?, ?)",
            (src, tgt, json.dumps(pi) if pi is not None else None),
        )

    else:
        raise ValueError(f"unknown rel_type: {rel_type!r}")

    db.commit()
    return (rel_type, src, tgt)


def remove(db: sqlite3.Connection, rel_id: RelId, hard: bool = False) -> None:
    rel_type, src, tgt = rel_id

    if rel_type == "agent_topic":
        db.execute("UPDATE Agents SET ID_topic = NULL WHERE ID = ?", (src,))

    elif rel_type == "judge_chat":
        if hard:
            db.execute(
                "DELETE FROM Judge_evaluation WHERE ID_judge = ? AND ID_chat = ?",
                (src, tgt),
            )
        else:
            db.execute(
                "UPDATE Judge_evaluation SET deleted_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE ID_judge = ? AND ID_chat = ?",
                (src, tgt),
            )

    else:
        raise ValueError(f"unknown rel_type: {rel_type!r}")

    db.commit()


def list_rels(
    db: sqlite3.Connection,
    src: int | None = None,
    tgt: int | None = None,
    rel_type: str | None = None,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    if rel_type in (None, "agent_topic"):
        clauses, params = ["deleted_at IS NULL"], []
        if src is not None:
            clauses.append("ID = ?")
            params.append(src)
        if tgt is not None:
            clauses.append("ID_topic = ?")
            params.append(tgt)
        rows = db.execute(
            f"SELECT ID, ID_topic FROM Agents WHERE {' AND '.join(clauses)}",
            params,
        ).fetchall()
        for r in rows:
            if r["ID_topic"] is not None:
                results.append(
                    {"rel_type": "agent_topic", "src": r["ID"], "tgt": r["ID_topic"]}
                )

    if rel_type in (None, "judge_chat"):
        clauses, params = ["deleted_at IS NULL"], []
        if src is not None:
            clauses.append("ID_judge = ?")
            params.append(src)
        if tgt is not None:
            clauses.append("ID_chat = ?")
            params.append(tgt)
        rows = db.execute(
            f"SELECT ID_judge, ID_chat FROM Judge_evaluation WHERE {' AND '.join(clauses)}",
            params,
        ).fetchall()
        for r in rows:
            results.append(
                {"rel_type": "judge_chat", "src": r["ID_judge"], "tgt": r["ID_chat"]}
            )

    return results
