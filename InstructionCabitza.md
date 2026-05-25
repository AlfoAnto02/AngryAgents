# InstructionCabitza.md — Group Chat Fix: Complete Implementation Guide

## Context

The `angry-agents` project is a chat app where users talk to AI persona-agents. The backend is
FastAPI + SQLite (Python 3.12). The frontend is a pure-JavaScript prototype served separately at
`http://localhost:8001`, with the API at `http://localhost:8000`.

The group-chat autonomous conversation feature was already broken and has been **partially fixed**:
the backend `ui_routes.py` already has `BackgroundTasks` wired to auto-start the conversation when
a chat is created (this change is committed and live in the current codebase).

The **remaining problem** is that the frontend (the React prototype in `ui/`) is completely
disconnected from the real backend. It uses hardcoded fake data, fake personas with string IDs
(`"p-01"`, `"p-02"`...), and no API calls. When a user "launches" a group chat, the UI creates a
local fake chat with an ID like `"c-9876"` — no HTTP call is made, no real chat is created in the
DB, and no agents ever speak.

This document describes **exactly** what must be changed in **6 files** to make group chats work
end-to-end. Read every section before touching any code.

---

## Architecture overview (what matters for this fix)

```
ui/index.html          — loads all JS/JSX files in order
ui/data.js             — defines window.PERSONAS (fake), window.SAMPLE_CHATS (fake), window.findPersona
ui/app.jsx             — root React component: auth state, page routing, launch handlers
ui/screens-auth.jsx    — LoginScreen + RegisterScreen components
ui/screens-newchat.jsx — NewGroupScreen + NewDMScreen (wizard, reads window.PERSONAS directly)
ui/screens-chat.jsx    — ChatScreen + ChatSidebar + MessageBubble (reads window.SAMPLE_MESSAGES)
ui/screens-library.jsx — LibraryScreen (agent cards, reads window.PERSONAS)
ui/components.jsx      — Avatar, AvatarStack, etc. (Avatar uses persona.color with "#5E5E68" fallback)
```

**Backend endpoints that the UI will call:**

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/auth/login` | none | `{email, password}` → `{access_token, token_type, user, refresh_token}` |
| POST | `/auth/register` | none | `{username, password, name, surname, email, role}` → UserOut |
| GET | `/ui/agents` | Bearer | → `[{id: int, name, slug, source_type, source_title, desc, tags}]` |
| GET | `/ui/chats` | Bearer | → `[{id: int, type, title, topics, tone, participants: [int], ...}]` |
| POST | `/ui/chats` | Bearer | `{type, participants: [int\|slug], topics, tone, opener}` → chat object |
| GET | `/ui/chats/{id}/messages` | none | → `[{kind, text, author, persona_id: int\|null, ts, time}]` |
| POST | `/ui/chats/{id}/messages` | Bearer | `{text}` → message object |

**Key field mappings:**
- Real agent `id` is an **integer** (e.g., `2`), not a string like `"p-01"`.
- Real chat `id` is an **integer** (e.g., `45`).
- Message from API: `{kind: "agent", text: "...", persona_id: 2, time: "14:30"}`.
  The UI uses `agentId` in `MessageBubble`, so map `persona_id → agentId` when receiving.

---

## File 1 — `ui/app.jsx`

### What it does now (broken)
- `handleLaunchGroup` creates a fake local chat with `id = "c-" + timestamp.slice(-4)`, no API call.
- `handleLaunchDM` same problem.
- Login `onSubmit` checks if email starts with "admin" to decide role — no API call.
- Register `onSubmit` sets fake user state — no API call.
- `chats` state is initialized from `window.SAMPLE_CHATS` (fake data), never refreshed from API.
- No JWT token is stored anywhere.

### What it must do (fixed)
1. Expose `API_BASE = "http://localhost:8000"` and a shared `apiCall` helper.
2. Store JWT token in React state: `const [token, setToken] = React.useState(null)`.
3. Login: POST `/auth/login` → store token, load agents into `window.PERSONAS`, load chats.
4. Register: POST `/auth/register` → then POST `/auth/login` → same as login.
5. `handleLaunchGroup`: async, POST `/ui/chats` with real integer agent IDs, use returned chat.
6. `handleLaunchDM`: async, POST `/ui/chats` with real integer agent ID, use returned chat.
7. Pass `token` prop to `ChatScreen`.

### Exact changes (show complete replaced blocks)

**Change A — add before `const TWEAK_DEFAULTS`:**

```javascript
const API_BASE = "http://localhost:8000";

