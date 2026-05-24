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

from ..client import _post


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

    # ── create_chat ───────────────────────────────────────────────────────────

    @mcp.tool()
    async def preview_create_chat(id_topic: int) -> dict[str, Any]:
        """[Tier 2 — PREVIEW] Show what will be sent before opening a group chat.
        Display this to the user and ask for explicit 'yes' before calling confirm_create_chat."""
        return {
            "action": "create_chat",
            "payload": {"id_topic": id_topic},
            "instructions": (
                "Show the user:\n"
                "[CONFIRMATION REQUIRED]\n"
                f"Action  : Open a new group chat under topic id={id_topic}\n"
                f"Payload : {{\"id_topic\": {id_topic}}}\n\n"
                "Proceed? (yes / no) >\n\n"
                "Call confirm_create_chat only if user answers 'yes'."
            ),
        }

    @mcp.tool()
    async def confirm_create_chat(id_topic: int) -> dict[str, Any]:
        """[Tier 2 — EXECUTE] Open a new group chat. Call ONLY after user confirmed the preview.
        Verify the topic exists with get_topic_by_id before calling."""
        return await _post("/chats", {"id_topic": id_topic})

    # ── create_message ────────────────────────────────────────────────────────

    @mcp.tool()
    async def preview_create_message(
        chat_id: int,
        agent_id: int,
        message: str,
    ) -> dict[str, Any]:
        """[Tier 2 — PREVIEW] Show what will be sent before posting a message.
        Display this to the user and ask for explicit 'yes' before calling confirm_create_message.
        Read the chat messages first (get_chat_messages) to avoid breaking narrative continuity."""
        return {
            "action": "create_message",
            "payload": {"chat_id": chat_id, "agent_id": agent_id, "message": message},
            "instructions": (
                "Show the user:\n"
                "[CONFIRMATION REQUIRED]\n"
                f"Action  : Post a message to chat id={chat_id} as agent id={agent_id}\n"
                f"Payload : {{\"chat_id\": {chat_id}, \"agent_id\": {agent_id}, "
                f"\"message\": \"{message[:80]}{'...' if len(message) > 80 else ''}\"}}\n\n"
                "Proceed? (yes / no) >\n\n"
                "Call confirm_create_message only if user answers 'yes'."
            ),
        }

    @mcp.tool()
    async def confirm_create_message(
        chat_id: int,
        agent_id: int,
        message: str,
    ) -> dict[str, Any]:
        """[Tier 2 — EXECUTE] Post a message to a group chat. Call ONLY after user confirmed.
        The author token in the response is HMAC-anonymised — do not try to reverse-engineer it."""
        return await _post(f"/chats/{chat_id}/messages", {"agent_id": agent_id, "message": message})
