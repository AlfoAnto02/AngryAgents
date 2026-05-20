from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    db_path: str
    author_secret: str
    jwt_secret: str
    access_token_expire_minutes: int
    refresh_token_expire_days: int
    refresh_token_expire_minutes: int  # overrides days when > 0
    cookie_secure: bool


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        db_path=os.environ.get("ANGRY_DB_PATH", "angry_agents.db"),
        author_secret=os.environ["ANGRY_AUTHOR_SECRET"],
        jwt_secret=os.environ["JWT_SECRET_KEY"],
        access_token_expire_minutes=int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "15")),
        refresh_token_expire_days=int(os.environ.get("REFRESH_TOKEN_EXPIRE_DAYS", "7")),
        refresh_token_expire_minutes=int(os.environ.get("REFRESH_TOKEN_EXPIRE_MINUTES", "0")),
        cookie_secure=os.environ.get("COOKIE_SECURE", "0") == "1",
    )
