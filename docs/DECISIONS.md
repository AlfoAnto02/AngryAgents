# How Angry Agents evolved: key decisions

The project did not follow a fixed plan. Each week surfaced a problem that reshaped earlier work. This page lists the decisions that defined the final system: what triggered each one, what was chosen, and what it changed. Every entry links to the document or note where the decision was originally recorded.

Sources: the "Project Evolution" section of the [technical report](report/report.pdf), the [sprint notes](sprints/) and the [process documents](process/).

## Timeline

| # | When | Decision | Measured effect |
|---|---|---|---|
| 1 | May 5–13 | Anonymize message authors at the schema level | Judges cannot link a message to a persona, even by accident |
| 2 | May 14–24 | Merge fiction and real-world context tables into one | One profile format for every persona |
| 3 | May 14–24 | Move all prompts into Jinja2 templates | Prompts versioned and reviewed like code |
| 4 | May 19–25 | Run the 20 judges in parallel instead of in a loop | Lower judging cost and wall-clock time |
| 5 | May 25–27 | RAG pre-filtering of candidate personas | ~2,000 → ~80 LLM calls per run (−97%); 33 min → ~30 s |
| 6 | May 25–27 | Hungarian algorithm instead of greedy argmax | Persona-ID accuracy no longer inflated |
| 7 | May 25–27 | Two-stage persona extraction | 80 personas extracted for $0.57 (1.19M tokens) |
| 8 | May 25–31 | MCP server with preview → confirm writes | An AI assistant can drive the app, but every write needs the user's approval |
| 9 | May 28–31 | Batch evaluation across chats | Confidence intervals across chats, not just per chat |
| 10 | Jun 1–3 | DB v4: structured judge results | Judge output became queryable for the dashboards |
| 11 | Jun 1–3 | Direct 1:1 assignment for persona ID (dropped 1–5 scores) | Removed a noisy intermediate step |
| 12 | Jun 1–3 | Dynamic RAG candidate pool | Shortlist scales with the number of participants |
| 13 | Jun 1–3 | Group fidelity as its own LLM call | Clean separation between judging concerns |
| 14 | Jun 1–3 | RAG tool only called when needed | Less latency, no loss of accuracy |
| 15 | Jun 1–3 | Phase 2 deliberation dropped | Scope cut to ship a complete, measured Phase 1 |
| 16 | Jun 1–3 | Stay on `gpt-4o-mini` | GPT-5 gave ~+63 accuracy points at ~17× the cost |

---

## 1. Author anonymity enforced by the schema

**Context.** The evaluation is only meaningful if judges cannot know which agent wrote which message. Jiang et al. (2024) showed that raters who know they are reading AI output underestimate persona fidelity ([SOTA](process/02_SOTA.md)).
**Decision.** `Chat_messages.author` stores an HMAC-SHA256 digest of the agent's identity, with **no foreign key** back to `Agents`.
**Result.** Anonymity holds even if application code is wrong: there is nothing to join on. This decision survived every later schema version ([DB v4](architecture/DB_v4.md)).

## 2. One context table for every persona

**Context.** The first schema had separate context tables for fiction and podcast personas ([problem definition](process/01_NEW_PROBLEM.md)). As profiles became richer, both types needed the same structured JSON.
**Decision.** A single `Agent_context` table holds the structured profile for both persona types. A `User` table, JWT authentication and soft-delete timestamps were added in the same phase.
**Result.** One extraction format and one runtime path for every persona.

## 3. Prompts as templates, not Python strings

