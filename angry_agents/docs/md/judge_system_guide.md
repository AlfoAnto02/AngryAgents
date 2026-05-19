# Judge System Guide — Angry Agents

A reference for understanding and extending the multi-judge evaluation pipeline in this project.

---

## 1. Project Context

Angry Agents is a chat application where users talk to AI agents that impersonate real-world or fictional personas. Conversations happen either as **DMs** (user ↔ one agent) or **group chats** (user + 8 agents around a topic).

The judge system sits on top of completed chats. Its job is to evaluate how faithfully each agent performed its persona. **20 judge agents** evaluate every group chat independently across four dimensions, then collaborate in a second phase to produce a consolidated assessment.

Crucially, **judges never see real agent identities**. The `Chat_messages.author` field stores a HMAC-SHA256 digest computed from name + surname + a server secret. Judges reason about digests only — this anonymisation is enforced at the DB schema level with no FK from `Chat_messages` to `Agents`.

---

## 2. Database Structure Relevant to Judges

### Tables judges interact with

**`Judges`**

| Field | Type | Notes |
|---|---|---|
| `ID` | Serial PK | — |
| `Role` | String NOT NULL | One of: `style` / `ideology` / `general` / `behavioral` |
| `Temperature` | Float NULLABLE | LLM temperature for this judge |
| `Guess` | String NULLABLE | — |
| `Created_at` / `Updated_at` / `Deleted_at` | Timestamp | Soft-delete pattern |

**`Judge_evaluation`**

| Field | Type | Notes |
|---|---|---|
| `ID_judge` | FK → `Judges.ID` | Composite PK with `ID_chat` |
| `ID_chat` | FK → `Group_chat.ID` | Composite PK with `ID_judge` |
| `Score` | Float NULLABLE | Overall score assigned |
| `Created_at` / `Updated_at` / `Deleted_at` | Timestamp | Soft-delete pattern |

**Invariants enforced by the service layer:**
- Maximum **20** `Judge_evaluation` rows per chat (`JudgeEvaluationService` enforces the cap → HTTP 409 if exceeded).
- Soft-deleted evaluation slots do not count toward the cap.
- Hard delete is admin-only (`?hard=true`).

**`Group_chat`** / **`Chat_messages`**

| Field | Notes |
|---|---|
| `Chat_messages.author` | HMAC digest — judges see this, never the real agent name |
| `Chat_messages.ID_Chat` | FK → `Group_chat.ID` |
| No FK to `Agents` | Anonymity enforced at schema level |

### DB access pattern

All SQL lives in `api/`. Judges read chat data and write evaluations exclusively through the service layer — never with raw SQL.

---

## 3. Current Architecture

### File layout

```
angry_agents/src/agents/
├── agent_config.py              ← LLM dispatch, prompt formatting, score parsing
└── judges/
    ├── base_judge.py            ← Abstract base + shared data classes
    ├── style_judge.py           ← Lens: vocabulary, tone, sentence structure
    ├── ideology_judge.py        ← Lens: values, political views, moral stances
    ├── general_judge.py         ← Lens: all observable traits combined
    ├── judge_example.py         ← Standalone generic scorer (Ollama only, CSV output)
    └── evaluation_test.py       ← Test runner → angry_agents/src/agents/judge_eval/
```

### Data classes (`base_judge.py`)

```python
@dataclass
class AgentScore:
    author: str   # anonymised HMAC digest from Chat_messages
    score: int    # 1–5

@dataclass
class PersonaMatch:
    persona_name: str
    scores: list[AgentScore]  # one score per agent in the chat

    @property
    def predicted(self) -> str:
        return max(self.scores, key=lambda x: x.score).author

@dataclass
class PersonaIdentificationResult:
    matches: list[PersonaMatch]  # one per persona profile
```

### Abstract base (`BaseJudge`)

```python
class BaseJudge(ABC):
    name: str   # e.g. "style"
    focus: str  # injected into prompts

    @abstractmethod
    def persona_identification(self, chat, personas) -> PersonaIdentificationResult: ...

    @abstractmethod
    def individual_fidelity(self, chat) -> None: ...

    @abstractmethod
    def group_fidelity(self, chat) -> None: ...

    @abstractmethod
    def behavioural_fidelity(self, chat) -> None: ...
```

`individual_fidelity`, `group_fidelity`, and `behavioural_fidelity` are declared but not yet implemented in any concrete judge (all return `pass`). Only `persona_identification` is active.

### LLM dispatch (`agent_config.py`)

The module exposes one public function and one dispatcher:

```
llm_call(prompt, model)
    ├── LLM_BACKEND=ollama  →  _ollama_call()   POST http://localhost:11434/api/chat
    └── LLM_BACKEND=openai  →  _openai_call()   POST https://api.openai.com/v1/chat/completions
```

