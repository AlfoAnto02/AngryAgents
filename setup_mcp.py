"""
setup_mcp.py — generate .mcp.json for this machine.

Run once after cloning, with the venv activated:
    python setup_mcp.py

This writes a .mcp.json pointing to the correct Python executable and
project root for the current machine. The file is git-ignored; each
team member generates their own.
"""

import json
import pathlib
import sys

root = pathlib.Path(__file__).parent.resolve()
python = sys.executable

config = {
    "mcpServers": {
        "angry-agents": {
            "command": str(python),
            "args": ["-m", "angry_agents.src.mcp.mcp_server"],
            "cwd": str(root),
        }
    }
}

out = root / ".mcp.json"
out.write_text(json.dumps(config, indent=2), encoding="utf-8")

print(f"Written  {out}")
print(f"Python   {python}")
print(f"CWD      {root}")
print()
print("Restart Claude Code to pick up the new MCP server.")
