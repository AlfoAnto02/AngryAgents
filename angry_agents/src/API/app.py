from __future__ import annotations

from fastapi import FastAPI

from .routes import (
    agent_context,
    agents,
    chat_messages,
    group_chats,
    judge_evaluations,
    judges,
    topics,
)

app = FastAPI(title="Angry Agents API")

app.include_router(topics.router, prefix="/topics", tags=["topics"])
app.include_router(agents.router, prefix="/agents", tags=["agents"])
app.include_router(agent_context.router, prefix="/contexts", tags=["agent-context"])
app.include_router(group_chats.router, prefix="/chats", tags=["chats"])
app.include_router(chat_messages.router, tags=["messages"])
app.include_router(judges.router, prefix="/judges", tags=["judges"])
app.include_router(judge_evaluations.router, prefix="/evaluations", tags=["evaluations"])
