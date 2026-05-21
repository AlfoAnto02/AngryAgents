# Evaluation Design: Open Questions and Trade-off Analysis

**Project:** Multi-Agent Persona Evaluation System  
**Document type:** Design discussion
**Date:** May 2026  

---

## Overview

This document formalises three open design questions that emerged during the definition of the evaluation pipeline for the multi-agent persona system. Each question concerns a specific methodological choice in the persona identification and fidelity measurement protocol. The decisions are interdependent: the answer to one question directly constrains the feasible options for the others.

---

## 1. Candidate Set Size for Persona Identification

### Problem Statement

The persona identification task asks judge-agents to map anonymous author tags to known persona names. The statistical properties of this task — in particular the random-guess baseline against which judge accuracy is compared — depend directly on how many candidate personas are shown to each judge. Three design options are available.

### Option A — Closed Set (K = 8)

Each judge receives exactly the eight author tags present in the conversation and the eight persona names present in the system. The task is a forced bijection: every tag must be assigned to exactly one persona, and every persona must be used exactly once.

The random baseline under this design is:

\[ P(\text{correct}) = \frac{1}{8} = 12.5\% \]

This baseline is the null hypothesis for the one-sided binomial exact test (Clopper-Pearson):

\[ H_0: p = 0.125, \quad H_1: p > 0.125 \]

**Advantages:** the statistical framework is clean. A single binomial test with a well-defined null hypothesis applies directly, and the 8×8 confusion matrix chi-square test is fully interpretable.

**Disadvantages:** the forced-choice structure is ecologically invalid. In a real evaluation scenario a rater would not know a priori that exactly the eight personas in the chat are the only possible authors. The constraint artificially elevates accuracy by eliminating the possibility of assigning a tag to an agent not present in the conversation.

### Option B — Expanded Set (K > 8, fixed)

Each judge receives K candidate personas, where K > 8. The additional K − 8 personas are drawn randomly from the full agent database and serve as decoys. The judge must identify which eight of the K candidates are actually present in the conversation.

For a fixed K, the per-tag random baseline becomes:

\[ P(\text{correct per tag}) = \frac{1}{K} \]

For example, with K = 16: \( P = 1/16 = 6.25\% \). The lower baseline makes it harder to reach statistical significance at a fixed accuracy level, but the task itself is harder, so raw accuracy will also decrease. The binomial test and confusion matrix remain applicable; only the null hypothesis value changes.

**Advantages:** more realistic than the closed set — judges cannot rely on process of elimination. A fixed K keeps the statistical framework stable across evaluation runs.

**Disadvantages:** choosing the value of K introduces an additional free parameter. Larger K reduces statistical power for a fixed number of judges; smaller K approaches the unrealistic closed-set regime.

### Option C — Full Database (K = N)

Each judge receives all N agents in the database as candidates and must identify the eight present in the conversation from scratch.

The random baseline approaches zero as N grows:

\[ P(\text{correct set}) \approx \frac{1}{\binom{N}{8}} \]

This is the most ecologically valid design, but it is operationally impractical: the number of possible assignments grows combinatorially with N, making the task cognitively overloading for both human and LLM judges. Prompt length scales linearly with N, and inference cost becomes prohibitive.

### Comparative Summary

| | Option A (K = 8) | Option B (K = 16) | Option C (K = N) |
|---|---|---|---|
| Random baseline | 12.5% | 6.25% | ≈ 0% |
| Task difficulty | Low | Medium | Very high |
| Statistical tractability | High | High | Low |
| Ecological validity | Low | Medium | High |
| Token cost | Low | Medium | Prohibitive |

---

## 2. Identification Response Format

### Problem Statement

Once a judge has read the conversation, the question is how the identification response should be structured. Two formats are possible: a direct hard guess or a fidelity-scored ranking over all candidates.

### Option A — Hard Point Guess

The judge assigns each anonymous tag directly to one persona name. The response is a one-to-one mapping with no confidence scores or rankings.

The evaluation metric is binary accuracy per tag:

\[ \text{accuracy} = \frac{\text{correct guesses}}{n_{\text{total guesses}}} \]

Token cost scales as \( O(1) \) per tag. The binomial exact test and confusion matrix apply directly.

**Advantages:** minimal prompt complexity, low token cost, clean binary metric.

**Disadvantages:** all incorrect guesses are treated as equivalent regardless of how close the judge was to the correct answer. A judge who ranked the correct persona second is indistinguishable from one who ranked it last. This discards potentially useful partial-credit signal.

### Option B — Fidelity-Scored Ranking

For each anonymous tag, the judge scores every candidate persona in the candidate set on fidelity (1–5). The persona with the highest score becomes the hard guess (argmax), but the full ranked list is also recorded.

\[ \text{guess}(tag_i) = \arg\max_{j \in K} \, \text{score}(tag_i, \, \text{persona}_j) \]

Token cost scales as \( O(K) \) per tag. With K = 16 candidates and 8 tags per conversation, each judge produces 128 individual fidelity scores per evaluation run. Across 20 judges, this represents a significant increase in total token budget.

The ranked output enables richer metrics beyond binary accuracy: Spearman rank correlation between predicted and true ranking, and normalised discounted cumulative gain (NDCG) treating the correct persona as the single relevant item.

