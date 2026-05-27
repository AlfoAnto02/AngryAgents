# Progress Report
**Week of:** May 19–27, 2026

---

## 1. Problem Statement

We are building a chat application in which users interact with AI persona-agents that faithfully represent real-world or fictional characters. Conversations are evaluated by 20 judge-agents across four fidelity dimensions: persona identification, individual fidelity, group fidelity, and behavioral fidelity. The judges operate in two phases: independent evaluation (Phase 1) followed by structured deliberation among high-variance cases (Phase 2).

### Open Challenges Addressed This Week

- **Evaluation scalability wall:** running 20 judges against a full transcript with 100+ candidate personas exceeded any reasonable time and cost budget. Solved via RAG pre-filtering that reduces candidates from 100+ to 20, cutting LLM calls from ~2 000 to ~80 (−97%) and latency from 33 min to ~30 sec.
- **Persona assignment ambiguity:** the previous evaluation loop could assign the same persona to multiple authors. Solved by adding the Hungarian algorithm to `metrics_persona_id.py`, enforcing one-to-one author ↔ persona assignment.
- **Two separate chat modes:** DM (one user, one agent) and group chat (multi-agent) shared no implementation, blocking UI wiring. Solved by implementing a dedicated `dm_chat` module and revising group chat architecture so both modes share the same persona engine.
- **Extraction depth:** source transcripts alone under-specify some persona traits (catchphrases, syntactic tics). Solved by a two-phase extraction pipeline where Phase 1 grounds every field in the transcript and Phase 2 calls a stronger model (gpt-4o) for pure model-knowledge fields.
- **UI disconnected from live backend:** all screens were wired to static mock data. Solved by replacing `data.js` with live API calls across all screens and wiring the eval metrics dashboard.

---

## 2. Focus, Scope & Key Contributions

### Workstream Ownership

| Workstream | Owner(s) | In Scope | Out of Scope |
|------------|----------|----------|--------------|
| RAG evaluation pipeline | Alfonso Antognozzi | ChromaDB index, field-weighted retrieval, RAG-as-tool judge pass, Hungarian assignment, token/cost reporting | Model fine-tuning |
| Chat infrastructure (DM + group) | Davide Cabitza | DM chat module, group chat architecture revision, Jinja2 persona/judge template overhaul, chat stop mechanism | Production scaling |
| UI wiring + eval dashboard | Kevin Shimaj, Alfonso Antognozzi | Live API integration (all screens), eval metrics dashboard, MCP layer | Mobile app |
| Persona extraction pipeline | Gabriele Fronzoni | Two-phase extraction (transcript + model knowledge), Twitter scraping, persona batch rebuilds | Model fine-tuning |
| Evaluation metrics design | Kevin Shimaj, Marco Massa | EVAL.md redefinition, eval presentation, open questions document | Statistical inference implementation |
| Week 3 presentation | Marco Massa, Gabriele Fronzoni | `week3presentation.html` full build | — |

### Key Contributions

- **RAG system** (`src/rag/`): ChromaDB index built from per-field profile chunks with configurable field weights; `retriever.py` queries top-k chunks and deduplicates by persona; `judge_with_tools.py` lets judges query ChromaDB as a tool call for deeper semantic retrieval. Full explanation in `RAG_EXPLANATION.md` (697 lines).
- **Hungarian algorithm for persona identification:** `metrics_persona_id.py` now uses `scipy.optimize.linear_sum_assignment` to enforce bijective author ↔ persona mapping, eliminating duplicate assignments that inflated accuracy metrics.
- **DM chat module** (`src/dm_chat/`): `factory.py` + `session.py` implement the single-user / single-agent conversation path. Unified with group chat behind the same persona and template system.
- **Two-phase extraction pipeline:** `extract_profile.py` now calls gpt-4o-mini for transcript-grounded fields (Phase 1) and gpt-4o for pure model-knowledge fields (`favored_words`, `structural_patterns`, `do_not_say`) without sending the transcript (Phase 2). Each Phase 2 item must fail the "similar figure" test. Total build cost for 80 personas: **$0.57** (1,056,763 input + 136,657 output tokens).
- **UI fully wired to live API:** `api.js` + `agents-store.jsx` added; all screens (`app.jsx`, `screens-admin.jsx`, `screens-chat.jsx`, etc.) replaced static mock data with live `GET/POST` calls.
- **Eval metrics dashboard** (`screens-admin.jsx`): renders `metrics_report.json` output — persona identification accuracy, confusion matrix, fidelity scores — wired via `/api/eval/metrics` route.
- **MCP layer** (`src/mcp/`): MCP server and client wrappers; `tools/read.py` and `tools/write.py` expose DB read/write operations as MCP tools. Setup documented in `MCP_SETUP.md`.
- **Token usage reporter:** evaluation scripts now print a full token report (input, output, total, estimated cost) after each judge run.

