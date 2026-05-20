from __future__ import annotations

import json
import logging
import os
import sqlite3
import time as _time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ...db.services.chat_messages_service import ChatMessageService
from ..config import Settings, get_settings
from ..deps import get_current_user, get_db

router = APIRouter()
log = logging.getLogger(__name__)


def _to_str(v) -> str:
    if isinstance(v, str):
        return v
    if isinstance(v, dict):
        # flatten nested style objects to a readable summary
        return "; ".join(f"{k}: {val}" for k, val in v.items() if isinstance(val, str))
    return str(v) if v else ""


def _run_agent_turns(db: sqlite3.Connection, chat_id: int, settings: Settings) -> None:
    """Generate agent replies for the given chat using GroupChatSession."""
    from ...group_chat.group_chat_factory import GroupChatFactory

    model = os.getenv("OLLAMA_DEFAULT_MODEL", "mistral")
    try:
        session = GroupChatFactory.build_session(
            db, chat_id, model, settings.author_secret
        )
        if not session.agents:
            return
        for _ in session.agents:
            session.run_turn(db)
    except Exception as exc:
        log.warning("Agent turn generation failed for chat %s: %s", chat_id, exc)


def _relative_time(ts: str | None) -> str:
    if not ts:
        return ""
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        delta = now - dt
        secs = delta.total_seconds()
        if secs < 60:
            return "just now"
        if secs < 3600:
            return f"{int(secs / 60)}m"
        if secs < 86400:
            return f"{int(secs / 3600)}h"
        if delta.days == 1:
            return "Yesterday"
        return dt.strftime("%b %d")
    except Exception:
        return ts[:10] if ts else ""


def _short_time(ts: str | None) -> str:
    if not ts:
        return ""
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return dt.strftime("%H:%M")
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------

@router.get("/ui/agents")
def ui_list_agents(db: sqlite3.Connection = Depends(get_db)) -> list:
    rows = db.execute(
        "SELECT ID, Name, Surname, Slug, Summary FROM Agents WHERE deleted_at IS NULL ORDER BY Name"
    ).fetchall()
    result = []
    for a in rows:
        summary: dict = {}
        try:
            summary = json.loads(a["Summary"] or "{}")
        except Exception:
            pass
        result.append({
            "id": a["ID"],
            "name": f"{a['Name']} {a['Surname']}".strip(),
            "slug": a["Slug"],
            "source_type": summary.get("source_type", "fiction"),
            "source_title": summary.get("source_title") or a["Surname"],
            "desc": _to_str(
                summary.get("core_style")
                or summary.get("description")
                or summary.get("desc")
                or ""
            ),
            "tags": summary.get("tags") or [],
        })
    return result


# ---------------------------------------------------------------------------
# Chats
# ---------------------------------------------------------------------------

class UIChatCreate(BaseModel):
    type: str = "group"
    participants: list
    topics: list[str] = []
    tone: str = "Debate"
    opener: str | None = None