async function apiCall(method, path, body, token) {
  const headers = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const opts = { method, headers };
  if (body != null) opts.body = JSON.stringify(body);
  const resp = await fetch(API_BASE + path, opts);
  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw Object.assign(new Error(err.detail || resp.statusText), { status: resp.status });
  }
  if (resp.status === 204) return null;
  return resp.json();
}

function colorFromId(id) {
  const palette = ["#B45309","#0E7490","#7C3AED","#15803D","#475569","#DB2777",
                   "#BE185D","#1E40AF","#9333EA","#DC2626","#1D4ED8","#A16207"];
  return palette[Math.abs(id) % palette.length];
}
```

**Change B — add token state inside `App()`, after the `user` state line:**

Locate this line:
```javascript
const [user, setUser] = React.useState({ name: "Ada Lovelace", handle: "ada-lovelace" });
```
Add immediately after it:
```javascript
const [token, setToken] = React.useState(null);
```

**Change C — replace `handleLaunchGroup`:**

Old (lines ~74–96):
```javascript
const handleLaunchGroup = ({ participants, topics, tone }) => {
    const id = `c-${Date.now().toString().slice(-4)}`;
    const newChat = {
      id, type: "group",
      title: topics[0] || "Untitled session",
      topics, tone,
      participants,
      unread: 0,
      last: "Session started",
      lastTime: "now",
      started: "now",
    };
    setChats([newChat, ...chats]);
    setActiveChatId(id);
    setSessionDraft([]);
    // Admin role: never enter chat as a participant — return to dashboard.
    if (role === "admin") {
      setAdminSection("sessions");
      setPage("admin");
    } else {
      setPage("chat");
    }
  };
```

Replace with:
```javascript
const handleLaunchGroup = async ({ participants, topics, tone }) => {
    try {
      const newChat = await apiCall("POST", "/ui/chats",
        { type: "group", participants, topics, tone }, token);
      setChats(prev => [newChat, ...prev]);
      setActiveChatId(newChat.id);
      setSessionDraft([]);
      if (role === "admin") {
        setAdminSection("sessions");
        setPage("admin");
      } else {
        setPage("chat");
      }
    } catch (e) {
      console.error("Failed to launch group chat:", e);
    }
  };
```

**Change D — replace `handleLaunchDM`:**

Old (lines ~98–117):
```javascript
const handleLaunchDM = ({ persona, opener }) => {
    const id = `c-${Date.now().toString().slice(-4)}`;
    const newChat = {
      id, type: "dm",
      title: persona.name,
      participants: [persona.id],
      unread: 0,
      last: opener || "Session started",
      lastTime: "now",
      started: "now",
    };
    setChats([newChat, ...chats]);
    setActiveChatId(id);
    if (role === "admin") {
      setAdminSection("sessions");
      setPage("admin");
    } else {
      setPage("chat");
    }
  };
```

Replace with:
```javascript
const handleLaunchDM = async ({ persona, opener }) => {
    try {
      const newChat = await apiCall("POST", "/ui/chats", {
        type: "dm",
        participants: [persona.id],
        topics: [],
        tone: "Casual",
        opener: opener || "",
      }, token);
      setChats(prev => [newChat, ...prev]);
      setActiveChatId(newChat.id);
      if (role === "admin") {
        setAdminSection("sessions");
        setPage("admin");
      } else {
        setPage("chat");
      }
    } catch (e) {
      console.error("Failed to launch DM:", e);
    }
  };