Backend is selected via the `LLM_BACKEND` env var (`"ollama"` default). `OPENAI_API_KEY` and `OPENAI_MODEL` are read from `.env`.

`run_persona_identification` is the shared loop that all judge classes delegate to:

```
for each persona:
    build_prompt(name, profile_block, messages_block, author_list)
    → llm_call(prompt, model)
    → _parse_agent_scores(raw, authors)   ← regex: "digest: score" per line
    → PersonaMatch(persona_name, scores)
→ PersonaIdentificationResult(matches)
```

### Prompt format (current)

Prompts are plain Python f-strings embedded in each judge file. The pattern is:

```
You are identifying which agent in a group chat is acting as a specific persona.
Your only lens is {FOCUS}.

--- PERSONA PROFILE: {persona_name} ---
{profile_block}

--- MESSAGES BY AUTHOR ---
{messages_block}

Score each author 1–5 on how likely they are acting as {persona_name}:
  1 = very unlikely  5 = very likely

Reply with one line per author in this exact format:
author_digest: score

Authors to score (in this order): {author_list}
```

### Persona profiles

Profiles are `.json` files under `data/personas/`. Each file is loaded and formatted by `format_profile()` in `agent_config.py`, which extracts:

- `core_style`, `humor`, `vocabulary_markers`
- `ideological_positions`, `emotional_triggers`
- `response_patterns`, `social_positioning`
- `exemplar_quotes`

Two persona types exist per the domain model:
- **`fiction`** — extracted from books, movies, TV series (scarce source material).
- **`real_world`** — extracted from podcast transcripts (rich Q&A pairs).

### Test runner (`evaluation_test.py`)

```
python -m angry_agents.src.agents.judges.evaluation_test
```

Reads `data/eval/test_chat.jsonl` and all `data/personas/*.json`, runs all three active judges, prints results to stdout, and writes `angry_agents/src/agents/judge_eval/eval_test_N.jsonl` (one JSON object per judge per line).

---

## 4. The Four Evaluation Dimensions

| Dimension | What it measures | Status |
|---|---|---|
| **Persona identification** | Which digest is acting as which persona | Implemented (Phase 1) |
| **Individual fidelity** | How faithfully each agent's messages match its persona (score 1–5) | Not implemented |
| **Group fidelity** | How well agents behave as a coherent group (Gini on turn distribution, cosine distance) | Not implemented |
| **Behavioural fidelity** | How human-like each agent's behaviour is | Not implemented |

The four judge roles (`style`, `ideology`, `general`, `behavioral`) apply their specific lens to all four dimensions.

---

## 5. The Two-Phase Evaluation Pipeline

### Phase 1 — Independent evaluation

All 20 judges work independently. No judge sees another's output. Each produces:

- Persona identification (argmax digest per persona)
- Individual fidelity score per agent (1–5)
- Group fidelity assessment
- Behavioural fidelity assessment

**Phase 1 must complete before Phase 2 starts.** No cross-contamination.

### Phase 2 — Structured deliberation

Triggered on high-variance cases only. Judges see each other's Phase 1 outputs as context and revise their scores over 3–5 rounds. Confidence is tracked per round. Variance reduction across rounds and convergence rate are the key metrics.

### External omniscient agent

A separate agent with full context — persona profiles, full chat, all 20 judge outputs — evaluates the quality of the judging process itself. It does not influence the evaluation scores. It operates after both phases complete.

---

## 6. Metrics

| Metric | Formula |
|---|---|
| Persona ID accuracy | Binomial CI, baseline 12.5% (random over 8 agents) |
| Individual fidelity | Median + IQR per persona, 20 ratings each |
| Group fidelity | Gini on turn distribution; cosine distance matrix (Spearman vs real) |
| Deliberation quality | Variance reduction across rounds, convergence rate with binomial CI |

---

## 7. Architecture to Build Toward

### 7.1 One template file per judge dimension

Replace the embedded Python f-strings with Jinja2 `.j2` templates. One file per judge × dimension combination. This makes prompts independently versionable and diffable without touching Python.

```
angry_agents/src/agents/judges/templates/
├── persona_id_style.j2
├── persona_id_ideology.j2
├── persona_id_general.j2
├── persona_id_behavioral.j2
├── individual_fidelity_style.j2
├── individual_fidelity_ideology.j2
├── ...
└── phase2_deliberation.j2
```

Template anatomy (two blocks, static vs dynamic):

```jinja2
{%- block system -%}
You are a judge evaluating a group chat. Your lens is STYLE only.

[Criteria, output schema, rating rubric — all static]
{%- endblock -%}

{%- block user -%}
{{ persona_profile }}

{{ messages_block }}
{%- endblock -%}
```

The `render_prompt` loader:

