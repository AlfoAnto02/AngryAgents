from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from ..client import _get


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    async def get_agents(
        id_topic: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """[Tier 1] List persona agents (compact — no summary). Filter by id_topic to narrow to one topic.
        Use get_agent_by_id or get_agent_by_slug to fetch the full profile for a specific agent."""
        agents = await _get("/agents", {"id_topic": id_topic, "limit": limit, "offset": offset})
        for a in agents:
            a.pop("summary", None)
        return agents

    @mcp.tool()
    async def get_agent_by_id(id: int) -> dict[str, Any]:
        """[Tier 1] Retrieve a single agent by numeric ID."""
        return await _get(f"/agents/{id}")

    @mcp.tool()
    async def get_agent_by_slug(slug: str) -> dict[str, Any]:
        """[Tier 1] Retrieve a single agent by slug (e.g. 'walter-white')."""
        return await _get(f"/agents/slug/{slug}")

    @mcp.tool()
    async def get_agent_contexts(
        id_agent: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """[Tier 1] List agent context records (signature phrases, source corpus metadata)."""
        return await _get("/contexts", {"id_agent": id_agent, "limit": limit, "offset": offset})

    @mcp.tool()
    async def get_topics(limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        """[Tier 1] List all topics. Start here to discover available domains."""
        return await _get("/topics", {"limit": limit, "offset": offset})

    @mcp.tool()
    async def get_topic_by_id(id: int) -> dict[str, Any]:
        """[Tier 1] Retrieve a single topic by numeric ID."""
        return await _get(f"/topics/{id}")

    @mcp.tool()
    async def get_chats(
        id_topic: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """[Tier 1] List group chat sessions. Filter by id_topic to see chats in one domain."""
        return await _get("/chats", {"id_topic": id_topic, "limit": limit, "offset": offset})

    @mcp.tool()
    async def get_chat_by_id(id: int) -> dict[str, Any]:
        """[Tier 1] Retrieve a single group chat by ID."""
        return await _get(f"/chats/{id}")

    @mcp.tool()
    async def get_chat_messages(
        chat_id: int,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """[Tier 1] List all messages in a chat ordered by creation time.
        The author field is an anonymised HMAC token — do not attempt to reverse-engineer it."""
        return await _get(f"/chats/{chat_id}/messages", {"limit": limit, "offset": offset})
