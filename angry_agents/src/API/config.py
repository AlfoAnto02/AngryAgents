from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class Settings:
    db_path: str
    author_secret: str


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        db_path=os.environ.get("ANGRY_DB_PATH", "angry_agents.db"),
        author_secret=os.environ["ANGRY_AUTHOR_SECRET"],
    )
