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
        "Never update, delete, access judge data, or call endpoints outside the defined tools."
    ),
)

register_read(mcp)
register_write(mcp)

if __name__ == "__main__":
    mcp.run()
