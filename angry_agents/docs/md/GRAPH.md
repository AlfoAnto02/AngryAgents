# Knowledge Graph — Quick Reference

This repo ships a **pre-built** knowledge graph in `graphify-out/graph.json` (6,920 nodes, 8,337 edges).

**Do NOT re-run `/graphify .`** — the graph is already built and committed. Just install the tool and query it directly. Re-running a full build costs ~88 LLM agent calls and is unnecessary.

## Setup (one-time)

```bash
pip install graphifyy
```

## Querying the graph

Run these from the **project root** inside Claude Code with `/graphify`:

```bash
# Ask an architecture question — BFS traversal, broad context
/graphify query "how does the judge pipeline work"
/graphify query "how is agent anonymisation enforced in chat messages"
/graphify query "what connects the RAG system to persona agents"
/graphify query "how does authentication work"

# Trace a specific dependency path between two concepts
/graphify path "PersonaAgent" "JudgeEvaluation"
/graphify path "GroupChatService" "RAG Index Builder"

# Deep-dive on a single node — all its connections explained
/graphify explain "GroupChatService"
/graphify explain "per_judge_type"
/graphify explain "HMAC Author Token"
```

## Key communities (what lives where)

| Community | What's in it |
|---|---|
| Architecture & Core Concepts | Design docs, CLAUDE.md, abstract base classes, domain concepts |
| Application Core & Auth | FastAPI app, config, deps, JWT utils |
| Agent API & Repository | `/agents` routes, agents DB repository and models |
| User API & Service | `/users` routes, user service |
| Agent Context API | `/agent_context` routes, context service |
| Group Chat Runtime | GroupChatFactory, ContextWindow, TurnScheduler, ChatMessage model |
| Group Chat API & Tests | `/group_chats` routes, group chat service tests |
| Topic API & Service | `/topics` routes, topic service |
| Judge Pipeline | BaseJudge, pipeline.py, judge orchestration |
| Judge Evaluation API | `/judge_evaluations` routes and service |
| Judges API & Tests | `/judges` routes, judge repository tests |
| Evaluation Statistics Engine | bootstrap.py, deliberation metrics, fidelity metrics |
| Evaluation Framework Design | Design concepts from eval presentation (Gini, cosine distance, CI) |
| Persona Agent Engine | PersonaAgent class, profile builder, burst mode |
| Persona Profile Extraction | extract_profile.py — LLM-based profile extraction pipeline |
| RAG Index Builder | build_index.py, builder.py, indexer.py |
| PDF Content Scraping | pdf_scraping.py |
| Movie/Fiction Scraping | movies_scraping.py |
| UI & Admin Routes | ui_routes.py, admin streaming endpoints |
| UI Component Library | React components (Avatar, Btn, Checkbox, …) |
| UI App Shell | App.jsx, routing, error boundary |
| Admin Dashboard UI | AdminDashboard, AgentPerformanceSection, FidelityBar |

## God nodes (most-connected abstractions)

These are the highest-degree nodes — the concepts everything else depends on:

1. `UserService` (45 edges)
2. `GroupChatService` (41 edges)
3. `TopicService` (39 edges)
4. `AgentService` (35 edges)
5. `AgentContextService` (30 edges)
6. `JudgeService` (29 edges)
7. `JudgeEvaluationService` (28 edges)
8. `_make()` — shared test factory across all test suites (27 edges)

## Key design decisions captured in the graph

- **Author anonymisation** — `Chat_messages.author` is `name + surname + DIGEST`, deliberately not a FK to `Agents`. The graph flags this as an AMBIGUOUS edge between the two tables — by design.
- **Two-phase judge pipeline** — Phase 1 (all 20 judges independent) → Phase 2 (high-variance deliberation). The graph has a hyperedge linking `concept_judge_pipeline_phase1`, `concept_judge_pipeline_phase2`, `concept_omniscient_agent`.
- **Persona context stack** — five mechanisms work together: structured profile + RAG + sliding window + reflection + perturbation. Captured as a hyperedge in the graph.
- **`gini()` bridges Chat and Eval** — the Gini coefficient for turn distribution is computed from chat message data but consumed by the evaluation statistics engine. High betweenness centrality node.

## Keeping the graph up to date

Only if **you added or modified files** since the last commit, regenerate only the changed parts:

```bash
/graphify . --update   # re-extracts only new/changed files, then commits graph.json
```

**Never run `/graphify .`** (no `--update`) unless you want to rebuild everything from scratch — it spawns ~88 LLM agents and is expensive.
