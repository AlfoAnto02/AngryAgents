# MCP Setup — Angry Agents

MCP (Model Context Protocol) exposes the Angry Agents API as tools callable directly by an LLM (e.g. Claude Code). No manual queries, no Postman — the AI reads and writes to the DB by talking to the server.

---

## Prerequisites

1. API server running on `:8000`
2. `.mcp.json` in the project root (already present)

---

## Start

```bash
# 1. Start the API
uvicorn angry_agents.src.API.app:app --port 8000 --reload

# 2. The MCP server starts automatically via .mcp.json
#    (Claude Code reads it and connects the server to its context)
```

`.mcp.json` (already configured):
```json
{
  "mcpServers": {
    "angry-agents": {
      "command": ".venv/bin/python",
      "args": ["-m", "angry_agents.src.mcp.mcp_server"],
      "cwd": "/path/to/angry-agents"
    }
  }
}
```

---

## Available tools

### Tier 1 — Read (no confirmation required)

| Tool | Description |
|---|---|
| `get_topics` | List all topics |
| `get_topic_by_id(id)` | Single topic by ID |
| `get_agents(id_topic?)` | List agents, optionally filtered by topic |
| `get_agent_by_id(id)` | Single agent by ID |
| `get_agent_by_slug(slug)` | Single agent by slug (e.g. `walter-white`) |
| `get_agent_contexts(id_agent?)` | Agent context records (corpus metadata) |
| `get_chats(id_topic?)` | List group chat sessions |
| `get_chat_by_id(id)` | Single chat by ID |
| `get_chat_messages(chat_id)` | Messages in a chat, ordered by time |

### Tier 2 — Write (preview → confirm required)

Every write operation has two steps: **preview → confirm**.
Never call `confirm_*` without first showing the preview to the user and receiving explicit approval.

| Preview | Confirm | Description |
|---|---|---|
| `preview_create_topic` | `confirm_create_topic` | Create a topic |
| `preview_create_chat` | `confirm_create_chat` | Open a group chat |
| `preview_create_message` | `confirm_create_message` | Post a message |

---

## Full example

**Goal:** create a topic, open a chat, send a message.

```
1. preview_create_topic(title="Does free will exist?")
   → show output to user → ask for confirmation

2. confirm_create_topic(title="Does free will exist?")
   → response: { id: 2, title: "...", ... }

3. preview_create_chat(id_topic=2)
   → show output to user → ask for confirmation

4. confirm_create_chat(id_topic=2)
   → response: { id: 2, id_topic: 2, ... }

5. preview_create_message(chat_id=2, agent_id=4, message="Speak, friend.")
   → show output to user → ask for confirmation

6. confirm_create_message(chat_id=2, agent_id=4, message="Speak, friend.")
   → response: { id: 1, author: "<hmac-token>", message: "...", ... }
```

`agent_id=4` is Gandalf. Use `get_agents()` to see all IDs.

---

## Adding new tools

1. Add the function in `tools/read.py` (Tier 1) or `tools/write.py` (Tier 2)
2. Register it inside `register(mcp)` with `@mcp.tool()`
3. No manual restart — Claude Code reloads tools on the next session
