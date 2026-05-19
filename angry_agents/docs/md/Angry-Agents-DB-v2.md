# Angry Agents DB v3
_Schema definition — May 19, 2026_


> **How to use this file:**
> Review every table and field below. Add, remove, or annotate any parameter or relationship before passing this file to the model-generation step.

---

## Tables

---


### `Judges`

Represents the human (or automated) judges who evaluate agent conversations.

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `ID` | Serial | Primary Key | — |
| `Role` | String | NOT NULL | Used to distinguish judge types. There are four evaluation types, divided by role. |
| `Temperature` | Float | NULLABLE | — |
| `Guess` | String | NULLABLE | — |
| `Created_at` | Timestamp | NOT NULL, default NOW | — |
| `Updated_at` | Timestamp | NOT NULL, default NOW | — |
| `Deleted_at` | Timestamp | NULLABLE, default NULL | — |

---

### `Judge_evaluation`

Stores the evaluation scores that judges assign to group chats.

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `ID_judge` | Serial | Foreign Key → `Judges.ID`, PK (composite) | — |
| `ID_chat` | Serial | Foreign Key → `Group_chat.ID`, PK (composite) | — |
| `Score` | List(Float) | NULLABLE | The evaluation score. |
| `Created_at` | Timestamp | NOT NULL, default NOW | — |
| `Updated_at` | Timestamp | NOT NULL, default NOW | — |
| `Deleted_at` | Timestamp | NULLABLE, default NULL | — |

> **Note:** Primary key is the composite `(ID_judge, ID_chat)`.

---

### `Group_chat`

Represents a single chat session between agents, tied to a topic.

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `ID` | Serial | Primary Key | — |
| `Created_at` | Timestamp | NOT NULL, default NOW | — |
| `Updated_at` | Timestamp | NOT NULL, default NOW | — |
| `Deleted_at` | Timestamp | NULLABLE, default NULL | — |
| `ID_topic` | Serial | Foreign Key → `Topic.ID` | Each group chat belongs to one topic. |
| `Created_by` | Serial | Foreign Key → `User.ID` | The user who created the group chat. |

---

### `Topic`


Defines the subject/theme that a group chat is built around.


| Field | Type | Constraints | Notes |
|---|---|---|---|
| `ID` | Serial | Primary Key | — |
| `Created_at` | Timestamp | NOT NULL, default NOW | — |
| `Updated_at` | Timestamp | NOT NULL, default NOW | — |
| `Deleted_at` | Timestamp | NULLABLE, default NULL | — |
| `Created_by` | Serial | Foreign Key → `User.ID` | The user who created the topic. |
| `Description` | Text | NULLABLE | Long-form description of the topic. |
| `Title` | String | NOT NULL, UNIQUE | Short display title. |

---

### `User`

Represents a platform user who can create topics, group chats, and messages.

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `ID` | Serial | Primary Key | — |
| `Username` | String | NOT NULL, UNIQUE | — |
| `Password` | String | NOT NULL | Store as hashed value, never plaintext. |
| `Name` | String | NOT NULL | — |
| `Surname` | String | NOT NULL | — |
| `Role` | String | NOT NULL | Determines user permissions on the platform. |
| `Email` | String | NOT NULL, UNIQUE | — |
| `Created_at` | Timestamp | NOT NULL, default NOW | — |
| `Updated_at` | Timestamp | NOT NULL, default NOW | — |
| `Deleted_at` | Timestamp | NULLABLE, default NULL | — |
| `Slug` | String | NOT NULL, UNIQUE | URL-friendly identifier. `name` + `surname`. |

---

### `Agents`

Represents an AI agent that participates in group chats.

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `ID` | Serial | Primary Key | — |
| `ID_topic` | Serial | Foreign Key → `Topic.ID`, NULLABLE | Optional. An agent may be associated with a specific topic. |
| `Name` | String | NOT NULL | — |
| `Surname` | String | NOT NULL | — |
| `Created_at` | Timestamp | NOT NULL, default NOW | — |
| `Updated_at` | Timestamp | NOT NULL, default NOW | — |
| `Deleted_at` | Timestamp | NULLABLE, default NULL | — |
| `Created_by` | Serial | Foreign Key → `User.ID` | The user who created the agent. |
| `Slug` | String | UNIQUE, NOT NULL | URL-friendly identifier. `name` + `surname`. |
| `Summary` | JSON | NULLABLE | A JSON object storing a summary of the agent's state or profile. |

---

### `Agent_context`

Stores contextual data (e.g. background knowledge, persona details) assigned to agents. An agent can have multiple contexts.

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `ID_context` | Serial | Primary Key | — |
| `ID_agent` | Serial | Foreign Key → `Agents.ID` | — |
| `Signature_phrases` | JSON | NULLABLE | Signature phrases or prompts associated with this context entry. |
| `Created_at` | Timestamp | NOT NULL, default NOW | — |
| `Updated_at` | Timestamp | NOT NULL, default NOW | — |
| `Deleted_at` | Timestamp | NULLABLE, default NULL | — |

---

### `Chat_messages`

Stores individual messages sent within a group chat. Message authorship is anonymised by design.

| Field | Type | Constraints | Notes |
|---|---|---|---|
| `ID` | Serial (ascending) | Primary Key | Auto-incrementing to preserve message order within a chat. |
| `ID_Chat` | Serial | Foreign Key → `Group_chat.ID` | — |
| `message` | Text | NOT NULL | The message content. |
| `author` | String | NULLABLE| Composed of `name + surname + DIGEST`. The digest is a hash that allows the judge to distinguish message sources without knowing the actual agent identity (encryption layer). |
| `Created_at` | Timestamp | NOT NULL, default NOW | — |
| `Updated_at` | Timestamp | NOT NULL, default NOW | — |
| `Deleted_at` | Timestamp | NULLABLE, default NULL | — |
| `Created_by` | Serial | Foreign Key → `User.ID`, NULLABLE | The user who posted the message. |

> **Note:** The `author` field is intentionally not a foreign key to `Agents`. The encryption/digest mechanism lets judges distinguish different message sources without revealing which specific agent sent the message.


---


## Relationships


| # | From | Cardinality | To | Foreign Key | Notes |
|---|---|---|---|---|---|
| 1 | `Judges` | 1 : n | `Judge_evaluation` | `Judge_evaluation.ID_judge` | One judge can have many evaluations. |
| 2 | `Judge_evaluation` | n : 1 | `Group_chat` | `Judge_evaluation.ID_chat` | Many evaluations point to one group chat. |
| 3 | `Group_chat` | 1 : n | `Chat_messages` | `Chat_messages.ID_Chat` | One group chat contains many messages. |
| 4 | `Group_chat` | n : 1 | `Topic` | `Group_chat.ID_topic` | Many group chats belong to one topic. |
| 5 | `Topic` | 1 : n | `Agents` | `Agents.ID_topic` (optional) | A topic can have zero or many associated agents; an agent may have no topic. |
| 6 | `Agents` | 1 : n | `Agent_context` | `Agent_context.ID_agent` | One agent can have many context entries. |
| 7 | `User` | 1 : n | `Group_chat` | `Group_chat.Created_by` | One user can create many group chats. |
| 8 | `User` | 1 : n | `Topic` | `Topic.Created_by` | One user can create many topics. |
| 9 | `User` | 1 : n | `Agents` | `Agents.Created_by` | One user can create many agents. |
| 10 | `User` | 1 : n | `Chat_messages` | `Chat_messages.Created_by` | One user can post many messages. |
