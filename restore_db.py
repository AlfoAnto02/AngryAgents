"""
restore_db.py — import the shared demo database from seed_database.sql

Works on Windows, Mac and Linux (no sqlite3 CLI needed).

Usage:
    python restore_db.py                      # uses seed_database.sql in project root
    python restore_db.py path/to/other.sql    # custom dump path
"""

import shutil
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

DUMP = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("seed_database.sql")
DB = Path("angry_agents.db")

if not DUMP.exists():
    print(f"Error: {DUMP} not found. Run this script from the project root.")
    sys.exit(1)

if DB.exists():
    backup = DB.with_name(f"angry_agents_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db.bak")
    shutil.copy2(DB, backup)
    print(f"Existing DB backed up to {backup}")
    DB.unlink()

sql = DUMP.read_text(encoding="utf-8")
con = sqlite3.connect(DB)
con.executescript(sql)
con.close()
print(f"DB restored from {DUMP}")
