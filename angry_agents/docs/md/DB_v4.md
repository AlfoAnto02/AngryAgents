# Angry Agents DB v4
_Schema definition — June 1, 2026_

> **Changes from v3:** `Judges` gained a canonical `name` field and is now auto-seeded at startup. `Judge_evaluation` replaced the opaque `Score` column with three structured fields (`persona_identification`, `rag_candidates`, `group_fidelity_score`). `Group_chat` gained five operational columns (`status`, `author_map`, `speaker_stats`, `is_judged`, `report`).

---

## Tables

---

### `Judges`

Represents the 20 judge instances that evaluate agent conversations. Seeded automatically at server startup — never created manually.

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `ID` | Serial | Primary Key | — |
| `Role` | String | NOT NULL | One of: `style` \| `ideology` \| `general` \| `behavioral`. |
| `name` | String | NULLABLE, UNIQUE (non-null) | Canonical instance identifier: `style_1` … `style_5`, `ideology_1` … `behavioral_5`. Set at seed time; NULL for any manually-created judge rows. |
| `Temperature` | Float | NULLABLE | LLM sampling temperature for this judge instance. |
| `Guess` | String | NULLABLE | The judge's current top persona prediction (updated after each evaluation). |
| `Created_at` | Timestamp | NOT NULL, default NOW | — |
| `Updated_at` | Timestamp | NOT NULL, default NOW | — |
| `Deleted_at` | Timestamp | NULLABLE, default NULL | — |

> **Seeding:** `init_db()` calls `_seed_judges()` on every startup. The 20 canonical instances (5 per role × 4 roles) are inserted if not already present, keyed by `name`. Idempotent.

---

### `Judge_evaluation`

Stores the full output produced by one judge instance for one group chat. One row per (judge, chat) pair — max 20 rows per chat (one per judge instance).

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `ID_judge` | Serial | Foreign Key → `Judges.ID`, PK (composite) | — |
| `ID_chat` | Serial | Foreign Key → `Group_chat.ID`, PK (composite) | — |
| `persona_identification` | JSON | NULLABLE | Persona-centric scores: `[{persona_name, predicted, scores:[{author, score}]}]`. For each persona, which author digest the judge predicted played it and the full author×score matrix. Consumed by `metrics_persona_id.py` and `metrics_fidelity.py`. |
| `rag_candidates` | JSON | NULLABLE | List of persona names (`list[str]`) that this judge instance received as candidates from the RAG retrieval step. Records which shortlist the judge worked from. |
| `group_fidelity_score` | Integer | NULLABLE | Judge's 1–5 assessment of how well the group behaved as a coherent ensemble (extracted from the LLM response field `group_fidelity_score`). |
| `Created_at` | Timestamp | NOT NULL, default NOW | — |
| `Updated_at` | Timestamp | NOT NULL, default NOW | — |
| `Deleted_at` | Timestamp | NULLABLE, default NULL | — |

> **Primary key:** composite `(ID_judge, ID_chat)`.
> **Limit:** max 20 active (non-soft-deleted) rows per `ID_chat`, enforced in `JudgeEvaluationService.create()`.
> **v3 → v4:** `Score LIST(Float)` removed. Replaced by `persona_identification`, `rag_candidates`, `group_fidelity_score`.

---

### `Group_chat`

Represents a single chat session between agents, tied to a topic.

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `ID` | Serial | Primary Key | — |
| `ID_topic` | Serial | Foreign Key → `Topic.ID`, NOT NULL | Each group chat belongs to one topic. |
| `Created_by` | Serial | Foreign Key → `User.ID`, NULLABLE | The user who created the group chat. |
| `status` | String | NOT NULL, default `'pending'` | Chat lifecycle state: `pending` \| `running` \| `done` \| `stopped` \| `error`. |
| `author_map` | JSON | NULLABLE | `{author_digest: persona_name}` — maps each HMAC author token to the real persona name. **Secret: never exposed to judges or via public API.** Populated at judging time. |
| `speaker_stats` | JSON | NULLABLE | `{persona_name: {turns, share, ...}}` — per-persona turn counts and participation share. Used as input to `metrics_group.run()`. |
| `is_judged` | Integer | NOT NULL, default `0` | Boolean flag (0/1). Set to 1 when the judging pipeline completes successfully. Used by the UI to toggle the "Judge" / "View report" button. |
| `report` | JSON | NULLABLE | Flat UI report blob produced by `_build_ui_report()`. Contains all data needed to populate the 4 tabs of `JudgingModal` in the frontend. **Admin-only — not returned by the standard `GroupChatOut` schema.** |
| `Created_at` | Timestamp | NOT NULL, default NOW | — |
| `Updated_at` | Timestamp | NOT NULL, default NOW | — |
| `Deleted_at` | Timestamp | NULLABLE, default NULL | — |

> **v3 → v4:** Added `status`, `author_map`, `speaker_stats`, `is_judged`, `report`.

---

### `Topic`

Defines the subject/theme that a group chat is built around.

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `ID` | Serial | Primary Key | — |
| `Title` | String | NOT NULL, UNIQUE | Short display title. |
| `Description` | Text | NULLABLE | Long-form description of the topic. |
| `Created_by` | Serial | Foreign Key → `User.ID` | The user who created the topic. |
| `Created_at` | Timestamp | NOT NULL, default NOW | — |
| `Updated_at` | Timestamp | NOT NULL, default NOW | — |
| `Deleted_at` | Timestamp | NULLABLE, default NULL | — |

---

### `User`

