from __future__ import annotations

import asyncio
import hashlib
import hmac as _hmac
import json
import logging
import os
import random
import sqlite3
import time as _time
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from ...db.models.base import get_connection
from ...db.services.chat_messages_service import ChatMessageService
from ...db.services.group_chat_service import GroupChatService
from ...db.services.judge_evaluation_service import JudgeEvaluationService
from ...logging_setup import deviation
from ..config import Settings, get_settings
from ..deps import get_current_user, get_db

router = APIRouter()
log = logging.getLogger(__name__)


def _extract_desc(summary: dict) -> str:
    """Return a single human-readable sentence describing the persona."""
    sir = summary.get("self_image_vs_reality")
    if isinstance(sir, dict) and sir.get("self_image"):
        return str(sir["self_image"]).strip().rstrip(".")
    sp = summary.get("social_positioning")
    if isinstance(sp, dict) and sp.get("desired_position"):
        return str(sp["desired_position"]).strip().rstrip(".")
    wv = summary.get("worldview")
    if isinstance(wv, dict):
        for val in wv.values():
            if isinstance(val, str) and val.strip():
                return val.strip().rstrip(".")
    cs = summary.get("core_style")
    if isinstance(cs, dict) and cs.get("default_register"):
        return str(cs["default_register"]).strip()
    return ""


def _extract_tags(summary: dict) -> list[str]:
    """Derive up to 4 tags: direct 'tags' list first, then knowledge_domains, then worldview keys."""
    direct = summary.get("tags")
    if isinstance(direct, list) and direct:
        return [str(t).strip().lower() for t in direct if str(t).strip()][:4]
    kd = summary.get("knowledge_domains", {})
    domains: list[str] = []
    if isinstance(kd, dict):
        for key in ("expert", "surface"):
            for item in (kd.get(key) or []):
                if isinstance(item, str) and item.strip():
                    domains.append(item.strip().lower())
    if not domains:
        wv = summary.get("worldview", {})
        if isinstance(wv, dict):
            domains = [k.strip().lower() for k in list(wv.keys())[:4]]
    return domains[:4]


_DEFAULT_TURNS = 24
_TURN_DELAY_MIN = 8.0   # seconds — minimum pause between agent turns
_TURN_DELAY_MAX = 14.0  # seconds — maximum pause between agent turns


def _dm_run_agent_turn(db: sqlite3.Connection, chat_id: int, settings: Settings) -> None:
    """Single agent reply for DM chats (synchronous, in-request)."""
    from ...dm_chat.factory import DMFactory

    model = os.getenv("OLLAMA_DEFAULT_MODEL", "mistral")
    session = DMFactory.build_session(db, chat_id, model, settings.author_secret)
    try:
        session.respond(db)
    except Exception as exc:
        deviation("dm agent turn failed", chat_id=chat_id, exc=str(exc))


def _bg_run_conversation(
    chat_id: int, db_path: str, author_secret: str, n_turns: int
) -> None:
    """Background task: runs the autonomous group chat for n_turns."""
    from ...group_chat.group_chat_factory import GroupChatFactory

    conn = get_connection(db_path)
    try:
        svc = GroupChatService(conn)
        svc.set_status(chat_id, "running")
        model = os.getenv("OLLAMA_DEFAULT_MODEL", "mistral")
        session = GroupChatFactory.build_session(conn, chat_id, model, author_secret)
        if not session.agents:
            svc.set_status(chat_id, "done")
            return

        def _is_stopped() -> bool:
            row = svc.get(chat_id)
            return bool(row and row.status == "stopped")

        for _ in range(n_turns):
            if _is_stopped():
                return
            try:
                session.run_turn(conn, stop_check=_is_stopped)
            except Exception as exc:
                log.exception("group turn failed chat_id=%s: %s", chat_id, exc)
                deviation("group turn failed", chat_id=chat_id, exc=str(exc))
            # Interruptible sleep: check for stop every 0.5 s
            deadline = _time.time() + random.uniform(_TURN_DELAY_MIN, _TURN_DELAY_MAX)
            while _time.time() < deadline:
                if _is_stopped():
                    return
                _time.sleep(0.5)
        svc.set_status(chat_id, "done")
    except Exception as exc:
        deviation("group conversation failed", chat_id=chat_id, exc=str(exc))
        try:
            GroupChatService(conn).set_status(chat_id, "error")
        except Exception:
            pass
    finally:
        conn.close()


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
        src_type = summary.get("source_type", "fiction")
        if src_type == "real_world":
            src_title = summary.get("occupation") or summary.get("source_title") or a["Surname"]
        else:
            src_title = summary.get("source_title") or a["Surname"]
        result.append({
            "id": a["ID"],
            "name": f"{a['Name']} {a['Surname']}".strip(),
            "slug": a["Slug"],
            "source_type": src_type,
            "source_title": src_title,
            "desc": _extract_desc(summary),
            "tags": _extract_tags(summary),
        })
    return result


