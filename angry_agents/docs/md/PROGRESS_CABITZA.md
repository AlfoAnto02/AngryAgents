# Progress Log — Cabitza Session (2026-05-18)

## 1. `base_judge.py` — redesigned abstract class

Replaced the old per-message `evaluate` / `deliberate` interface with four abstract methods aligned to the evaluation dimensions in the problem definition:

| Method | Status |
|---|---|
| `persona_identification(chat, personas)` | Implemented in all judges |
| `individual_fidelity(chat)` | Stub — not yet designed |
| `group_fidelity(chat)` | Stub — not yet designed |
| `behavioural_fidelity(chat)` | Stub — not yet designed |

New dataclasses:
- `AgentScore` — author DIGEST + score 1–5
- `PersonaMatch` — one per persona; holds per-agent scores and `.predicted` argmax
- `PersonaIdentificationResult` — list of `PersonaMatch`, one per persona profile

Input is the full `chat: dict` plus a `personas: list[dict]` of profile files.

## 2. Judge implementations

Three concrete judges, each extending `BaseJudge`:

| File | Class | Focus |
|---|---|---|
| `style_judge.py` | `StyleJudge` | Vocabulary, sentence structure, tone, rhetorical habits |
| `ideology_judge.py` | `IdeologyJudge` | Political views, values, moral stances, belief systems |
| `general_judge.py` | `GeneralJudge` | All observable traits combined |

`persona_identification` loops over all persona profiles. For each persona it calls Ollama (mistral) asking the model to score every agent 1–5 on how likely they are acting as that persona, then takes the argmax as the predicted agent. Each judge differs only in its focus-specific prompt.

## 3. `agent_config.py` — shared config and helpers

Created `angry_agents/src/agents/agent_config.py` to centralise all code shared across judges:

- `OLLAMA_BASE_URL` and `DEFAULT_MODEL` — read from `.env` via `python-dotenv`.
- `format_messages(chat)` — groups chat messages by author DIGEST.
- `format_profile(profile)` — serialises a persona profile dict into prompt text.
- `_parse_agent_scores(raw, authors)` — parses LLM output into `AgentScore` list.
- `_ollama_call(prompt, model)` — raw HTTP call to Ollama, returns response text.
- `run_persona_identification(build_prompt, chat, personas, model)` — shared loop: iterates over personas, builds the prompt via the judge's lambda, calls Ollama, parses scores, returns `PersonaIdentificationResult`.

Each judge file is now just a prompt template constant and a class definition.

## 4. `evaluation_test.py` — test runner

Loads the real transcript (`data/eval/transcript.jsonl`, JSONL format) and all persona profiles from `data/personas/*.json`. Runs `persona_identification` on all three judges and:

1. Prints per-judge, per-persona score tables and predicted agents to stdout.
2. Saves a `Judge_evaluation` JSON to `angry_agents/data/judge_eval/eval_test_n.json`, where `n` auto-increments on each run.

The saved JSON follows the `Judge_evaluation` schema from DB_v2.md (`ID_judge`, `ID_chat`, `Score`, `Created_at`, `Updated_at`, `Deleted_at`) plus a `persona_identification` block with full per-persona results. `Score` is `null` pending design of the aggregate metric.

Run from repo root:
```bash
python -m angry_agents.src.agents.judges.evaluation_test
```

Requires Ollama running in a separate terminal (`ollama serve`) with mistral available (`ollama pull mistral`).

## 5. Real transcript integration

Switched from the fake chat JSON to `data/eval/transcript.jsonl` (40 messages, 7 agents). Key difference: JSONL format (one JSON object per line), fields are `msg_id`, `turn`, `author`, `message`, `drifted`. The loader parses it line-by-line and wraps it in the `{"messages": [...]}` envelope the judges expect.

Personas available in `data/personas/`: `cicciogamer89`, `INDY`, `JACK`, `LUKE`, `RIGGAN`, `VADER`, `YODA`.

## Open points

- `individual_fidelity`, `group_fidelity`, `behavioural_fidelity` are empty stubs — design pending.
- A fourth judge type (`behavioral`) is referenced in the problem definition but not yet created.
- No `__init__.py` files exist under `src/agents/` — package structure relies on running via `-m`.
- `Score` in `Judge_evaluation` output is always `null` — aggregate scoring metric not yet designed.
- Timeout hit during testing: 40-message transcript × 7 personas is too large for mistral within 120 s. Prompt size or chunking strategy needs revisiting.