---

## 3. Summary Status

| Dimension | Status | Notes |
|-----------|--------|-------|
| Overall | 🟢 On track | RAG live, DM chat done, UI wired, extraction pipeline two-phase |
| Data / Infrastructure | 🟢 Ahead | RAG index built, MCP layer up, UI fully wired to API |
| Modeling / Core work | 🟢 Ahead | DM + group chat working end-to-end; two-phase persona extraction in prod |
| Evaluation | 🟡 On track | Pipeline running with 20 judges + RAG; Hungarian assignment fixed; fidelity metrics wired to UI |
| Writeup / Communication | 🟢 Ahead | Week 3 presentation done; RAG_EXPLANATION.md; group_chat_spiegazione.md; EVAL.md revised |

---

## 4. Progress This Week

### Alfonso Antognozzi — RAG system, evaluation pipeline, UI

- **Done:**
  - **RAG system from scratch:** designed and implemented the full `src/rag/` package:
    - `builder.py`: splits each persona profile into typed semantic chunks (`style`, `voice`, `worldview`, `behavior`, `quote`) with configurable field weights.
    - `indexer.py`: embeds chunks with `text-embedding-3-small` and stores them in ChromaDB under `data/chroma/`.
    - `retriever.py`: queries ChromaDB per author digest, deduplicates by persona, returns top-20 candidates for judge shortlisting.
    - `_chroma.py`: singleton ChromaDB client.
    - `build_index.py`: one-shot index builder script.
    - `evaluation_test_20_judges.py`: runs all 20 judges against the RAG-shortlisted candidate set.
    - `judge_with_tools.py`: judge variant that can call ChromaDB as a tool for deeper semantic retrieval on borderline cases (+~10% accuracy, ~2× token cost).
    - `RAG_EXPLANATION.md`: 697-line technical reference covering chunking strategy, embedding choice, retrieval flow, judge integration, and latency/cost breakdown.
  - **Field-weighted retrieval:** `builder.py` and `retriever.py` updated so each chunk type contributes a configurable weight to the final candidate score, prioritising `quote` and `style` chunks over generic `worldview`.
  - **Refactored evaluation output:** evaluation runners now produce `report_persona_id_20j_1.json` and `report_fidelity_20j_1.json` as structured JSON artefacts aligned with the RAG system's output schema.
  - **Hungarian algorithm:** integrated `scipy.optimize.linear_sum_assignment` into `metrics_persona_id.py` — author ↔ persona assignment is now guaranteed bijective, eliminating the double-assignment bug that inflated accuracy.
  - **Parallel judge calls + cost reduction:** judge API calls now run in parallel; removed inner persona-level loops; 20 judges implemented correctly with proper concurrency.
  - **API timeout to reduce bottlenecking:** added configurable timeout to LLM API calls in `evaluation_test_20_judges.py` and `judge_with_tools.py`; routes in `ui_routes.py` updated to surface timeout errors cleanly.
  - **Token usage report:** evaluation scripts print total input tokens, output tokens, total tokens, and estimated cost after each run.
  - **UI Admin dashboard + judging phase wired:** admin UI now shows judge evaluation results; `/api/eval/` routes added in `ui_routes.py`; fixed routing conflicts from earlier UI implementations.
  - **RAG index rebuilt for new personas:** re-indexed ChromaDB after each batch of new persona profiles landed.
