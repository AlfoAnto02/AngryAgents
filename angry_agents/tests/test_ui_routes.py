"""
Integration tests for the UI adapter routes.
Run: ANGRY_AUTHOR_SECRET=test JWT_SECRET_KEY=test pytest angry_agents/tests/test_ui_routes.py -v
"""
from __future__ import annotations

import json
import os
import tempfile

import pytest
from fastapi.testclient import TestClient

# Patch env before importing the app so get_settings() is correct.
os.environ["ANGRY_AUTHOR_SECRET"] = "test-secret"
os.environ["JWT_SECRET_KEY"] = "test-jwt-secret"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "60"
os.environ["REFRESH_TOKEN_EXPIRE_DAYS"] = "7"
os.environ["COOKIE_SECURE"] = "0"


@pytest.fixture(scope="module")
def client():
    # Use a real temp file so every get_db() call shares the same DB.
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    os.environ["ANGRY_DB_PATH"] = db_path

    # Clear lru_cache so get_settings() re-reads the env.
    from angry_agents.src.API.config import get_settings
    get_settings.cache_clear()

    from angry_agents.src.API.app import app
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c

    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.fixture(scope="module")
def auth_headers(client):
    # Register a user then login
    client.post("/auth/register", json={
        "username": "testuser",
        "name": "Test",
        "surname": "User",
        "email": "test@example.com",
        "password": "password123",
        "role": "common",
    })
    r = client.post("/auth/login", json={"email": "test@example.com", "password": "password123"})
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def agent_id(client, auth_headers):
    r = client.post("/agents", json={
        "name": "Walter",
        "surname": "White",
        "summary": json.dumps({
            "source_type": "fiction",
            "source_title": "Breaking Bad",
            "description": "A chemistry teacher turned drug kingpin.",
            "tags": ["drama", "crime"],
        }),
    }, headers=auth_headers)
    assert r.status_code == 201, r.text
    return r.json()["id"]


@pytest.fixture(scope="module")
def agent_id2(client, auth_headers):
    r = client.post("/agents", json={
        "name": "Jesse",
        "surname": "Pinkman",
        "summary": json.dumps({
            "source_type": "fiction",
            "source_title": "Breaking Bad",
            "description": "A young drug dealer with a conscience.",
            "tags": ["drama"],
        }),
    }, headers=auth_headers)
    assert r.status_code == 201, r.text
    return r.json()["id"]


# ---------------------------------------------------------------------------
# /ui/agents
# ---------------------------------------------------------------------------

def test_ui_agents_empty(client):
    """GET /ui/agents returns list (possibly empty at test start)."""
    r = client.get("/ui/agents")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_ui_agents_has_fields(client, agent_id):
    r = client.get("/ui/agents")
    assert r.status_code == 200
    agents = r.json()
    assert len(agents) >= 1
    a = next((x for x in agents if x["id"] == agent_id), None)
    assert a is not None, "Created agent not found in /ui/agents"
    assert a["name"] == "Walter White"
    assert a["source_type"] == "fiction"
    assert a["source_title"] == "Breaking Bad"
    assert "drama" in a["tags"]
    assert "desc" in a


# ---------------------------------------------------------------------------
# /ui/chats
# ---------------------------------------------------------------------------

def test_ui_chats_empty_for_new_user(client, auth_headers):
    r = client.get("/ui/chats", headers=auth_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_ui_create_group_chat(client, auth_headers, agent_id, agent_id2):
    r = client.post("/ui/chats", json={
        "type": "group",
        "participants": [agent_id, agent_id2],
        "topics": ["climate policy", "wealth tax"],
        "tone": "Debate",
    }, headers=auth_headers)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["type"] == "group"
    assert body["tone"] == "Debate"
    assert set(body["participants"]) == {agent_id, agent_id2}
    assert "climate policy" in body["topics"]


def test_ui_create_dm_chat(client, auth_headers, agent_id):
    r = client.post("/ui/chats", json={
        "type": "dm",
        "participants": [agent_id],
        "topics": [],
        "tone": "Casual",
        "opener": "Hello Walter.",
    }, headers=auth_headers)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["type"] == "dm"
    assert body["participants"] == [agent_id]


def test_ui_list_chats_after_create(client, auth_headers, agent_id, agent_id2):
    # Ensure at least one chat exists first
    client.post("/ui/chats", json={
        "type": "group",
        "participants": [agent_id, agent_id2],
        "topics": ["test topic"],
        "tone": "Formal",
    }, headers=auth_headers)

    r = client.get("/ui/chats", headers=auth_headers)
    assert r.status_code == 200
    chats = r.json()
    assert len(chats) >= 1
    chat = chats[0]
    assert "id" in chat
    assert "type" in chat
    assert "title" in chat
    assert "participants" in chat
    assert "topics" in chat
    assert "tone" in chat
    assert "unread" in chat


def test_ui_create_chat_no_valid_participants(client, auth_headers):
    r = client.post("/ui/chats", json={
        "type": "group",
        "participants": [999999],
        "topics": ["test"],
        "tone": "Debate",
    }, headers=auth_headers)
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# /ui/chats/{id}/messages
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def chat_id(client, auth_headers, agent_id, agent_id2):
    r = client.post("/ui/chats", json={
        "type": "group",
        "participants": [agent_id, agent_id2],
        "topics": ["messages test"],
        "tone": "Debate",
    }, headers=auth_headers)
    assert r.status_code == 201
    return r.json()["id"]


def test_ui_messages_empty(client, auth_headers, chat_id):
    r = client.get(f"/ui/chats/{chat_id}/messages")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_ui_send_message(client, auth_headers, chat_id):
    r = client.post(f"/ui/chats/{chat_id}/messages", json={"text": "Hello!"}, headers=auth_headers)
    assert r.status_code == 201, r.text
    msg = r.json()
    assert msg["kind"] == "user"
    assert msg["text"] == "Hello!"


def test_ui_messages_after_send(client, auth_headers, chat_id):
    client.post(f"/ui/chats/{chat_id}/messages", json={"text": "Second message"}, headers=auth_headers)
    r = client.get(f"/ui/chats/{chat_id}/messages")
    assert r.status_code == 200
    msgs = r.json()
    assert len(msgs) >= 1
    m = msgs[-1]
    assert "kind" in m
    assert "text" in m
    assert m["kind"] in ("user", "agent", "system")


# ---------------------------------------------------------------------------
# Admin routes
# ---------------------------------------------------------------------------

def test_admin_overview(client):
    r = client.get("/admin/overview")
    assert r.status_code == 200
    data = r.json()
    assert "sessions_today" in data
    assert "active_users" in data
    assert "avg_session" in data
    assert "judge_confidence" in data


def test_admin_sessions(client):
    r = client.get("/admin/sessions")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_admin_agent_performance(client, agent_id):
    r = client.get("/admin/agent-performance")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    entry = next((x for x in data if x["agent_id"] == agent_id), None)
    assert entry is not None
    assert "sessions" in entry
    assert "individual_fidelity" in entry
    assert "group_fidelity" in entry
    assert "flagged" in entry
