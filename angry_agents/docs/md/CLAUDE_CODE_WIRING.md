# Wiring Guide — 8 Angry Agents UI ↔ FastAPI

> **For Claude Code.** This document is a complete, self-contained brief to wire the
> prototype UI in this folder to the existing FastAPI backend at the repository root
> (`angry_agents/http/main.py`, running on `:8000`). Follow the steps in order.
> Do not skip the milestones — each one is independently testable.

---

## Context you should load first

Before touching anything, read:

1. `../CLAUDE.md` — architectural rules. Especially:
   - **Only `api/` touches SQL.** The UI must never know about SQL.
   - **Auth:** `AUTH_DISABLED=1` reads the `X-User-Slug` header. We assume this is on in dev.
   - **`Chat_messages.author` is `name + surname + DIGEST`** — judges see source diversity, not identity. The UI receives whatever string the server sends; it does **not** reconstruct or map it.
   - **No FK from `Chat_messages` → `Agents`.** The UI must not assume it can join messages back to agent ids client-side.
   - **`Users.role` ∈ {`common`, `admin`}.**
   - **`Agents.Type_of_context` ∈ {`fiction`, `real_world`}.**

2. The current UI source in this folder. Files of interest:
   - `app.jsx` — root component, auth state, routing.
   - `data.js` — **all mock data lives here**. Your goal is to make this file disappear.
   - `screens-auth.jsx` — Login + Register.
   - `screens-home.jsx` — Landing page; reads `chats` + `PERSONAS`.
   - `screens-library.jsx` — Agent library; reads `PERSONAS`.
   - `screens-newchat.jsx` — DM + Group wizard; reads `PERSONAS`.
   - `screens-chat.jsx` — Active chat; reads `SAMPLE_MESSAGES` and has **toy reply generators** at the bottom of the file. Both must be removed.
   - `screens-admin.jsx` — Admin dashboard; reads `RECENT_SESSIONS`, `PERSONAS`.

3. Backend route registrations under `angry_agents/http/`. Map the routes you find there to the calls below. **If a route does not exist, do not invent it** — flag it in your output as "needs backend route" and stop.

---

## Step 0 — Create the API client

Add a new file `api.js` at the root of this UI folder.

```js
// api.js — single source of truth for talking to the FastAPI backend.
const API_BASE = window.__API_BASE__ || "http://localhost:8000";
let _slug = localStorage.getItem("aa.user-slug") || null;

function headers() {
  return {
    "Content-Type": "application/json",
    ...(_slug ? { "X-User-Slug": _slug } : {}),
  };
}

async function req(method, path, body) {
  const r = await fetch(API_BASE + path, {
    method,
    headers: headers(),
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!r.ok) {
    const text = await r.text().catch(() => "");
    const err = new Error(`${method} ${path} → ${r.status} ${text}`);
    err.status = r.status;
    throw err;
  }
  if (r.status === 204) return null;
  return r.json();
}

window.api = {
  base: API_BASE,
  get slug() { return _slug; },
  setSlug(slug) { _slug = slug; localStorage.setItem("aa.user-slug", slug); },
  clear()      { _slug = null; localStorage.removeItem("aa.user-slug"); },

  get:   (p)    => req("GET",    p),
  post:  (p, b) => req("POST",   p, b),
  patch: (p, b) => req("PATCH",  p, b),
  del:   (p)    => req("DELETE", p),
};
```

Register it in `index.html` **before** any `text/babel` script:

```html
<script src="data.js"></script>
<script src="api.js"></script>             <!-- ADD THIS LINE -->
<script type="text/babel" src="tweaks-panel.jsx"></script>
...
```

---

## Step 1 — Authentication: server tells us the role

The Login screen currently calls `onSubmit()` with no payload. Re-wire it to hit the
backend, store the slug, and let the server decide whether the user is `common` or `admin`.

### 1.1 — Backend contract

Confirm or implement a login route on the server:

- **`POST /auth/login`**
  - Request: `{ email: string, password: string }`
  - Response: `{ slug: string, name: string, role: "common" | "admin", email: string }`
  - Errors: `401` invalid credentials, `404` no such user.

