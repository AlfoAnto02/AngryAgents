# Session Report — DB Branch (`DB_creation_v1`) — 2026-05-18

---

## 1. DB Layer Analysis

Reviewed the full existing stack under `angry_agents/src/db/`:

- **Models** (`db/models/`) — seven `@dataclass` entities: `Topic`, `Agent`, `AgentContext`,
  `GroupChat`, `ChatMessage`, `Judge`, `JudgeEvaluation`. Each carries `created_at`,
  `updated_at`, `deleted_at` (soft delete). `JudgeEvaluation` uses a composite PK
  `(id_judge, id_chat)`.
- **Repositories** (`db/repositories/`) — thin SQLite CRUD per entity (`create`, `get`,
  `update`, `delete`, `query`). `rels.py` manages agent-topic and judge-chat relationships.
- **Services** (`db/services/`) — business logic on top of repositories:
  - `ChatMessageService` computes an HMAC-SHA256 digest author token so judges never see
    real agent identity.
  - `JudgeEvaluationService` enforces the 20-evaluations-per-chat cap.
  - `JudgeService` validates `role` against the `JudgeRole` enum
    (`style / ideology / general / behavioral`).

---

## 2. REST API Layer — `angry_agents/src/API/`

Built a FastAPI API layer from scratch on top of the service layer.

### Core files

| File | Purpose |
|------|---------|
| `src/__init__.py` | Makes `src` a proper Python package, enabling relative imports from `API/` to `db/` |
| `API/__init__.py` | Package marker |
| `API/config.py` | `Settings` dataclass + `get_settings()` (cached via `@lru_cache`). Reads `ANGRY_DB_PATH` and `ANGRY_AUTHOR_SECRET` from env |
| `API/deps.py` | `get_db()` FastAPI dependency — opens a SQLite connection per request, closes in `finally` |
| `API/app.py` | FastAPI app instance, registers all seven routers, runs `init_db()` on startup via `lifespan` |
| `API/schemas.py` | Seven Pydantic response models (`TopicOut`, `AgentOut`, etc.) with `Field(description=...)` |

### Route files

| File | Prefix | Notes |
|------|--------|-------|
| `routes/topics.py` | `/topics` | Standard CRUD |
| `routes/agents.py` | `/agents` | Adds `GET /agents/slug/{slug}` declared before `/{id}` to avoid routing conflict |
| `routes/agent_context.py` | `/contexts` | Filterable by `id_agent` |
| `routes/group_chats.py` | `/chats` | Filterable by `id_topic` |
| `routes/chat_messages.py` | `/chats/{chat_id}/messages` + `/messages` | Injects `get_db` and `get_settings` to wire `author_secret` into `ChatMessageService` |
| `routes/judges.py` | `/judges` | `ValueError` on bad role → HTTP 422 |
| `routes/judge_evaluations.py` | `/evaluations` | Composite key routes `/{id_judge}/{id_chat}`, max-20 cap → HTTP 409 |

### Dependency injection pattern

No IoC container. FastAPI's built-in `Depends()` handles it:

```
get_settings()  ──→  get_db()  ──→  route handler  ──→  Service(db)
                         └──────────────────────────→  ChatMessageService(db, secret)
```

`get_settings` is `@lru_cache(maxsize=1)` so env vars are read once at startup.

---

## 3. Swagger UI

Added full OpenAPI / Swagger UI support:

- **`API/schemas.py`** — Pydantic `Out` models for all 7 entities with typed fields and
  `Field(description=...)`. These drive the Schemas section and response bodies in Swagger.
- **`API/app.py`** — `openapi_tags` metadata: each tag has a human-readable description.
  `swagger_ui_parameters` set to expand the endpoint list by default.
- **All 7 route files** updated with `response_model=EntityOut` (or `list[EntityOut]`),
  `summary=`, `description=` on non-obvious endpoints, and `Field(ge=..., le=...)` constraints
  on `score` (1–5) and `temperature` (0–2) for in-browser validation.