**Context.** Judge and persona prompts were embedded in Python code and hard to review ([first judge guide](process/06_judge_system_guide.md)).
**Decision.** All prompts moved to Jinja2 `.j2` templates. Every judge template requires motivation before the rating, a fixed rubric and JSON output.
**Result.** Prompt changes are versioned diffs. Later decisions (#11, #13, #14) were template edits rather than code rewrites.

## 4. Parallel judges

**Context.** The first 20-judge implementation looped over judges and was expensive ([sprint 3, Alfonso](sprints/sprint-3-alfonso.md)).
**Decision.** The 20 judge calls run in parallel, and the judge output became a JSON report aligned with the RAG system.
**Result.** Lower cost and wall-clock time per evaluation, and the groundwork for #5.

## 5. RAG pre-filtering: the scalability fix

**Context.** Three judges evaluating a 40-message chat with seven personas already hit the 120-second timeout. The full design called for 20 judges against 100+ personas, so every judge was comparing against the whole database.
**Decision.** Persona profiles are split into typed semantic chunks, embedded with `text-embedding-3-small` and stored in ChromaDB. Before judging, each judge retrieves a shortlist ranked by field-weighted similarity and re-ranked with MMR, so no single "attractor" persona dominates ([RAG explanation](../angry_agents/src/rag/RAG_EXPLANATION.md)).
**Result.** **~2,000 → ~80 LLM calls per run (−97%)**, and latency dropped **from 33 minutes to about 30 seconds**.

## 6. Hungarian assignment for persona identification

**Context.** The greedy argmax could assign the same author to several personas. One very distinctive author could "win" multiple slots and inflate accuracy.
**Decision.** Use `scipy.optimize.linear_sum_assignment` (the Hungarian algorithm) to force a one-to-one mapping between authors and personas ([sprint 4, Alfonso](sprints/sprint-4-alfonso.md)).
**Result.** Accuracy figures became valid. Without this fix, the headline metric would have been wrong.

## 7. Two-stage persona extraction

**Context.** Transcripts alone missed widely known catchphrases and verbal tics that rarely appear in any single source.
**Decision.** Pass 1 uses `gpt-4o-mini` over the full transcript to ground behaviour in observed speech. Pass 2 uses `gpt-4o` with no transcript to add model-knowledge fields (`favored_words`, `structural_patterns`, `do_not_say`). Any entry that a similar persona could also have said is discarded ([sprint 4, Gabriele](sprints/sprint-4-gabriele.md)).
**Result.** 80 personas extracted for **$0.57** in total.

## 8. MCP with a confirmation boundary

**Context.** We wanted an AI assistant to operate the platform (create chats, post messages, launch judging) without letting it change data unsupervised. The first draft was a tool manifest with two permission tiers ([tool manifest v1](process/05_tools_managementv1.md)).
**Decision.** A FastMCP server with 14 read tools and 5 write actions. Each write action is a `preview_*` / `confirm_*` pair. Listing agents was trimmed from ~575 kB to ~5 kB after it overflowed the model's context ([sprint 4, Kevin](sprints/sprint-4-kevin.md)).
**Result.** 6 demo DM chats with 60 messages were generated from Claude Code in about 8 minutes ([MCP session log](process/09_report_mcp.md)).

## 9. Batch evaluation

**Context.** One chat is a noisy measurement.
**Decision.** Aggregate across chats: bootstrap confidence intervals below 20 chats, CLT normal approximation from 20 upwards ([EVAL_BATCH](architecture/EVAL_BATCH.md)).
**Result.** The final results (51.1% persona-ID accuracy, 95% CI 42.3–60.0%) come from 21 chats.

## 10. DB v4: structured judge results

**Context.** The first end-to-end run showed that a single opaque `Score` column could not hold what judges actually produce.
**Decision.** `Judge_evaluation` gained `persona_identification`, `rag_candidates` and `group_fidelity_score`. `Group_chat` gained `status`, `author_map`, `speaker_stats`, `is_judged` and `report` ([DB v4](architecture/DB_v4.md)).
**Result.** The admin dashboards query judge results directly.

## 11. Direct assignment instead of 1–5 identification scores

**Context.** Judges first scored every author against every candidate on a 1–5 scale, and the matrix was then resolved. This was one of the options analysed in the [evaluation design questions](process/07_evaluation_design_open_questions.md).
**Decision.** Judges assign each author directly to one persona. The Hungarian step is applied when votes are aggregated ([sprint 5, Alfonso](sprints/sprint-5-alfonso.md)).
**Result.** Empirical testing showed the 1–5 step added noise without improving accuracy.

## 12. Dynamic candidate pool

**Context.** A fixed shortlist size is too large for small chats and too small for large ones. The design doc compared fixed K = 8, K = 16 and the full database ([evaluation design questions](process/07_evaluation_design_open_questions.md)).
**Decision.** The shortlist size is `max(n + 1, ⌊2.5·n⌋)`, where `n` is the number of participants, and it always includes semantic distractors.
**Result.** The difficulty of the task stays proportional to the chat size.

## 13. Group fidelity as a dedicated call

**Context.** Group fidelity was a second output of the persona-ID call, so one prompt did two unrelated jobs, and all four judge lenses used the same rubric ([refactor record](process/08_GROUP_FIDELITY_REFACTOR.md)).
**Decision.** Each judge makes one extra small call with a role-specific `group_fidelity_{role}.j2` template that reads the chat in chronological order.
**Result.** One extra cheap call per judge (transcript only, no profiles), in exchange for no cross-task anchoring.

## 14. Calibrated RAG tool usage

**Context.** Judges called the RAG search tool unconditionally. Testing showed it added latency without improving accuracy for well-represented personas.
**Decision.** Templates invoke the tool only when no shortlisted candidate clearly matches through the judge's lens.
**Result.** Lower latency with no loss of accuracy.

## 15. Phase 2 deliberation dropped

**Context.** The original design had judges deliberate on high-variance cases over 3–5 rounds ([experimentation plan](process/03_EXPERIMENTATION.md)). It was designed but never executed.
**Decision.** Removed from the pipeline, the metrics and the UI in the final week ([sprint 5, Kevin](sprints/sprint-5-kevin.md)). The design is kept as future work.
**Result.** A complete, measured Phase 1 shipped on time instead of two half-finished phases.

## 16. Model choice as a cost/quality trade-off

**Context.** Results with `gpt-4o-mini` varied a lot between chats.
**Experiment.** Three chats were re-run with GPT-5.
**Result.** Accuracy rose by about 63 points on average (in one case from 14.4% to 94.4%), at roughly 17× the cost. `gpt-4o-mini` stayed the default, in line with the project's cost-driven principle. This trade-off is reported rather than hidden.

---

## Open after the project

These came out of the decisions above and are listed in the [README](../README.md#limitations-and-future-work): an operational definition of behavioural fidelity, quality for personas with sparse source material, the optimal conversation length, MCP authentication, and the deliberation phase.
