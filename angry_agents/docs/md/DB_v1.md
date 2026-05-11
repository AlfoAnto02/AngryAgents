# Angry Agents DB v1

> Schema version: 1 — May 6, 2026

## Overview

This database supports a system where **AI agents** converse in chats and their conversations are anonymously evaluated by **judges**. The design intentionally hides agent identities from judges through cryptographic hashing, ensuring unbiased scoring.

---

## Tables

### `Judges`

Stores the judge entities responsible for scoring conversations.

| Column      | Type / Constraint | Description                                                                |
|-------------|-------------------|----------------------------------------------------------------------------|
| ID          | Primary Key       | Unique judge identifier                                                    |
| Role        | —                 | Determines which type of evaluation this judge performs (four roles total) |
| Temperature | —                 | Likely a sampling/creativity parameter for the judge model                 |
| Guess       | —                 | A guess value associated with the judge's evaluation strategy              |

> Judges are divided by **role** to cover the four types of evaluation the system supports.

---

### `Judge_evaluation`

Junction table recording each judge's score for a given chat.

| Column    | Type / Constraint          | Description                         |
|-----------|----------------------------|------------------------------------ |
| ID_judge  | Foreign Key → `Judges.ID`  | Which judge evaluated               |
| ID_chat   | Foreign Key → `Chat.ID`    | Which chat was evaluated            |
| Score     | —                          | Numeric score assigned              |
| Date      | —                          | When the evaluation was recorded    |

**Cardinality:** each `Chat` can receive up to **20** evaluations (one per judge per chat).

---

### `Chat`

Represents a single conversation session.

| Column        | Type / Constraint | Description                     |
|---------------|-------------------|---------------------------------|
| ID            | Primary Key       | Unique chat identifier          |
| creation_date | —                 | Timestamp when the chat started |

---

### `Chat_messages`

Stores the individual messages within a chat. The author field is **anonymised** to protect agent identity.

| Column            | Type / Constraint          | Description                                         |
|-------------------|----------------------------|-----------------------------------------------------|
| ID                | Primary Key (ascending)    | Auto-incrementing message identifier                |
| ID_Chat           | Foreign Key → `Chat.ID`    | Which chat this message belongs to                  |
| message           | —                          | The message content                                 |
| author            | name + surname + **DIGEST**| Hashed identifier of the sender                     |

**Privacy design:** the `author` field concatenates the agent's name and surname with a cryptographic digest. This lets judges distinguish *different* sources within a conversation without learning *who* the actual agent is. The link between `Chat_messages` and `Agents` is therefore **not explicit** at the database level — the author field in this table is intentionally decoupled from the `Agents` table.

---

### `Agents`

Stores the AI agents that participate in chats.

| Column          | Type / Constraint | Description                                        |
|-----------------|-------------------|----------------------------------------------------|
| ID              | Primary Key       | Unique agent identifier                            |
| Name            | —                 | Agent's name (used in hashed author field)         |
| Surname         | —                 | Agent's surname (used in hashed author field)      |
| Type of context | —                 | Discriminator indicating which context table applies (`Podcast` or `Fiction`) |

Each agent has exactly **one** context type, enforced as **mutually exclusive** between `Podcast_Agent_Context` and `Fiction_Agents_Context`.

---

### `Podcast_Agent_Context`

Context data for agents operating in a **podcast** scenario (Q&A format).

| Column      | Type / Constraint              | Description                           |
|-------------|--------------------------------|---------------------------------------|
| ID_agent    | Foreign Key → `Agents.ID`      | Which agent this context belongs to   |
| ID_question | Primary Key                    | Unique question identifier            |
| Question    | —                              | The question the agent is given       |
| Answer      | —                              | The expected or reference answer      |

---

### `Fiction_Agents_Context`

Context data for agents operating in a **fictional/roleplay** scenario (script/line format).

| Column      | Type / Constraint              | Description                                         |
|-------------|--------------------------------|-----------------------------------------------------|
| ID_agent    | Foreign Key → `Agents.ID`      | Which agent this context belongs to                 |
| ID_line     | —                              | Identifier for the script line                      |
| line        | —                              | The line of dialogue or text the agent is assigned  |
| context     | Optional                       | Motivation or source information for the line       |

> The optional `context` field provides background on the line's origin or the character's motivation.

---

## Relationships and cardinalities

The E-R diagram contains the following main relationships.

| Relationship | Cardinality | Interpretation |
|---|---:|---|
| `Agents` → `Podcast_Agent_Context`  | 1 : n                                         | One agent can have multiple podcast question/answer context entries. |
| `Agents` → `Fiction_Agents_Context` | 1 : n                                         | One agent can have multiple fictional dialogue/context entries.      |
| `Chat`   → `Chat_messages`          | 1 : n                                         | One chat contains many messages; each message belongs to one chat.   | 
| `Judges` → `Judge_evaluation`       | 1 : n                                         | One judge can submit multiple evaluations.                           |
| `Chat`   → `Judge_evaluation`       | 1 : n (annotated as 20 on the evaluation side)| One chat can receive many evaluations; the diagram suggests a target of 20 evaluation records per chat. |
| `Agents` ↔ context subtype tables   | Mutually exclusive specialization             | An agent should be linked to one context family only, based on `Type of context`. |

## Key Design Decisions


| Author stored as `name + surname + DIGEST` in `Chat_messages` | Judges can tell messages apart by source but cannot identify the actual agent, removing evaluation bias |
| No explicit FK from `Chat_messages` to `Agents` | Enforces the anonymity guarantee at the schema level |
| `Podcast_Agent_Context` and `Fiction_Agents_Context` are mutually exclusive | An agent belongs to exactly one scenario type, controlled by `Agents.Type of context` |
| Judges split by `Role` | Four distinct evaluation types require four judge roles; the role field routes each judge to the correct rubric |
| Up to 20 evaluations per chat | Bounded multi-judge scoring to ensure coverage without unbounded growth |
