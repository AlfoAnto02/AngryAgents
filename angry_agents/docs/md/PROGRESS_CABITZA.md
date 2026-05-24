# Progress Log — Cabitza Session (2026-05-18 → 2026-05-24)

## 1. `base_judge.py` — redesigned abstract class

Replaced the old per-message `evaluate` / `deliberate` interface with four abstract methods aligned to the evaluation dimensions in the problem definition:

| Method | Status |
|---|---|
| `persona_identification(chat, personas)` | Implemented in all judges |
| `individual_fidelity(chat)` | Stub — not yet designed |
| `group_fidelity(chat)` | Stub — not yet designed |
| `behavioural_fidelity(chat)` | Stub — not yet designed |

New dataclasses:
- `AgentScore` — author DIGEST + score 1–5
- `PersonaMatch` — one per persona; holds per-agent scores and `.predicted` argmax
- `PersonaIdentificationResult` — list of `PersonaMatch`, one per persona profile

Input is the full `chat: dict` plus a `personas: list[dict]` of profile files.

## 2. Judge implementations

Three concrete judges, each extending `BaseJudge`:

| File | Class | Focus |
|---|---|---|
| `style_judge.py` | `StyleJudge` | Vocabulary, sentence structure, tone, rhetorical habits |
| `ideology_judge.py` | `IdeologyJudge` | Political views, values, moral stances, belief systems |
| `general_judge.py` | `GeneralJudge` | All observable traits combined |

`persona_identification` loops over all persona profiles. For each persona it calls Ollama (mistral) asking the model to score every agent 1–5 on how likely they are acting as that persona, then takes the argmax as the predicted agent. Each judge differs only in its focus-specific prompt.

## 3. `agent_config.py` — shared config and helpers

Created `angry_agents/src/agents/agent_config.py` to centralise all code shared across judges:

- `OLLAMA_BASE_URL` and `DEFAULT_MODEL` — read from `.env` via `python-dotenv`.
- `format_messages(chat)` — groups chat messages by author DIGEST.
- `format_profile(profile)` — serialises a persona profile dict into prompt text.
- `_parse_agent_scores(raw, authors)` — parses LLM output into `AgentScore` list.
- `_ollama_call(prompt, model)` — raw HTTP call to Ollama, returns response text.
- `run_persona_identification(build_prompt, chat, personas, model)` — shared loop: iterates over personas, builds the prompt via the judge's lambda, calls Ollama, parses scores, returns `PersonaIdentificationResult`.

Each judge file is now just a prompt template constant and a class definition.

## 4. `evaluation_test.py` — test runner

Loads the real transcript (`data/eval/transcript.jsonl`, JSONL format) and all persona profiles from `data/personas/*.json`. Runs `persona_identification` on all three judges and:

1. Prints per-judge, per-persona score tables and predicted agents to stdout.
2. Saves a `Judge_evaluation` JSON to `angry_agents/data/judge_eval/eval_test_n.json`, where `n` auto-increments on each run.

The saved JSON follows the `Judge_evaluation` schema from DB_v2.md (`ID_judge`, `ID_chat`, `Score`, `Created_at`, `Updated_at`, `Deleted_at`) plus a `persona_identification` block with full per-persona results. `Score` is `null` pending design of the aggregate metric.

Run from repo root:
```bash
python -m angry_agents.src.agents.judges.evaluation_test
```

Requires Ollama running in a separate terminal (`ollama serve`) with mistral available (`ollama pull mistral`).

## 5. Real transcript integration

Switched from the fake chat JSON to `data/eval/transcript.jsonl` (40 messages, 7 agents). Key difference: JSONL format (one JSON object per line), fields are `msg_id`, `turn`, `author`, `message`, `drifted`. The loader parses it line-by-line and wraps it in the `{"messages": [...]}` envelope the judges expect.

Personas available in `data/personas/`: `cicciogamer89`, `INDY`, `JACK`, `LUKE`, `RIGGAN`, `VADER`, `YODA`.

## Open points

