<p align="center">
  <img src="ui/logo.png" alt="Angry Agents logo" width="140">
</p>

<h1 align="center">Angry Agents</h1>

<p align="center">
  <b>Talk with anyone.</b><br>
  A multi-agent platform for simulating real and fictional personas and evaluating how faithful they really are.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white">
  <img src="https://img.shields.io/badge/FastAPI-backend-009688?logo=fastapi&logoColor=white">
  <img src="https://img.shields.io/badge/React-UI-61DAFB?logo=react&logoColor=black">
  <img src="https://img.shields.io/badge/OpenAI-gpt--4o--mini-412991?logo=openai&logoColor=white">
  <img src="https://img.shields.io/badge/ChromaDB-RAG-FF6F00">
  <img src="https://img.shields.io/badge/MCP-enabled-black">
</p>

---

## The idea

Angry Agents is a web application where users chat with AI agents that impersonate real people (politicians, tech founders, athletes, comedians) or fictional characters (from movies and TV series). You can talk to a single persona in a private DM, or pick a topic, drop up to eight personas into a group chat and watch them argue on their own, stepping in whenever you want.

Behind the chat sits the real point of the project: a **blind evaluation pipeline of 20 AI judges** that tries to recognise who is who in a conversation, without knowing which agent wrote which message. The project is built around one research question:

> *Can an LLM, conditioned on a structured persona profile extracted from source material, simulate a real or fictional character in a multi-turn conversation so faithfully that independent judge-agents can correctly identify it?*

The guiding principle was not just to solve a case study, but to deliver a **feasible, cost-driven system**: every design choice was weighed against latency and token cost as well as quality.

---

## How it works

```
 Raw sources                Persona profiles            Conversations              Evaluation
 ─────────────              ────────────────            ─────────────              ──────────
 Movie & TV scripts   ──►   Two-pass LLM         ──►    DM chats            ──►    20 blind judges
 YouTube / podcasts         extraction into             Autonomous group           RAG pre-filtering
 Twitter/X threads          structured JSON             chats (2–8 agents)         Statistical metrics
```

### 1. Persona extraction

Personas are built from real source material, aiming at 10k–50k tokens per character: movie and TV scripts (IMSDB pages and PDFs) for fictional characters, and YouTube transcripts, podcasts and Twitter/X threads for real people.

Extraction happens in **two LLM passes**. The first, with the cheaper `gpt-4o-mini`, reads the full transcript and grounds behavioural traits in observed speech: style, worldview, emotional tells, escalation patterns, relationships and annotated quotes. The second, with `gpt-4o` and no transcript, adds what the model already knows about the character, such as favoured words, structural speech patterns and lines the persona would never say. Each entry must pass a "similar figure" test: if a confusable persona could have said the same thing, it is discarded.

The result is a rich JSON profile with fields like `core_style`, `humor`, `speech_signature`, `vocabulary_fingerprint`, `worldview`, `self_image_vs_reality`, `emotional_tells`, `situational_behavior`, `knowledge_domains`, `social_positioning` and `do_not_say`. The platform ships with **101 persona profiles**; extracting 80 of them cost just **$0.57** (1.19M tokens).

### 2. Persona agents and chat simulation

Each `PersonaAgent` derives its conversational behaviour from its own profile: a dominant character gets a higher speaking weight and shorter cooldown, a reserved one naturally yields the floor. In group chats a `TurnScheduler` (weighted-random with cooldown penalties, or round-robin) decides who speaks next, and a `ContextWindow` keeps the history manageable, so the agents can converse fully autonomously.

Long conversations suffer from well-known problems: agents drift toward a generic "LLM voice" after 30–40 turns, and groups converge toward excessive agreement. Angry Agents counters this with a layered context stack:

| Mechanism | What it does |
|---|---|
| Structured profile | Persona profile injected on every call (cached) |
| RAG grounding | Relevant profile chunks retrieved per turn |
| Sliding window + compression | Last 5 turns verbatim, older history summarised every 10 turns |
| Reflection | Every 15–20 turns the agent re-anchors itself against its profile |
| Perturbation | Private nudge to react genuinely when the group drifts toward consensus |
| Drift detection | Cosine similarity between agents' messages triggers early correction |