**Advantages:** partial-credit signal is preserved. The ranked list reveals systematic confusion patterns that the confusion matrix alone cannot capture. The argmax guess is directly comparable to Option A's output, so no metric changes are required for the identification accuracy computation.

**Disadvantages:** prompt complexity grows substantially. The judge must evaluate all K candidates per tag, which introduces cross-candidate anchoring and may reduce the quality of individual scores. Token cost scales with K, creating a direct dependency on the candidate set size decision (Section 1).

### Interaction with Candidate Set Size

The cost of Option B is directly coupled to the candidate set size K chosen in Section 1. This coupling is non-trivial:

| K | Scores per judge per conversation | Total scores (20 judges) |
|---|---|---|
| 8 (closed) | 64 | 1,280 |
| 16 (expanded) | 128 | 2,560 |
| N (full DB) | 8N | Prohibitive |

Option B is therefore only operationally viable in combination with Option A or Option B from Section 1 (bounded K). Combining Option B here with the full-database candidate set (Section 1, Option C) is computationally infeasible.

### Comparative Summary

| | Option A (Hard Guess) | Option B (Scored Ranking) |
|---|---|---|
| Token cost | O(1) per tag | O(K) per tag |
| Metric richness | Binary accuracy only | Accuracy + Spearman ρ + NDCG |
| Partial-credit signal | None | Present |
| Prompt complexity | Low | High |
| K dependency | None | Strong |

---

## 3. Individual Fidelity Measurement Protocol

### Problem Statement

Individual fidelity measures how convincingly each agent portrays its assigned persona, rated on a 1–5 Likert scale by judge-agents. The open question is whether the agents responsible for persona identification (Phase 1 blind guessing) should also produce fidelity scores, or whether these two tasks should be assigned to separate judge pools with separate prompts.

### Option A — Sequential Design (Single Pool)

The same 20 judge-agents perform both tasks in sequence. In Phase 1, each judge reads the anonymised conversation and submits a persona identification guess. In Phase 2, the correct author map is revealed to the judge, who then scores each agent on fidelity (1–5) based on retrospective knowledge of the correct identity.

**Advantages:** a single judge pool reduces operational cost. The same judge who performed the identification task carries implicit context into the fidelity scoring step, potentially producing more informed ratings.

**Disadvantages:** revealing the correct answer before fidelity scoring introduces **anchoring bias**. A judge who guessed incorrectly may adjust their fidelity ratings upward or downward to rationalise the revealed answer rather than rating the actual quality of the persona portrayal. This conflates the identification signal with the fidelity signal, producing scores that are correlated with the judge's own identification accuracy rather than with the agent's true character consistency. Additionally, a single prompt that serves both tasks is necessarily longer and more ambiguous than a purpose-built prompt for each task individually.

### Option B — Parallel Design (Dedicated Pools)

Two judge pools with separate prompts are used concurrently.

- **Pool 1** (20 judges): blind identification only. The prompt is designed exclusively to elicit persona guesses. Judges in Pool 1 never learn the correct author map.
- **Pool 2** (N judges): persona descriptions are provided from the outset. Judges in Pool 2 score each agent on fidelity (1–5) without performing any identification task. The prompt is designed exclusively to elicit fidelity ratings against the known persona profile.

**Advantages:** prompt specificity is maximised — each pool receives a minimal, purpose-built prompt. Anchoring bias is eliminated because Pool 2 judges never performed a blind guess and therefore have no prior prediction to rationalise. The two evaluation dimensions remain statistically independent. Pool 2 can use the existing four judge types (`style`, `ideology`, `general`, `behavioral`) without modification.

**Disadvantages:** two separate inference runs increase total token cost. Pool 2 requires additional judge instantiation overhead.

### Comparative Summary

| | Option A (Sequential) | Option B (Parallel) |
|---|---|---|
| Judge pools | 1 (20 judges) | 2 (Pool 1: 20, Pool 2: 12–20) |
| Anchoring bias | Present | Absent |
| Prompt specificity | Low (dual-purpose) | High (single-purpose each) |
| Statistical independence | No (ID and fidelity correlated) | Yes |
| Total cost | Lower | Moderately higher |
| Signal validity | Lower | Higher |

---

## 4. Interdependency Map

The three design decisions above are not independent. The table below summarises which combinations are feasible and which create operational or statistical conflicts.

| Section 1 (K) | Section 2 (Pool design) | Section 3 (Response format) | Feasibility |
|---|---|---|---|
| Closed (K = 8) | Sequential | Hard guess | ✓ Feasible, lowest cost |
| Closed (K = 8) | Sequential | Scored ranking | ✓ Feasible, moderate cost |
| Expanded (K = 16) | Parallel | Hard guess | ✓ Recommended combination |
| Expanded (K = 16) | Parallel | Scored ranking | ✓ Feasible, higher cost |
| Full DB (K = N) | Parallel | Hard guess | ⚠ Feasible only if N is small |
| Full DB (K = N) | Any | Scored ranking | ✗ Prohibitive token cost |
| Any | Sequential | Scored ranking | ⚠ Anchoring bias compounds |

The recommended baseline configuration — pending supervisor feedback — is **K = 16 (Option B, Section 1)** combined with **parallel dedicated pools (Option B, Section 3)** and **hard point guess (Option A, Section 2)**. This combination maximises construct validity and prompt specificity while keeping token costs manageable and the statistical framework tractable.

---