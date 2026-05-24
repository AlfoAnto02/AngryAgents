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
]


def init_db(conn: sqlite3.Connection) -> None:
    from . import ALL_DDL
    for ddl in ALL_DDL:
        conn.executescript(ddl)
    for sql in _MIGRATIONS:
        try:
            conn.execute(sql)
        except sqlite3.OperationalError:
            pass  # column already exists
    conn.commit()