This brings the prompt down to roughly **2,550 tokens per turn instead of ~30,000** for a raw transcript, about **92% savings**.

### 3. Blind evaluation with 20 judges

Message authors are stored as an **HMAC-SHA256 digest**, with no foreign key back to the agent table. Anonymity is enforced at the schema level, so judges can tell sources apart but can never see who is behind them.

The judge panel has **20 judges: 5 instances for each of 4 lenses**:

| Role | Focus |
|---|---|
| `style` | Vocabulary, sentence structure, rhetorical habits |
| `ideology` | Political views, values, moral stances |
| `behavioral` | Human-likeness, realistic behaviour |
| `general` | All traits combined |

Each judge makes three calls. First, **persona identification**: it assigns every anonymous author to exactly one persona, with the Hungarian algorithm enforcing a one-to-one mapping when votes are aggregated. Then, once the true mapping is revealed, it rates **individual fidelity** (1–5) through its own lens. Finally it rates **group fidelity** (1–5), reading the chat in chronological order to judge turn-taking and group dynamics.

#### Making evaluation scale: RAG pre-filtering

The first version asked every judge to consider every persona in the database, which with 100+ personas became unusable. The fix was a retrieval layer: profiles are split into 13 semantic chunk types, converted to natural language, embedded with `text-embedding-3-small` and stored in ChromaDB. Each judge queries the index using the last messages of every author, with role-specific boosts (style, vocabulary, worldview) and MMR re-ranking (λ = 0.7) so that no single persona dominates the shortlist. The candidate pool scales dynamically with the number of participants and always includes semantic distractors.

The impact: **LLM calls dropped from ~2,000 to ~80 per run (−97%)** and **latency from 33 minutes to about 30 seconds**.

### 4. Statistical metrics

| Dimension | Metrics |
|---|---|
| Persona identification | Accuracy vs. 12.5% random baseline, Clopper-Pearson exact 95% CI, one-sided binomial test, Cohen's κ, confusion matrix, per-persona precision/recall/F1 |
| Individual fidelity | Median, mean and IQR per persona, bootstrap 95% CI (10,000 resamples), Mean Absolute Deviation between judge types |
| Group fidelity | Gini coefficient on turn distribution, checked against a realistic reference range of 0.28–0.42 |
| Batch aggregation | Bootstrap CI for fewer than 20 chats, CLT normal approximation beyond |

All metrics are visible live in the admin **Chat Analytics** dashboard, together with a per-persona performance panel and token-cost tracking.

---

## Results

The full pipeline was run on **21 evaluated chats** using `gpt-4o-mini`:

| Metric | Result | 95% CI |
|---|---|---|
| Persona identification accuracy | **51.1%** (≈ 4× the 12.5% random baseline) | 42.3% – 60.0% |
| Cohen's κ (pooled) | **0.66** (good agreement) | — |
| Gini coefficient on turns | **0.297**, inside the realistic range | 0.26 – 0.34 |
| Individual fidelity (median, 1–5) | **4.83** | 4.74 – 4.93 |

### What we learned

**Who is in the room matters as much as the topic.** Two chats on the same "politics" topic gave very different outcomes: a mixed cast of singers, gamers and cartoon characters reached only 23.8% accuracy, while a panel of real politicians and public figures (Obama, Sanders, Trump, Meloni and others) reached 67.9%. Likewise, on an open "free will" chat, a cast from The Boys was identified with 91.4% accuracy, while a mix of sitcom and Stranger Things characters stopped at 14.4%.

**Similar personas are hard to tell apart.** In a chat between Charles Leclerc and Lewis Hamilton, two drivers with overlapping vocabulary and worldview, the judges systematically swapped them.

**Weak portrayals are harder to recognise.** When an agent's individual fidelity was low, identification accuracy dropped with it, confirming that the two dimensions are linked.

**Model choice is a cost/quality trade-off.** Re-running three chats with GPT-5 instead of `gpt-4o-mini` raised accuracy by about 63 points on average (in one case from 14.4% to 94.4%), but at roughly **17× the cost**.

---

## Tech stack