- Swagger UI available at `http://localhost:8080/docs` after server start.
- ReDoc available at `http://localhost:8080/redoc`.

---

## 4. DB Auto-Initialisation on Startup

Added a `lifespan` context manager to `app.py` so `init_db()` runs automatically when the
server starts (`CREATE TABLE IF NOT EXISTS` — safe to call on every boot):

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    conn = get_connection(settings.db_path)
    init_db(conn)
    conn.close()
    yield
```

Before this, the first API call would fail with `sqlite3.OperationalError: no such table`.

---

## 5. How to Run

```powershell
# Install dependencies (once)
pip install fastapi uvicorn pydantic pytest

# Set required env var
$env:ANGRY_AUTHOR_SECRET = "your-secret"

# Start server from project root
uvicorn angry_agents.src.API.app:app --reload --port 8080
```

Open `http://localhost:8080/docs` for Swagger UI.

---

## 6. AI Agent Tool Manifest — `docs/md/tools_managementv1.md`

Created `angry_agents/docs/md/tools_managementv1.md` following the lecture at
`https://reliableai.github.io/ai-design-2026-pub/labs/06_ai-api/aoa.html`.

Key content:
- **Autonomy boundary table**: Tier 1 (read-only, no confirmation) vs Tier 2 (write,
  CLI confirmation required).
- **12 tool definitions** in JSON Schema style: 9 read tools, 3 write tools.
- **CLI confirmation protocol**: required format, per-action (no bundling).
- **3 workflow sequences**: reading state, starting a new conversation, contributing to
  an existing chat.
- **Response object schemas** for all 5 accessible entities.
- **Anti-patterns table**: 7 explicit wrong behaviours with reasons.
- **Out-of-scope section**: judges, evaluations, agent/context creation, any updates or
  deletes are explicitly forbidden.

---

## 7. Test Suite — `angry_agents/tests/db/`

Built a full test suite: **170 tests, all passing (0.49 s)**.

### Files

| File | Tests | Focus |
|------|-------|-------|
| `conftest.py` | — | In-memory SQLite fixture + `topic`, `agent`, `chat`, `judge` fixtures |
| `test_topic_repository.py` | 16 | Full CRUD, duplicate title → exception, pagination |
| `test_agents_repository.py` | 18 | Duplicate slug → exception, FK to topic, filter |
| `test_agent_context_repository.py` | 13 | Filter by `id_agent`, soft/hard delete |
| `test_group_chat_repository.py` | 12 | Multiple chats per topic, FK update |
| `test_chat_messages_repository.py` | 13 | Author field immutable on update, ORDER BY ID ASC |
| `test_judges_repository.py` | 17 | All 4 roles, filter by role |
| `test_judge_evaluation_repository.py` | 13 | Composite PK duplicate → exception, filter by judge/chat |
| `test_rels.py` | 16 | Unknown rel_type → ValueError, soft vs hard remove, `list_rels` filters |
| `test_agents_service.py` | 15 | Slug auto-gen, collision → `-2`/`-3`, soft-deleted slug excluded |
| `test_chat_messages_service.py` | 11 | HMAC token ≠ raw name, deterministic per secret, different secrets diverge |
| `test_judges_service.py` | 13 | All 4 roles parametrized, invalid role → `ValueError` on create and update |
| `test_judge_evaluation_service.py` | 11 | **20-eval cap enforced**, cap is per-chat not global, soft-deleted slots don't count |

### Run

```powershell
python -m pytest angry_agents/tests/db/ -v
```

---

## 8. Key Invariants Preserved Throughout

- `ChatMessage.author` is always the HMAC digest — the API accepts `agent_name` +
  `agent_surname` and the service computes the token internally.
- Judge role validation raises `ValueError` in the service → converted to HTTP 422 in the API.
- Max 20 evaluations per chat enforced in service → HTTP 409 in the API.
- All deletes default to soft delete (`hard=False`). Hard delete requires `?hard=true`.
- No FK from `Chat_messages` to `Agents` — judge anonymity enforced at schema level.
