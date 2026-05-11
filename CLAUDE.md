# CLAUDE.md — Angry Agents

## What it is
Chat app: users talk to AI persona-agents (DM or group). 20 judge-agents evaluate conversations. Stack: Node.js / ES modules, REST API, SQL DB.

## Persona types
- **Fiction**: extracted from books/movies/TV. Source: script lines + context.
- **Real-world**: extracted from podcast transcripts. Source: Q&A pairs.

Each agent maps to exactly one type (`Agents.Type_of_context`). Mutually exclusive — enforced at schema level via `Podcast_Agent_Context` vs `Fiction_Agents_Context`.

## Chat types
- **DM**: user ↔ one agent.
- **Group**: user + 8 agents, one topic.

## DB invariants
- `Chat_messages.author` = `name + surname + DIGEST` — judges see source diversity, not identity.
- **No FK** from `Chat_messages` → `Agents`. Anonymity enforced at schema level.
- Max **20** `Judge_evaluation` rows per chat.
- `Judges.Role` has 4 values (style / ideology / general / behavioral). Routes judge to correct rubric.

## Judge pipeline
**Phase 1** — all 20 judges work independently on: persona identification, individual fidelity (1–5), group fidelity, behavioral fidelity.
**Phase 2** — high-variance cases enter structured deliberation (3–5 rounds). Judges revise ratings. Track confidence alongside scores.

External omniscient agent has full context (persona profiles + chat + all judge outputs) and evaluates judge quality.

## User roles
- **Common**: chat, manage own conversations.
- **Admin**: manage personas, view judge evaluations on past chats.

## Key invariants
- Never expose real agent identity to judges during evaluation.
- Judge Phase 1 must complete before Phase 2 starts (no cross-contamination).
- LLM calls: not on every tick — only on meaningful state changes.
- Personas need 10k–50k tokens of source material before instantiation.

## Metrics (brief)
- Persona ID accuracy: binomial CI, baseline 12.5% (random over 8).
- Individual fidelity: median + IQR per persona, 20 ratings each.
- Group fidelity: Gini on turn distribution, cosine distance matrix (Spearman vs real).
- Deliberation: variance reduction across rounds, convergence rate with binomial CI.

## Out of scope
Model training. All agents use external API calls only.
