# RAG System — Angry Agents

## What problem this solves

The judge pipeline evaluates every group chat by comparing each anonymous author's
messages against every persona profile in the database. Without filtering, each
evaluation requires one LLM call per persona per judge — a number that scales
linearly with the database size. At 100 personas and 20 judges this becomes
unsustainable, both in cost and latency.

The RAG layer solves this by pre-filtering the database **before** any judge sees
the chat. Instead of 100 profiles, each judge receives the 15 most relevant
candidates retrieved via semantic similarity. The judges themselves do not change
— they still receive `personas: list[dict]`, just a shorter one.

---

## Architecture

```
BUILD TIME (once)
─────────────────────────────────────────────────────────────────────
 data/personas/*.json
        │
        ▼
   builder.py          chunks each profile into semantic units
        │               (style, voice, worldview, behavior, quotes)
        ▼
   indexer.py          calls OpenAI text-embedding-3-small per chunk
        │               stores vectors + metadata in ChromaDB
        ▼
   data/chroma/        persistent vector store on disk


QUERY TIME (every evaluation)
─────────────────────────────────────────────────────────────────────
 Chat transcript
        │
        ▼
 group messages by digest → {digest: [msg1, msg2, ...]}
        │
        ▼
   retriever.py        embeds each author's messages (last 5)
        │               queries ChromaDB for nearest chunks
        │               aggregates scores across all authors
        │               returns top-15 distinct persona profiles
        ▼
 candidates: list[dict]   (15 profiles instead of 100)
        │
        ▼
   judges (style / ideology / general / behavioral)
```

---

## File responsibilities

| File | Responsibility |
|---|---|
| `builder.py` | Splits a profile JSON into typed chunks. No external dependencies. |
| `indexer.py` | Embeds chunks via OpenAI API and upserts them into ChromaDB. |
| `retriever.py` | Queries ChromaDB per author digest, merges scores, returns top-K profiles. |
| `build_index.py` | One-shot script to index all profiles in `data/personas/`. |
| `evaluation_test_with_rag.py` | Judge evaluation pipeline with RAG pre-filter. |

---

## Chunking strategy

Each profile is split into 4–9 chunks depending on how many fields are present.
Splitting by semantic dimension means a query that matches on style alone will
still surface the right persona, even if the worldview or ideology chunks are
not similar.

| Chunk type | Fields included | Most useful for |
|---|---|---|
| `style` | `core_style`, `speech_signature`, `response_patterns`, `register_shift_triggers` | style judge |
| `voice` | `humor`, `vocabulary_fingerprint`, `vocabulary_markers` | style / general judge |
| `worldview` | `worldview`, `self_image_vs_reality`, `emotional_tells`, `ideological_positions`, `emotional_triggers`, `knowledge_domains` | ideology / behavioral judge |
| `behavior` | `situational_behavior`, `escalation_pattern`, `conversation_goals`, `social_positioning` | behavioral judge |
| `quote` (×N) | one chunk per annotated or exemplar quote | all judges — highest signal |

Quote chunks are the most discriminating because they encode linguistic
fingerprints (rhythm, register, irony) that the embedding model captures even
without lexical overlap with the query.

---

## Retrieval logic

For each anonymous digest in the chat, the retriever:

1. Takes the author's last 5 messages and joins them into a single query string.
2. Embeds the query string using the same model used at index time (`text-embedding-3-small`).
3. Queries ChromaDB for the `top_k × 3` nearest chunks (over-samples to allow deduplication).
4. Converts L2 distance to a score: `score = 1 / (1 + distance)`.
5. Keeps only the **best score per persona** across all chunks and all authors.
6. Returns the top-K personas by score as full profile dicts.

The union across all digests ensures that if one author's messages are stylistically
close to JIMMY and another's are close to WALTER WHITE, both appear in the candidate
list passed to the judges.

---

## Cost analysis

### Assumptions

- **100 personas** in the database (production target).
- **20 judges**, persona identification only (Phase 1).
- **Group chat**: 8 agents, ~30 messages, ~1 500 tokens.
- **Average profile size**: ~550 tokens (varies from ~300 for simple profiles to ~950 for rich ones).
- **System + prompt overhead**: ~300 tokens per call.
- **LLM model**: `gpt-4o-mini` — $0.150 / 1M input tokens, $0.600 / 1M output tokens.
- **Embedding model**: `text-embedding-3-small` — $0.020 / 1M tokens.
- **Batch size** (where batching applies): 5 profiles per call.
- **RAG top-K**: 15 candidates.