- `individual_fidelity`, `group_fidelity`, `behavioural_fidelity` are empty stubs — design pending.
- A fourth judge type (`behavioral`) is referenced in the problem definition but not yet created.
- No `__init__.py` files exist under `src/agents/` — package structure relies on running via `-m`.
- `Score` in `Judge_evaluation` output is always `null` — aggregate scoring metric not yet designed.
- Timeout hit during testing: 40-message transcript × 7 personas is too large for mistral within 120 s. Prompt size or chunking strategy needs revisiting.

---

## 6. `PersonaAgent` — agent runtime class (2026-05-20)

New module `src/agents/personas/` with two public classes:

**`PersonaAgent`** (`persona_agent.py`) — wraps a DB `Agent` row and its `AgentContext` entries into a live, chat-ready object:

| Method | Behaviour |
|---|---|
| `bind_to_chat(chat_id, topic)` | Resolves persona name, profile block, and topic block from DB data; derives `dominance_weight` from `social_positioning` keywords in context |
| `respond(history, turn_count)` | Renders `persona_chat.j2`, calls `llm_call`, returns the raw reply string |
| `update_summary(chat_id, message, summary)` | Increments `turn_count` in the agent's JSON summary dict |

`dominance_weight` drives turn scheduling: `assertive`/`dominant`/`leader` → 0.7, `reserved`/`quiet`/`passive` → 0.3, default → 0.5.

**`AgentFactory`** (`factory.py`) — two static methods:

- `from_db(db, agent_id, model)` — loads one agent + its contexts from the DB and returns a `PersonaAgent`.
- `for_chat(db, chat_id, model)` — looks up all agents bound to the chat's topic, instantiates and binds them all, returns the full list.

**`persona_chat.j2`** — Jinja2 prompt template with `{% block system %}` (persona identity, profile, topic, behavioural rules) and `{% block user %}` (conversation history + reground reminder every 20 turns). The reground block is injected conditionally to prevent persona drift over long sessions.

Documented in `docs/md/agents_system_guide.md` (440 lines).

---

## 7. Group Chat runtime (2026-05-20)

New module `src/group_chat/` with four classes wired together by `GroupChatFactory`:

**`TurnScheduler`** — selects which agent speaks next:
- `round_robin` — cycles through agents in order.
- `weighted_random` — samples using `agent.dominance_weight` as probability weights.

**`ContextWindow`** — trims message history before passing it to each agent:
- `rolling` — keeps the last `max_messages` messages.
- `selective` — keeps the first 25 % (anchoring) + last 75 % (recency), total capped at `max_messages`.

**`GroupChatSession`** — orchestrates a full chat loop:
- `run(db, n_turns, on_message)` — runs `n_turns` turns, calls optional `on_message` callback per message.
- `run_turn(db)` — picks next agent via scheduler, trims history via context window, calls `agent.respond()`, persists the message to DB via `ChatMessageService` (author field = HMAC-anonymised digest), triggers `agent.update_summary()` every 10 turns.

**`GroupChatFactory.build_session(db, chat_id, model, author_secret, ...)`** — assembles all components from the DB in one call: loads `GroupChat` + `Topic`, builds agents via `AgentFactory.for_chat`, wires scheduler and context window, returns a ready `GroupChatSession`.

---

## 8. Template and judge cleanup (2026-05-20)

- Removed `generic_agent.py` — superseded by `PersonaAgent`.
- Minor prompt fixes in `persona_id_ideology.j2` and `persona_id_behavioral.j2`.
- Updated `evaluation_test.py` loader to match the new JSONL transcript format.

---

## 9. Judge architecture corrections (2026-05-20)

Resolved all coherence issues found between the judge agent code and the DB/API layer:

