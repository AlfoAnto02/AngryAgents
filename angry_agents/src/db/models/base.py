from __future__ import annotations

import sqlite3
from pathlib import Path


def get_connection(db_path: str | Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


_MIGRATIONS = [
    "ALTER TABLE Group_chat ADD COLUMN status TEXT NOT NULL DEFAULT 'pending'",
    "ALTER TABLE Group_chat ADD COLUMN author_map TEXT",
    "ALTER TABLE Group_chat ADD COLUMN speaker_stats TEXT",
    "ALTER TABLE Group_chat ADD COLUMN is_judged INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE Group_chat ADD COLUMN report TEXT",
    "ALTER TABLE Judges ADD COLUMN name TEXT",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_judges_name ON Judges(name) WHERE name IS NOT NULL",
    "ALTER TABLE Judge_evaluation ADD COLUMN persona_identification TEXT",
    "ALTER TABLE Judge_evaluation ADD COLUMN rag_candidates TEXT",
    "ALTER TABLE Judge_evaluation ADD COLUMN group_fidelity_score INTEGER",
]

# Canonical 20 judge instances: 5 per role × 4 roles.
# Must stay in sync with JUDGES in angry_agents/src/rag/evaluation_test_20_judges.py.
_SEED_JUDGES = (
    [{"role": "style",      "name": f"style_{i}"}      for i in range(1, 6)]
  + [{"role": "ideology",   "name": f"ideology_{i}"}   for i in range(1, 6)]
  + [{"role": "general",    "name": f"general_{i}"}    for i in range(1, 6)]
  + [{"role": "behavioral", "name": f"behavioral_{i}"} for i in range(1, 6)]
)


def _seed_judges(conn: sqlite3.Connection) -> None:
    existing = {
        r[0]
        for r in conn.execute(
            "SELECT name FROM Judges WHERE name IS NOT NULL"
        ).fetchall()
    }
    for j in _SEED_JUDGES:
        if j["name"] not in existing:
            conn.execute(
                "INSERT INTO Judges (Role, name) VALUES (?, ?)",
                (j["role"], j["name"]),
            )
    conn.commit()


def init_db(conn: sqlite3.Connection) -> None:
    from . import ALL_DDL
    for ddl in ALL_DDL:
        conn.executescript(ddl)
    for sql in _MIGRATIONS:
        try:
            conn.execute(sql)
        except sqlite3.OperationalError:
            pass  # column/index already exists
    conn.commit()
    _seed_judges(conn)