- **In progress:** Tuning field weights for optimal retrieval recall; deliberation (Phase 2) implementation.
- **Blockers:** Retrieval recall degrades on personas with sparse source material (< 5 k tokens of transcript); no mitigation yet.

---

### Davide Cabitza — DM chat, group chat revision, persona templates

- **Done:**
  - **DM chat implementation:** new `src/dm_chat/` package:
    - `factory.py`: builds a `DmChatSession` from a `PersonaAgent` and DB connection; injects the persona profile and the DM-specific Jinja2 template.
    - `session.py`: drives the single-user / single-agent turn loop; handles message persistence with anonymous author token.
    - `logging_setup.py` added to centralise structured logging.
  - **DM chat Jinja2 template + group chat template revision:** new `group_persona_chat.j2` template (35 lines); `persona_chat.j2` revised to enforce same-language replies and direct user engagement for DM mode.
  - **Group chat architecture revision:** `scheduler.py` and `session.py` in `src/group_chat/` refactored — turn selection logic decoupled from session state; burst-mode handling improved.
  - **DB and API revision after chat changes:** `ui_routes.py` expanded (+141 lines) to expose DM and group chat start/send/stop endpoints; `persona_agent.py` extended with new fields; `base.py` model updated; `group_chat_repository.py` and `group_chat_service.py` aligned.
  - **Chat stop mechanism + fixes:** implemented graceful chat stop; fixed agent context loading; resolved group chat state inconsistencies.
  - **Major template and agent overhaul:** `persona_agent.py` rewritten (+159/−41 lines) — profile injection, language detection, and re-grounding logic all moved into the agent class. Both `persona_chat.j2` (DM) and `group_persona_chat.j2` (group) templates heavily revised for cleaner persona injection and explicit writing constraints.
  - **Judge template improvements:** `persona_id_ideology_batch.j2`, `persona_id_rag_batch.j2`, and `persona_id_style_batch.j2` updated with clearer rubric language and fix for missing newline.
  - **Documentation:** `group_chat_spiegazione.md` restructured and expanded (+527 lines net change); `PROGRESS_CABITZA.md` written as personal progress log.
- **In progress:** Re-grounding mechanism every 20 turns; `context_window.py` strategy tuning for long conversations.
- **Blockers:** DM session re-grounding not yet implemented; `behavioral` judge stub not yet promoted to full implementation.

---

### Gabriele Fronzoni — Persona extraction pipeline, scraping, UI persona display

- **Done:**
  - **Two-phase extraction pipeline:** `extract_profile.py` rewritten (+210 lines): Phase 1 calls `gpt-4o-mini` with the full transcript to ground all behavioral fields; Phase 2 calls `gpt-4o` with **no transcript** to extract `favored_words`, `structural_patterns`, and `do_not_say` from pure model knowledge. Each Phase 2 entry must fail the "similar figure" discriminability test. Profiles merged after both calls. Total build cost for 80 personas: **$0.57** (1.19M tokens).
  - **Twitter scraping implementation:** new scraper in `src/agents/personas/` that collects tweet threads for real-world personas and converts them to extraction-ready text.
  - **YouTube scraping improvements:** algorithm updated to handle failed transcript fetches gracefully without crashing the batch pipeline.
  - **PDF scraping batch processing:** PDF scraper updated to process all files from a folder in a single call rather than one file at a time.
  - **Profile extraction prompt refinement:** extraction prompt revised to produce more discriminating `annotated_quotes` and tighter `do_not_say` entries.
  - **Persona batch rebuilds (multiple commits):** rebuilt all existing personas through the new two-phase pipeline; deleted stale profiles that failed quality checks. New personas added this week include Federico Frusciante.
  - **Fixed profile injection into agent prompts:** corrected how persona profiles are serialised and passed to the LLM at chat time — fields were being truncated for long profiles.
  - **UI persona detail display:** persona library screen now shows richer profile details (core style, humor, worldview snippets) rather than just name and type.
  - **Week 3 presentation first draft and revisions:** wrote the initial HTML presentation covering persona extraction, RAG, chat modes, group chat, judge pipeline.
