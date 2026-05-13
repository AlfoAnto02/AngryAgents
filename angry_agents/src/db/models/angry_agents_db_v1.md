# Angry Agents DB v1
_Schema definition — May 11, 2026_

> **How to use this file:**
> Review every table and field below. Add, remove, or annotate any parameter or relationship before passing this file to the model-generation step.

---

## Tables

---

### `Judges`

Represents the human (or automated) judges who evaluate agent conversations.

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `ID` | UUID / Serial | Primary Key | — |
| `Role` | Enum / String | NOT NULL | Used to distinguish judge types. There are four evaluation types, divided by role. |
| `Temperature` | Float | NULLABLE | — |
| `Guess` | String / Boolean | NULLABLE | — |
| `Created_at` | Timestamp | NOT NULL, default NOW | — |
| `Updated_at` | Timestamp | NOT NULL, default NOW | — |
| `Slug` | String | UNIQUE, NOT NULL | URL-friendly identifier. |

> **TODO:** Clarify the four `Role` values (enum values). Clarify the exact type and purpose of `Guess`.

---

### `Judge_evaluation`

Stores the evaluation scores that judges assign to group chats.

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `ID_judge` | UUID / Serial | Foreign Key → `Judges.ID` | — |
| `ID_chat` | UUID / Serial | Foreign Key → `Group_chat.ID` | — |
| `Score` | Float / Integer | NULLABLE | The evaluation score. |
| `Date` | Date | NULLABLE | Date the evaluation refers to (may differ from `Created_at`). |
| `Created_at` | Timestamp | NOT NULL, default NOW | — |
| `Updated_at` | Timestamp | NOT NULL, default NOW | — |
| `Slug` | String | UNIQUE, NOT NULL | URL-friendly identifier. |

> **TODO:** Define the score scale (e.g. 0–100, 1–5). Clarify whether `(ID_judge, ID_chat)` should be a composite unique constraint. The diagram shows cardinality **20 : 1** between `Judge_evaluation` and `Group_chat` — confirm whether one chat can receive up to 20 evaluations or if 20 is a fixed count.

---

### `Group_chat`

Represents a single chat session between agents, tied to a topic.

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `ID` | UUID / Serial | Primary Key | — |
| `creation_date` | Timestamp | NOT NULL, default NOW | — |
| `Updated_at` | Timestamp | NOT NULL, default NOW | — |
| `ID_topic` | UUID / Serial | Foreign Key → `Topic.ID` | Each group chat belongs to one topic. |

> **TODO:** Clarify if `creation_date` and a standard `Created_at` are the same concept or serve different purposes.

---

### `Topic`

Defines the subject/theme that a group chat is built around.

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `ID` | UUID / Serial | Primary Key | — |
| `creation_date` | Timestamp | NOT NULL, default NOW | — |
| `Updated_at` | Timestamp | NOT NULL, default NOW | — |
| `Description` | Text | NULLABLE | Long-form description of the topic. |
| `Title` | String | NOT NULL | Short display title. |

> **TODO:** Should `Title` be unique? Is there a maximum length?

---

### `Agents`

Represents an AI agent that participates in group chats.

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `ID` | UUID / Serial | Primary Key | — |
| `ID_topic` | UUID / Serial | Foreign Key → `Topic.ID`, NULLABLE | Optional. An agent may be associated with a specific topic. |
| `Name` | String | NOT NULL | — |
| `Surname` | String | NOT NULL | — |
| `Type_of_context` | Enum / String | NOT NULL | Describes the type of context the agent operates with. |
| `Created_at` | Timestamp | NOT NULL, default NOW | — |
| `Updated_at` | Timestamp | NOT NULL, default NOW | — |
| `Slug` | String | UNIQUE, NOT NULL | URL-friendly identifier. |
| `Summary` | JSON | NULLABLE | A JSON object storing a summary of the agent's state or profile. |