If `AUTH_DISABLED=1` is still required for dev, the route may simply look up by email and skip password verification — but it must still return `role`. **Do not fall back to client-side role selection.**

### 1.2 — UI change: `app.jsx`

Find the `LoginScreen` block inside `App()`:

```jsx
{authState.screen === "login" && (
  <AuthShell>
    <LoginScreen
      onSubmit={() => setAuthState({ screen: "app" })}
      onSwitch={() => setAuthState({ screen: "register" })}
    />
  </AuthShell>
)}
```

Replace the `onSubmit` with:

```jsx
onSubmit={async ({ email, password }) => {
  try {
    const me = await window.api.post("/auth/login", { email, password });
    window.api.setSlug(me.slug);
    setUser({ name: me.name, handle: me.slug });
    const r = me.role === "admin" ? "admin" : "user";
    setUserRole(r);
    setRole(r);
    setAuthState({ screen: "app" });
  } catch (err) {
    alert("Login failed. Check email and password.");
  }
}}
```

> The `LoginScreen` component already accepts `onSubmit({ email, password })`. No change needed inside `screens-auth.jsx`.

### 1.3 — Register

Wire the Register submit the same way:

```jsx
onSubmit={async (form) => {
  const me = await window.api.post("/auth/register", {
    name: form.firstName,
    surname: form.lastName,
    email: form.email,
    password: form.password,
  });
  window.api.setSlug(me.slug);
  setUser({ name: me.name, handle: me.slug });
  setUserRole("user");      // new accounts are always common
  setRole("user");
  setAuthState({ screen: "app" });
}}
```

### 1.4 — Logout

In `app.jsx`, find `onLogout={() => setAuthState({ screen: "login" })}` and make it also clear the slug:

```jsx
onLogout={() => {
  window.api.clear();
  setAuthState({ screen: "login" });
}}
```

### 1.5 — Session restore (optional but cheap)

At the top of `App()` add a one-shot effect to restore the session if a slug is in localStorage:

```jsx
React.useEffect(() => {
  if (!window.api.slug) return;
  window.api.get("/auth/me").then(me => {
    setUser({ name: me.name, handle: me.slug });
    const r = me.role === "admin" ? "admin" : "user";
    setUserRole(r);
    setRole(r);
    setAuthState({ screen: "app" });
  }).catch(() => window.api.clear());
}, []);
```

> Requires `GET /auth/me` returning the same shape as `/auth/login`. If the route doesn't exist, skip this step and let users log in on every reload.

**Milestone 1 done when:** Logging in as a real `admin` user lands you on the Admin Dashboard with the role-switch visible; logging in as `common` lands you on Home with no switcher.

---

## Step 2 — Personas (Agents)

This is the highest-leverage swap — Library, Group wizard, DM picker, Admin tables, Home tiles, and the chat sidebar avatars all read from `window.PERSONAS`.

### 2.1 — Backend contract

- **`GET /agents`** → `Array<Agent>` where each agent matches:
  ```ts
  {
    id: string,            // server-side id (slug or uuid)
    name: string,          // e.g. "MARLA THORNE"
    source_type: "fiction" | "real_world",
    source_title: string,  // free-form, e.g. "Economics podcast host"
    desc: string,          // short personality descriptor
    tags: string[],        // e.g. ["economics", "politics"]
  }
  ```
- **`POST /agents`** (admin-only) — for the "Add new agent" button later.

The UI also uses a `color` field for the avatar. If the server doesn't provide one, derive it client-side from the slug (see §2.3).

### 2.2 — Move PERSONAS into React state

Replace `window.PERSONAS = [...]` in `data.js` with a stub that returns the loaded list:

Actually — **the cleanest path is to delete `window.PERSONAS` from `data.js` and replace every reader with a React Context.**

Add a new file `agents-store.jsx`:

