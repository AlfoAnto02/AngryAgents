# Context Management for Persona Agents

## Overview

Three distinct problems arise when running LLM-based persona agents in a multi-turn chat:

| # | Problem | When it appears |
|---|---------|----------------|
| 1 | **Grounding** — injecting the persona into the model | Every inference call |
| 2 | **Character drift** — persona degrades over long conversations | After ~30–40 turns |
| 3 | **Group dynamic drift** — agents converge toward similar tone/positions | In group chats with 8+ agents |

Each requires a different mitigation. They stack — solve them in order.

---

## Problem 1 — Grounding

### What it is

The model has no inherent knowledge of the persona. On every inference call, you must supply enough context for the model to reproduce the character's style, ideology, and behavioral patterns faithfully.

Passing the raw transcript is not viable: 10 videos × ~3,000 tokens each = ~30,000 tokens per inference call.

### Solution: Structured Profile + RAG

Two layers work together.

#### Layer A — Structured Profile (static, always in context)

Extract a structured JSON profile offline from raw source material using an LLM. Do this once per persona. The profile is always included in the system prompt.

Target size: **800–1,500 tokens**.

```json
{
  "core_style": "short sentences, heavy slang, frequent exclamations",
  "humor": "self-deprecating, comic exaggeration, uses food as moral currency",
  "vocabulary_markers": ["pazzesco", "una follia", "però", "onestamente"],
  "ideological_positions": {
    "food": "purist but curious, accepts fusion only if 'honest'",
    "content": "spontaneity over production, anti-hype"
  },
  "emotional_triggers": {
    "positive": "local authenticity, strong flavors, simplicity",
    "negative": "inflated prices, empty hype, inauthenticity"
  },
  "response_patterns": {
    "when_disagreeing": "laughs first, then dismantles with a concrete example",
    "when_enthusiastic": "superlative + pause + reconfirmation ('insane. Actually insane.')"
  },
  "exemplar_quotes": [
    "This thing right here is an atomic bomb.",
    "I genuinely didn't expect it, I thought it was just hype."
  ]
}
```

**Grounding in literature:** Zhou et al. (2025) show that personal detail features are the single most critical driver of behavioral fidelity — removing them causes the largest accuracy drop across all profile conditions.

#### Layer B — RAG on Transcript Chunks (dynamic, per turn)

Retrieves character-specific nuances relevant to the current topic without loading the full transcript.

**Offline (once per persona):**
- Chunk transcript into segments of 150–200 tokens
- Embed each chunk with a lightweight model (e.g., `text-embedding-3-small`)
- Store in a vector index

**Online (each turn):**
- Embed the incoming user message
- Cosine search → retrieve top-3 most relevant chunks
- Append as `<retrieved_examples>` in the prompt

```
[system, cached]
You are {persona_name}.
{structured_profile}

[retrieved_context]
In a similar context, {persona_name} said: "..."
On this topic: "..."

[conversation]
...

[user]
...
```

RAG adds ~300–500 tokens per turn. The vector index for 10–50 videos is negligible in storage cost.

#### Prompt Caching

The structured profile does not change during a conversation. Use a cache breakpoint after the system prompt so the model does not reprocess it on every turn.

```python
messages = [
    {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": system_prompt_with_profile,
                "cache_control": {"type": "ephemeral"}  # 5-min TTL
            },
            {"type": "text", "text": current_turn}
        ]
    }
]
```

Savings: 60–80% of input token cost on the static portion after the first turn.

---

## Problem 2 — Character Drift

### What it is

After 30–40 turns, the conversational context grows large enough to dominate the system prompt. The agent starts following the flow of the conversation rather than maintaining its distinctive character. It becomes more generic, more agreeable, more "LLM-like."

### Solution: Sliding Window + Compression + Reflection

Three mechanisms work in sequence.

#### Sliding Window

Never pass the full conversation history. Keep only the last **K turns verbatim** (K = 5 is a reasonable default).

#### History Compression

Every 10 turns, call the model to compress the earlier turns into a short summary (~200–300 tokens):

> "So far: [persona A] defended local food, [persona B] pushed back on the authenticity argument, tension is building around the definition of 'honest' cuisine."

The summary replaces the raw turns. This keeps the context window bounded regardless of conversation length.

Trigger: `if len(history) % 10 == 0: compress(history[:-K])`

#### Reflection

Every N turns (N = 15–20 recommended), inject a reflection step before the agent generates its next message:

