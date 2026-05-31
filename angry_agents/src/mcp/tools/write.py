from __future__ import annotations

"""
Tier 2 write tools — each action has TWO tools:
  preview_*  → returns the payload for user inspection (no side effects)
  confirm_*  → executes only after the user has approved the preview

Never call confirm_* without first showing the user the preview output and
receiving explicit confirmation. Never bundle multiple confirms in one step.
"""

from typing import Any

from mcp.server.fastmcp import FastMCP

from ..client import _patch, _post


def register(mcp: FastMCP) -> None:

    # ── create_topic ──────────────────────────────────────────────────────────

    @mcp.tool()
    async def preview_create_topic(
        title: str,
        description: str | None = None,
    ) -> dict[str, Any]:
        """[Tier 2 — PREVIEW] Show what will be sent before creating a topic.
        Display this to the user and ask for explicit 'yes' before calling confirm_create_topic."""
        return {
            "action": "create_topic",
            "payload": {"title": title, "description": description},
            "instructions": (
                "Show the user:\n"
                "[CONFIRMATION REQUIRED]\n"
                f"Action  : Create a new topic titled '{title}'\n"
                f"Payload : {{\"title\": \"{title}\", \"description\": \"{description}\"}}\n\n"
                "Proceed? (yes / no) >\n\n"
                "Call confirm_create_topic only if user answers 'yes'."
            ),
        }

    @mcp.tool()
    async def confirm_create_topic(
        title: str,
        description: str | None = None,
    ) -> dict[str, Any]:
        """[Tier 2 — EXECUTE] Create a new topic. Call ONLY after user confirmed the preview.
        Topic titles are unique — check get_topics first to avoid duplicates."""
        return await _post("/topics", {"title": title, "description": description})

    # ── create_full_chat ──────────────────────────────────────────────────────
    # Creates a chat with participant selection. 1 participant = DM, 2–8 = group.
    # Group chats auto-start a background agent conversation.

    @mcp.tool()
    async def preview_create_full_chat(
        participants: list[int],
        topics: list[str] | None = None,
        tone: str = "Debate",
        opener: str | None = None,
        created_by: int | None = None,
    ) -> dict[str, Any]:
        """[Tier 2 — PREVIEW] Show what will be sent before creating a DM or group chat.
        participants: list of agent IDs — 1 = DM, 2–8 = group chat.
        created_by: optional user ID to post as (LLM user identity).
        Display this to the user and ask for explicit 'yes' before calling confirm_create_full_chat."""
        topics = topics or []
        chat_type = "DM" if len(participants) == 1 else "group"
        return {
            "action": "create_full_chat",
            "payload": {
                "participants": participants,
                "topics": topics,
                "tone": tone,
                "opener": opener,
                "created_by": created_by,
            },
            "instructions": (
                "Show the user:\n"
                "[CONFIRMATION REQUIRED]\n"
                f"Action  : Create a {chat_type} chat with {len(participants)} participant(s)\n"
                f"Participants: {participants}\n"
                f"Topics  : {topics}\n"
                f"Opener  : {opener!r}\n\n"
                "Proceed? (yes / no) >\n\n"
                "Call confirm_create_full_chat only if user answers 'yes'."
            ),
        }

    @mcp.tool()
    async def confirm_create_full_chat(
        participants: list[int],
        topics: list[str] | None = None,
        tone: str = "Debate",
        opener: str | None = None,
        created_by: int | None = None,
    ) -> dict[str, Any]:
        """[Tier 2 — EXECUTE] Create a DM or group chat with participant selection.
        Call ONLY after user confirmed the preview.
        1 participant = DM chat. 2–8 participants = group chat (auto-starts background conversation).
        Use get_agents first to find valid agent IDs."""
        return await _post(
            "/ui/chats/create-for-llm",
            {
                "participants": participants,
                "topics": topics or [],
                "tone": tone,
                "opener": opener,
                "created_by": created_by,
            },
        )

    # ── create_message ────────────────────────────────────────────────────────

    @mcp.tool()
    async def preview_create_message(
        chat_id: int,
        message: str,
        agent_id: int | None = None,
        created_by: int | None = None,
    ) -> dict[str, Any]:
        """[Tier 2 — PREVIEW] Show what will be sent before posting a message.
        Provide either agent_id (post as a persona) OR created_by (post as yourself/LLM user).
        Display this to the user and ask for explicit 'yes' before calling confirm_create_message.
        Read the chat messages first (get_chat_messages) to avoid breaking narrative continuity."""
        if agent_id is None and created_by is None:
            return {"error": "Provide either agent_id or created_by — not both, not neither."}
        if agent_id is not None and created_by is not None:
            return {"error": "agent_id and created_by are mutually exclusive."}
        author = f"agent id={agent_id}" if agent_id is not None else f"user id={created_by}"
        return {
            "action": "create_message",
            "payload": {"chat_id": chat_id, "agent_id": agent_id, "created_by": created_by, "message": message},
            "instructions": (
                "Show the user:\n"
                "[CONFIRMATION REQUIRED]\n"
                f"Action  : Post a message to chat id={chat_id} as {author}\n"
                f"Payload : {{\"chat_id\": {chat_id}, \"agent_id\": {agent_id}, "
                f"\"created_by\": {created_by}, "
                f"\"message\": \"{message[:80]}{'...' if len(message) > 80 else ''}\"}}\n\n"
                "Proceed? (yes / no) >\n\n"
                "Call confirm_create_message only if user answers 'yes'."
            ),
        }

    @mcp.tool()
    async def confirm_create_message(
        chat_id: int,
        message: str,
        agent_id: int | None = None,
        created_by: int | None = None,
    ) -> dict[str, Any]:
        """[Tier 2 — EXECUTE] Post a message to a chat. Call ONLY after user confirmed.
        Provide either agent_id (speak as a persona) OR created_by (speak as yourself).
        The author token in the response is HMAC-anonymised for agent messages; NULL for user messages."""
        return await _post(
            f"/chats/{chat_id}/messages",
            {"agent_id": agent_id, "created_by": created_by, "message": message},
        )

    # ── stop_chat ─────────────────────────────────────────────────────────────

    @mcp.tool()
    async def preview_stop_chat(chat_id: int) -> dict[str, Any]:
        """[Tier 2 — PREVIEW] Show what will happen before stopping a chat.
        Stopping sets status='stopped', halting the background agent conversation loop.
        Display this to the user and ask for explicit 'yes' before calling confirm_stop_chat."""
        return {
            "action": "stop_chat",
            "payload": {"chat_id": chat_id, "status": "stopped"},
            "instructions": (
                "Show the user:\n"
                "[CONFIRMATION REQUIRED]\n"
                f"Action  : Stop chat id={chat_id} (halts background agent turns)\n\n"
                "Proceed? (yes / no) >\n\n"
                "Call confirm_stop_chat only if user answers 'yes'."
            ),
        }

    @mcp.tool()
    async def confirm_stop_chat(chat_id: int) -> dict[str, Any]:
        """[Tier 2 — EXECUTE] Stop a chat by setting status='stopped'.
        Call ONLY after user confirmed the preview.
        The background agent conversation loop will halt within its next iteration (~0.5s)."""
        return await _patch(f"/chats/{chat_id}", {"status": "stopped"})

    # ── start_judging ─────────────────────────────────────────────────────────

    @mcp.tool()
    async def preview_start_judging(chat_id: int) -> dict[str, Any]:
        """[Tier 2 — PREVIEW] Show what will happen before starting the judge evaluation pipeline.
        WARNING: Judging runs 20 LLM judges against all chat messages — costs ~$0.40 and takes ~9 minutes.
        Display this to the user and ask for explicit 'yes' before calling confirm_start_judging."""
        return {
            "action": "start_judging",
            "payload": {"chat_id": chat_id},
            "instructions": (
                "Show the user:\n"
                "[CONFIRMATION REQUIRED]\n"
                f"Action  : Start judge evaluation pipeline for chat id={chat_id}\n"
                f"Cost    : ~$0.40 in LLM API calls\n"
                f"Time    : ~9 minutes (runs in background)\n\n"
                "After confirming, poll get_judge_status(chat_id) until status='done',\n"
                "then call get_judge_result(chat_id) to fetch the full evaluation report.\n\n"
                "Proceed? (yes / no) >\n\n"
                "Call confirm_start_judging only if user answers 'yes'."
            ),
        }

    @mcp.tool()
    async def confirm_start_judging(chat_id: int) -> dict[str, Any]:
        """[Tier 2 — EXECUTE] Start the judge evaluation pipeline for a chat.
        Call ONLY after user confirmed the preview.
        Returns immediately with status='running'. Poll get_judge_status(chat_id) for progress,
        then get_judge_result(chat_id) once done."""
        return await _post(f"/admin/judge-chat/{chat_id}", {})