```jsx
// agents-store.jsx — single React-side cache for the agent library.
const AgentsContext = React.createContext({ agents: [], byId: () => null, refresh: () => {} });

function AgentsProvider({ children }) {
  const [agents, setAgents] = React.useState([]);
  const [loaded, setLoaded] = React.useState(false);

  const refresh = React.useCallback(async () => {
    const list = await window.api.get("/agents");
    const decorated = list.map(a => ({ ...a, color: a.color || colorFromSlug(a.id) }));
    setAgents(decorated);
    setLoaded(true);
  }, []);

  React.useEffect(() => { refresh(); }, [refresh]);

  const byId = React.useCallback((id) => agents.find(a => a.id === id) || null, [agents]);

  return (
    <AgentsContext.Provider value={{ agents, byId, refresh, loaded }}>
      {children}
    </AgentsContext.Provider>
  );
}

function colorFromSlug(s) {
  // deterministic hue from string
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) & 0xffff;
  return `oklch(60% 0.15 ${h % 360})`;
}

window.useAgents = () => React.useContext(AgentsContext);
window.AgentsProvider = AgentsProvider;
```

Register before `app.jsx` in `index.html`:

```html
<script type="text/babel" src="agents-store.jsx"></script>
<script type="text/babel" src="app.jsx"></script>
```

Wrap `<App />` in `<AgentsProvider>`:

```jsx
root.render(<AgentsProvider><App /></AgentsProvider>);
```

### 2.3 — Replace every reader

**Search and replace** across the project:

| Find | Replace with |
|---|---|
| `window.PERSONAS` | `useAgents().agents` (inside a component) |
| `window.findPersona(id)` | `useAgents().byId(id)` |

Files that need touching:
- `screens-library.jsx` — `LibraryScreen`: `const { agents } = useAgents();`
- `screens-newchat.jsx` — `NewGroupScreen`, `NewDMScreen`
- `screens-chat.jsx` — `MessageBubble`, `ChatScreen`, `ChatSidebar`
- `screens-admin.jsx` — `AgentPerformanceSection`, `RecentSessionsTable`
- `screens-home.jsx` — featured agents

After every file compiles, **delete `window.PERSONAS` and `window.findPersona` from `data.js`**.

**Milestone 2 done when:** With personas seeded in the DB, the Library shows them, the Group wizard lets you pick them, and the empty DB state shows an empty grid (no client-side leftovers).

---

## Step 3 — Chats list

### 3.1 — Backend contract

- **`GET /chats`** — chats where the current user (`X-User-Slug`) is a participant.
  ```ts
  Array<{
    id: string,
    type: "dm" | "group",
    title: string,           // group title or agent name for DM
    topics?: string[],
    tone?: "Formal" | "Casual" | "Debate",
    participants: string[],  // agent ids
    unread: number,
    last: string,            // preview line of last message
    lastTime: string,        // human-friendly ("2m", "Yesterday")
    started: string,
  }>
  ```
- **`POST /chats`** — create a chat. Body:
  ```ts
  { type: "dm" | "group", participants: string[], topics?: string[], tone?: string, opener?: string }
  ```
  Returns the created chat object.

### 3.2 — UI change: `app.jsx`

Replace `const [chats, setChats] = React.useState(window.SAMPLE_CHATS);` with:

```jsx
const [chats, setChats] = React.useState([]);

const reloadChats = React.useCallback(async () => {
  if (!window.api.slug) return;
  const list = await window.api.get("/chats");
  setChats(list);
}, []);

React.useEffect(() => { reloadChats(); }, [authState.screen, reloadChats]);
```

Replace `handleLaunchGroup` and `handleLaunchDM` with API calls:

```jsx
const handleLaunchGroup = async ({ participants, topics, tone }) => {
  const chat = await window.api.post("/chats", { type: "group", participants, topics, tone });
  setChats(cs => [chat, ...cs]);
  setActiveChatId(chat.id);
  setSessionDraft([]);
  setPage("chat");
};

const handleLaunchDM = async ({ persona, opener }) => {
  const chat = await window.api.post("/chats", { type: "dm", participants: [persona.id], opener });
  setChats(cs => [chat, ...cs]);
  setActiveChatId(chat.id);
  setPage("chat");
};
```

Delete `window.SAMPLE_CHATS` from `data.js`.

**Milestone 3 done when:** Empty DB → empty Home + sidebar. Creating a group via the wizard hits `POST /chats` and the new chat appears at the top of the sidebar.