```python
from jinja2 import Environment, FileSystemLoader

_env = Environment(
    loader=FileSystemLoader(_TEMPLATES_DIR),
    keep_trailing_newline=False,
    trim_blocks=True,
    lstrip_blocks=True,
)

def render_prompt(template_name: str, **kwargs) -> tuple[str, str]:
    tmpl = _env.get_template(template_name)
    ctx = tmpl.new_context(vars=kwargs)
    system, user = "", ""
    for name, block_fn in tmpl.blocks.items():
        rendered = "".join(block_fn(ctx)).strip()
        if name == "system":
            system = rendered
        elif name == "user":
            user = rendered
    return system, user
```

### 7.2 Motivation before rating

Every judge template must return structured JSON with motivation first, rating second:

```jinja2
Respond in JSON with exactly two keys:
- "motivation": brief assessment (2–5 sentences)
- "rating": integer 1–5
```

Motivation before rating forces reasoning before committing to a number. Use `response_format={"type": "json_object"}` on every LLM call.

### 7.3 Explicit rating rubric in every template

```
5 = unmistakable match
4 = strong match, minor divergences
3 = plausible match, notable divergences
2 = weak match, more misses than hits
1 = very unlikely to be this persona
```

Without a rubric, judges drift to different implicit scales across personas and dimensions.

### 7.4 `temperature=0` for all judge calls

Judges must be deterministic and reproducible. Only the persona-playing agents use non-zero temperature.

### 7.5 Batching for Phase 1

20 judges × 7 personas × 1 LLM call each = 140 calls. Use batch prompts where the LLM scores multiple personas in one call:

```
Input:  [{"id": "cicciogamer89", "profile": "..."}, {"id": "YODA", "profile": "..."}, ...]
Output: {"items": [{"id": "cicciogamer89", "scores": {...}, "motivation": "..."}, ...]}
```

Batch size of 5–7 personas per call is safe. Keep batches within a single judge role.

### 7.6 Phase 2 deliberation template

A separate template receives all Phase 1 outputs as context:

```jinja2
{%- block system -%}
You are judge {{ judge_name }} in a structured deliberation round {{ round_number }}.
You have seen all other judges' Phase 1 outputs. You may revise your score.
Output: {"revised_score": int, "confidence": float 0-1, "rationale": str}
{%- endblock -%}

{%- block user -%}
Your Phase 1 score: {{ my_phase1_score }}

Other judges' outputs:
{{ other_judges_json }}

Chat:
{{ messages_block }}
{%- endblock -%}
```

### 7.7 DB write-back

After Phase 1, write one `Judge_evaluation` row per judge via the service layer:

```python
from angry_agents.src.db.services.judge_evaluation_service import JudgeEvaluationService

svc = JudgeEvaluationService(db)
svc.create(db, {
    "id_judge": judge.db_id,
    "id_chat": chat_id,
    "score": result.aggregate_score,
})
```

The service enforces the 20-per-chat cap and raises on duplicates. The route converts these to HTTP 409.

---

## 8. Key Design Principles

| Principle | Rule |
|---|---|
| One template per judge × dimension | Never combine two evaluation criteria in one prompt |
| Motivation before rating | Forces reasoning before committing to a score |
| Explicit rubric in every template | No implicit scales |
| `temperature=0` for judges | Reproducibility |
| `json_mode=True` | Prevents markdown wrapping that breaks parsing |
| Phase 1 completes before Phase 2 | No cross-contamination |
| Judges never see real agent identities | Only HMAC digests — enforced at DB schema level |
| SQL only in `api/` | Judges write evaluations through the service layer |

---

## 9. What Exists vs What Is Left to Build

| Component | Status |
|---|---|
| `BaseJudge` ABC + data classes | Done |
| `StyleJudge`, `IdeologyJudge`, `GeneralJudge` — persona ID | Done |
| `BehavioralJudge` | Not built |
| `individual_fidelity`, `group_fidelity`, `behavioural_fidelity` | Declared, not implemented |
| Jinja2 template system | Not built (prompts are inline f-strings) |
| Phase 2 deliberation | Not built |
| External omniscient agent | Not built |
| DB write-back of evaluation results | Not built (test runner writes local `.jsonl` only) |
| Batch LLM calls for Phase 1 | Not built |

---

## 10. Quick Reference

```python
# Current: run persona identification with the style judge
from angry_agents.src.agents.judges.style_judge import StyleJudge

judge = StyleJudge()
result = judge.persona_identification(chat_dict, personas_list)
# result.matches[i].persona_name  → persona name
# result.matches[i].predicted     → digest of most likely agent
# result.matches[i].scores        → [AgentScore(author, score), ...]

# LLM backend switch (set in .env)
# LLM_BACKEND=openai   OPENAI_API_KEY=sk-...   OPENAI_MODEL=gpt-4o-mini
# LLM_BACKEND=ollama   OLLAMA_DEFAULT_MODEL=mistral

# Run the test evaluation
python -m angry_agents.src.agents.judges.evaluation_test
# Output: angry_agents/src/agents/judge_eval/eval_test_N.jsonl
```
