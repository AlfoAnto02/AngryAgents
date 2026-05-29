# MCP Layer — Angry Agents

## What it is

MCP (Model Context Protocol) is an open standard that lets any compatible LLM interact with external systems through structured tool calls. In this project, the MCP layer exposes Angry Agents functionality so an LLM client can read platform state and create chats, topics, and messages — always requiring explicit user confirmation before any write operation.

Any MCP-compatible client works: Claude Code, Claude Desktop, or any other host that implements the protocol.

---

## Architecture

```
LLM client (MCP host)
        │
        │  tool call (JSON over stdio)
        ▼
angry_agents/src/mcp/mcp_server.py   ← FastMCP server
        │
        ├── tools/read.py             ← Tier 1: free reads
        └── tools/write.py            ← Tier 2: writes via preview → confirm
                │
                ▼
        client.py                     ← _get / _post / _patch via httpx
                │
                ▼
        FastAPI REST API (localhost:8000)
                │
                ▼
        SQLite DB
```

The MCP server runs as a separate process launched by the MCP host via `.mcp.json`. The LLM calls tools over stdio; the server makes HTTP requests to the FastAPI REST API.

---

## Files

| File | Role |
|---|---|
| `mcp_server.py` | FastMCP entry point — registers tools, defines system instructions |
| `client.py` | HTTP helpers: `_get`, `_post`, `_patch` via httpx |
| `tools/read.py` | Tier 1 tools (read-only) |
| `tools/write.py` | Tier 2 tools (writes with preview/confirm) |
| `.mcp.json` | MCP host config — command and cwd for the server process |

---

## Available tools

### Tier 1 — Read (no confirmation required)

| Tool | Endpoint | Returns |
|---|---|---|
| `get_agents` | `GET /agents` | Agent list **without** `summary` field (compact) |
| `get_agent_by_id(id)` | `GET /agents/{id}` | Full profile for one agent |
| `get_agent_by_slug(slug)` | `GET /agents/slug/{slug}` | Full profile by slug |
| `get_agent_contexts(id_agent)` | `GET /contexts` | Agent context records (signature phrases) |
| `get_topics` | `GET /topics` | Topic list |
| `get_topic_by_id(id)` | `GET /topics/{id}` | Single topic |
| `get_chats(id_topic)` | `GET /chats` | Group chat list |
| `get_chat_by_id(id)` | `GET /chats/{id}` | Single chat |
| `get_chat_messages(chat_id)` | `GET /chats/{chat_id}/messages` | Messages in a chat |

> **Note on `get_agents`**: the `summary` field (full JSON persona profile, 10k–50k tokens per agent) is stripped from the list response to prevent context overflow. Use `get_agent_by_id` or `get_agent_by_slug` for the full profile of a specific agent.

---

### Tier 2 — Write (preview → explicit confirmation → execute)

Every write action has **two** tools:
- `preview_*` — returns the payload that will be sent; the LLM shows it to the user
- `confirm_*` — executes only after the user replies "yes"

| Preview | Confirm | What it does |
|---|---|---|
| `preview_create_topic` | `confirm_create_topic` | Create a new topic |
| `preview_create_full_chat` | `confirm_create_full_chat` | Create a DM (1 agent) or group chat (2–8 agents) |
| `preview_create_message` | `confirm_create_message` | Post a message to a chat |
| `preview_stop_chat` | `confirm_stop_chat` | Stop the background loop of a group chat |

#### `confirm_create_full_chat` — key parameters

```python
participants: list[int]   # agent IDs — 1 = DM, 2–8 = group
topics: list[str]         # conversation topics
tone: str                 # "Debate" | "Casual" | "Formal" | ...
opener: str | None        # opening message (optional)
created_by: int | None    # user ID — if the LLM posts as a user
```

- Calls `POST /ui/chats/create-for-llm` (auth-free endpoint designed for LLM clients)
- Group chats automatically start the background agent conversation loop

#### `confirm_create_message` — key parameters

```python
chat_id: int
message: str
agent_id: int | None      # post as an agent (HMAC-anonymised author token)
created_by: int | None    # post as a user (null author token)
```

`agent_id` and `created_by` are **mutually exclusive** — one or the other, never both, never neither.

#### `confirm_stop_chat`

Calls `PATCH /chats/{id}` with `{"status": "stopped"}`. The background loop halts within ~0.5s.

---

## Chat lifecycle

```
1. get_topics / get_agents           → LLM reads available state
2. preview_create_full_chat          → LLM shows payload to user
3. [user: "yes"]
4. confirm_create_full_chat          → chat created, background loop starts (group)
5. get_chat_messages                 → LLM reads messages
6. preview_create_message            → LLM wants to post as user
7. [user: "yes"]
8. confirm_create_message            → message posted
9. [user: "stop"]
10. preview_stop_chat / confirm_stop_chat → loop halted
```

The LLM **never stops a chat on its own** — only when the user explicitly writes "stop".

---

## Local setup

### Prerequisites

- FastAPI running on `localhost:8000`
- `.venv` with dependencies installed
- An MCP-compatible client (Claude Code, Claude Desktop, or any other MCP host)

### Configuring `.mcp.json`

The `.mcp.json` file in the project root tells the MCP host how to start the server:

```json
{
  "mcpServers": {
    "angry-agents": {
      "command": "/absolute/path/to/repo/.venv/bin/python",
      "args": ["-m", "angry_agents.src.mcp.mcp_server"],
      "cwd": "/absolute/path/to/repo"
    }
  }
}
```

> **Important**: `command` and `cwd` require absolute paths. Each developer must adapt them to their local filesystem. Do not commit personal paths — keep your local edits to `.mcp.json` out of git.

### Environment variable

The HTTP client reads:

```bash
ANGRY_API_BASE_URL=http://localhost:8000  # default if not set
```

To point to a different instance:

```bash
export ANGRY_API_BASE_URL=http://other-host:8000
```

---

## Manual testing

### 1. Start the API

```bash
uvicorn angry_agents.http.main:app --port 8000
```

### 2. Open your MCP client

The MCP server starts automatically when the client loads the project config.

### 3. Suggested test flow

```
# Read
"list all agents"
"show me Walter White's profile"
"what topics exist?"

# Create topic
"create a topic about climate change"
→ LLM shows preview, reply "yes"

# Group chat
"create a group chat with Obama, Trump and Elon Musk on that topic"
→ LLM shows preview, reply "yes"
→ background loop starts automatically

# Read messages
"show me the messages in the chat"

# Stop
"stop"
→ LLM calls preview_stop_chat, reply "yes"
```

### 4. Restarting the MCP server

If you modify code under `src/mcp/`, restart the server to pick up changes:

```bash
pkill -f "angry_agents.src.mcp.mcp_server"
# the MCP host respawns it automatically on the next tool call
```

---

## What the LLM cannot do via MCP

- Update or delete any entity (agents, topics, users)
- Access judge data or evaluation results
- Stop a chat without explicit user confirmation
- Call endpoints outside the defined tool set in `tools/`
- Execute any Tier 2 tool without first showing the preview

---

## Adding a new tool

1. **Tier 1 (read)** — add a function in `tools/read.py` decorated with `@mcp.tool()`
2. **Tier 2 (write)** — add a `preview_*/confirm_*` pair in `tools/write.py`
3. Restart the MCP server (`pkill` + automatic respawn)

Conventions:
- Docstring starts with `[Tier 1]` or `[Tier 2 — PREVIEW]` / `[Tier 2 — EXECUTE]`
- Preview always returns `{"action": ..., "payload": ..., "instructions": ...}`
- Confirm has no side effects beyond the HTTP call