---

## Step 4 — Messages and the toy reply generator

This is the step that **removes the leftover placeholder dialogue from group chats**.

### 4.1 — Backend contract

- **`GET /chats/:id/messages`** →
  ```ts
  Array<
    | { kind: "system", text: string, ts: string }
    | { kind: "user",   author: string, text: string, ts: string }
    | { kind: "agent",  author: string, text: string, ts: string, persona_id?: string }
  >
  ```
  Notes:
  - `author` is the server-set anonymized string (`name + surname + DIGEST`) per CLAUDE.md. The UI displays it verbatim.
  - `persona_id` is optional and only present in non-judging contexts (e.g. for avatar coloring). If the schema-level anonymity rule forbids it, **omit it** and the UI falls back to a neutral avatar.
  - `ts` is ISO-8601 UTC; UI formats it.
- **`POST /chats/:id/messages`** → `{ text: string }` returns the newly created user message. Agent replies arrive **separately** (poll or WS).
- **Live updates:** either
  - `GET /chats/:id/messages?since=<ts>` polled every 2 s while the chat is open, or
  - `WS /chats/:id/stream` pushing the same objects.

Pick one based on what the backend already supports and document it in your output.

### 4.2 — Strip the placeholders

Open `screens-chat.jsx`. There are **three** chunks to remove:

#### (a) The seeded transcript

Find the second `useEffect` inside `ChatScreen` (the one that branches on `chat.id === "c-001"`, `chat.type === "dm"`, etc.) and replace the entire block with:

```jsx
React.useEffect(() => {
  if (!chat) return;
  let cancelled = false;
  window.api.get(`/chats/${chat.id}/messages`)
    .then(msgs => { if (!cancelled) setMessages(msgs); })
    .catch(() => { if (!cancelled) setMessages([]); });
  return () => { cancelled = true; };
}, [activeId]);
```

Also change the initial state from `useState(window.SAMPLE_MESSAGES)` to `useState([])`.

#### (b) The `send()` function

Replace the body with:

```jsx
const send = async () => {
  if (!draft.trim()) return;
  const text = draft.trim();
  setDraft("");
  await window.api.post(`/chats/${chat.id}/messages`, { text });
  const fresh = await window.api.get(`/chats/${chat.id}/messages`);
  setMessages(fresh);
};
```

If you implemented WS in §4.1, the `setMessages(fresh)` line becomes redundant — the WS already pushes the user message back.

#### (c) The `provoke()` function

Either:
- Remove the button (in the same file, find the `provoke` btn in `<footer className="chat-composer">` and delete it), **OR**
- Wire it to a backend route, e.g. `POST /chats/:id/provoke`, and rely on the same live-update channel for the resulting agent messages.

#### (d) Delete the toy generators

At the bottom of `screens-chat.jsx`, **delete all five helper functions**: `greetingFor`, `secondLineFor`, `groupLineFor`, `replyFor`, `provokeLineFor`.

### 4.3 — MessageBubble's persona color

Currently `MessageBubble` does `const p = window.findPersona(msg.agentId)` and uses `p.color` for the author label. After §4.1, server messages may not carry `persona_id`. Adjust:

```jsx
const { byId } = useAgents();
const p = msg.persona_id ? byId(msg.persona_id) : null;
const authorColor = p?.color || "var(--fg-1)";
const author = msg.author || p?.name || "AGENT";
```

And render `<span className="msg-author" style={{ color: authorColor }}>{author}</span>`.

If the server forbids `persona_id` entirely, the UI degrades to a neutral grey author label — that's correct and matches the anonymity invariant.

### 4.4 — Delete from `data.js`

Remove `window.SAMPLE_MESSAGES` entirely.

**Milestone 4 done when:** Opening a chat triggers exactly one `GET /chats/:id/messages` and renders **only** what the server returned. Empty conversation = empty chat area. Sending a message produces a `POST` and the message appears (or the WS pushes it).

---

## Step 5 — Admin dashboard

### 5.1 — Backend contract