Represents a platform user who can create topics, group chats, and messages.

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `ID` | Serial | Primary Key | — |
| `Username` | String | NOT NULL, UNIQUE | — |
| `Password` | String | NOT NULL | Stored as bcrypt hash, never plaintext. |
| `Name` | String | NOT NULL | — |
| `Surname` | String | NOT NULL | — |
| `Role` | String | NOT NULL | One of: `common` \| `admin`. |
| `Email` | String | NOT NULL, UNIQUE | — |
| `Slug` | String | NOT NULL, UNIQUE | URL-friendly identifier derived from `name` + `surname`. |
| `Created_at` | Timestamp | NOT NULL, default NOW | — |
| `Updated_at` | Timestamp | NOT NULL, default NOW | — |
| `Deleted_at` | Timestamp | NULLABLE, default NULL | — |

---

### `Agents`

Represents an AI persona agent that participates in group chats.

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `ID` | Serial | Primary Key | — |
| `ID_topic` | Serial | Foreign Key → `Topic.ID`, NULLABLE | Optional topic association. |
| `Created_by` | Serial | Foreign Key → `User.ID` | The user who created the agent. |
| `Name` | String | NOT NULL | — |
| `Surname` | String | NOT NULL | — |
| `Slug` | String | NOT NULL, UNIQUE | URL-friendly identifier derived from `name` + `surname`. |
| `Summary` | JSON | NULLABLE | Full persona profile JSON (loaded from `data/personas/*.json` at seed time). Used as the authoritative profile when no `Agent_context` rows exist. |
| `Created_at` | Timestamp | NOT NULL, default NOW | — |
| `Updated_at` | Timestamp | NOT NULL, default NOW | — |
| `Deleted_at` | Timestamp | NULLABLE, default NULL | — |

---

### `Agent_context`

Stores contextual data (extracted persona profile, signature phrases) assigned to agents.

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `ID_context` | Serial | Primary Key | — |
| `ID_agent` | Serial | Foreign Key → `Agents.ID` | — |
| `Signature_phrases` | JSON | NULLABLE | Structured persona profile used to build the prompt profile block. When present, takes priority over `Agents.Summary`. |
| `Created_at` | Timestamp | NOT NULL, default NOW | — |
| `Updated_at` | Timestamp | NOT NULL, default NOW | — |
| `Deleted_at` | Timestamp | NULLABLE, default NULL | — |

---

### `Chat_messages`

Stores individual messages sent within a group chat. Message authorship is anonymised by design.

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `ID` | Serial (ascending) | Primary Key | Auto-incrementing to preserve message order. |
| `ID_Chat` | Serial | Foreign Key → `Group_chat.ID` | — |
| `message` | Text | NOT NULL | The message content. |
| `author` | String | NULLABLE | HMAC-SHA256 digest of `name:surname` keyed with `ANGRY_AUTHOR_SECRET`. Allows judges to distinguish message sources without knowing agent identity. NULL for user-posted messages. |
| `Created_by` | Serial | Foreign Key → `User.ID`, NULLABLE | Set for user-posted messages; NULL for agent-posted messages. |
| `Created_at` | Timestamp | NOT NULL, default NOW | — |
| `Updated_at` | Timestamp | NOT NULL, default NOW | — |
| `Deleted_at` | Timestamp | NULLABLE, default NULL | — |

> **Anonymity invariant:** `author` is intentionally not a foreign key to `Agents`. The digest lets judges distinguish sources without revealing real agent identity. The mapping is stored in `Group_chat.author_map` (admin-only, never sent to judges).

---

## Relationships

| # | From | Cardinality | To | Foreign Key | Notes |
|---|---|---|---|---|---|
| 1 | `Judges` | 1 : n | `Judge_evaluation` | `Judge_evaluation.ID_judge` | One judge instance has at most one evaluation per chat; many chats over time. |
| 2 | `Judge_evaluation` | n : 1 | `Group_chat` | `Judge_evaluation.ID_chat` | Up to 20 evaluation rows per chat (one per judge instance). |
| 3 | `Group_chat` | 1 : n | `Chat_messages` | `Chat_messages.ID_Chat` | One group chat contains many messages. |
| 4 | `Group_chat` | n : 1 | `Topic` | `Group_chat.ID_topic` | Many group chats belong to one topic. |
| 5 | `Topic` | 1 : n | `Agents` | `Agents.ID_topic` (optional) | A topic can have zero or many associated agents. |
| 6 | `Agents` | 1 : n | `Agent_context` | `Agent_context.ID_agent` | One agent can have many context entries. |
| 7 | `User` | 1 : n | `Group_chat` | `Group_chat.Created_by` | One user can create many group chats. |
| 8 | `User` | 1 : n | `Topic` | `Topic.Created_by` | One user can create many topics. |
| 9 | `User` | 1 : n | `Agents` | `Agents.Created_by` | One user can create many agents. |
| 10 | `User` | 1 : n | `Chat_messages` | `Chat_messages.Created_by` | One user can post many messages. |

---

## Migration notes (v3 → v4)

All changes are additive (no columns dropped except `Score` in `Judge_evaluation`). Applied via `_MIGRATIONS` in `angry_agents/src/db/models/base.py` — idempotent, safe to run on any v3 database.

| Table | Change |
|---|---|
| `Judges` | Added `name TEXT`; unique index `idx_judges_name` on non-null names |
| `Judge_evaluation` | `Score TEXT` → removed (legacy column, ignored); added `persona_identification TEXT`, `rag_candidates TEXT`, `group_fidelity_score INTEGER` |
| `Group_chat` | Added `status TEXT NOT NULL DEFAULT 'pending'`, `author_map TEXT`, `speaker_stats TEXT`, `is_judged INTEGER NOT NULL DEFAULT 0`, `report TEXT` |
