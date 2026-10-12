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

#### Admin dashboard (Tier 1)

| Tool | Endpoint | Returns |
|---|---|---|
| `get_admin_overview` | `GET /admin/overview` | Platform counters: sessions today, active users, avg session duration, judge confidence |
| `get_admin_sessions(limit)` | `GET /admin/sessions` | Recent chat sessions — `display_id`, topic, date, `is_judged` flag |
| `get_admin_agent_performance` | `GET /admin/agent-performance` | Per-agent session count, individual fidelity, group fidelity |
| `get_judged_chats` | `GET /admin/judged-chats` | All chats with a completed evaluation report (`{chat_id: ui_report, ...}`) |
| `get_judge_result(chat_id)` | `GET /admin/judged-chats/{id}` | Full evaluation report for one chat (see fields below) |
| `get_judge_status(chat_id)` | `GET /admin/judge-chat/{id}/status` | Job status without blocking: `not_started \| running \| done \| error`, `progress` 0–100 |

`get_judge_result` returns:

```
accuracy, ciLow, ciHigh    — persona ID accuracy with 95 % binomial CI
pValue                     — binomial test vs random baseline (1/N agents)
cohenKappa, macroF1        — inter-rater agreement and classification quality
prfRows                    — precision / recall / F1 per persona
fidelityRows               — mean / median / IQR / CI per persona (individual fidelity)
gini, giniZ, giniCI        — turn-distribution Gini coefficient with z-score and CI
turnShares                 — share of turns per persona
cm, cmLabels               — confusion matrix with persona labels
```

> **Note on `get_judge_status`**: the job state is held in memory — it resets on server restart. If the server was restarted after judging completed, `get_judge_status` returns `not_started` but `get_judge_result` still works because results are persisted to the DB and to `data/eval/chat_{id}/`.

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
| `preview_start_judging` | `confirm_start_judging` | Launch the 20-judge evaluation pipeline for a chat |

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

#### `confirm_start_judging` — key parameters

```python
chat_id: int   # the chat to evaluate
```

- Calls `POST /admin/judge-chat/{chat_id}` (returns immediately, job runs in background)
- Runs **20 LLM judges** independently on all agent messages in the chat
- Cost: **~$0.40** in LLM API calls; estimated duration: **~9 minutes**
- After confirming, poll `get_judge_status(chat_id)` until `status='done'`, then call `get_judge_result(chat_id)`
- Returns 409 if judging is already in progress for that chat

---

## Admin dashboard

The LLM can act as an admin observer and evaluation trigger. All reads are free; launching the judge pipeline requires explicit user confirmation.

### What the LLM can read

- **Platform health** — `get_admin_overview` gives a snapshot of today's activity (sessions, unique users).
- **Session inventory** — `get_admin_sessions` lists recent chats with their `is_judged` flag, so the LLM can identify which sessions still need evaluation.
- **Agent performance** — `get_admin_agent_performance` shows how many sessions each persona has participated in and their aggregated fidelity scores.
- **Evaluation reports** — `get_judged_chats` returns all completed reports at once; `get_judge_result(chat_id)` returns the full report for a single chat including the confusion matrix, per-persona fidelity statistics, and turn-distribution Gini coefficient.
- **Live job progress** — `get_judge_status(chat_id)` can be polled to track an in-progress judging job without blocking.

### What the LLM can trigger

The LLM can propose launching the evaluation pipeline for any chat. The user must confirm explicitly before anything runs.

```
1. get_admin_sessions            → identify sessions where is_judged = false
2. get_chat_messages(chat_id)    → verify the chat has sufficient agent messages
3. preview_start_judging(chat_id)→ LLM shows cost/time warning to user
4. [user: "yes"]
5. confirm_start_judging         → pipeline starts in background
6. get_judge_status(chat_id)     → poll until status = 'done'  (or call repeatedly)
7. get_judge_result(chat_id)     → fetch full evaluation report
```

### Admin workflow example

```
"show me an overview of the platform"
→ get_admin_overview

"which sessions haven't been judged yet?"
→ get_admin_sessions  →  filter is_judged = false

"judge session 17"
→ preview_start_judging(17), reply "yes"
→ confirm_start_judging(17)   ← background job starts

"how is the judging going?"
→ get_judge_status(17)        ← returns progress 0–100

"show me the results"
→ get_judge_result(17)        ← accuracy, fidelity, confusion matrix, ...

"how is Walter White performing across all sessions?"
→ get_admin_agent_performance → filter by agent_id
```

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

### 4. Suggested admin test flow

```
# Platform overview
"show me an overview of the platform"

# Find unjudged sessions
"which sessions haven't been judged yet?"

# Trigger evaluation
"judge session 17"
→ LLM shows cost warning (~$0.40, ~9 min), reply "yes"

# Poll progress
"how is the judging going?"
→ repeat until status = 'done'

# Read results
"show me the evaluation report for session 17"
"how is Walter White performing across all sessions?"
```

### 5. Restarting the MCP server

If you modify code under `src/mcp/`, restart the server to pick up changes:

```bash
pkill -f "angry_agents.src.mcp.mcp_server"
# the MCP host respawns it automatically on the next tool call
```

---

## What the LLM cannot do via MCP

- Update or delete any entity (agents, topics, users)
- Start the judge pipeline without explicit user confirmation
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