---

### Per-call token breakdown

**Current (no RAG, no batching) — one profile per call:**

```
Input  = 550 (profile) + 1 500 (chat) + 300 (overhead) = 2 350 tokens
Output = 150 tokens (scores + motivation)
Total  = 2 500 tokens / call
```

**With batching only — 5 profiles per call:**

```
Input  = 5 × 550 (profiles) + 1 500 (chat) + 300 (overhead) = 4 550 tokens
Output = 750 tokens
Total  = 5 300 tokens / call   (but 5× fewer calls)
```

**With RAG + batching — 15 candidates, 3 batches per judge:**

```
RAG query  = 8 authors × ~100 tokens (5 messages × 20 tokens) = 800 tokens
             cost: negligible ($0.000016 at embedding price)

Per batch  = 5 × 550 (profiles) + 1 500 (chat) + 300 (overhead) = 4 550 tokens input
Output     = 750 tokens
Total      = 5 300 tokens / call   (97% fewer calls)
```

---

### Single evaluation comparison

| Approach | LLM calls | Input tokens | Output tokens | Cost |
|---|---|---|---|---|
| No RAG, no batching | 2 000 | 4 700 000 | 300 000 | **$0.885** |
| Batching only (5/call) | 400 | 1 820 000 | 300 000 | **$0.453** |
| RAG (top-15) + batching | 60 | 273 000 | 45 000 | **$0.068** |

> RAG + batching vs no RAG: **−97% calls, −94% tokens, −92% cost per evaluation.**

The one-time index build cost is:

```
100 profiles × 600 tokens avg = 60 000 tokens
Cost = (60 000 / 1 000 000) × $0.020 = $0.001
```

Essentially free relative to the savings per evaluation.

---

### Cost over multiple evaluations

| Evaluations | No RAG, no batching | Batching only | RAG + batching |
|---|---|---|---|
| 1 | $0.885 | $0.453 | $0.069 (index + eval) |
| 10 | $8.85 | $4.53 | $0.68 |
| 100 | $88.50 | $45.30 | $6.80 |
| 1 000 | $885.00 | $453.00 | $68.00 |

The index is built once and reused across all evaluations. Re-indexing is only
needed when a new persona is added or an existing one is updated.

---

### Latency comparison

Fewer LLM calls also means lower wall-clock time per evaluation.

| Approach | Sequential latency (est. 1s/call) |
|---|---|
| No RAG, no batching | ~33 minutes |
| Batching only | ~7 minutes |
| RAG + batching | ~1 minute |

With async dispatch the numbers improve further, but the relative ratio holds.

---

## Important caveat — retrieval recall

The RAG pre-filter introduces a risk: if the correct persona for a given author
is **not** among the top-15 candidates, no judge can identify them correctly.
This is a **recall miss** at the retrieval layer, invisible in the judge scores.

To monitor this, `evaluation_test_with_rag.py` saves `rag_candidates` in every
output record. When ground truth is available, compare the actual personas in the
chat against `rag_candidates` to measure recall@15.

A recall@15 above 95% means the RAG is working correctly. If recall drops, the
first step is to increase `TOP_K` before investigating the embedding quality.

---

## Design choice: RAG as pre-filter vs RAG as judge

Two fundamentally different ways to use RAG in this pipeline.

---

### Approach A — RAG as pre-filter (implemented above)

RAG runs upstream of the judges. It narrows the database from 100 profiles to 15
candidates. The LLM judge then scores those 15 using natural language reasoning.

```
author messages → RAG → top-15 profiles → LLM judge → scores
```

The judge never sees the other 85 profiles. Its reasoning is confined to the
shortlist RAG prepared.

---

### Approach B — RAG as judge

RAG is the judge. No LLM is involved in persona identification. The vector
similarity score between the author's messages and each profile's chunks in
ChromaDB directly produces the 1-5 score. Every profile in the database is
scored — nothing is pre-filtered.

```
author messages → embed → query all ChromaDB → similarity scores → scores
```