@router.get("/ui/chats")
def ui_list_chats(
    current_user=Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db),
) -> list:
    chats = db.execute(
        """
        SELECT gc.ID, gc.created_at,
               t.Title  AS topic_title,
               t.Description AS topic_desc
        FROM Group_chat gc
        JOIN Topic t ON gc.ID_topic = t.ID
        WHERE gc.deleted_at IS NULL
          AND gc.Created_by = ?
        ORDER BY gc.created_at DESC
        LIMIT 50
        """,
        (current_user.id,),
    ).fetchall()

    result = []
    for chat in chats:
        agents = db.execute(
            """
            SELECT a.ID, a.Name, a.Surname, a.Slug
            FROM Chat_agent ca
            JOIN Agents a ON ca.id_agent = a.ID
            WHERE ca.id_chat = ? AND a.deleted_at IS NULL
            """,
            (chat["ID"],),
        ).fetchall()

        last_msg = db.execute(
            """
            SELECT message, author, Created_by, created_at
            FROM Chat_messages
            WHERE ID_Chat = ? AND deleted_at IS NULL
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (chat["ID"],),
        ).fetchone()

        meta: dict = {}
        try:
            meta = json.loads(chat["topic_desc"] or "{}")
        except Exception:
            pass

        chat_type = "dm" if len(agents) == 1 else "group"
        participant_ids = [a["ID"] for a in agents]

        if chat_type == "dm" and agents:
            title = f"{agents[0]['Name']} {agents[0]['Surname']}".strip().upper()
        else:
            title = meta.get("title") or chat["topic_title"]

        last = ""
        last_time = ""
        if last_msg:
            preview = (last_msg["message"] or "")[:60]
            if last_msg["author"]:
                label = last_msg["author"].split("::")[0] + ": "
            elif last_msg["Created_by"]:
                label = "You: "
            else:
                label = ""
            last = f'{label}"{preview}"'
            last_time = _relative_time(last_msg["created_at"])

        result.append({
            "id": chat["ID"],
            "type": chat_type,
            "title": title,
            "topics": meta.get("topics", [chat["topic_title"]]),
            "tone": meta.get("tone", "Debate"),
            "participants": participant_ids,
            "unread": 0,
            "last": last,
            "lastTime": last_time,
            "started": _relative_time(chat["created_at"]),
        })

    return result


@router.post("/ui/chats", status_code=201)
def ui_create_chat(
    body: UIChatCreate,
    current_user=Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    # Resolve agent IDs (participants can be int IDs or slug strings)
    agent_ids: list[int] = []
    for p in body.participants:
        if isinstance(p, int):
            row = db.execute(
                "SELECT ID FROM Agents WHERE ID = ? AND deleted_at IS NULL", (p,)
            ).fetchone()
        else:
            row = db.execute(
                "SELECT ID FROM Agents WHERE Slug = ? AND deleted_at IS NULL", (str(p),)
            ).fetchone()
        if row:
            agent_ids.append(row["ID"])

    if not agent_ids:
        raise HTTPException(status_code=422, detail="No valid participants")

    display_title = body.topics[0] if body.topics else "Untitled session"
    # Topic.Title is UNIQUE — append ms timestamp to avoid collisions
    unique_title = f"{display_title}__{int(_time.time() * 1000)}"
    meta_json = json.dumps({
        "topics": body.topics,
        "tone": body.tone,
        "title": display_title,
    })

    cur = db.execute(
        "INSERT INTO Topic (Title, Description, Created_by) VALUES (?, ?, ?)",
        (unique_title, meta_json, current_user.id),
    )
    topic_id = cur.lastrowid

    cur = db.execute(
        "INSERT INTO Group_chat (ID_topic, Created_by) VALUES (?, ?)",
        (topic_id, current_user.id),
    )
    chat_id = cur.lastrowid

    for aid in agent_ids:
        db.execute(
            "INSERT OR IGNORE INTO Chat_agent (id_chat, id_agent) VALUES (?, ?)",
            (chat_id, aid),
        )

    db.commit()

    if body.opener and body.opener.strip():
        ChatMessageService(db, settings.author_secret).create(
            id_chat=chat_id,
            message=body.opener.strip(),
            created_by=current_user.id,
        )

    agents = db.execute(
        "SELECT ID, Name, Surname FROM Agents WHERE ID IN ({})".format(
            ",".join("?" * len(agent_ids))
        ),
        agent_ids,
    ).fetchall()

    chat_type = "dm" if len(agent_ids) == 1 else "group"
    if chat_type == "dm":
        title = f"{agents[0]['Name']} {agents[0]['Surname']}".strip().upper()
    else:
        title = display_title

    return {
        "id": chat_id,
        "type": chat_type,
        "title": title,
        "topics": body.topics,
        "tone": body.tone,
        "participants": agent_ids,
        "unread": 0,
        "last": "",
        "lastTime": "just now",
        "started": "just now",
    }


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------

class UIMessageCreate(BaseModel):
    text: str


def _build_author_lookup(db: sqlite3.Connection, chat_id: int, secret: str) -> dict[str, int]:
    """Map HMAC digest → agent_id for all agents in a chat."""
    import hashlib
    import hmac as _hmac

    agents = db.execute(
        """
        SELECT a.ID, a.Name, a.Surname
        FROM Chat_agent ca
        JOIN Agents a ON ca.id_agent = a.ID
        WHERE ca.id_chat = ? AND a.deleted_at IS NULL
        """,
        (chat_id,),
    ).fetchall()
    lookup: dict[str, int] = {}
    for a in agents:
        digest = _hmac.new(
            secret.encode(),
            f"{a['Name']}:{a['Surname']}".encode(),
            hashlib.sha256,
        ).hexdigest()
        lookup[digest] = a["ID"]
    return lookup


@router.get("/ui/chats/{chat_id}/messages")
def ui_list_messages(
    chat_id: int,
    db: sqlite3.Connection = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> list:
    rows = db.execute(
        """
        SELECT ID, message, author, Created_by, created_at
        FROM Chat_messages
        WHERE ID_Chat = ? AND deleted_at IS NULL
        ORDER BY created_at ASC
        """,
        (chat_id,),
    ).fetchall()

    author_to_agent = _build_author_lookup(db, chat_id, settings.author_secret)

    result = []
    for m in rows:
        if m["Created_by"] is not None:
            kind = "user"
        elif m["author"]:
            kind = "agent"
        else:
            kind = "system"
        persona_id = author_to_agent.get(m["author"]) if m["author"] else None
        result.append({
            "kind": kind,
            "text": m["message"],
            "author": m["author"],
            "persona_id": persona_id,
            "ts": m["created_at"],
            "time": _short_time(m["created_at"]),
        })
    return result


@router.post("/ui/chats/{chat_id}/messages", status_code=201)
def ui_create_message(
    chat_id: int,
    body: UIMessageCreate,
    current_user=Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    msg = ChatMessageService(db, settings.author_secret).create(
        id_chat=chat_id,
        message=body.text,
        created_by=current_user.id,
    )
    _run_agent_turns(db, chat_id, settings)
    return {
        "kind": "user",
        "text": msg.message,
        "author": None,
        "ts": msg.created_at,
        "time": _short_time(msg.created_at),
    }


# ---------------------------------------------------------------------------
# Admin
# ---------------------------------------------------------------------------

@router.get("/admin/overview")
def admin_overview(db: sqlite3.Connection = Depends(get_db)) -> dict:
    today_n = db.execute(
        "SELECT COUNT(*) AS n FROM Group_chat WHERE date(created_at) = date('now') AND deleted_at IS NULL"
    ).fetchone()["n"]

    users_n = db.execute(
        "SELECT COUNT(DISTINCT Created_by) AS n FROM Group_chat WHERE deleted_at IS NULL AND Created_by IS NOT NULL"
    ).fetchone()["n"]

    return {
        "sessions_today":  {"value": today_n,  "delta_pct": 0, "spark": []},
        "active_users":    {"value": users_n,   "delta_pct": 0, "spark": []},
        "avg_session":     {"value": "00:00:00", "delta_pct": 0, "spark": []},
        "judge_confidence": {"value": 0.0,       "delta_abs": 0, "spark": []},
    }


@router.get("/admin/sessions")
def admin_sessions(
    limit: int = 24,
    db: sqlite3.Connection = Depends(get_db),
) -> list:
    chats = db.execute(
        """
        SELECT gc.ID, gc.created_at,
               t.Title AS topic_title,
               t.Description AS topic_desc
        FROM Group_chat gc
        JOIN Topic t ON gc.ID_topic = t.ID
        WHERE gc.deleted_at IS NULL
        ORDER BY gc.created_at DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()

    result = []
    for c in chats:
        meta: dict = {}
        try:
            meta = json.loads(c["topic_desc"] or "{}")
        except Exception:
            pass

        agents = db.execute(
            """
            SELECT a.ID FROM Chat_agent ca
            JOIN Agents a ON ca.id_agent = a.ID
            WHERE ca.id_chat = ?
            """,
            (c["ID"],),
        ).fetchall()

        result.append({
            "id": f"S-{c['ID']:04d}",
            "participants": [a["ID"] for a in agents],
            "topic": meta.get("title") or c["topic_title"],
            "duration": "00:00:00",
            "date": (c["created_at"] or "")[:16].replace("T", " "),
            "status": "complete",
        })

    return result


@router.get("/admin/agent-performance")
def admin_agent_performance(db: sqlite3.Connection = Depends(get_db)) -> list:
    rows = db.execute(
        """
        SELECT a.ID AS agent_id, COUNT(DISTINCT ca.id_chat) AS sessions
        FROM Agents a
        LEFT JOIN Chat_agent ca ON a.ID = ca.id_agent
        WHERE a.deleted_at IS NULL
        GROUP BY a.ID
        ORDER BY sessions DESC
        """
    ).fetchall()

    return [
        {
            "agent_id": r["agent_id"],
            "sessions": r["sessions"],
            "individual_fidelity": 0.0,
            "group_fidelity": 0.0,
            "flagged": 0,
        }
        for r in rows
    ]
