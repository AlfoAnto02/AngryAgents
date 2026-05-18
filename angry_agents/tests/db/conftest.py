from __future__ import annotations

import sqlite3

import pytest

from angry_agents.src.db.models import ALL_DDL
from angry_agents.src.db.repositories import (
    agents_repository as agents_repo,
    group_chat_repository as chat_repo,
    judges_repository as judges_repo,
    topic_repository as topic_repo,
)


@pytest.fixture
def db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    for ddl in ALL_DDL:
        conn.executescript(ddl)
    conn.commit()
    yield conn
    conn.close()


@pytest.fixture
def topic(db):
    return topic_repo.create(db, {"title": "Breaking Bad", "description": "AMC drama"})


@pytest.fixture
def agent(db, topic):
    return agents_repo.create(
        db,
        {"name": "Walter", "surname": "White", "slug": "walter-white", "id_topic": topic.id},
    )


@pytest.fixture
def chat(db, topic):
    return chat_repo.create(db, {"id_topic": topic.id})


@pytest.fixture
def judge(db):
    return judges_repo.create(db, {"role": "style", "temperature": 0.7})