- **`GET /admin/sessions?limit=24`** → `Array<Session>`:
  ```ts
  {
    id: string,                  // e.g. "S-2061"
    participants: string[],      // agent ids
    topic: string,
    duration: string,            // "HH:MM:SS"
    date: string,                // formatted server-side
    status: "live" | "complete" | "evaluating" | "flagged",
  }
  ```
- **`GET /admin/overview`** → KPIs:
  ```ts
  {
    sessions_today: { value: number, delta_pct: number, spark: number[] },
    active_users:   { value: number, delta_pct: number, spark: number[] },
    avg_session:    { value: string, delta_pct: number, spark: number[] },
    judge_confidence: { value: number, delta_abs: number, spark: number[] },
  }
  ```
- **`GET /admin/agent-performance`** → per-agent stats:
  ```ts
  Array<{ agent_id: string, sessions: number, individual_fidelity: number, group_fidelity: number, flagged: number }>
  ```

### 5.2 — UI changes: `screens-admin.jsx`

Replace the hardcoded `kpis` array in `OverviewSection` with `useState(null)` + `useEffect` calling `window.api.get("/admin/overview")`.

Replace `window.RECENT_SESSIONS.map(s => ...)` in `RecentSessionsTable` with state loaded from `/admin/sessions`.

Replace `window.PERSONAS.map(p => { ... Math.random() ... })` in `AgentPerformanceSection` with state loaded from `/admin/agent-performance` joined with `useAgents().byId(agent_id)`.

Delete `window.RECENT_SESSIONS` from `data.js`.

### 5.3 — "Add new agent" button

In `AdminDashboard`'s header (currently has `Add new agent` with empty `onClick`), wire it to a modal that POSTs to `/agents`:

```jsx
const [newAgentOpen, setNewAgentOpen] = React.useState(false);
const { refresh } = useAgents();

<Btn variant="primary" size="sm" icon={<Icons.Plus size={12} sw={2.5} />}
     onClick={() => setNewAgentOpen(true)}>Add new agent</Btn>

<Modal open={newAgentOpen} onClose={() => setNewAgentOpen(false)} title="Add agent"
       footer={<>
         <Btn variant="ghost" onClick={() => setNewAgentOpen(false)}>Cancel</Btn>
         <Btn variant="primary" onClick={async () => {
           await window.api.post("/agents", form);
           await refresh();
           setNewAgentOpen(false);
         }}>Create</Btn>
       </>}>
  {/* form: name, source_type radio, source_title, desc, tags */}
</Modal>
```

Use the existing `Modal`, `Field`, and form primitives from `components.jsx`. Mirror the visual style of the New DM picker modal.

---

## Step 6 — Final cleanup

When all milestones are green:

1. **Delete `data.js` entirely** (or reduce it to a single `// intentionally empty` comment).
2. Remove the `<script src="data.js"></script>` line from `index.html`.
3. Search the project for any remaining `window.SAMPLE_`, `window.RECENT_`, `Math.random()` in `screens-*.jsx`, `window.PERSONAS`, `window.findPersona`. There should be zero hits outside `agents-store.jsx`.
4. Run the app with an empty DB — every list should render an Empty state. Seed one persona, one chat, one message; each should appear.

---

## Anti-checklist (things NOT to do)

- ❌ Do **not** add SQL anywhere outside `api/` per CLAUDE.md.
- ❌ Do **not** try to derive agent identity from `Chat_messages.author` — that string is intentionally a digest.
- ❌ Do **not** reinstate the demo role chooser. Role comes from the server.
- ❌ Do **not** keep mock fallback data "in case the server is down." If a fetch fails, render an Empty state with a retry button. Silent fallbacks hide real bugs.
- ❌ Do **not** widen the existing CRUD signatures from CLAUDE.md (`get → None`, `query → []`, `create → IntegrityError`, etc.) — match them on the route level.

---

## What to output

When done, produce:
1. A short summary listing each backend route you confirmed already existed vs. needed to add.
2. The final `index.html` script load order.
3. A grep of remaining `Math.random()` and `SAMPLE_` references — should be empty.
4. Any milestone you could not complete due to a missing backend route, with the precise contract you would need.