@router.get("/ui/agents/{agent_id}")
def ui_get_agent(agent_id: int, db: sqlite3.Connection = Depends(get_db)) -> dict:
    row = db.execute(
        "SELECT ID, Name, Surname, Slug, Summary FROM Agents WHERE ID = ? AND deleted_at IS NULL",
        (agent_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    summary: dict = {}
    try:
        summary = json.loads(row["Summary"] or "{}")
    except Exception:
        pass
    src_type = summary.get("source_type", "fiction")
    if src_type == "real_world":
        src_title = summary.get("occupation") or summary.get("source_title") or row["Surname"]
    else:
        src_title = summary.get("source_title") or row["Surname"]
    return {
        "id": row["ID"],
        "name": f"{row['Name']} {row['Surname']}".strip(),
        "slug": row["Slug"],
        "source_type": src_type,
        "source_title": src_title,
        "desc": _extract_desc(summary),
        "tags": _extract_tags(summary),
        "profile": summary,
    }


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
    background_tasks: BackgroundTasks,
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
    meta_json = json.dumps({
        "topics": body.topics,
        "tone": body.tone,
        "title": display_title,
    })

    existing_topic = db.execute(
        "SELECT id FROM Topic WHERE lower(Title) = lower(?) AND deleted_at IS NULL",
        (display_title,),
    ).fetchone()
    if existing_topic:
        topic_id = existing_topic["id"]
    else:
        cur = db.execute(
            "INSERT INTO Topic (Title, Description, Created_by) VALUES (?, ?, ?)",
            (display_title, meta_json, current_user.id),
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
        background_tasks.add_task(
            _bg_run_conversation, chat_id, settings.db_path, settings.author_secret, _DEFAULT_TURNS
        )

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
# LLM / MCP chat creation (no auth — accepts explicit created_by)
# ---------------------------------------------------------------------------

class ChatCreateForLLM(BaseModel):
    participants: list[int]
    topics: list[str] = []
    tone: str = "Debate"
    opener: str | None = None
    created_by: int | None = None


@router.post("/ui/chats/create-for-llm", status_code=201)
def create_chat_for_llm(
    body: ChatCreateForLLM,
    background_tasks: BackgroundTasks,
    db: sqlite3.Connection = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    if not body.participants:
        raise HTTPException(status_code=422, detail="participants must not be empty")
    if len(body.participants) > 8:
        raise HTTPException(status_code=422, detail="participants must be 2–8 for group chat or 1 for DM")

    agent_ids: list[int] = []
    for pid in body.participants:
        row = db.execute(
            "SELECT ID FROM Agents WHERE ID = ? AND deleted_at IS NULL", (pid,)
        ).fetchone()
        if row:
            agent_ids.append(row["ID"])

    if not agent_ids:
        raise HTTPException(status_code=422, detail="No valid participants")

    display_title = body.topics[0] if body.topics else "Untitled session"
    meta_json = json.dumps({"topics": body.topics, "tone": body.tone, "title": display_title})

    existing_topic = db.execute(
        "SELECT id FROM Topic WHERE lower(Title) = lower(?) AND deleted_at IS NULL",
        (display_title,),
    ).fetchone()
    if existing_topic:
        topic_id = existing_topic["id"]
    else:
        cur = db.execute(
            "INSERT INTO Topic (Title, Description, Created_by) VALUES (?, ?, ?)",
            (display_title, meta_json, body.created_by),
        )
        topic_id = cur.lastrowid

    cur = db.execute(
        "INSERT INTO Group_chat (ID_topic, Created_by) VALUES (?, ?)",
        (topic_id, body.created_by),
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
            created_by=body.created_by,
        )

    agents = db.execute(
        "SELECT ID, Name, Surname FROM Agents WHERE ID IN ({})".format(
            ",".join("?" * len(agent_ids))
        ),
        agent_ids,
    ).fetchall()

    chat_type = "dm" if len(agent_ids) == 1 else "group"
    if chat_type == "group":
        background_tasks.add_task(
            _bg_run_conversation, chat_id, settings.db_path, settings.author_secret, _DEFAULT_TURNS
        )
        title = display_title
    else:
        title = f"{agents[0]['Name']} {agents[0]['Surname']}".strip().upper()

    return {
        "id": chat_id,
        "type": chat_type,
        "title": title,
        "topics": body.topics,
        "tone": body.tone,
        "participants": agent_ids,
        "status": "running" if chat_type == "group" else "pending",
    }


# ---------------------------------------------------------------------------
# Group chat: start + SSE stream
# ---------------------------------------------------------------------------

@router.get("/ui/chats/{chat_id}")
def ui_get_chat(
    chat_id: int,
    current_user=Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db),
) -> dict:
    chat = db.execute(
        """
        SELECT gc.ID, gc.created_at,
               t.Title  AS topic_title,
               t.Description AS topic_desc
        FROM Group_chat gc
        JOIN Topic t ON gc.ID_topic = t.ID
        WHERE gc.ID = ? AND gc.deleted_at IS NULL
        """,
        (chat_id,),
    ).fetchone()
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")

    agents = db.execute(
        """
        SELECT a.ID, a.Name, a.Surname
        FROM Chat_agent ca
        JOIN Agents a ON ca.id_agent = a.ID
        WHERE ca.id_chat = ? AND a.deleted_at IS NULL
        """,
        (chat_id,),
    ).fetchall()

    last_msg = db.execute(
        """
        SELECT message, author, Created_by, created_at
        FROM Chat_messages
        WHERE ID_Chat = ? AND deleted_at IS NULL
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (chat_id,),
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

    return {
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
    }


@router.get("/ui/chats/{chat_id}/status")
def ui_chat_status(chat_id: int, db: sqlite3.Connection = Depends(get_db)) -> dict:
    row = db.execute(
        "SELECT status FROM Group_chat WHERE ID = ? AND deleted_at IS NULL", (chat_id,)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    return {"status": row["status"] or "pending"}


@router.post("/ui/chats/{chat_id}/stop", status_code=200)
def ui_stop_chat(
    chat_id: int,
    current_user=Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db),
) -> dict:
    chat = GroupChatService(db).get(chat_id)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    if chat.status not in ("running", "pending"):
        raise HTTPException(status_code=409, detail=f"Chat is not running (status: {chat.status})")
    GroupChatService(db).set_status(chat_id, "stopped")
    return {"chat_id": chat_id, "status": "stopped"}


@router.post("/ui/chats/{chat_id}/start", status_code=202)
def ui_start_chat(
    chat_id: int,
    background_tasks: BackgroundTasks,
    n_turns: int = _DEFAULT_TURNS,
    current_user=Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    chat = GroupChatService(db).get(chat_id)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    if chat.status in ("running", "done"):
        raise HTTPException(status_code=409, detail=f"Chat already {chat.status}")

    background_tasks.add_task(
        _bg_run_conversation, chat_id, settings.db_path, settings.author_secret, n_turns
    )
    return {"chat_id": chat_id, "status": "running", "n_turns": n_turns}


@router.get("/ui/chats/{chat_id}/stream")
async def ui_stream_chat(
    chat_id: int,
    after: int = 0,
    settings: Settings = Depends(get_settings),
):
    async def generate():
        conn = get_connection(settings.db_path)
        try:
            last_id = after
            idle_ticks = 0
            max_idle = 1200  # 10 minutes at 0.5s intervals

            while idle_ticks < max_idle:
                rows = conn.execute(
                    """SELECT ID, message, author, Created_by, created_at
                       FROM Chat_messages
                       WHERE ID_Chat = ? AND ID > ? AND deleted_at IS NULL
                       ORDER BY ID ASC LIMIT 20""",
                    (chat_id, last_id),
                ).fetchall()

                for row in rows:
                    last_id = row["ID"]
                    idle_ticks = 0
                    kind = "agent" if row["author"] else ("user" if row["Created_by"] else "system")
                    payload = json.dumps({
                        "id": row["ID"],
                        "kind": kind,
                        "text": row["message"],
                        "author": row["author"],
                        "ts": row["created_at"],
                        "time": _short_time(row["created_at"]),
                    })
                    yield f"data: {payload}\n\n"

                if not rows:
                    chat_row = conn.execute(
                        "SELECT status FROM Group_chat WHERE ID = ?", (chat_id,)
                    ).fetchone()
                    if chat_row and chat_row["status"] in ("done", "error", "stopped"):
                        yield "event: done\ndata: {}\n\n"
                        break
                    idle_ticks += 1

                await asyncio.sleep(0.5)
        finally:
            conn.close()

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


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


def _build_label_lookup(db: sqlite3.Connection, chat_id: int, secret: str) -> dict[str, str]:
    """Map HMAC digest → 'AgentN' label, in the same order GroupChatSession assigns them."""
    import hashlib
    import hmac as _hmac

    agents = db.execute(
        """
        SELECT a.Name, a.Surname
        FROM Chat_agent ca
        JOIN Agents a ON ca.id_agent = a.ID
        WHERE ca.id_chat = ? AND a.deleted_at IS NULL
        """,
        (chat_id,),
    ).fetchall()
    lookup: dict[str, str] = {}
    for i, a in enumerate(agents, 1):
        digest = _hmac.new(
            secret.encode(),
            f"{a['Name']}:{a['Surname']}".encode(),
            hashlib.sha256,
        ).hexdigest()
        lookup[digest] = f"Agent{i}"
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
    author_to_label = _build_label_lookup(db, chat_id, settings.author_secret)

    result = []
    for m in rows:
        if m["Created_by"] is not None:
            kind = "user"
        elif m["author"]:
            kind = "agent"
        else:
            kind = "system"
        persona_id = author_to_agent.get(m["author"]) if m["author"] else None
        agent_label = author_to_label.get(m["author"]) if m["author"] else None
        result.append({
            "kind": kind,
            "text": m["message"],
            "author": m["author"],
            "persona_id": persona_id,
            "agent_label": agent_label,
            "ts": m["created_at"],
            "time": _short_time(m["created_at"]),
        })
    return result


@router.post("/ui/chats/{chat_id}/messages", status_code=201)
def ui_create_message(
    chat_id: int,
    body: UIMessageCreate,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    msg = ChatMessageService(db, settings.author_secret).create(
        id_chat=chat_id,
        message=body.text,
        created_by=current_user.id,
    )
    agent_count = db.execute(
        "SELECT COUNT(*) AS n FROM Chat_agent WHERE id_chat = ?", (chat_id,)
    ).fetchone()["n"]
    if agent_count == 1:
        _dm_run_agent_turn(db, chat_id, settings)
    elif body.text.strip().lower() in ("stop", "exit"):
        GroupChatService(db).set_status(chat_id, "stopped")
    else:
        chat = GroupChatService(db).get(chat_id)
        if chat and chat.status == "stopped":
            GroupChatService(db).set_status(chat_id, "running")
            background_tasks.add_task(
                _bg_run_conversation, chat_id, settings.db_path, settings.author_secret, _DEFAULT_TURNS
            )
    return {
        "kind": "user",
        "text": msg.message,
        "author": None,
        "ts": msg.created_at,
        "time": _short_time(msg.created_at),
    }


# ---------------------------------------------------------------------------
# Judge pipeline — background jobs + SSE stream
# ---------------------------------------------------------------------------

# chat_id → {"status": "running"|"done"|"error", "progress": 0-100, "result": {...}|None, "error": str|None}
_judge_jobs: dict[int, dict] = {}


def _build_ui_report(
    chat_id: int,
    pid_result: dict,
    fid_result: dict,
    grp_result: dict,
    author_map: dict[str, str],
    digest_to_agent_id: dict[str, int],
    messages: list[dict],
) -> dict:
    """Translate src/eval module outputs into the shape the UI JudgingModal expects."""
    # persona_id string → DB agent_id
    pid_to_agent_id: dict[str, int] = {pid: digest_to_agent_id[d] for d, pid in author_map.items() if d in digest_to_agent_id}

    # ── Persona ID ──────────────────────────────────────────────
    pi_agg = pid_result.get("persona_identification", {}).get("aggregate", {})
    accuracy = float(pi_agg.get("accuracy") or 0.0)
    ci_95 = pi_agg.get("ci_95") or [0.0, 0.0]
    cm_data = pid_result.get("persona_identification", {}).get("confusion_matrix", {})
    cm = cm_data.get("matrix") or []
    cm_labels = cm_data.get("labels") or []  # persona display names, same order as matrix rows/cols

    # ── Individual fidelity ──────────────────────────────────────
    per_persona = fid_result.get("individual_fidelity", {}).get("per_persona", {})
    # per_persona is keyed by persona display name ("Claire Dunphy")
    fidelity_rows = []
    for pname, stats in per_persona.items():
        overall = stats.get("overall", {})
        agent_id = pid_to_agent_id.get(pname, 0)
        ci = overall.get("ci_95") or [0.0, 0.0]
        fidelity_rows.append({
            "personaId": agent_id,
            "mean": float(overall.get("mean") or 0.0),
            "median": float(overall.get("median") or 0.0),
            "iqr": float(overall.get("iqr") or 0.0),
            "ciL": float(ci[0]),
            "ciH": float(ci[1]),
        })

    # ── Individual fidelity — judge type agreement ───────────────
    jta = fid_result.get("individual_fidelity", {}).get("judge_type_agreement", {})
    judge_type_agreement = {
        "medians": {k: round(float(v), 4) for k, v in (jta.get("judge_median_scores") or {}).items()},
        "mad": {k: round(float(v), 4) for k, v in (jta.get("mad_between_types") or {}).items()},
    }

    # ── Group fidelity ───────────────────────────────────────────
    gf = grp_result.get("group_fidelity", {})
    gini_data = gf.get("gini", {})
    gini = float(gini_data.get("gini") or 0.0)
    gini_ci_raw = gini_data.get("ci_95") or [0.0, 0.0]
    gini_z = float(gini_data.get("z_vs_reference") or 0.0)
    judge_scores_data = gf.get("judge_scores", {})

    # Turn distribution from raw messages
    turn_counts: dict[str, int] = {}
    for msg in messages:
        author = msg.get("author")
        if author and author in digest_to_agent_id:
            pid_str = author_map.get(author, "")
            turn_counts[pid_str] = turn_counts.get(pid_str, 0) + 1
    total_turns = sum(turn_counts.values())
    turn_shares = [
        {"personaId": pid_to_agent_id.get(pid, 0), "share": cnt / total_turns if total_turns else 0.0}
        for pid, cnt in turn_counts.items()
    ]

    # ── Persona ID — new metrics ──────────────────────────────────
    prf_data = cm_data.get("precision_recall_f1") or {}
    prf_per_persona = prf_data.get("per_persona") or {}
    # Attach prf to each cm label in order
    prf_rows = [
        {
            "label": lbl,
            "precision": float((prf_per_persona.get(lbl) or {}).get("precision") or 0.0),
            "recall":    float((prf_per_persona.get(lbl) or {}).get("recall")    or 0.0),
            "f1":        float((prf_per_persona.get(lbl) or {}).get("f1")        or 0.0),
        }
        for lbl in cm_labels
    ]
    judge_var = pid_result.get("persona_identification", {}).get("judge_accuracy_variance") or {}

    return {
        "sessionId": chat_id,
        "ranAt": datetime.now(timezone.utc).isoformat(),
        "accuracy": accuracy,
        "ciLow": float(ci_95[0]),
        "ciHigh": float(ci_95[1]),
        "pValue": float(pi_agg["p_value"]) if pi_agg.get("p_value") is not None else 1.0,
        "cohenKappa": float(cm_data.get("cohen_kappa") or 0.0),
        "macroF1": float(prf_data.get("macro_f1") or 0.0),
        "prfRows": prf_rows,
        "judgeVarMean": float(judge_var.get("mean") or 0.0),
        "judgeVarStd": float(judge_var.get("std") or 0.0),
        "cm": cm,
        "cmLabels": cm_labels,
        "fidelityRows": fidelity_rows,
        "judgeTypeAgreement": judge_type_agreement,
        "gini": gini,
        "giniZ": gini_z,
        "giniCI": [float(gini_ci_raw[0]), float(gini_ci_raw[1])],
        "groupFidelityMean": float(judge_scores_data.get("mean") or 0.0),
        "groupFidelityMedian": float(judge_scores_data.get("median") or 0.0),
        "groupFidelityCIL": float((judge_scores_data.get("ci_95") or [0.0, 0.0])[0]),
        "groupFidelityCIH": float((judge_scores_data.get("ci_95") or [0.0, 0.0])[1]),
        "driftScore": 0.0,
        "turnShares": turn_shares,
        # Phase 2 deliberation not yet implemented
        "convergenceRate": 0.0,
        "convCIL": 0.0,
        "convCIH": 0.0,
        "pearson": 0.0,
        "fTestP": 1.0,
        "calibration": [{"c": c, "acc": 0.0} for c in range(1, 6)],
    }


_EVAL_DIR = (
    # repo_root/data/eval/
    __import__("pathlib").Path(__file__).parents[4] / "data" / "eval"
)


class _NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        import numpy as np  # noqa: PLC0415
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, (np.bool_,)):
            return bool(obj)
        return super().default(obj)


def _save_eval_report(
    chat_id: int,
    records: list[dict],
    pid_result: dict,
    fid_result: dict,
    grp_result: dict,
    author_map: dict[str, str],
) -> None:
    """Write the full evaluation report to data/eval/chat_<id>/."""
    from pathlib import Path

    out_dir = _EVAL_DIR / f"chat_{chat_id}"
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Raw judge records — one JSON object per line (same format as eval_20j_N.jsonl)
    records_path = out_dir / "judge_records.jsonl"
    records_path.write_text(
        "\n".join(json.dumps(r, cls=_NumpyEncoder) for r in records),
        encoding="utf-8",
    )

    # 2. Full metrics report — all three eval modules merged
    full_report = {
        "chat_id": chat_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "author_map": author_map,
        **pid_result,
        **fid_result,
        **grp_result,
        "deliberation": {"note": "Phase 2 not yet implemented"},
    }
    report_path = out_dir / "metrics_report.json"
    report_path.write_text(
        json.dumps(full_report, indent=2, ensure_ascii=False, cls=_NumpyEncoder),
        encoding="utf-8",
    )
    log.info("eval report saved → %s", out_dir)


def _bg_run_judging(chat_id: int, db_path: str, author_secret: str) -> None:
    """Background task: run 20 real judges on a DB chat then compute metrics via src/eval."""
    _judge_jobs[chat_id] = {"status": "running", "progress": 2, "result": None, "error": None}
    _t_start = _time.monotonic()
    print(f"\n{'='*60}")
    print(f"  [chat {chat_id}] JUDGING START")
    print(f"{'='*60}")
    try:
        conn = get_connection(db_path)

        # Load agent messages only (author digest is set; user messages have Created_by)
        rows = conn.execute(
            """SELECT message, author FROM Chat_messages
               WHERE ID_Chat = ? AND deleted_at IS NULL AND author IS NOT NULL
               ORDER BY created_at ASC""",
            (chat_id,),
        ).fetchall()
        messages = [{"author": r["author"], "message": r["message"]} for r in rows]

        agents = conn.execute(
            """SELECT a.ID, a.Name, a.Surname, a.Summary
               FROM Chat_agent ca JOIN Agents a ON ca.id_agent = a.ID
               WHERE ca.id_chat = ? AND a.deleted_at IS NULL""",
            (chat_id,),
        ).fetchall()
        conn.close()

        # author_map: {digest: "Claire Dunphy"} — actual persona display name from DB
        author_map: dict[str, str] = {}
        digest_to_agent_id: dict[str, int] = {}

        for a in agents:
            digest = _hmac.new(
                author_secret.encode(),
                f"{a['Name']}:{a['Surname']}".encode(),
                hashlib.sha256,
            ).hexdigest()
            try:
                summary = json.loads(a["Summary"] or "{}")
            except Exception:
                summary = {}
            persona_name = summary.get("persona_name") or f"{a['Name']} {a['Surname']}"
            author_map[digest] = persona_name
            digest_to_agent_id[digest] = a["ID"]

        if not messages:
            _judge_jobs[chat_id] = {"status": "error", "progress": 0, "result": None, "error": "Chat has no agent messages"}
            return

        # Digests that actually appear in the chat — silent participants cannot be identified.
        active_digests = {msg["author"] for msg in messages}

        from ...rag.evaluation_test_20_judges import _load_all_profiles, run_evaluation_from_db_data
        from ...eval import metrics_persona_id, metrics_fidelity, metrics_group

        all_profiles = _load_all_profiles()
        _judge_jobs[chat_id]["progress"] = 5

        def _progress(done: int, total: int) -> None:
            _judge_jobs[chat_id]["progress"] = 5 + int(done / total * 80)

        chat = {"messages": messages}
        # Force-include only active participants — silent agents have no messages to match against.
        forced_names = [name for digest, name in author_map.items() if digest in active_digests]

        # Build speaker_stats and compute Gini before the judge pipeline so
        # the structural signal can be injected into each judge's prompt.
        speaker_stats: dict[str, dict] = {}
        for msg in messages:
            author = msg.get("author")
            if author and author in author_map:
                pid = author_map[author]
                speaker_stats.setdefault(pid, {"turns": 0})
                speaker_stats[pid]["turns"] += 1
        transcript_meta = {"speaker_stats": speaker_stats}
        grp_result = metrics_group.run(transcript_meta)
        gini_data = grp_result.get("group_fidelity", {}).get("gini")

        _t_llm_start = _time.monotonic()
        print(f"  [chat {chat_id}] ── LLM calls START  (20 judges × {len(all_profiles)} profiles → {len(forced_names or [])} forced)")
        records = run_evaluation_from_db_data(
            chat, all_profiles, chat_id, _progress,
            forced_names=forced_names,
            out_dir=_EVAL_DIR / f"chat_{chat_id}",
            gini_data=gini_data,
        )
        _t_llm_end = _time.monotonic()
        print(f"  [chat {chat_id}] ── LLM calls DONE   ({_t_llm_end - _t_llm_start:.1f}s)")
        _judge_jobs[chat_id]["progress"] = 88

        # ── Persist per-judge evaluations to DB ──────────────────────
        _conn_evals = get_connection(db_path)
        try:
            judge_rows = _conn_evals.execute(
                "SELECT ID, name FROM Judges WHERE deleted_at IS NULL AND name IS NOT NULL"
            ).fetchall()
            judge_name_to_id = {r["name"]: r["ID"] for r in judge_rows}
            svc_eval = JudgeEvaluationService(_conn_evals)
            for rec in records:
                if rec is None:
                    continue
                jid = judge_name_to_id.get(rec.get("judge_name"))
                if jid is None:
                    log.warning("No DB judge found for '%s' — skipping eval row", rec.get("judge_name"))
                    continue
                pi = rec.get("persona_identification")
                cands = rec.get("rag_candidates")
                gfs = rec.get("group_fidelity_score")
                if svc_eval.get(jid, chat_id) is None:
                    svc_eval.create(jid, chat_id, persona_identification=pi, rag_candidates=cands, group_fidelity_score=gfs)
                else:
                    svc_eval.update(jid, chat_id, {"persona_identification": pi, "rag_candidates": cands, "group_fidelity_score": gfs})
        finally:
            _conn_evals.close()

        # author_map is {digest: "Claire Dunphy"} — only map personas whose authors spoke.
        # Silent participants can never be identified correctly; excluding them prevents
        # their 20 guaranteed-wrong predictions from dragging down the accuracy denominator.
        name_to_author = {name: digest for digest, name in author_map.items() if digest in active_digests}
        chat_persona_names = sorted(name_to_author.keys())
        acc = metrics_persona_id.compute_accuracy(records, name_to_author)
        all_pairs = acc.pop("all_pairs")
        cm_data = metrics_persona_id.confusion_matrix(all_pairs, chat_persona_names)
        pid_result = {"persona_identification": {**acc, "confusion_matrix": cm_data}}

        agg = acc.get("aggregate", {})
        print(f"  [chat {chat_id}] ── accuracy: {agg.get('correct')}/{agg.get('total')} "
              f"= {agg.get('accuracy')} (baseline {agg.get('random_baseline')}, "
              f"p={agg.get('p_value')}, significant={agg.get('significant')})")
        for pj in acc.get("per_judge", []):
            mark = "✓" if pj.get("accuracy", 0) == 1.0 else ("~" if pj.get("accuracy", 0) > 0 else "✗")
            print(f"    {mark} {pj['judge_name']:20s} {pj['correct']}/{pj['total']} = {pj['accuracy']}")
        _t_metrics_start = _time.monotonic()
        print(f"  [chat {chat_id}] ── metrics START")
        _judge_jobs[chat_id]["progress"] = 93
        fid_result = metrics_fidelity.compute_fidelity(records, name_to_author)
        _judge_jobs[chat_id]["progress"] = 97
        grp_result["group_fidelity"].update(metrics_group.compute_judge_scores(records))
        _t_metrics_end = _time.monotonic()
        print(f"  [chat {chat_id}] ── metrics DONE     ({_t_metrics_end - _t_metrics_start:.1f}s)")

        result = _build_ui_report(chat_id, pid_result, fid_result, grp_result, author_map, digest_to_agent_id, messages)

        # ── Persist full report to data/eval/ ───────────────────────
        _save_eval_report(chat_id, records, pid_result, fid_result, grp_result, author_map)

        # ── Persist UI-shaped report so it survives server restarts ──
        ui_path = _EVAL_DIR / f"chat_{chat_id}" / "ui_report.json"
        ui_path.write_text(json.dumps(result, cls=_NumpyEncoder), encoding="utf-8")

        # ── Persist to DB (is_judged flag + report blob) ─────────────
        _conn_report = get_connection(db_path)
        try:
            GroupChatService(_conn_report).set_report(chat_id, result)
        finally:
            _conn_report.close()

        _t_total = _time.monotonic() - _t_start
        _t_llm = _t_llm_end - _t_llm_start
        _t_metrics = _t_metrics_end - _t_metrics_start
        print(f"\n{'='*60}")
        print(f"  [chat {chat_id}] JUDGING DONE")
        print(f"  LLM calls : {_t_llm/60:.1f}m  ({_t_llm:.1f}s)")
        print(f"  Metrics   : {_t_metrics:.1f}s")
        print(f"  Total     : {_t_total/60:.1f}m  ({_t_total:.1f}s)")
        print(f"{'='*60}\n")
        _judge_jobs[chat_id] = {"status": "done", "progress": 100, "result": result, "error": None}

    except Exception as exc:
        _t_total = _time.monotonic() - _t_start
        print(f"\n{'='*60}")
        print(f"  [chat {chat_id}] JUDGING ERROR after {_t_total:.1f}s: {exc}")
        print(f"{'='*60}\n")
        log.exception("judge pipeline failed for chat %d", chat_id)
        _judge_jobs[chat_id] = {"status": "error", "progress": 0, "result": None, "error": str(exc)}


def _reconstruct_ui_report(
    chat_id: int,
    metrics: dict,
    db: sqlite3.Connection,
    author_secret: str,
) -> dict:
    """Rebuild the UI report shape from a saved metrics_report.json + DB."""
    import hashlib
    import hmac as _hmac_mod

    author_map: dict[str, str] = metrics.get("author_map") or {}

    agents = db.execute(
        """SELECT a.ID, a.Name, a.Surname
           FROM Chat_agent ca JOIN Agents a ON ca.id_agent = a.ID
           WHERE ca.id_chat = ? AND a.deleted_at IS NULL""",
        (chat_id,),
    ).fetchall()
    digest_to_agent_id: dict[str, int] = {}
    for a in agents:
        digest = _hmac_mod.new(
            author_secret.encode(),
            f"{a['Name']}:{a['Surname']}".encode(),
            hashlib.sha256,
        ).hexdigest()
        digest_to_agent_id[digest] = a["ID"]

    rows = db.execute(
        """SELECT message, author FROM Chat_messages
           WHERE ID_Chat = ? AND deleted_at IS NULL AND author IS NOT NULL
           ORDER BY created_at ASC""",
        (chat_id,),
    ).fetchall()
    messages = [{"author": r["author"], "message": r["message"]} for r in rows]

    pid_result = {"persona_identification": metrics.get("persona_identification", {})}
    fid_result = {"individual_fidelity": metrics.get("individual_fidelity", {})}
    grp_result = {"group_fidelity": metrics.get("group_fidelity", {})}

    report = _build_ui_report(
        chat_id, pid_result, fid_result, grp_result,
        author_map, digest_to_agent_id, messages,
    )
    # Patch in the original timestamp if available
    if metrics.get("generated_at"):
        report["ranAt"] = metrics["generated_at"]
    return report


@router.get("/admin/judged-chats")
def admin_judged_chats(
    db: sqlite3.Connection = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Return {chat_id: ui_report} for every chat that has a saved evaluation."""
    result: dict[int, dict] = {}

    # Primary path: read from DB (is_judged = 1)
    rows = db.execute(
        "SELECT ID, report FROM Group_chat WHERE is_judged = 1 AND report IS NOT NULL AND deleted_at IS NULL"
    ).fetchall()
    for row in rows:
        try:
            result[row["ID"]] = json.loads(row["report"])
        except Exception:
            log.exception("failed to parse report for chat %d", row["ID"])

    # Backward-compat path: file-based reports not yet migrated to DB
    if _EVAL_DIR.exists():
        for d in sorted(_EVAL_DIR.iterdir()):
            if not (d.is_dir() and d.name.startswith("chat_")):
                continue
            try:
                chat_id = int(d.name.split("_", 1)[1])
            except ValueError:
                continue
            if chat_id in result:
                continue  # already loaded from DB

            ui_path = d / "ui_report.json"
            if ui_path.exists():
                try:
                    result[chat_id] = json.loads(ui_path.read_text(encoding="utf-8"))
                    continue
                except Exception:
                    pass

            metrics_path = d / "metrics_report.json"
            if not metrics_path.exists():
                continue
            try:
                metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
                report = _reconstruct_ui_report(chat_id, metrics, db, settings.author_secret)
                ui_path.write_text(json.dumps(report, cls=_NumpyEncoder), encoding="utf-8")
                result[chat_id] = report
            except Exception:
                log.exception("failed to reconstruct UI report for chat %d", chat_id)

    return result


@router.post("/admin/judge-chat/{chat_id}", status_code=202)
def admin_start_judging(
    chat_id: int,
    background_tasks: BackgroundTasks,
    db: sqlite3.Connection = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    chat = db.execute(
        "SELECT ID FROM Group_chat WHERE ID = ? AND deleted_at IS NULL", (chat_id,)
    ).fetchone()
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")

    job = _judge_jobs.get(chat_id)
    if job and job["status"] == "running":
        raise HTTPException(status_code=409, detail="Judging already in progress")

    background_tasks.add_task(_bg_run_judging, chat_id, settings.db_path, settings.author_secret)
    return {"chat_id": chat_id, "status": "running"}


@router.get("/admin/judge-chat/{chat_id}/stream")
async def admin_judge_stream(chat_id: int):
    async def generate():
        idle = 0
        while idle < 600:  # max 5 min
            job = _judge_jobs.get(chat_id)
            if job is None:
                idle += 1
                await asyncio.sleep(0.5)
                continue

            status = job["status"]
            progress = job.get("progress", 0)

            if status == "running":
                idle = 0
                yield f"data: {json.dumps({'type': 'progress', 'progress': progress})}\n\n"
                await asyncio.sleep(0.5)
            elif status == "done":
                yield f"data: {json.dumps({'type': 'result', 'result': job['result']})}\n\n"
                yield "event: done\ndata: {}\n\n"
                break
            elif status == "error":
                yield f"data: {json.dumps({'type': 'error', 'error': job.get('error', 'Unknown error')})}\n\n"
                yield "event: done\ndata: {}\n\n"
                break
            else:
                idle += 1
                await asyncio.sleep(0.5)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/admin/judge-chat/{chat_id}/status")
def admin_judge_status(chat_id: int) -> dict:
    """Poll judging job status without SSE. Safe to call repeatedly until status='done'."""
    job = _judge_jobs.get(chat_id)
    if job is None:
        return {"status": "not_started", "progress": 0, "error": None}
    return {
        "status": job["status"],
        "progress": job.get("progress", 0),
        "error": job.get("error"),
    }


@router.get("/admin/judged-chats/{chat_id}")
def admin_judged_chat(
    chat_id: int,
    db: sqlite3.Connection = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Return the persisted evaluation report for a single chat. 404 if not judged yet."""
    row = db.execute(
        "SELECT report FROM Group_chat WHERE ID = ? AND is_judged = 1 AND report IS NOT NULL AND deleted_at IS NULL",
        (chat_id,),
    ).fetchone()
    if row is not None:
        try:
            return json.loads(row["report"])
        except Exception:
            log.exception("failed to parse report for chat %d", chat_id)

    # File-based fallback
    chat_dir = _EVAL_DIR / f"chat_{chat_id}"
    ui_path = chat_dir / "ui_report.json"
    if ui_path.exists():
        try:
            return json.loads(ui_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    metrics_path = chat_dir / "metrics_report.json"
    if metrics_path.exists():
        try:
            metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
            return _reconstruct_ui_report(chat_id, metrics, db, settings.author_secret)
        except Exception:
            pass

    raise HTTPException(status_code=404, detail="No evaluation report found for this chat")


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
        SELECT gc.ID, gc.created_at, gc.is_judged,
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
            "id": c["ID"],
            "display_id": f"S-{c['ID']:04d}",
            "participants": [a["ID"] for a in agents],
            "topic": meta.get("title") or c["topic_title"],
            "duration": "00:00:00",
            "date": (c["created_at"] or "")[:16].replace("T", " "),
            "status": "complete",
            "is_judged": bool(c["is_judged"]),
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