```

**Change E — replace the login `onSubmit` block inside the `if (authState.screen === "login")` return:**

Old:
```javascript
            onSubmit={(form) => {
              // Demo convention: any email starting with "admin" signs in as admin.
              const asAdmin = (form?.email || "").trim().toLowerCase().startsWith("admin");
              setUserRole(asAdmin ? "admin" : "user");
              setRole(asAdmin ? "admin" : "user");
              if (asAdmin) {
                setUser({ name: "Ops Admin", handle: "ops-admin" });
                setPage("admin");
              } else {
                setPage("home");
              }
              setAuthState({ screen: "app" });
            }}
```

Replace with:
```javascript
            onSubmit={async (form) => {
              const data = await apiCall("POST", "/auth/login",
                { email: form.email, password: form.password });
              const agents = await apiCall("GET", "/ui/agents", null, data.access_token);
              window.PERSONAS = agents.map(a => ({
                id: a.id,
                name: a.name,
                slug: a.slug,
                source_type: a.source_type,
                source_title: a.source_title || a.name,
                desc: typeof a.desc === "string" ? a.desc : "",
                tags: Array.isArray(a.tags) ? a.tags : [],
                color: colorFromId(a.id),
                tension: 0.5,
              }));
              const chatsData = await apiCall("GET", "/ui/chats", null, data.access_token)
                .catch(() => []);
              const asAdmin = data.user.role === "admin";
              setToken(data.access_token);
              setUserRole(asAdmin ? "admin" : "user");
              setRole(asAdmin ? "admin" : "user");
              setUser({
                name: `${data.user.name} ${data.user.surname}`.trim(),
                handle: data.user.slug,
              });
              setChats(chatsData);
              setActiveChatId(chatsData.length > 0 ? chatsData[0].id : null);
              setAuthState({ screen: "app" });
              setPage(asAdmin ? "admin" : "home");
            }}
```

**Change F — replace the register `onSubmit` block inside the `if (authState.screen === "register")` return:**

Old:
```javascript
            onSubmit={(form) => {
              setUser({ name: `${form.firstName} ${form.lastName}`, handle: `${form.firstName}-${form.lastName}`.toLowerCase() });
              // new registrations are always common users
              setUserRole("user");
              setRole("user");
              setAuthState({ screen: "app" });
            }}
```

Replace with:
```javascript
            onSubmit={async (form) => {
              await apiCall("POST", "/auth/register", {
                username: form.email,
                password: form.password,
                name: form.firstName,
                surname: form.lastName,
                email: form.email,
                role: "common",
              });
              const data = await apiCall("POST", "/auth/login",
                { email: form.email, password: form.password });
              const agents = await apiCall("GET", "/ui/agents", null, data.access_token);
              window.PERSONAS = agents.map(a => ({
                id: a.id,
                name: a.name,
                slug: a.slug,
                source_type: a.source_type,
                source_title: a.source_title || a.name,
                desc: typeof a.desc === "string" ? a.desc : "",
                tags: Array.isArray(a.tags) ? a.tags : [],
                color: colorFromId(a.id),
                tension: 0.5,
              }));
              const chatsData = await apiCall("GET", "/ui/chats", null, data.access_token)
                .catch(() => []);
              setToken(data.access_token);
              setUser({
                name: `${form.firstName} ${form.lastName}`,
                handle: `${form.firstName}-${form.lastName}`.toLowerCase(),
              });
              setUserRole("user");
              setRole("user");
              setChats(chatsData);
              setActiveChatId(chatsData.length > 0 ? chatsData[0].id : null);
              setAuthState({ screen: "app" });
              setPage("home");
            }}
```

**Change G — pass `token` prop to `ChatScreen`:**

Locate the `ChatScreen` JSX block (inside the main app return):
```jsx
        {role === "user" && page === "chat" && (
          <ChatScreen
            chats={chats}
            activeId={activeChatId}
            onSelectChat={setActiveChatId}
            onNewDM={handleNewDM}
            onNewGroup={handleNewGroup}
            role={role}
          />
        )}
```

Replace with:
```jsx
        {role === "user" && page === "chat" && (
          <ChatScreen
            chats={chats}
            activeId={activeChatId}
            onSelectChat={setActiveChatId}
            onNewDM={handleNewDM}
            onNewGroup={handleNewGroup}
            role={role}
            token={token}
          />
        )}
