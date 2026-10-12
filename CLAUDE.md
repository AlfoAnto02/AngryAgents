# CLAUDE.md — Angry Agents

> **About this file.** These are the instructions the team wrote for AI coding assistants (Claude Code) during development, starting in Sprint 2. They record the *intended* conventions. Where the final code differs, this is marked inline with **Actual:**. Human-facing docs are in [`docs/`](docs/README.md).

## What it is
Chat app: users talk to AI persona-agents (DM or group). 20 judge-agents evaluate conversations.
Stack: Python 3.12, FastAPI, SQLite (raw SQL), Pydantic, pytest, stdlib logging.

## Architectural rules

- **`api/` is the only layer that touches SQL.** SQL outside `api/` is a bug.
  **Actual:** SQL lives in `angry_agents/src/db/repositories/`, reached through `db/services/`. Known exception: `src/API/routes/ui_routes.py` runs aggregate queries for the UI and admin dashboards directly.
- Every named entity has `id`, `name`, `slug`, `created_at`, `updated_at`, `deleted_at`, `details` (JSON).
- `slug` is `UNIQUE WHERE deleted_at IS NULL`; server-derived via `make_slug()` with collision suffix.
  **Actual:** `_make_slug()` in `db/services/agents_service.py` and `db/services/user_service.py`.
- Timestamps: UTC ISO-8601 strings, server-set in `api/`. Never trust client timestamps.
- All relationships live in one `rels` table (`src_id`, `src_type`, `tgt_id`, `tgt_type`, `rel_type`, `details`).
- Soft-delete is default. `delete(db, id, hard=True)` is admin-only. Cascade rules in `deletion.py` only.
- Auth: `AUTH_DISABLED=1` in dev reads `X-User-Slug` header. Never enable in prod.
- Use `deviation(msg, **kwargs)` for unexpected paths — NOT `log.warning(msg, id=...)` (raises `TypeError`).

## Fail loudly — minimal try-catch

**Write code that fails visibly, especially early in development.**

- No `except: pass`. No `except Exception:` in business logic.
- Catch only specific, named exceptions you intend to handle (`IntegrityError`, `NotFound`).
- Let unhandled exceptions propagate up — a crash with a traceback is faster to debug than a silent `None`.
- Every unexpected branch calls `deviation(...)`, not a quiet `return None`.
- `STRICT_MODE=1` turns `deviation()` into a hard raise. Run tests under it: `STRICT_MODE=1 pytest`.
- Legitimate broad-catch sites: outermost process boundary, log-and-reraise (annotation only), plugin/LLM dispatch.

```python
# logging_setup.py
STRICT = os.getenv("STRICT_MODE", "0") == "1"

def deviation(msg: str, **kwargs) -> None:
    if STRICT:
        raise UnexpectedDeviation(f"{msg} | {kwargs}")
    log.warning(msg, extra=kwargs)
```

## Error conventions

| api call | not found | conflict | HTTP maps to |
|---|---|---|---|
| `get` / `get_by_slug` | `None` | — | route returns 404 |
| `query` | `[]` | — | 200 empty list |
| `create` | — | `IntegrityError` | 409 |
| `update` | `NotFound` | `IntegrityError` | 404 / 409 |
| `delete` | `NotFound` | — | 404 |

`NotFound` declared once in `api/__init__.py`. `@app.exception_handler(NotFound)` → 404. Routes never
catch these — let them flow.
**Actual:** no shared `NotFound` exception was introduced. Routes in `src/API/routes/` raise FastAPI `HTTPException` directly.

## CRUD signatures (same for every entity)

```python
users.create(db, data)          # → UserRead
users.get(db, id)               # → UserRead | None
users.get_by_slug(db, slug)     # → UserRead | None
users.update(db, id, patch)     # → UserRead
users.delete(db, id, hard=False)
users.query(db, *, filters, limit, offset)

rels.add(db, src, tgt, rel_type, details=None)
rels.remove(db, rel_id, hard=False)
rels.list(db, src=None, tgt=None, rel_type=None)
```

## Domain — Angry Agents specifics

**Persona types:**
- `fiction` — extracted from books/movies/TV (script lines + context)
- `real_world` — extracted from podcast transcripts (Q&A pairs)

Stored in `Agents.Type_of_context`. Mutually exclusive, enforced at schema level via
`Podcast_Agent_Context` vs `Fiction_Agents_Context`.
**Actual:** the two context tables were merged into a single `Agent_context` table in Phase II (see `docs/architecture/DB_v4.md`).

**Chat types:**
- `dm` — user ↔ one agent
- `group` — user + 8 agents, one topic (**Actual:** 2–8 agents)

**DB invariants:**
- `Chat_messages.author` = `name + surname + DIGEST` — judges see source diversity, not identity
- No FK from `Chat_messages` → `Agents`. Anonymity enforced at schema level.
- Max 20 `Judge_evaluation` rows per chat.
- `Judges.Role`: 4 values (`style` / `ideology` / `general` / `behavioral`).

**Judge pipeline:**
- Phase 1 — all 20 judges work independently: persona ID, individual fidelity (1–5), group fidelity, behavioral fidelity.
- Phase 2 — high-variance cases: structured deliberation 3–5 rounds, judges revise. Track confidence.
- External omniscient agent has full context (persona profiles + chat + all judge outputs), evaluates judge quality.
- Phase 1 MUST complete before Phase 2 (no cross-contamination).
- **Actual:** Phase 2 deliberation and the omniscient agent were not built; deliberation was dropped in the final week. The final pipeline is Phase 1 (persona ID → individual fidelity) plus a dedicated group-fidelity call per judge. See `docs/DECISIONS.md`.

**User roles:**
- `common` — chat, manage own conversations
- `admin` — manage personas, view judge evaluations

**Key invariants:**
- Never expose real agent identity to judges during evaluation.
- Never call LLM on every tick — only on meaningful state changes.
- Personas need 10k–50k tokens of source material before instantiation.

**Metrics:**
- Persona ID accuracy: binomial CI, baseline 12.5% (random over 8)
- Individual fidelity: median + IQR per persona, 20 ratings each
- Group fidelity: Gini on turn distribution, cosine distance matrix (Spearman vs real)
- Deliberation: variance reduction across rounds, convergence rate with binomial CI

## Run

```bash
uvicorn angry_agents.src.API.app:app --port 8000  # API
python -m http.server 8001 -d ui/                 # UI (separate process)
pytest                                             # tests
STRICT_MODE=1 pytest                              # strict CI leg
ruff check .                                       # lint
python restore_db.py                              # load demo database (API stopped)
python -m angry_agents.src.rag.build_index        # build RAG index for judging
```

Full setup: `docs/architecture/SETUP.md`.

## Out of scope
Model training. All agents use external API calls only.