- **In progress:** Deciding optimal token budget for Phase 2 calls; evaluating whether `do_not_say` entries need a second discriminability pass.
- **Blockers:** Some Twitter accounts return no usable data due to rate limits; those personas fall back to YouTube-only extraction.

---

### Kevin Shimaj — UI wiring, MCP layer, evaluation metrics

- **Done:**
  - **MCP layer:** new `src/mcp/` package implementing Model Context Protocol:
    - `mcp_server.py` and `client.py`: server/client wrappers.
    - `tools/read.py`: MCP tool exposing DB read operations (chat history, persona profiles, evaluation results).
    - `tools/write.py`: MCP tool exposing DB write operations (post message, record evaluation).
    - `run_mcp.py`: entry-point to launch the MCP server.
    - `MCP_SETUP.md`: setup guide (100 + 141 lines across two commits).
  - **Full UI wiring:** replaced all static mock data with live API calls:
    - `api.js` (80 lines): fetch helpers for all backend endpoints.
    - `agents-store.jsx` (59 lines): React store for persona list and selection state.
    - All screens updated: `app.jsx`, `screens-admin.jsx`, `screens-chat.jsx`, `screens-home.jsx`, `screens-library.jsx`, `screens-newchat.jsx`.
  - **Eval metrics dashboard wired:** `screens-admin.jsx` now fetches `metrics_report.json` from `/api/eval/metrics` and renders persona identification accuracy, confusion matrix, and per-persona fidelity scores. Route added to `ui_routes.py`.
  - **Evaluation metrics redefinition:** `EVAL.md` rewritten with 60 lines of new content — cleaner metric definitions, removed metrics with unclear statistical grounding, aligned with what the current pipeline actually produces.
  - **`metrics_persona_id.py` and `metrics_fidelity.py` revision:** persona identification script restructured (+62/−26 lines) to align with Hungarian-assignment output format; fidelity metrics extended to handle per-field breakdowns from the RAG report.
  - **Removed unused evaluation metric:** deleted a group fidelity metric that was producing misleading results without a valid reference baseline.
  - **UI bug fix:** resolved a rendering issue in the chat screen caused by missing null-check on the message author field.
  - **Removed unused files:** cleaned up stale scripts from the `eval` branch before merging.
  - **Eval presentation:** wrote and refined the evaluation methodology presentation (EVAL.md companion).
- **In progress:** Aligning MCP tool schemas with the current DB API; wiring Phase 2 deliberation output to the admin dashboard.
- **Blockers:** MCP read/write tools currently bypass the FastAPI auth layer — needs `Authorization` header injection before production use.

---

### Marco Massa — Evaluation design, presentation, system prompt experiments

- **Done:**
  - **Evaluation design open questions document:** `evaluation_design_open_questions.md` (185 lines) — comprehensive structured document covering 3 major open design decisions:
    - *Candidate set size:* closed 8-tag set vs. expanded K-tag set with decoys vs. full agent database.
    - *Fidelity measurement protocol:* sequential same-judge pool (guess first, score after reveal) vs. parallel dedicated pools.
    - *Identification response format:* hard point guess per tag vs. fidelity-scored ranking with argmax.
    - Each question includes rationale, trade-offs, and a recommended approach.
  - **Eval presentation:** `eval_presentation.html` built as a companion slide deck for the evaluation methodology; +265 lines.
  - **Week 3 presentation:** significant expansion of `week3presentation.html` (+388 lines net): restructured slides covering RAG, persona extraction with cost data, chat modes, group chat architecture, and judge pipeline with tool comparison table.
  - **System prompt experiments:** added 2 lines to both `group_persona_chat.j2` and `persona_chat.j2` templates — minor but measurable effect on response register consistency, documented in commit message.
  - **Seed personas updated:** `data/personas/seed/` profiles revised to match new two-phase extraction format.
- **In progress:** Finalising the evaluation design protocol document with a recommended decision on candidate set size.
- **Blockers:** Evaluation design decisions (candidate set, protocol, response format) still pending team alignment — blocks finalising the judge pipeline configuration.