The 4 judge roles stay meaningful by querying different chunk subsets:

| Judge role | Chunks queried |
|---|---|
| Style | `style`, `voice` |
| Ideology | `worldview` |
| Behavioral | `behavior` |
| General | all chunks |

For **Individual Fidelity**, each message is embedded individually and queried
against the known persona's chunks. Average similarity = raw fidelity score,
mapped to 1-5.

For **Group Fidelity**, the metric-based calculations (Gini, cosine distance
matrix) remain unchanged. RAG contributes by querying `behavior` and
`social_positioning` chunks to verify that the observed group dynamic matches
what each persona's profile predicts.

---

### Conceptual difference

The fundamental objection to Approach A is that pre-filtering is a form of
**assisted judgment**. The judge is handed a shortlist by a system that has
already done part of the reasoning. If the correct persona is not in the
top-15, the judge cannot find it — and the failure is silent.

Approach B removes this assistance entirely. The judge works against the full
database with no prior knowledge of which profiles are "likely". The score it
produces is earned from scratch. If it gets it wrong, the error is visible in
the full score distribution — not hidden by a pre-filter.

---

### Cost comparison — all three dimensions

#### Assumptions (same as above, plus)
- **Individual Fidelity**: 8 agents × ~20 messages each = 160 messages to score.
- **Group Fidelity**: metric calculations are free (no API calls); only the
  qualitative RAG query costs tokens.
- **Embedding cost**: `text-embedding-3-small` at $0.020 / 1M tokens.
- **LLM cost** (Approach A): `gpt-4o-mini` at $0.150 / 1M input, $0.600 / 1M output.
- Average message length: ~20 tokens.

---

#### Persona Identification

| | Approach A (pre-filter + LLM) | Approach B (RAG as judge) |
|---|---|---|
| LLM calls | 60 (15 profiles × 20 judges, batched 5) | 0 |
| Embedding calls | 8 (one per author digest) | 8 (same) |
| Tokens embedded | ~800 (query) | ~800 (query) |
| LLM input tokens | 273 000 | 0 |
| LLM output tokens | 45 000 | 0 |
| Embedding tokens | 800 | 800 |
| **Cost** | **$0.068** | **$0.000016** |

Approach B is effectively free for persona identification. ChromaDB scores all
100 profiles locally — no API call per profile, only the single embedding of the
query messages.

---

#### Individual Fidelity

| | Approach A (full profile + LLM) | Approach B (RAG as judge) |
|---|---|---|
| LLM calls | 8 (one per agent, full profile) | 0 |
| Embedding calls | 0 | 160 (one per message) |
| LLM input tokens | 8 × (600 profile + 400 messages + 300 overhead) = 10 400 | 0 |
| LLM output tokens | 8 × 150 = 1 200 | 0 |
| Embedding tokens | 0 | 160 × 20 = 3 200 |
| **Cost** | **$0.0023** | **$0.000064** |

Approach B embeds each message individually to get a per-message fidelity signal,
then averages. More granular and cheaper.

---

#### Group Fidelity

Metric calculations (Gini, cosine distance matrix) are identical in both
approaches — no API cost. The qualitative dimension:

| | Approach A (full profiles + LLM) | Approach B (RAG behavior chunks) |
|---|---|---|
| LLM calls | 1 (8 profiles + full transcript) | 0 |
| Embedding calls | 0 | 8 (behavior chunk queries) |
| LLM input tokens | 8 × 600 + 1 500 + 300 = 6 600 | 0 |
| LLM output tokens | 400 | 0 |
| Embedding tokens | 0 | ~400 |
| **Cost** | **$0.00099 + $0.00024 = $0.00123** | **$0.000008** |

---

#### Total per full evaluation (all 3 dimensions, 20 judges)

| | No RAG | Approach A (pre-filter) | Approach B (RAG as judge) |
|---|---|---|---|
| LLM calls | 2 000 | 69 | 0 |
| Embedding calls | 0 | 16 | 176 |
| Total tokens | 4 700 000 | ~320 000 | ~5 200 (embeddings only) |
| **Total cost** | **$0.885** | **$0.071** | **$0.0001** |
| **vs no RAG** | baseline | −92% | −99.99% |
| **vs Approach A** | — | baseline | −99.9% |

---

#### Cost over multiple evaluations

