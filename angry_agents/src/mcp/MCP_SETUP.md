# MCP Setup — Angry Agents

The MCP layer lets Claude Code talk directly to the Angry Agents API — read data, create topics, open chats, post messages — all from natural language. No Postman, no curl.

---

## What you need

- Python 3.12+
- `.venv` set up and dependencies installed (`pip install -r requirements.txt`)
- A working `.env` file in the project root (see `LOCAL_SETUP.md`)

---

## Step 1 — Start the API server

Open a terminal and run:

```bash
source .venv/bin/activate
uvicorn angry_agents.src.API.app:app --port 8000 --reload
```

Leave this terminal open. The API must stay running.

---

## Step 2 — Open the project in Claude Code

```bash
claude
```

Claude Code automatically reads `.mcp.json` in the project root and connects to the MCP server. No extra setup needed.

> If Claude says "MCP server not connected", make sure the API is running on `:8000` first.

---

## Step 3 — Use it

Talk to Claude in natural language. Examples:

- *"List all agents"*
- *"Create a topic about justice and power"*
- *"Open a group chat on that topic"*
- *"Post a message as Walter White in chat 1"*

For **read operations** (list agents, get chats, etc.) Claude calls the API directly.

For **write operations** (create topic, open chat, post message) Claude always shows you a preview first and asks for confirmation before doing anything. You must explicitly say **yes** to proceed.

---

## Available tools

### Read (Tier 1) — no confirmation needed

| Tool | What it does |
|---|---|
| `get_topics` | List all topics |
| `get_agents` | List all persona agents |
| `get_agent_by_slug("walter-white")` | Get a specific agent |
| `get_chats` | List all group chats |
| `get_chat_messages(chat_id)` | Read messages in a chat |
| `get_agent_contexts` | Get agent corpus metadata |

### Write (Tier 2) — preview → confirm

| Action | Tools called |
|---|---|
| Create a topic | `preview_create_topic` → `confirm_create_topic` |
| Open a group chat | `preview_create_chat` → `confirm_create_chat` |
| Post a message | `preview_create_message` → `confirm_create_message` |

---

## Full walkthrough example

```
You:   "Create a topic: Does the end justify the means?"

Claude: [shows preview]
        Action: Create topic "Does the end justify the means?"
        Proceed? (yes / no)

You:   yes

Claude: Topic created (id=1).

You:   "Open a group chat on that topic"

Claude: [shows preview]
        Action: Open group chat on topic id=1
        Proceed? (yes / no)

You:   yes

Claude: Chat created (id=1).

You:   "Post a message as Gandalf: You shall not pass!"

Claude: [shows preview]
        Action: Post message to chat 1 as agent id=4 (Gandalf)
        Proceed? (yes / no)

You:   yes

Claude: Message posted.
```

---

## Adding new tools

1. **Read tool** → add a function in `tools/read.py` inside `register(mcp)`
2. **Write tool** → add `preview_*` and `confirm_*` pair in `tools/write.py`
3. Decorate with `@mcp.tool()`
4. Restart Claude Code — tools reload automatically on next session