- **Removed `AgentScore`** from `base_judge.py` — redundant intermediate dataclass that duplicated `PersonaScore`. `_parse_json_scores` in `agent_config.py` now returns `dict[str, int]` (author → score) directly; call site constructs `PersonaScore` objects inline. No more mid-function type conversion.
- **`format_messages` null-author guard** — messages without an `author` field (user-posted rows where `author IS NULL`) are now skipped with a `log.warning` instead of silently keying the `defaultdict` on `None`.
- **Template block guard** — `render_prompt` in both `judges/templates/__init__.py` and `personas/templates/__init__.py` now raises `ValueError` if a template is missing either `{% block system %}` or `{% block user %}`, preventing silent empty-prompt LLM calls.
- **`pipeline.py`** (`src/agents/judges/pipeline.py`) — new integration layer: `run_and_persist(db, judge_db_id, chat_id, judge, chat, personas)` runs persona identification, writes the top predicted persona to `Judges.Guess`, and creates a `Judge_evaluation` row in the DB (`score=None` until fidelity methods are implemented). This closes the gap between the agent pipeline and the persistence layer.
- **`Score` type fixed in tests** — all test fixtures and assertions for `Judge_evaluation.score` corrected from scalar `float` to `list[float]`, matching the dataclass declaration and DB_v3 schema.
- **Removed `persona_id_behavioral.j2`** — orphaned template with no corresponding judge class.

## Updated open points (2026-05-20)

- `individual_fidelity`, `group_fidelity`, `behavioural_fidelity` still empty stubs — design pending.
- `BehavioralJudge` class not created; `behavioral` role remains valid in the DB enum for future use.
- `Score` in `Judge_evaluation` is always `null` until fidelity methods are implemented.
- Timeout hit during LLM evaluation: 40-message transcript × 7 personas still too slow for mistral within 120 s.

---

## 10. `logging_setup.py` — `deviation()` and fail-loudly fix (2026-05-24)

New shared module `src/logging_setup.py` implementing the `deviation()` convention from CLAUDE.md:

- `UnexpectedDeviation(RuntimeError)` — raised when `STRICT_MODE=1`.
- `deviation(msg, **kwargs)` — calls `log.warning` in normal mode, raises `UnexpectedDeviation` in strict mode.

Fixed `_run_agent_turns` in `ui_routes.py` (now `_dm_run_agent_turn` / `_bg_run_conversation`):
- Removed the outer `except Exception` that swallowed all errors silently.
- Moved broad-catch **inside** the per-turn loop so one failing agent does not abort the others.
- Replaced `log.warning(...)` with `deviation(...)` so CI under `STRICT_MODE=1 pytest` surfaces failures as hard errors.

---

## 11. `PersonaAgent` — profile-driven scheduling behaviour (2026-05-24)

Extended `PersonaAgent` with two new behavioural attributes derived from `signature_phrases` at `bind_to_chat()` time:

| Attribute | Source field | Semantics |
|---|---|---|
| `cooldown_turns` | `core_style.rhythm` | Turns before this agent's weight recovers after speaking. `fast`/`staccato` → 1, `slow`/`deliberate` → 6, default 3 |
| `burst_size` | `core_style.sentence_shape` | Consecutive messages per scheduled turn. `clipped`/`fragment` → 3, `compound`/`rhetorical` → 1, default 2 |

Fixed `_extract_dominance_weight`: fiction profiles store `social_positioning` as a nested dict (keys `desired_position`, `actual_dynamic`, `contradiction`), not a plain string. The function now flattens the dict values before keyword matching; all fiction agents previously fell through to the 0.5 default.

Added `_template_name` field (default `"group_persona_chat.j2"`), set by `bind_to_chat()` and used by `respond()` to select the correct Jinja2 template.

---

## 12. `TurnScheduler` — real `mark_spoke()` and cooldown (2026-05-24)

`TurnScheduler` rewritten to make `mark_spoke()` functional:

- `_last_spoke: dict[int, int]` — maps `agent.id` → turn number of last speech.
- `_effective_weight(agent)` — returns `dominance_weight * 0.1` if agent is within its `cooldown_turns` window, else full weight.
- `next()` now uses `_effective_weight` for `weighted_random` selection.
- `mark_spoke(agent)` records the current turn in `_last_spoke`.

`GroupChatSession.run_turn()` updated to loop `burst_size` times per chosen agent, fetching fresh history from DB before each burst message so agents see their own previous burst messages in context.

