# Progress Report
**Week of:** May 8–22, 2026

---

## 1. Problem Statement

We are building a chat application in which users interact with AI persona-agents that faithfully represent real-world or fictional characters (politicians, podcasters, movie characters). Conversations are evaluated by 20 judge-agents across four fidelity dimensions: persona identification, individual fidelity, group fidelity, and behavioral fidelity. The judges operate in two phases: independent evaluation (Phase 1) followed by structured deliberation among high-variance cases (Phase 2). An external omniscient agent evaluates judge quality without influencing the process.

### What Makes It Hard

- **Sparse source material for fictional personas:** a movie character may have only a few dozen lines to extract a full personality profile from — far below the 10k–50k token threshold for reliable instantiation.
- **No ground truth for fidelity:** persona identification has a measurable baseline (12.5% random over 8 agents); individual and group fidelity have no direct ground truth, requiring indirect proxies (LIWC, cosine similarity, Gini on turn distribution).
- **Author anonymity as an invariant:** judges must never learn which agent sent which message. The anonymization must hold end-to-end across the DB schema, service layer, and API — not just at inference time.
- **Character drift in long conversations:** after ~30–40 turns, agents converge toward a generic LLM voice. Requires sliding window + compression + reflection + perturbation mechanisms (documented in CONTEXT_MANAGEMENT.md).
- **Group dynamic convergence:** 8 agents in a group chat tend toward excessive agreeableness (Park et al., 2023). Per-agent perturbation signals are needed to maintain distinct positions.
- **Blind evaluation protocol:** Jiang et al. (2024) show that informing raters of AI authorship significantly degrades personality attribution accuracy — all judge evaluation must be run blind.
- **LLM output parsing for structured scores:** judge prompts ask Ollama to score each agent 1–5 per persona, but the model returns free text — `_parse_agent_scores` must reliably extract structured data from unformatted LLM responses, which is fragile by nature.
- **Evaluation pipeline scalability:** running `persona_identification` on a 40-message transcript across 7 personas already exceeds 120 s locally with mistral. With 20 judges and a full-length group chat this becomes a hard latency wall — prompt chunking or a lighter model is required before the pipeline can run end-to-end.
- **Aggregate scoring metric undefined:** each judge produces per-agent, per-persona scores (1–5). Collapsing these into a single meaningful `Score` for `Judge_evaluation` has no clear formula yet — median, weighted average, and argmax confidence all have different statistical implications for Phase 2 deliberation.
- **Behavioral fidelity lacks operational definition:** unlike `style` (lexical patterns) or `ideology` (stance detection), "behavioral fidelity" — whether an agent behaves like a human in chat — has no established evaluation protocol in the literature. This is the least-defined of the four evaluation dimensions.

---

## 2. Focus, Scope & Key Contributions

### Workstream Ownership

| Workstream | Owner(s) | In Scope | Out of Scope |
|------------|----------|----------|--------------|
| Database layer + REST API | Alfonso Antognozzi, Marco Massa (co-author) | SQLite schema, CRUD repositories, service layer, FastAPI endpoints, Pydantic schemas, Swagger UI, test suite | Production deployment, cloud DB, authentication beyond `AUTH_DISABLED` dev header |
| Persona scraping & extraction | Kevin Shimaj, Gabriele Fronzoni | YouTube/podcast transcript scraping, movie script + PDF scraping, LLM-based persona profile extraction | Model fine-tuning, web crawling beyond identified sources |
| Judge implementation | Davide Cabitza | Abstract `Judge` base class, 3 role specializations implemented (`style`, `ideology`, `general`), `persona_identification` running against real transcript, Phase 1 independent evaluation | `behavioral` judge (stub), Phase 2 deliberation, external omniscient agent |
| Chat simulation | Kevin Shimaj | Ollama-based simulation loop, persona integration, author identity hashing | RAG retrieval, context management mechanisms, UI polish |
| Context management design | Kevin Shimaj | Architecture spec: structured profile + RAG + sliding window + reflection + perturbation | Full implementation (design phase only this week) |
| SOTA & problem definition | Davide Cabitza, Gabriele Fronzoni | Literature review (5 papers), problem statement iterations, evaluation metrics derivation | — |

### Key Contributions