| Evaluations | No RAG | Approach A | Approach B |
|---|---|---|---|
| 1 | $0.885 | $0.072 | $0.001 |
| 10 | $8.85 | $0.72 | $0.001 |
| 100 | $88.50 | $7.20 | $0.010 |
| 1 000 | $885.00 | $72.00 | $0.10 |
| 10 000 | $8 850.00 | $720.00 | $1.00 |

---

### Trade-offs

| | Approach A | Approach B |
|---|---|---|
| **Cost** | Low | Near zero |
| **LLM reasoning** | Yes — nuanced, cross-field | No |
| **Written motivation** | Yes (per judge guide §7.2) | No |
| **Silent failure risk** | Yes — recall miss at pre-filter | No — full database always scored |
| **Style identification** | Strong | Strong |
| **Ideology identification** | Strong (LLM reads worldview) | Moderate (embedding similarity) |
| **Behavioral identification** | Strong (LLM reasons about patterns) | Moderate |
| **Determinism** | Low (LLM temperature) | High (vector math) |
| **Scalability** | Linear cost with judges | Flat cost regardless of judge count |

### Which to choose

Approach B is the right default for **persona identification** — it is cheaper,
deterministic, scales to any database size, and removes the silent failure risk
of pre-filtering. The cost is so low it becomes negligible even at 10 000
evaluations.

Approach A remains relevant for **individual fidelity** when written motivation
is required (the judge guide mandates it), or when the evaluation must explain
*why* a score was assigned, not just produce a number.

The practical recommendation is a **hybrid**:
- Persona Identification → Approach B (RAG as judge, zero LLM cost)
- Individual Fidelity → Approach A or B depending on whether motivation text is required
- Group Fidelity metrics → neither (pure calculation)
- Group Fidelity qualitative → Approach B (behavior chunk similarity)

---

## Approach C — RAG pre-filter + LLM with tool access (chosen design)

### Why Approach A and B are not enough

Approach A gives the judge a pre-filtered shortlist — but the judge is
**passive**: it receives whatever RAG prepared and cannot go beyond it. If the
right persona is just outside the top-15, the judge is stuck.

Approach B removes LLM reasoning entirely — the judges become identical
mathematical functions. Phase 2 deliberation, written motivation, and the
external omniscient agent all become meaningless because there is no reasoning
to compare or evaluate.

Approach C combines the strengths of both: RAG makes the search tractable and
each judge role gets its own field-specific shortlist. The LLM judge then
reasons over that shortlist **and can call ChromaDB on demand** whenever a
message pattern requires deeper investigation.

---

### Architecture

```
BUILD TIME (once — same as before)
─────────────────────────────────────────────────────────────────────
 data/personas/*.json  →  builder.py  →  indexer.py  →  data/chroma/


QUERY TIME (every evaluation)
─────────────────────────────────────────────────────────────────────
 Chat transcript
        │
        ▼
 messages grouped by digest → {digest: [msg1, msg2, ...]}
        │
        ├── Style judge    → retriever (fields: style, voice)    → 15 candidates
        ├── Ideology judge → retriever (fields: worldview)       → 15 candidates
        ├── Behavioral j.  → retriever (fields: behavior)        → 15 candidates
        └── General judge  → retriever (all fields)              → 15 candidates
                │
                ▼  (each judge gets its own shortlist — diversity preserved)
        LLM judge + tool access
                │
                ├── can call search_persona_profiles(query, field)
                │         → embeds query → hits ChromaDB → returns top-5 chunks
                │         → result added to conversation context
                │         → judge continues reasoning
                │
                └── produces: {"motivation": "...", "scores": {digest: 1-5, ...}}
```

Each judge role queries a different chunk subset for retrieval, so different
roles may receive different shortlists. A style judge and an ideology judge
start from different evidence — their disagreements in Phase 2 are genuine.

---

### New files

| File | Role |
|---|---|
| `tool.py` | `SEARCH_TOOL` schema (OpenAI function calling) + `execute()` |
| `judge_with_tools.py` | Tool-call loop + `run_persona_identification_with_tools()` |
| `templates/persona_id_rag.j2` | Prompt template with tool instructions and rubric |

`retriever.py` gained a `field_filter` parameter so each judge role can restrict
its retrieval to its relevant chunk types.

