# Group Fidelity Refactor

## Summary

Group fidelity was originally a secondary output of the persona identification judge call — each judge returned `group_fidelity_score` as a second key in the same JSON response as the persona assignment. This had two problems:

1. **Mixed concerns**: a single LLM call was doing two unrelated jobs (assign personas + rate group dynamics), with the group fidelity rubric polluting the persona ID prompt.
2. **No lens separation**: all 20 judges used the same generic rubric. The 4 judging dimensions (style, ideology, general, behavioral) had no distinct group fidelity perspective.

The refactor makes group fidelity its **own dedicated LLM call** with **its own per-role templates**, fully separated from persona identification and individual fidelity. Each judge now makes a small, focused call that scores group dynamics through its role lens — no anchoring against persona-matching scores, and each concern is independently tunable.

---

## What group fidelity measures

Group fidelity measures whether the agents behaved as a real group conversation — not whether each agent portrayed their persona correctly (that is individual fidelity). It answers: did the agents engage with each other, respond to what others said, maintain topic coherence, and produce natural turn-taking? Or did they each post standalone opinions in a vacuum?

Each role evaluates group fidelity through its own lens:

| Role | Group fidelity question |
|---|---|
| `general` | Did the agents engage with each other across all dimensions? |
| `style` | Did communication registers and tone adapt to and build on each other? |
| `ideology` | Did ideological alignments and tensions get actively navigated between agents? |
| `behavioral` | Did turn-taking, responsiveness, and social positioning reflect real group behavior? |

The judge reads the conversation in **chronological order** and scores qualitatively on a 1–5 scale. No persona profiles or true identities are passed — group dynamics are observable from the anonymised transcript alone.

> Note: this LLM-judged `group_fidelity_score` is distinct from the **computed** group-fidelity metrics (Gini on the turn distribution, cosine distance matrix) produced by `eval/metrics_group.py` and shown on the dashboard. The two are complementary: the computed metrics capture structural balance objectively; the judge scores capture qualitative social coherence.

---

## Design: dedicated templates + dedicated call

### New templates — `group_fidelity_{role}.j2` (all 4)

`angry_agents/src/agents/judges/templates/group_fidelity_{style,ideology,general,behavioral}.j2`

Each template accepts two variables: `topic` (optional) and `conversation_block`.

`conversation_block` is the full conversation in chronological order (`[author_digest]: message`), built by `_format_conversation()`. Chronological order (distinct from `format_messages()`, which groups by author) is required so the judge can observe who responded to whom, turn-taking patterns, and conversational flow.

Each template returns exactly one key, with a **role-specific** rubric:
```json
{ "group_fidelity_score": <1-5> }
```

All rubrics share the same 1–5 scale anchored at:
- 5 = coherent, responsive, naturally flowing group
- 1 = disconnected agents, ignored messages, no group dynamic

### `judge_with_tools.py`

**`run_group_fidelity_with_tools(role, chat, ...)` (new):**
- Builds the chronological `conversation_block` via `_format_conversation(chat)` and extracts `topic` from `chat`
- Renders the role's `group_fidelity_*.j2` template
- Makes one `_openai_simple_call` with `call_type="group_fidelity"` (recorded in the token tracker)
- Extracts `group_fidelity_score`; defaults to 3 with a warning if missing or out of range
- Returns `int`

**`_openai_simple_call`:** gained a `call_type` parameter (default `"individual_fidelity"`) so fidelity and group-fidelity calls are tracked separately.

**`run_persona_identification_with_tools`:**
- Removed the `gini_data` parameter and the dead Gini template injection
- Removed `group_fidelity_score` extraction from the response
- Return type changed from `tuple[PersonaIdentificationResult, int]` to `PersonaIdentificationResult`

The persona ID templates (`persona_id_*_batch.j2`) and individual fidelity templates (`individual_fidelity_*.j2`) are each single-concern: persona ID returns only `assignment`; individual fidelity returns only `individual_fidelity`.

### `evaluation_test_20_judges.py`

- `run_evaluation_from_db_data` lost its `gini_data` parameter.
- Both `_run_judge` closures now call group fidelity as a separate step:
  ```python
  result = run_persona_identification_with_tools(...)
  gf_score = run_group_fidelity_with_tools(role=judge["role"], chat=chat, judge_name=judge["name"], tracker=tracker)
  ```
- `gf_score` is now always computed (it no longer depends on `author_map`).

### `angry_agents/src/API/routes/ui_routes.py`

- Removed `gini_data=gini_data` from the `run_evaluation_from_db_data` call (parameter no longer exists).
- The structural Gini metric is still computed (`metrics_group.run`) for the dashboard report — it is just no longer injected into judge prompts.

---

## Call Count Impact

Group fidelity now adds **one extra LLM call per judge** (20 total): a small call carrying only the chronological transcript (~1,500 tokens) and returning a single integer.

| Call type | Count | Notes |
|---|---|---|
| `main` | 20 | Persona identification (+ RAG `tool_followup` calls) |
| `group_fidelity` | 20 | New dedicated group fidelity call |
| `individual_fidelity` | 20 | Only when a ground-truth `author_map` is provided |

The extra call is cheap because it carries no persona profiles — only the transcript. Trade-off vs. the old folded-in approach: a modest token increase in exchange for clean lens separation and no cross-task anchoring.