- **End-to-end author anonymization pipeline:** client sends `agent_id` → service does DB lookup → SHA-256 HMAC computed server-side → stored as 64-char opaque hex. Name/surname never leave the server. Enforced at schema level (no FK from `Chat_messages` → `Agents`).
- **170-test suite** covering all 7 repositories and 5 services with in-memory SQLite fixtures. Includes boundary tests for soft-delete, hard-delete, composite PKs, and the 20-evaluation cap per chat.
- **First working chat simulation** with Ollama using extracted real-world personas, with persona identity hashed in the simulation output.
- **Judge class hierarchy** with 3 concrete specializations (`StyleJudge`, `IdeologyJudge`, `GeneralJudge`) running `persona_identification` against a real 40-message transcript with 7 personas, merged to main.
- **PDF-based fictional persona scraping** producing the first batch of extracted movie personas.

---

## 3. Summary Status

| Dimension | Status | Notes |
|-----------|--------|-------|
| Overall | 🟡 On track | Core infrastructure complete; pipeline assembly is next |
| Data / Infrastructure | 🟢 Ahead | DB schema, full CRUD API, 170 tests, Swagger — all merged to main |
| Modeling / Core work | 🟡 On track | Chat simulation MVP working with Ollama; judge structure defined but not yet wired to simulation |
| Evaluation | 🟡 On track | Judge types implemented; Phase 1 pipeline not yet assembled end-to-end |
| Writeup / Communication | 🟢 Ahead | SOTA reviewed (5 papers), problem statement finalized, context management architecture documented |

---

## 4. Progress This Week

### Alfonso Antognozzi — Database layer, REST API, testing

- **Done:**
  - **Entity models:** Python dataclasses + DDL for all 7 entities: `Topic`, `Agent`, `AgentContext`, `GroupChat`, `ChatMessage`, `Judge`, `JudgeEvaluation`. All share the same schema contract (`id`, `slug`, `created_at`, `updated_at`, `deleted_at`, `details`). Soft-delete enforced via `deleted_at IS NULL` in all queries; `updated_at` maintained by SQL trigger; `slug` unique only among non-deleted rows.
  - **Repositories:** raw-SQL CRUD for every entity — `create`, `get`, `get_by_slug`, `update`, `delete(hard=False)`, `query(filters, limit, offset)`. Plus `rels.py` for the shared relationship table (agent↔topic, judge↔chat associations). No ORM.
  - **Service layer:** business logic sitting on top of repositories — `ChatMessageService` (server-side author token: `agent_id` → DB name lookup → SHA-256 HMAC hexdigest, 64 chars, fully opaque; name never passed by client); `JudgeEvaluationService` (judge role validation, cap of 20 evaluations per chat enforced at write time).
  - **FastAPI + Swagger:** `app.py` with `lifespan` hook calling `init_db()` on startup. `config.py` loading env vars via `python-dotenv`. `deps.py` with per-request DB connection and cached settings via `Depends()`. 7 route files with full CRUD, query param constraints (`ge=`/`le=`), soft/hard delete flag, and composite-PK routes for `JudgeEvaluation`. `schemas.py` with 7 Pydantic `Out` models (`Field(description=...)` on every field). `response_model=` on all endpoints. Swagger UI browsable at `/docs`.
  - **Test suite:** `conftest.py` with shared in-memory SQLite fixtures. 170 tests across 13 files covering all repository methods and service edge cases — HMAC determinism and opacity, different-agent/different-secret token divergence, role validation rejection, 20-evaluation cap enforcement, soft-delete visibility, hard-delete removal, composite PK operations.
  - AI agent tools manifest (`tools_managementv1.md`): 12 tools across 2 tiers with confirmation rules and workflow sequences.
- **In progress:** Nothing — all work merged to main
- **Blockers:** None

### Kevin Shimaj — Scraping, chat simulation, UI, context management

