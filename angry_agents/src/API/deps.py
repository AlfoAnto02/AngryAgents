from __future__ import annotations

import sqlite3
from typing import Generator

from fastapi import Depends

from ..db.models.base import get_connection
from .config import Settings, get_settings


def get_db(settings: Settings = Depends(get_settings)) -> Generator[sqlite3.Connection, None, None]:
    conn = get_connection(settings.db_path)
    try:
        yield conn
    finally:
        conn.close()