```

---

## File 2 — `ui/screens-auth.jsx`

### What it does now (broken)
`LoginScreen.submit` calls `onSubmit(form)` synchronously (no `await`). Since our new `onSubmit`
is async (it makes API calls), errors from failed logins are silently swallowed and the login
spinner would never show.

### What it must do (fixed)
Make `LoginScreen.submit` `async` and wrap `await onSubmit(form)` in a try/catch that sets the
internal `error` state to the server error message.

### Exact changes

**Change A — make `submit` in `LoginScreen` async:**

Old (inside `LoginScreen`):
```javascript
  const submit = (e) => {
    e.preventDefault();
    if (!validateEmail(form.email)) { setError("Doesn't look like an email"); return; }
    if (!form.password) { setError("Password required"); return; }
    setError("");
    onSubmit(form);
  };
```

Replace with:
```javascript
  const submit = async (e) => {
    e.preventDefault();
    if (!validateEmail(form.email)) { setError("Doesn't look like an email"); return; }
    if (!form.password) { setError("Password required"); return; }
    setError("");
    try {
      await onSubmit(form);
    } catch (err) {
      setError(err.message || "Login failed. Check your credentials.");
    }
  };
```

**Change B — make `RegisterScreen` form submit handler async:**

Old (inside `RegisterScreen`, the `<form>` tag):
```javascript
      <form onSubmit={(e) => { e.preventDefault(); canSubmit && onSubmit(form); }} className="col" style={{ gap: 12 }}>
```

Replace with:
```javascript
      <form onSubmit={async (e) => { e.preventDefault(); if (canSubmit) { try { await onSubmit(form); } catch (_) {} } }} className="col" style={{ gap: 12 }}>