---

### Tool-call loop

```
messages = [system_prompt, user_prompt_with_candidates_and_chat]

loop (max 3 iterations):
    call OpenAI with tools=[search_persona_profiles]
    if finish_reason == "tool_calls":
        execute each tool call → append result to messages
    else:
        return final content   ← JSON with motivation + scores

if max iterations reached:
    force final answer with response_format=json_object
```

The loop runs per-persona call (same structure as existing
`run_persona_identification`). The judge can use the tool when a message
pattern does not clearly match any pre-filtered candidate.

---

### Cost analysis — Approach C

#### Additional assumptions
- **Tool calls**: average 1.5 per LLM turn (judge does not always need extra lookup).
- **Tool result size**: ~300 tokens (5 profile chunks, ~60 tokens each).
- **Tool query embedding**: ~30 tokens per call.
- **Approach C calls**: 1 per persona per judge = 15 × 20 = 300 calls.
- **Approach C+** (batching 5 profiles per call): 3 × 20 = 60 calls.

---

#### Per-call token breakdown

**Approach C — one profile per call + tool:**

```
Initial input  = 550 (current profile) + 1 500 (chat) + 300 (overhead) = 2 350 tokens
Tool context   = 1.5 calls × 300 tokens returned = 450 tokens added
Total input    = ~2 800 tokens / call
Output         = ~200 tokens (motivation + scores)
```

**Approach C+ — batch of 5 profiles per call + tool:**

```
Initial input  = 5 × 550 (profiles) + 1 500 (chat) + 300 (overhead) = 4 550 tokens
Tool context   = 1.5 calls × 300 = 450 tokens added
Total input    = ~5 000 tokens / call
Output         = ~750 tokens
```

---

#### Persona Identification cost comparison

| | Approach A | Approach B | Approach C | Approach C+ |
|---|---|---|---|---|
| Description | pre-filter + batching | RAG as judge | pre-filter + tool (1/call) | pre-filter + batching + tool |
| LLM calls | 60 | 0 | 300 | 60 |
| LLM input tokens | 273 000 | 0 | 840 000 | 300 000 |
| LLM output tokens | 45 000 | 0 | 60 000 | 45 000 |
| Embed tokens (retrieval) | 800 | 800 | 3 200 | 3 200 |
| Embed tokens (tool queries) | 0 | 0 | 13 500 | 3 600 |
| **Total cost** | **$0.068** | **$0.000016** | **$0.162** | **$0.073** |

Approach C+ (batching + tool use) costs only ~7% more than Approach A while
adding full tool-use reasoning to every judge call.

---

#### Full evaluation cost — all three dimensions

| | No RAG | Approach A | Approach B | Approach C+ |
|---|---|---|---|---|
| LLM calls | 2 000 | 69 | 0 | 69 |
| Embedding calls | 0 | 16 | 176 | 180 |
| LLM input tokens | 4 700 000 | 320 000 | 0 | 351 000 |
| LLM output tokens | 300 000 | 47 400 | 0 | 47 400 |
| Embedding tokens | 0 | ~4 000 | ~5 200 | ~22 000 |
| **Total cost** | **$0.885** | **$0.071** | **$0.0001** | **$0.079** |
| vs no RAG | baseline | −92% | −99.99% | −91% |
| vs Approach A | — | baseline | −99.9% | +11% |

Approach C+ costs only 11% more than Approach A for the full pipeline — a
negligible premium that buys tool-use reasoning, per-role diverse shortlists,
written motivations, and a functioning Phase 2 deliberation.

---

#### Cost over multiple evaluations

| Evaluations | No RAG | Approach A | Approach B | Approach C+ |
|---|---|---|---|---|
| 1 | $0.885 | $0.072 | $0.001 | $0.080 |
| 10 | $8.85 | $0.72 | $0.001 | $0.80 |
| 100 | $88.50 | $7.20 | $0.010 | $8.00 |
| 1 000 | $885.00 | $72.00 | $0.10 | $80.00 |
| 10 000 | $8 850.00 | $720.00 | $1.00 | $800.00 |

---

### Trade-offs — all four approaches

