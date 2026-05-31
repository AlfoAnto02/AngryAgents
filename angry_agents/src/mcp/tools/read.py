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

    # ── Admin dashboard ───────────────────────────────────────────────────────

    @mcp.tool()
    async def get_admin_overview() -> dict[str, Any]:
        """[Tier 1 — Admin] Platform overview: sessions today, active users, avg session, judge confidence."""
        return await _get("/admin/overview")

    @mcp.tool()
    async def get_admin_sessions(limit: int = 24) -> list[dict[str, Any]]:
        """[Tier 1 — Admin] List recent chat sessions with display_id, topic, date, and is_judged flag.
        Use is_judged to find chats ready for evaluation or already evaluated."""
        return await _get("/admin/sessions", {"limit": limit})

    @mcp.tool()
    async def get_admin_agent_performance() -> list[dict[str, Any]]:
        """[Tier 1 — Admin] Per-agent session count and fidelity metrics."""
        return await _get("/admin/agent-performance")

    # ── Judge evaluation ──────────────────────────────────────────────────────

    @mcp.tool()
    async def get_judged_chats() -> dict[str, Any]:
        """[Tier 1 — Admin] Return all chats that have a completed evaluation report.
        Keys are chat IDs (as strings). Each value is the full ui_report with accuracy,
        fidelityRows, gini, confusion matrix, etc."""
        return await _get("/admin/judged-chats")

    @mcp.tool()
    async def get_judge_result(chat_id: int) -> dict[str, Any]:
        """[Tier 1 — Admin] Return the evaluation report for a single chat.
        Contains: accuracy, ciLow, ciHigh, pValue, cohenKappa, macroF1, prfRows,
        fidelityRows (mean/median/IQR/CI per persona), gini, giniZ, giniCI, turnShares, cm, cmLabels.
        Raises 404 if judging has not completed for this chat."""
        return await _get(f"/admin/judged-chats/{chat_id}")

    @mcp.tool()
    async def get_judge_status(chat_id: int) -> dict[str, Any]:
        """[Tier 1 — Admin] Poll the judging job status for a chat without blocking.
        Returns: status ('not_started' | 'running' | 'done' | 'error'), progress (0–100), error (str | null).
        Call repeatedly until status='done', then use get_judge_result to fetch the full report."""
        return await _get(f"/admin/judge-chat/{chat_id}/status")
