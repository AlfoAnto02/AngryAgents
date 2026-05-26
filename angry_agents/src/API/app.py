from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ..db.models.base import get_connection, init_db
from .config import get_settings
from .routes import (
    auth,
    users,
    agent_context,
    agents,
    chat_messages,
    group_chats,
    judge_evaluations,
    judges,
    topics,
    ui_routes,
)

def _setup_logging() -> None:
    level = getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(levelname)-8s %(name)s | %(message)s",
    )
    # suppress noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _setup_logging()
    settings = get_settings()
    conn = get_connection(settings.db_path)
    init_db(conn)
    conn.close()
    yield


_tags_metadata = [
    {
        "name": "auth",
        "description": "Registration, login, and current-user lookup. Login returns a `slug` to send as `X-User-Slug` header.",
    },
    {
        "name": "users",
        "description": "User management (admin). Registration is at `/auth/register`.",
    },
    {
        "name": "topics",
        "description": "Conversation topics. Agents and group chats are scoped to a topic.",
    },
    {
        "name": "agents",
        "description": (
            "Persona agents (fiction or real-world). "
            "Each agent belongs to exactly one topic. "
            "Slug is auto-generated from name+surname and is URL-safe."
        ),
    },
    {
        "name": "agent-context",
        "description": (
            "Source material context attached to an agent "
            "(signature phrases, extracted from 10k–50k token corpora)."
        ),
    },
    {
        "name": "chats",
        "description": "Group chat sessions. One topic → many chats.",
    },
    {
        "name": "messages",
        "description": (
            "Chat messages inside a group chat. "
            "The `author` field is an anonymised HMAC token — "
            "judges see source diversity without knowing the real agent identity."
        ),
    },
    {
        "name": "judges",
        "description": (
            "Evaluation judges. Role must be one of: "
            "`style` | `ideology` | `general` | `behavioral`."
        ),
    },
    {
        "name": "evaluations",
        "description": (
            "Judge evaluations on a group chat. "
            "Composite key (id_judge, id_chat). "
            "Max 20 evaluations per chat — enforced at service level."
        ),
    },
]

app = FastAPI(
    title="Angry Agents API",
    lifespan=lifespan,
    description=(
        "REST API for the Angry Agents chat platform. "
        "Users talk to AI persona-agents (DM or group). "
        "20 judge-agents evaluate conversations independently, "
        "then enter structured deliberation on high-variance cases."
    ),
    version="0.1.0",
    openapi_tags=_tags_metadata,
    swagger_ui_parameters={"defaultModelsExpandDepth": 1, "docExpansion": "list"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(topics.router, prefix="/topics", tags=["topics"])
app.include_router(agents.router, prefix="/agents", tags=["agents"])
app.include_router(agent_context.router, prefix="/contexts", tags=["agent-context"])
app.include_router(group_chats.router, prefix="/chats", tags=["chats"])
app.include_router(chat_messages.router, tags=["messages"])
app.include_router(judges.router, prefix="/judges", tags=["judges"])
app.include_router(judge_evaluations.router, prefix="/evaluations", tags=["evaluations"])
app.include_router(ui_routes.router, tags=["ui"])