| | No RAG | Approach A | Approach B | Approach C+ |
|---|---|---|---|---|
| **Cost** | High | Low | Near zero | Low |
| **LLM reasoning** | Yes | Yes | No | Yes |
| **Written motivation** | Yes | Yes | No | Yes |
| **Tool-use reasoning** | No | No | No | Yes |
| **Per-role shortlists** | No | No | No | Yes |
| **Silent failure risk** | No | Yes — recall miss | No | Reduced — tool can escape shortlist |
| **Phase 2 deliberation** | Works | Works | Broken | Works best |
| **External omniscient agent** | Works | Works | Broken | Works best |
| **Determinism** | Low | Low | High | Low |
| **Scalability** | Linear | Linear (capped at 15) | Flat | Linear (capped at 15) |

---

### Why Approach C+ is the chosen design

1. **Project fidelity** — 20 AI agents that reason, disagree, and deliberate
   requires LLM reasoning. Approach B breaks the core concept.

2. **Silent failure fix** — the tool lets a judge escape the pre-filter when
   needed. If a message pattern is unusual, the judge can search the full
   database rather than being trapped in the shortlist.

3. **Diversity of judgment** — per-role retrieval means the style judge and
   ideology judge start from different evidence. Their Phase 2 disagreements
   are genuine, not artifacts of identical input.

4. **Cost** — only 11% above Approach A. At 1 000 evaluations the difference
   is $8 ($80 vs $72). Negligible relative to the quality improvement.

---

## Implementation optimizations

After the initial Approach C+ implementation, two optimizations were applied
that substantially reduced both cost and latency without changing the design.

---

### Optimization 1 — Batch scoring (1 call per judge, not per candidate)

The original loop called `_openai_tool_loop` once per candidate persona, passing
the full `candidates_block` every time:

```
for persona in candidates:          # 17 iterations
    call LLM(system, user)          # candidates_block sent 17 times
```

This was wasteful: the same 17 profiles were re-sent on every call. The fix is
to ask the model to score **all** (author × persona) pairs in a single call and
return a nested JSON:

```json
{
  "motivation": "...",
  "scores": {
    "<author_digest>": {"VADER": 2, "LUKE": 4, ...},
    ...
  }
}
```

One call per judge, all profiles sent once. A new template
`persona_id_rag_batch.j2` describes the expected output shape.

**Impact:**

| | Before (loop) | After (batch) |
|---|---|---|
| LLM calls (4 judges) | 68 | 4 |
| LLM calls (20 judges) | 340 | 20 |
| Cost — 4 judges | ~$0.071 | ~$0.006 |
| Cost — 20 judges | ~$0.355 | **~$0.029** |
| Wall-clock time | ~9 min (sequential) | ~30 sec (parallel) |

20 judges with the batch approach costs **less than 4 judges with the old loop**.

---

### Optimization 2 — Thread-safe ChromaDB singleton

Running judges in parallel with `ThreadPoolExecutor` caused a crash because
`chromadb.PersistentClient` opens the SQLite file each time it is called — and
SQLite cannot handle concurrent writers from multiple threads.

The fix is a module-level singleton in `_chroma.py` with a `threading.Lock()`:

```python
_lock = threading.Lock()
_collection: chromadb.Collection | None = None

def _get_collection() -> chromadb.Collection:
    global _collection
    if _collection is not None:
        return _collection
    with _lock:
        if _collection is None:          # double-checked locking
            client = chromadb.PersistentClient(path=str(_CHROMA_DIR))
            _collection = client.get_or_create_collection(...)
    return _collection
```

Both `retriever.py` and `tool.py` import `_get_collection` from `_chroma.py`.
Only one `PersistentClient` is ever opened per process — all threads share it.
ChromaDB's query interface is read-only during evaluation and is thread-safe.

---

### Updated cost table — all approaches + optimizations

| | No RAG | Approach A | Approach B | C+ original | **C+ optimized** |
|---|---|---|---|---|---|
| LLM calls (20 judges) | 2 000 | 60 | 0 | 300 | **20** |
| Cost per evaluation | $0.885 | $0.071 | $0.0001 | $0.073 | **$0.029** |
| vs No RAG | baseline | −92% | −99.99% | −92% | **−97%** |
| Wall-clock time | ~33 min | ~1 min | ~5 sec | ~3 min | **~30 sec** |

The optimized implementation outperforms the original Approach A even with
5× more judges (20 vs the original 4).