| Layer | Technology |
|---|---|
| Backend API | Python 3.12, FastAPI, Uvicorn |
| Database | SQLite (raw SQL, WAL mode, soft-delete, 10 tables) |
| Validation | Pydantic v2 |
| Auth | JWT (15-min access tokens), httpOnly refresh tokens, PBKDF2-SHA256 hashing |
| LLM | OpenAI (`gpt-4o-mini`, `gpt-4o`) or local Ollama (Mistral) |
| RAG | ChromaDB, `text-embedding-3-small`, MMR re-ranking |
| Prompting | Jinja2 templates for personas and judges |
| Statistics | NumPy, SciPy (Hungarian algorithm, binomial tests, bootstrap) |
| Scraping | BeautifulSoup, pdfplumber, yt-dlp, youtube-transcript-api |
| Frontend | React/JSX without a bundler, light and dark themes |
| AI integration | Model Context Protocol server (FastMCP) |
| Testing | pytest, ~290 tests on repositories and services |

### MCP integration

The platform exposes a **Model Context Protocol server**, so an assistant like Claude Code can drive the app directly: listing agents, reading chats, creating conversations or launching an evaluation. It offers 14 read-only tools and 5 write actions, each split into a *preview* and a *confirm* step, so nothing changes without explicit user approval. It was used to generate DM chats automatically from the terminal, posting over 60 messages without touching the UI.

---

## Getting started

```bash
# 1. Install
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Configure: copy .env.example to .env and set at least
#    OPENAI_API_KEY, ANGRY_AUTHOR_SECRET, JWT_SECRET_KEY, LLM_BACKEND=openai

# 3. Start the API (http://localhost:8000, docs at /docs)
uvicorn angry_agents.src.API.app:app --port 8000 --reload

# 4. Load the demo database with all personas and sample chats
#    (stop the API first, then restart it afterwards)
python restore_db.py

# 5. Build the RAG index (needed for judging, ~5-10 min)
python -m angry_agents.src.rag.build_index

# 6. Start the UI in a second terminal (http://localhost:8001)
python -m http.server 8001 -d ui/
```

Full instructions, including starting from an empty database, are in [`angry_agents/docs/md/SETUP.md`](angry_agents/docs/md/SETUP.md). MCP setup is described in [`angry_agents/src/mcp/MCP_SETUP.md`](angry_agents/src/mcp/MCP_SETUP.md).

---

## Repository structure

```
angry_agents/src/
├── API/          FastAPI app, routes, JWT auth
├── db/           models, repositories (raw SQL), services
├── agents/       persona runtime, profile extraction, judges + Jinja2 templates
├── group_chat/   session orchestrator, turn scheduler, context window
├── dm_chat/      one-on-one chat sessions
├── rag/          ChromaDB indexing and retrieval
├── eval/         statistical metrics and batch evaluation
├── scraping/     YouTube, Twitter, movie script and PDF scrapers
└── mcp/          Model Context Protocol server and tools
ui/               React front end
data/             persona profiles and raw source corpora
report/           full project report (LaTeX + PDF)
```

---

## Limitations and future work

- **Judge deliberation**: a second phase where judges discuss high-variance cases over several rounds was designed but left out of this iteration.
- **Behavioural fidelity** still lacks a solid operational definition; psycholinguistic profiling (e.g. LIWC) or human blind raters are the most promising options.
- **Sparse personas**: retrieval quality drops for characters with less than ~5k tokens of source material.
- **Conversation length**: too short misses deep patterns, too long causes drift, and the optimal range is still open.
- **MCP authentication** needs to be added before any production use.
- **New sources and user-created personas**: building personas from books and biographies, and letting users upload their own material.

---

## Research background

The design draws on Park et al. (2023, *Generative Agents*) for memory, reflection and the agreeableness problem in groups; Jiang et al. (2024, *PersonaLLM*) for the blind evaluation protocol; Zhou et al. (2025) for the role of personal details in behavioural fidelity; Salewski et al. (2023) on demographic bias in persona prompts; and Wason et al. (2024) on context management in dialogue agents. The novel contribution is a single experimental pipeline that combines persona identification, individual, group and behavioural fidelity on personas extracted from real text corpora.

The full write-up is available in [`report/report.pdf`](report/report.pdf).

<p align="center"><sub>Developed for the course <i>Designing Large Scale AI Systems</i>, AI Design 2026.</sub></p>
