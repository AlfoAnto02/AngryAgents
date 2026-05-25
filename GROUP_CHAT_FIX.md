# Group Chat Bug Fix — Root Cause & Resolution

## What wasn't working

When a user created a group chat and clicked **Launch group chat**, agents never produced any messages. The chat screen showed only the user's own messages. This happened consistently for every group chat created from the UI.

### Evidence from the database

All group chats had `status = 'pending'` even minutes after creation. The `pending` state means the background task that drives autonomous agent conversation was never registered. Any chat that reaches `status = 'running'` does so within milliseconds of the background task starting. A chat that stays `pending` for more than a few seconds was never started.

---

## Root cause

Creating a group chat was split into **two separate HTTP calls** in `handleLaunchGroup` (`ui/app.jsx`):

```javascript
// Step 1 — create the chat record
const chat = await window.api.post("/ui/chats", { type: "group", participants, topics, tone });

// Step 2 — start the autonomous conversation
await window.api.post(`/ui/chats/${chat.id}/start`);
```

The background task that drives agent conversation was only registered inside the `POST /ui/chats/{id}/start` endpoint (`ui_start_chat` in `ui_routes.py`). If step 2 never reached the server, or returned an error that was caught and dismissed, the background task was never scheduled and the chat stayed `pending` forever.

Step 2 was the fragile link. The backend and the background task itself worked correctly — manually calling `POST /ui/chats/{id}/start` via the API always succeeded and produced agent messages. The failure was in the UI-to-server call: whether due to a browser-cached old version of `app.jsx` that lacked the `/start` call, a dismissed error alert, or an auth token timing issue, step 2 silently did not fire for new chats created from the UI.

### Secondary issue: corrupted topic context sent to agents

Even when the background task did run (triggered manually), agents received a garbled topic description. `ui_create_chat` stores topic titles with a millisecond timestamp suffix to enforce `UNIQUE` constraint in the DB:

```
Topic.title = "What is the scariest thing ever?__1779699199081"
Topic.description = '{"topics": [...], "tone": "Debate", "title": "What is the scariest thing ever?"}'
```

`PersonaAgent.bind_to_chat` used `topic.title` and `topic.description` directly:

```python
self._topic_block = topic.title                          # timestamp-suffixed
if topic.description:
    self._topic_block += f": {topic.description}"        # raw JSON appended
```

Every agent received this as their debate topic:
```
What is the scariest thing ever?__1779699199081: {"topics": [...], "tone": "Debate", ...}
```

The LLM still responded, but with noise in the system prompt.

---

## Changes made

### 1. `angry_agents/src/API/routes/ui_routes.py`

**Added `BackgroundTasks` parameter to `ui_create_chat`** and registered `_bg_run_conversation` atomically with chat creation for group chats.

```python
# Before
@router.post("/ui/chats", status_code=201)
def ui_create_chat(
    body: UIChatCreate,
    current_user=Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:

# After
@router.post("/ui/chats", status_code=201)
def ui_create_chat(
    body: UIChatCreate,
    background_tasks: BackgroundTasks,          # added
    current_user=Depends(get_current_user),
    db: sqlite3.Connection = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
```

And at the end of the function, after the chat record and agent assignments are committed:

```python
# Before
chat_type = "dm" if len(agent_ids) == 1 else "group"

# After
chat_type = "dm" if len(agent_ids) == 1 else "group"
if chat_type == "group":
    background_tasks.add_task(
        _bg_run_conversation, chat_id, settings.db_path, settings.author_secret, _DEFAULT_TURNS
    )
```

The background task is now scheduled inside the same HTTP request that creates the chat. There is no second request to fail.

### 2. `ui/app.jsx`

**Removed the explicit `/start` call** from `handleLaunchGroup`. It is no longer needed because the server handles it.

```javascript
// Before
const chat = await window.api.post("/ui/chats", { type: "group", participants, topics, tone });
await window.api.post(`/ui/chats/${chat.id}/start`);   // removed
setChats(cs => [chat, ...cs]);

// After
const chat = await window.api.post("/ui/chats", { type: "group", participants, topics, tone });
setChats(cs => [chat, ...cs]);
```

The `POST /ui/chats/{id}/start` endpoint still exists for manually restarting a `pending` chat (e.g. old chats created before this fix).

### 3. `angry_agents/src/agents/personas/persona_agent.py`

**Fixed `bind_to_chat` to extract the clean display title** from the topic description JSON instead of using the raw DB title.

```python
# Before
self._topic_block = topic.title
if topic.description:
    self._topic_block += f": {topic.description}"

# After
topic_title = topic.title
if topic.description:
    try:
        meta = json.loads(topic.description)
        if isinstance(meta, dict) and meta.get("title"):
            topic_title = meta["title"]
    except (json.JSONDecodeError, TypeError):
        topic_title += f": {topic.description}"
self._topic_block = topic_title
```

Result: agents receive `"What is the scariest thing ever?"` instead of `"What is the scariest thing ever?__1779699199081: {raw JSON}"`.

---

## Why these changes fix the problem

| Problem | Fix | Why it works |
|---|---|---|
| `/start` call silently fails from UI | Register background task inside `ui_create_chat` | The task is scheduled in the same request that creates the chat — one atomic step that cannot partially fail |
| Redundant second HTTP call from UI | Remove `/start` from `handleLaunchGroup` | Eliminates the failure surface entirely |
| Garbled topic title in agent prompts | Parse clean title from `topic.description` JSON | Agents receive the human-readable topic, not the DB-internal uniqueness-suffixed key |

---

## What was confirmed working throughout

- The `_bg_run_conversation` background task itself was never broken. Calling `POST /ui/chats/{id}/start` directly via the API always worked and produced agent messages within seconds.
- The `GroupChatSession`, `PersonaAgent`, `TurnScheduler`, and `ContextWindow` logic were all correct.
- The message polling in `ChatScreen` (every 2 seconds) was correct.
- The `ChatMessageService` HMAC author digest and UI author lookup were consistent.

The only broken link was the two-step creation flow in the UI.