```
[reflection prompt]
You are {persona_name}. Review your last 15 messages and your character profile.
Answer in 2–3 sentences: how are you positioned in this conversation?
Are you staying true to your character, or have you drifted?
```

The reflection output (~150–200 tokens) is stored and prepended to the agent's next system prompt as a `<self_anchor>` block. This forces the agent to re-anchor to its character before replying.

Do not run reflection every turn — it adds latency and cost. Trigger it when:
- `turn_count % N == 0`, OR
- A drift signal is detected (see below)

#### Token Budget Per Turn (Target)

```
[system, cached]  structured_profile         ~1,000 tok
[dynamic]         rag_chunks                   ~400 tok
[dynamic]         compressed_history           ~300 tok
[dynamic]         self_anchor (reflection)     ~200 tok
[dynamic]         last 5 turns verbatim        ~600 tok
[dynamic]         user message                  ~50 tok
─────────────────────────────────────────────────────────
Total per turn                               ~2,550 tok
vs. raw transcript                          ~30,000 tok

Savings: ~92%
```

---

## Problem 3 — Group Dynamic Drift

### What it is

In a group chat with 8 agents, they tend to converge toward similar tone and positions over time. This is documented in Park et al. (2023) as "excessive agreeableness" — a side effect of instruction tuning that suppresses divergent behavior. Agents start imitating each other rather than maintaining their distinct character.

Reflection alone is not sufficient because the pressure comes from all 8 agents simultaneously.

### Solution: Perturbation Mechanism

Every N turns (N = 10–15 in group chats), inject a **perturbation signal** specific to each agent's character profile. This is a brief instruction appended to the system prompt:

```
[perturbation]
The conversation is moving toward consensus.
React to the last message in a way that reflects your genuine position,
even if it means disagreeing, redirecting, or introducing a new angle.
Stay fully in character.
```

The perturbation fires on a per-agent basis and is not visible to other agents. It does not force disagreement — it forces character-consistent reaction, which may be agreement, silence, or challenge depending on the persona.

### Drift Detection (Optional)

For measurable drift, track cosine similarity between each agent's embeddings turn-by-turn. A rising similarity across agents is a signal to trigger early reflection or perturbation.

```python
def drift_score(agent_embeddings: list[np.ndarray]) -> float:
    # pairwise cosine similarity between all agents' last-turn embeddings
    sims = [cosine(a, b) for a, b in combinations(agent_embeddings, 2)]
    return float(np.mean(sims))

# trigger early reflection if drift_score > threshold (e.g. 0.85)
```

---

## Full Architecture Summary

```
OFFLINE (once per persona)
─────────────────────────
raw_transcript
  → LLM extraction → structured_profile.json   (stored in DB)
  → chunking + embedding → vector_index         (stored per-persona)

ONLINE (each conversation turn)
────────────────────────────────
user_message
  → embed → cosine search → top-3 chunks        (RAG)

prompt assembly
  [cached]   structured_profile
  [dynamic]  rag_chunks
  [dynamic]  compressed_history
  [dynamic]  self_anchor          (if reflection fired this turn)
  [dynamic]  perturbation signal  (if group drift detected, group chat only)
  [dynamic]  last K turns
  [dynamic]  user_message
  → model call → agent response

every 10 turns: compress(history[:-K])
every 15 turns: reflection(agent, history)
every 10 turns (group): perturbation(agent) if drift_score > threshold
```

---

## Implementation Priority

| Priority | Component | Effort | Impact |
|----------|-----------|--------|--------|
| 1 | Structured profile extraction | Medium | Highest — drives fidelity |
| 2 | Prompt caching | Low | 60–80% cost reduction |
| 3 | Sliding window + compression | Low | Keeps context bounded |
| 4 | Reflection | Medium | Mitigates character drift |
| 5 | RAG on transcript | Medium | Adds topic-specific nuance |
| 6 | Perturbation mechanism | Low | Group chat only |
| 7 | Drift detection (embeddings) | High | Optional — useful for evaluation |

Start with 1–3 as the MVP. Add 4–5 if drift is observed in testing. Add 6 only when group chat is implemented.

---

## References

- Park et al. (2023) — Generative Agents: memory stream, reflection, excessive agreeableness failure mode
- Zhou et al. (2025) — personal detail features as the primary fidelity driver; RAG via FAISS
- Wason et al. (2024) — context management as an unsolved challenge in LLM dialogue agents