---

## 13. Group chat → autonomous agent conversation (2026-05-24)

Redesigned the group chat flow from a user-triggered per-message model to a fully autonomous agent-to-agent conversation:

**DB: `Group_chat.status` column**
- Added `status TEXT NOT NULL DEFAULT 'pending'` to `Group_chat`.
- Safe migration via `base.py:_MIGRATIONS` list (try/except `OperationalError` so existing DBs are updated without breaking).
- Values: `pending` → `running` → `done` | `error`.
- `GroupChatService.set_status(id, status)` added.

**New templates**
- `persona_chat.j2` revised: now correctly scoped to **DM** (one-on-one with a human user).
- `group_persona_chat.j2` new: autonomous peer conversation between agents, no external user, cold-open rule added for the first message.

**New endpoints in `ui_routes.py`**

| Endpoint | Method | Behaviour |
|---|---|---|
| `/ui/chats/{chat_id}/start` | POST | Validates status, launches `_bg_run_conversation` as a FastAPI `BackgroundTask`, returns 202 |
| `/ui/chats/{chat_id}/stream` | GET (SSE) | Polls DB every 0.5 s for new messages since `?after=<id>`, streams each as `data: {...}`, sends `event: done` when `status ∈ {done, error}` and no new rows remain |

**`ui_create_message`** — agent turns now only triggered for **DM** chats (`agent_count == 1`). Group chats are autonomous after `/start`; user messages are saved to DB but do not trigger agents.

**`_bg_run_conversation`** creates its own DB connection (request connection closes before task runs), sets status to `running`, calls `GroupChatSession.run(conn, n_turns)`, sets status to `done` on completion or `error` on unhandled exception.

---

## 14. `dm_chat/` — `DMSession` and `DMFactory` (2026-05-24)

New module `src/dm_chat/` separating DM logic from the group chat path:

**`DMSession`** (`session.py`) — dataclass with `chat_id`, `topic`, `agent`, `context_window`, `author_secret`:
- `respond(db)` — loads history, trims via `ContextWindow`, calls `agent.respond()`, writes message via `ChatMessageService`. No scheduler, no burst, no background task.

**`DMFactory`** (`factory.py`) — `build_session(db, chat_id, model, author_secret, ...)`:
- Loads the single agent from `Chat_agent` join.
- Calls `agent.bind_to_chat(chat_id, topic, template_name="persona_chat.j2")` explicitly.
- Default `window_strategy="rolling"` (DM history is linear, no need for selective anchoring).

`_dm_run_agent_turn` in `ui_routes.py` now delegates to `DMFactory` + `DMSession.respond()`.
`GroupChatFactory` simplified: DM template selection removed, always uses `group_persona_chat.j2`.

---

## 15. `.env.example` (2026-05-24)

Added `.env.example` to the repository root covering all environment variables found in the codebase:

- **Database**: `ANGRY_DB_PATH`
- **Security**: `ANGRY_AUTHOR_SECRET`, `JWT_SECRET_KEY`, token expiry settings, `COOKIE_SECURE`
- **Auth (dev)**: `AUTH_DISABLED`
- **LLM backend**: `LLM_BACKEND`, `OLLAMA_BASE_URL`, `OLLAMA_DEFAULT_MODEL`, `OPENAI_API_KEY`, `OPENAI_MODEL`
- **MCP client**: `ANGRY_API_BASE_URL`
- **Dev/CI**: `STRICT_MODE`

`.env` remains in `.gitignore`.

---

## Open points (2026-05-24)

- `individual_fidelity`, `group_fidelity`, `behavioural_fidelity` still empty stubs — design pending.
- `BehavioralJudge` class not yet created.
- `Score` in `Judge_evaluation` always `null` until fidelity methods are implemented.
- LLM evaluation timeout: 40-message transcript × 7 personas still too slow for mistral in 120 s.
- `GroupChatSession.run()` n_turns default (30) not yet exposed as a user-facing setting in the UI.
- No frontend changes to drive `/start` and consume `/stream` — UI integration pending.