> **TODO:** Clarify the possible values for `Type_of_context`. Clarify the shape/schema of the `Summary` JSON field.

---

### `Agent_context`

Stores contextual data (e.g. background knowledge, persona details) assigned to agents. An agent can have multiple contexts.

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `ID_context` | UUID / Serial | Primary Key | — |
| `ID_agent` | UUID / Serial | Foreign Key → `Agents.ID` | — |
| `Signature_phrases` | Text / JSON | NULLABLE | Signature phrases or prompts associated with this context entry. |
| `Created_at` | Timestamp | NOT NULL, default NOW | — |
| `Updated_at` | Timestamp | NOT NULL, default NOW | — |

> **TODO:** Clarify the type of `Signature_phrases` (plain text, array, JSON). Should `(ID_agent, ID_context)` enforce uniqueness?

---

### `Chat_messages`

Stores individual messages sent within a group chat. Message authorship is anonymised by design.

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `ID` | Serial (ascending) | Primary Key | Auto-incrementing to preserve message order within a chat. |
| `ID_Chat` | UUID / Serial | Foreign Key → `Group_chat.ID` | — |
| `message` | Text | NOT NULL | The message content. |
| `author` | String | NOT NULL | Composed of `name + surname + DIGEST`. The digest is a hash that allows the judge to distinguish message sources without knowing the actual agent identity (encryption layer). |
| `Created_at` | Timestamp | NOT NULL, default NOW | — |

> **Note (from diagram):** The `author` field is intentionally not a foreign key to `Agents`. The encryption/digest mechanism lets judges distinguish different message sources without revealing which specific agent sent the message.
>
> **TODO:** Clarify the hashing algorithm used for the DIGEST component of `author`. Clarify whether `message` can be empty/null (e.g. for system events).

---

## Relationships

| # | From | Cardinality | To | Foreign Key | Notes |
|---|---|---|---|---|---|
| 1 | `Judges` | 1 | `Judge_evaluation` | `Judge_evaluation.ID_judge` | One judge can have many evaluations. |
| 2 | `Judge_evaluation` | n (up to 20) | `Group_chat` | `Judge_evaluation.ID_chat` | Many evaluations point to one group chat; diagram shows 20:1. |
| 3 | `Group_chat` | n | `Chat_messages` | `Chat_messages.ID_Chat` | One group chat contains many messages. |
| 4 | `Group_chat` | n | `Topic` | `Group_chat.ID_topic` | Many group chats belong to one topic. |
| 5 | `Topic` | n | `Agents` | `Agents.ID_topic` (optional) | A topic can have zero or many associated agents; an agent may have no topic. |
| 6 | `Agents` | 1 | `Agent_context` | `Agent_context.ID_agent` | One agent can have many context entries. |

> **TODO:** Confirm cascade rules for all foreign keys (ON DELETE / ON UPDATE behaviour). Confirm the exact meaning of the **20** on the `Judge_evaluation ↔ Group_chat` relationship.

---

## Design Notes & Open Questions

1. **Encryption / anonymisation layer** — The `author` field in `Chat_messages` uses a `name + surname + DIGEST` pattern so judges cannot identify the actual agent from a message. The hashing algorithm is not yet specified.
2. **Four judge roles** — The diagram mentions four evaluation types divided by judge role. The actual enum values need to be confirmed.
3. **`ID_topic` on `Agents` is optional** — An agent does not need to be tied to a topic (`0` side of the `0..n` relationship on the diagram).
4. **`Summary (json)` on `Agents`** — The internal structure of this JSON blob is not yet defined. Consider whether it should be normalized into its own table.
5. **`Slug` fields** — Present on `Judges`, `Judge_evaluation`, `Agents`. Confirm whether slugs are also needed on `Topic`, `Group_chat`, or `Chat_messages`.
6. **Timestamps naming inconsistency** — Some tables use `creation_date` (e.g. `Group_chat`, `Topic`) while others use `Created_at`. Consider aligning to a single convention.
