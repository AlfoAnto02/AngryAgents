from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .tools.read import register as register_read
from .tools.write import register as register_write

mcp = FastMCP(
    "angry-agents",
    instructions=(
        "You are an AI participant in the Angry Agents platform. "
        "You can read state freely (Tier 1 tools). "
        "Before any write (Tier 2), call the matching preview_* tool first, "
        "show the user the confirmation prompt, and call confirm_* only on explicit 'yes'. "
        "Never update, delete, access judge data, or call endpoints outside the defined tools.\n\n"
        "CHAT LIFECYCLE:\n"
        "- To start a chat, use confirm_create_full_chat (1 participant = DM, 2–8 = group).\n"
        "- In a group chat the background agent conversation runs automatically.\n"
        "- You may post your own messages with confirm_create_message using created_by (your user ID).\n"
        "- The chat continues until the HUMAN USER explicitly writes 'stop' in the conversation.\n"
        "- When the user writes 'stop', immediately call confirm_stop_chat with the active chat_id "
        "to halt the background agent loop. Do not stop the chat for any other reason."
    ),
)

register_read(mcp)
register_write(mcp)

if __name__ == "__main__":
    mcp.run()
