"""
export_db.py — dump the current DB to seed_database.sql

Run this after you've created all the demo chats and are happy with the state.

Usage:
    python export_db.py
"""

import sqlite3
from pathlib import Path

DB = Path("angry_agents.db")
OUT = Path("seed_database.sql")

if not DB.exists():
    print(f"Error: {DB} not found.")
    raise SystemExit(1)

con = sqlite3.connect(DB)
OUT.write_text("\n".join(con.iterdump()), encoding="utf-8")
con.close()
print(f"Exported {DB} → {OUT}  ({OUT.stat().st_size // 1024} KB)")