- **Done:**
  - **Experimentation pipeline (`EXPERIMENTATION.MD`):** full methodology spec covering every stage of the system. Key design decisions documented:
    - *Optimal conversation length:* too short (< 20 turns) misses deep behavioral patterns; too long (> 150 turns) causes persona drift as conversational inertia overtakes the profile — target range to be determined empirically.
    - *Judge specialization and phases:* 20 judges divided by focus (`style`, `ideology`, `general`). Phase 1 fully independent; Phase 2 structured deliberation only on high-variance cases (3–5 rounds, judge confidence tracked per round alongside ratings).
    - *Statistical framework:* persona identification — binomial exact test + 95% CI against 12.5% random baseline + 8×8 confusion matrix with chi-square; individual fidelity — median + IQR over 20 Likert ratings per persona; group fidelity — Gini coefficient on turn distribution and Spearman correlation on pairwise agent sentiment-distance matrices; Phase 2 convergence — variance reduction across rounds with F-tests, convergence rate with binomial CI; bootstrap resampling for all small-sample estimates.
    - *Failure modes:* 8 identified risks with mitigations — judge unfamiliarity, source-material overfitting, ethical risks, time/budget constraints, low statistical power, poor persona extraction, information leakage.
  - First working chat simulation loop using Ollama, integrated with extracted real-world personas. `persona_id` and `persona_name` hashed in output.
  - Context management architecture (`CONTEXT_MANAGEMENT.MD`): structured profile + RAG + sliding window + compression + reflection + perturbation, with token budget (~2,550 tok/turn vs 30,000 raw).
  - Detailed documentation of YouTube scraping script internals.
- **In progress:** Evaluation pipeline (`eval` branch active)
- **Blockers:** Simulation currently uses Ollama locally — needs to be aligned with the REST API's author-token scheme before end-to-end evaluation can run

### Gabriele Fronzoni — Fictional persona scraping, problem definition

- **Done:**
  - Implemented movie personas scraping: working both on IMSDB database and PDF upload.
  - First batch of movie personas extracted and committed
  - Fictional scripts loading updated to handle new format
  - `.gitignore` updated, merge conflicts resolved
- Improved and ultimated problem statement definition
- **In progress:** Persona extraction refinement with entire script or only character lines.
- **Blockers:** Different scripts format makes difficult to implement general method, without need to manually refine extraction.

### Davide Cabitza — agents, judge implementation

- **Done:**
  - **Judge architecture:** `base_judge.py` defines 4 abstract evaluation methods (`persona_identification`, `individual_fidelity`, `group_fidelity`, `behavioural_fidelity`) plus three result dataclasses — `AgentScore` (DIGEST + score 1–5), `PersonaMatch` (per-agent scores + argmax prediction), `PersonaIdentificationResult` (full list of matches).
  - **3 concrete judges implemented:** `StyleJudge` (vocabulary, tone, rhetorical habits), `IdeologyJudge` (political views, moral stances), `GeneralJudge` (all traits combined). All backed by the same loop: for each persona profile, prompt Ollama (mistral) to score every agent 1–5, take argmax as predicted identity.
  - **Shared infrastructure (`agent_config.py`):** centralises Ollama URL/model config, message and profile formatters, LLM output parser, and the `run_persona_identification` loop. Each judge file is now just a prompt template constant.
  - **End-to-end evaluation test (`evaluation_test.py`):** runs all 3 judges against a real 40-message transcript (7 agents: `cicciogamer89`, `INDY`, `JACK`, `LUKE`, `RIGGAN`, `VADER`, `YODA`), prints per-judge score tables, and writes auto-incremented `Judge_evaluation` JSON files to `data/judge_eval/` following the DB schema.
  - SOTA review finalized (5 papers). `judge` branch merged to main.
- **In progress:** Designing the aggregate `Score` metric; `individual_fidelity`, `group_fidelity`, `behavioural_fidelity` remain empty stubs.
- **Blockers:**
  - Inference timeout: 40 messages × 7 personas exceeds 120 s with mistral locally — needs prompt chunking or a lighter model before the pipeline can scale

### Marco Massa — Repository structure, DB documentation

- **Done:**
  - **Project structure:** refactored the repository folder layout into the current `src/`, `tests/`, `docs/` hierarchy that all subsequent work builds on. Created the `DB_creation_v1` branch as the dedicated workspace for the database layer.
  - **DB documentation v1:** first written specification of the schema — all table definitions, field types, constraints, and relationship cardinalities documented in `DB_v1.md` as the reference used during model and repository implementation.
  - **DB documentation v2 (`DB_v2.md`):** updated schema reference reflecting the changes introduced during implementation (slug uniqueness rule, soft-delete pattern, `details` JSON field, `rels` table for relationships).
  - **Co-authored DB layer and API work (05-18):** active collaborator on the FastAPI application, Swagger integration, and tools manifest — the three major deliverables of the DB workstream this week.
  - **Co-authored statistical framework documentation (05-06):** contributed to the metrics and evaluation framework section of the pipeline overview documentation.
- **In progress:** Nothing explicitly tracked this week
- **Blockers:** None
