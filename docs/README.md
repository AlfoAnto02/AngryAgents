# Documentation

This folder holds two kinds of documents, kept deliberately separate:

- **[architecture/](architecture/)**: how the system works **now**. Use these docs to run, understand or extend the code.
- **[process/](process/)**: how we **got here**. These are design documents written during the project and kept exactly as written. Each one starts with a banner that says when it was written, by whom, and what changed afterwards.

[DECISIONS.md](DECISIONS.md) connects the two: one page covering the 16 decisions that shaped the final system, each linked to where it was first recorded.

## Where to start

| Time | Read |
|---|---|
| **5 min** | The project [README](../README.md), then the timeline at the top of [DECISIONS.md](DECISIONS.md) |
| **30 min** | All of [DECISIONS.md](DECISIONS.md), [EVAL.md](architecture/EVAL.md) and the [final presentation](presentations/04_final_presentation.pdf) |
| **Deep dive** | The [technical report](report/report.pdf), then the architecture docs below |
| **The raw process** | The [process docs](#process-how-we-got-here) in order, plus the [sprint notes](sprints/) |

## Architecture: how it works now

| Document | What it covers |
|---|---|
| [SETUP.md](architecture/SETUP.md) | From a fresh clone to a running app with the demo database |
| [DB_v4.md](architecture/DB_v4.md) | Final database schema and what changed from v3 |
| [agents_system_guide.md](architecture/agents_system_guide.md) | Persona agents, turn scheduler, context window, group-chat session |
| [group_chat_spiegazione.md](architecture/group_chat_spiegazione.md) | The same engine explained in Italian (English summary at the top) |
| [EVAL.md](architecture/EVAL.md) | Per-chat metrics: persona ID, individual and group fidelity |
| [EVAL_BATCH.md](architecture/EVAL_BATCH.md) | Aggregating metrics across many chats |
| [MCP.md](architecture/MCP.md) | The Model Context Protocol server and its tools |
| [GRAPH.md](architecture/GRAPH.md) | Querying the pre-built code knowledge graph in [`graphify-out/`](../graphify-out/) |
| [RAG_EXPLANATION.md](../angry_agents/src/rag/RAG_EXPLANATION.md) | Candidate retrieval for judges (kept next to the code) |
| [MCP_SETUP.md](../angry_agents/src/mcp/MCP_SETUP.md) | Connecting Claude Code to the MCP server (kept next to the code) |

## Process: how we got here

Numbered in the order they were written.

| # | Document | Written | Status |
|---|---|---|---|
| 01 | [Problem definition](process/01_NEW_PROBLEM.md) | May 5–11 | Scope later reduced (no deliberation, no omniscient agent) |
| 02 | [State of the art](process/02_SOTA.md) | May 6–11 | Literature review behind the evaluation design |
| 03 | [Experimentation plan](process/03_EXPERIMENTATION.md) | May 6–11 | Plan written before any code; partly pruned |
| 04 | [Context management](process/04_CONTEXT_MANAGEMENT.md) | May 11 | Design proposal, later implemented |
| 05 | [Tool manifest v1](process/05_tools_managementv1.md) | May 18 | Superseded by MCP.md |
| 06 | [Judge system guide](process/06_judge_system_guide.md) | May 19 | Superseded: first judge architecture |
| 07 | [Evaluation design questions](process/07_evaluation_design_open_questions.md) | May 21 | Trade-off analysis; banner records the outcome |
| 08 | [Group fidelity refactor](process/08_GROUP_FIDELITY_REFACTOR.md) | Jun 3 | Change record, part of the final system |
| 09 | [MCP session log](process/09_report_mcp.md) | Jun 3 | In Italian, with an English summary |

## Other material

- **[sprints/](sprints/)**: per-person notes for each sprint (what I did, what blocked me, what's next) and the team progress reports.
- **[presentations/](presentations/)**: the decks shown during the course, in order. Open the `.html` files in a browser.
  1. [Week 2: project overview](presentations/01_week2_presentation.html) (May 14)
  2. [Evaluation methodology](presentations/02_eval_presentation.html) (May 21)
  3. [Week 3: pipeline overview](presentations/03_week3_presentation.html) (May 27)
  4. [Final presentation (PDF)](presentations/04_final_presentation.pdf)
- **[report/](report/)**: the full technical report ([PDF](report/report.pdf), [LaTeX source](report/report.tex)).