```

---

## File 3 — `ui/screens-chat.jsx`

### What it does now (broken)
- `messages` state is initialized to `window.SAMPLE_MESSAGES` (fake hardcoded data).
- The `useEffect` that runs on `activeId` changes only generates more fake messages.
- `send()` generates fake replies via `setTimeout`.
- No API calls anywhere in this file.
- `ChatScreen` receives no `token` prop.

### What it must do (fixed)
- Accept a `token` prop.
- When `activeId` is a real backend chat (i.e., `typeof chat.id === "number"`), poll
  `GET /ui/chats/{id}/messages` every 2 seconds.
- Convert API message format `{kind, text, persona_id, time}` to internal format
  `{kind, text, agentId: persona_id, time}` (because `MessageBubble` uses `msg.agentId`).
- When `activeId` is a fake prototype chat (string like `"c-001"`), keep the existing
  sample-message generation unchanged.
- When `send()` is called on a real chat, POST to `/ui/chats/{id}/messages` and optimistically
  add the user message to local state.

### Exact changes

**Change A — add `token` to `ChatScreen` destructuring and change `messages` init:**

Old:
```javascript
function ChatScreen({ chats, activeId, onSelectChat, onNewDM, onNewGroup, onProvoke, role }) {
  const [messages, setMessages] = React.useState(window.SAMPLE_MESSAGES);
```

Replace with:
```javascript
function ChatScreen({ chats, activeId, onSelectChat, onNewDM, onNewGroup, onProvoke, role, token }) {
  const [messages, setMessages] = React.useState([]);
```

**Change B — replace the entire `useEffect(..., [activeId])` block:**

Old (the effect that starts with `React.useEffect(() => {` and ends with `}, [activeId]);`):
```javascript
  // Reset messages when switching chats — use a slightly different transcript per chat
  React.useEffect(() => {
    if (!chat) return;
    if (chat.id === "c-001") {
      setMessages(window.SAMPLE_MESSAGES);
    } else if (chat.type === "dm") {
      const p = personas[0];
      setMessages([
        { kind: "system", text: `Direct message started with ${p?.name}` },
        { kind: "agent", agentId: p?.id, time: "10:08", text: greetingFor(p) },
        { kind: "user", time: "10:09", text: "I want to think clearly about something. Help me." },
        { kind: "agent", agentId: p?.id, time: "10:09", text: secondLineFor(p) },
      ]);
    } else {
      setMessages([
        { kind: "system", text: `Group session — ${chat.title}` },
        ...personas.slice(0, 3).map((p, i) => ({
          kind: "agent", agentId: p.id, time: `${10 + i}:0${i}`, text: groupLineFor(p, chat.title),
        })),
      ]);
    }
  }, [activeId]);
```

Replace with:
```javascript
  // For real backend chats (integer IDs): poll API. For fake prototype chats: use sample data.
  React.useEffect(() => {
    if (!chat) return;
    const isReal = typeof chat.id === "number";
    if (isReal) {
      let cancelled = false;
      const poll = () => {
        const headers = {};
        if (token) headers["Authorization"] = `Bearer ${token}`;
        fetch(`${API_BASE}/ui/chats/${chat.id}/messages`, { headers })
          .then(r => r.ok ? r.json() : [])
          .then(msgs => {
            if (cancelled) return;
            setMessages(msgs.map(m => ({
              kind: m.kind,
              text: m.text,
              agentId: m.persona_id,
              time: m.time,
            })));
          })
          .catch(() => {});
      };
      poll();
      const timerId = setInterval(poll, 2000);
      return () => { cancelled = true; clearInterval(timerId); };
    } else {
      // Fake prototype mode
      if (chat.id === "c-001") {
        setMessages(window.SAMPLE_MESSAGES);
      } else if (chat.type === "dm") {
        const p = personas[0];
        setMessages([
          { kind: "system", text: `Direct message started with ${p?.name}` },
          { kind: "agent", agentId: p?.id, time: "10:08", text: greetingFor(p) },
          { kind: "user", time: "10:09", text: "I want to think clearly about something. Help me." },
          { kind: "agent", agentId: p?.id, time: "10:09", text: secondLineFor(p) },
        ]);
      } else {
        setMessages([
          { kind: "system", text: `Group session — ${chat.title}` },
          ...personas.slice(0, 3).map((p, i) => ({
            kind: "agent", agentId: p.id, time: `${10 + i}:0${i}`, text: groupLineFor(p, chat.title),
          })),
        ]);
      }
    }
  }, [activeId]);
```

Note: `API_BASE` is a global variable defined in `app.jsx` as `window.API_BASE` — you must also
add `window.API_BASE = API_BASE;` in `app.jsx` (after `const API_BASE = ...`) so that
`screens-chat.jsx` can reference it without importing. Add this line in `app.jsx`'s Change A block:

```javascript
const API_BASE = "http://localhost:8000";
window.API_BASE = API_BASE;   // ← ADD THIS LINE
```

**Change C — replace the `send` function:**

Old:
```javascript
  const send = () => {
    if (!draft.trim()) return;
    const t = new Date();
    const time = `${String(t.getHours()).padStart(2, "0")}:${String(t.getMinutes()).padStart(2, "0")}`;
    const newMsgs = [...messages, { kind: "user", time, text: draft.trim() }];
    setMessages(newMsgs);
    setDraft("");

    // Simulate one agent responding
    const respondent = personas[Math.floor(Math.random() * personas.length)];
    if (!respondent) return;
    setMessages(m => [...m, { kind: "typing", agentId: respondent.id }]);
    setTimeout(() => {
      setMessages(m => [
        ...m.filter(x => x.kind !== "typing"),
        { kind: "agent", agentId: respondent.id, time, text: replyFor(respondent, draft) }
      ]);
    }, 1400);
  };
```

Replace with:
```javascript
  const send = () => {
    if (!draft.trim()) return;
    const t = new Date();
    const time = `${String(t.getHours()).padStart(2, "0")}:${String(t.getMinutes()).padStart(2, "0")}`;
    const isReal = typeof chat.id === "number";
    if (isReal) {
      // Send to API; polling will pick up the reply automatically
      const headers = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;
      fetch(`${window.API_BASE}/ui/chats/${chat.id}/messages`, {
        method: "POST", headers,
        body: JSON.stringify({ text: draft.trim() }),
      }).catch(() => {});
      setMessages(m => [...m, { kind: "user", time, text: draft.trim() }]);
      setDraft("");
    } else {
      // Fake prototype mode
      const newMsgs = [...messages, { kind: "user", time, text: draft.trim() }];
      setMessages(newMsgs);
      setDraft("");
      const respondent = personas[Math.floor(Math.random() * personas.length)];
      if (!respondent) return;
      setMessages(m => [...m, { kind: "typing", agentId: respondent.id }]);
      setTimeout(() => {
        setMessages(m => [
          ...m.filter(x => x.kind !== "typing"),
          { kind: "agent", agentId: respondent.id, time, text: replyFor(respondent, draft) }
        ]);
      }, 1400);
    }
  };
```

---

## File 4 — `ui/screens-library.jsx`

### Problem
Line 50 calls `persona.id.toUpperCase()`. This works when `persona.id` is a string (`"p-01"`).
Once real agents are loaded, `persona.id` is an **integer** (`2`). Calling `.toUpperCase()` on an
integer throws `TypeError: persona.id.toUpperCase is not a function`.

### Fix
Locate line 50:
```javascript
          <span className="t-meta mono" style={{ fontSize: 10 }}>{persona.id.toUpperCase()}</span>
```

Replace with:
```javascript
          <span className="t-meta mono" style={{ fontSize: 10 }}>{String(persona.id).toUpperCase()}</span>
```

---

## File 5 — `ui/data.js`

### Problem
`window.findPersona` uses strict equality `===`. After loading real agents (integer IDs), all IDs
are integers. `window.findPersona(2)` where `p.id === 2` works fine (`2 === 2`). However, edge
cases exist: if for any reason an ID arrives as a string (e.g., parsed from a URL or DOM attribute),
`"2" === 2` is `false` and the lookup fails silently, causing `Avatar` to show "?" with a gray
background.

### Fix
Use loose equality `==` so that `"2" == 2` is `true`:

Old (last line of `data.js`):
```javascript
window.findPersona = (id) => window.PERSONAS.find(p => p.id === id);
```

Replace with:
```javascript
window.findPersona = (id) => window.PERSONAS.find(p => p.id == id);
```

---

## File 6 — `angry_agents/src/agents/personas/persona_agent.py`

### Problem
`bind_to_chat` builds `_topic_block` (the topic string injected into the LLM prompt) like this:

```python
self._topic_block = topic.title          # e.g., "What is AI?__1748012345678"
if topic.description:
    self._topic_block += f": {topic.description}"  # appends raw JSON blob
```

`topic.title` is stored with a unique timestamp suffix (`"<display_title>__<ms_ts>"`).
`topic.description` is a JSON string: `'{"topics": ["What is AI?"], "tone": "Debate", "title": "What is AI?"}'`.

The result injected into the LLM prompt is:
```
What is AI?__1748012345678: {"topics": ["What is AI?"], "tone": "Debate", "title": "What is AI?"}
```

This garbled string makes agents respond generically without understanding the topic.

### Fix
Parse `topic.description` as JSON and extract the clean `"title"` field. Fall back to the raw
`topic.title` (stripped of the `__timestamp` suffix) if parsing fails.

**Full replacement for `bind_to_chat` method:**

Old:
```python
    def bind_to_chat(
        self,
        _chat_id: int,
        topic: Topic,
        template_name: str = "group_persona_chat.j2",
    ) -> None:
        self._persona_name = f"{self.agent.name} {self.agent.surname}"
        self._profile_block = _build_profile_block(self.contexts)
        self._topic_block = topic.title
        if topic.description:
            self._topic_block += f": {topic.description}"
        self._template_name = template_name
        self.dominance_weight = _extract_dominance_weight(self.contexts)
        self.cooldown_turns = _extract_cooldown_turns(self.contexts)
        self.burst_size = _extract_burst_size(self.contexts)
```

Replace with:
```python
    def bind_to_chat(
        self,
        _chat_id: int,
        topic: Topic,
        template_name: str = "group_persona_chat.j2",
    ) -> None:
        import json as _json

        self._persona_name = f"{self.agent.name} {self.agent.surname}"
        self._profile_block = _build_profile_block(self.contexts)

        topic_title = topic.title
        if topic.description:
            try:
                meta = _json.loads(topic.description)
                if isinstance(meta, dict) and meta.get("title"):
                    topic_title = meta["title"]
            except (_json.JSONDecodeError, TypeError):
                pass
        self._topic_block = topic_title

        self._template_name = template_name
        self.dominance_weight = _extract_dominance_weight(self.contexts)
        self.cooldown_turns = _extract_cooldown_turns(self.contexts)
        self.burst_size = _extract_burst_size(self.contexts)
```

Note: placing `import json as _json` inside the method is intentional — the module-level `json`
import already exists in the file but using a local alias avoids shadowing the module-level import
used by other functions in the same file. Alternatively, you can use the existing `json` import
directly (remove the `import json as _json` line and replace `_json.` with `json.`).

---

## Order of changes

Apply changes in this order to minimise risk:
1. `persona_agent.py` (Python, independent, no frontend dependency)
2. `data.js` (tiny, safe)
3. `screens-library.jsx` (tiny, safe)
4. `screens-auth.jsx` (small, independent)
5. `app.jsx` (large, must be done atomically — all 7 changes together)
6. `screens-chat.jsx` (depends on `API_BASE` being set globally by `app.jsx`)

---

## Verification steps

After all changes are applied:

1. **Python lint:** `ruff check angry_agents/`
2. **Python tests:** `STRICT_MODE=1 pytest`
3. **Manual smoke test:**
   a. Start backend: `uvicorn angry_agents.http.main:app --port 8000`
   b. Start frontend: `python -m http.server 8001 -d ui/`
   c. Open `http://localhost:8001`
   d. Login with a seeded user (run `python -m examples.seed` first if DB is empty)
   e. Create a group chat with 2+ agents and a topic
   f. After launch, the chat screen should auto-populate with agent messages within ~30 seconds
   g. The topic shown in the chat header should be the clean display title (no `__timestamp` suffix
      and no raw JSON)
   h. Agent name colours in message bubbles should be distinct (cycling through the colour palette)

---

## Common pitfalls

- **`window.API_BASE` not defined:** `screens-chat.jsx` references `API_BASE` (or `window.API_BASE`).
  Make sure `app.jsx` sets `window.API_BASE = API_BASE` so it is accessible globally before
  `screens-chat.jsx` runs. The load order in `index.html` puts `app.jsx` last, so it is always
  available at runtime once the page renders.

- **CORS error:** If the browser console shows a CORS error when the UI calls the API, the FastAPI
  server needs `CORSMiddleware`. Check `angry_agents/http/main.py` for a CORS setup. If missing,
  add:
  ```python
  from fastapi.middleware.cors import CORSMiddleware
  app.add_middleware(
      CORSMiddleware,
      allow_origins=["http://localhost:8001"],
      allow_credentials=True,
      allow_methods=["*"],
      allow_headers=["*"],
  )
  ```

- **No agents in the DB:** If `GET /ui/agents` returns `[]`, `window.PERSONAS` becomes empty and
  no agents appear in the picker. Run `python -m examples.seed` or the dedicated persona seed
  script to populate the database.

- **Token expiry (15 minutes):** The access token expires after 15 minutes. Launching a chat will
  fail with a 401 error. For a longer dev session, set `ACCESS_TOKEN_EXPIRE_MINUTES=180` in `.env`.

- **`persona_id: null` in messages:** DM messages sent by the user have `persona_id: null`.
  `MessageBubble` only calls `window.findPersona` for `kind === "agent"` messages, so null is
  never passed. ✓

- **Integer vs string ID comparison:** After login, all persona IDs in `window.PERSONAS` are
  integers. The API returns integer participant IDs. The `==` (loose equality) in `findPersona`
  handles any stray string coercion. The `String(persona.id).toUpperCase()` call in
  `screens-library.jsx` handles integer display IDs safely.
