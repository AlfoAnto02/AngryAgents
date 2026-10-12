# Batch Evaluation — How It Works

## What problem does this solve?

The per-chat evaluation pipeline (`report.py`) already produces a `metrics_report.json`
for every individual chat: it tells you accuracy, fidelity, and Gini for *that one chat*.
But a single chat is a noisy measurement. What you really want to know is:

- **On average**, how well do judges identify personas across many chats?
- How much does accuracy **vary** from chat to chat?
- Are those differences meaningful or just random noise?

The batch pipeline answers those questions by aggregating per-chat results into a single
report with cross-chat statistics and confidence intervals.

---

## The two-step structure

```
Per-chat pipeline (already exists)
  simulate_transcript → judge 20 judges → report.py
       └─ writes: data/eval/chat_<id>/metrics_report.json

Batch pipeline (this feature)
  batch.py
       └─ reads all chat_<id>/metrics_report.json
       └─ aggregates with metrics_batch.py
       └─ writes: data/eval/batch_report.json
```

The batch pipeline is **read-only with respect to individual chats** — it never
re-runs judging, never touches the DB. It just reads what `report.py` already saved.

---

## Step 1 — Discovering reports (`discover_reports`)

`batch.py` scans the base directory for folders named `chat_<number>` and checks
whether each one contains a `metrics_report.json`. Folders that don't match the
pattern (or are missing the file) are silently skipped.

You can also pass `--chats 1,2,5,7` to restrict aggregation to specific chat IDs.

---

## Step 2 — Extracting scalars (`_extract`)

From each `metrics_report.json`, the batch pipeline pulls out exactly four numbers:

| Field | Where it comes from |
|---|---|
| `accuracy` | `persona_identification.aggregate.accuracy` |
| `fidelity_median` | `individual_fidelity.aggregate.median` |
| `gini` | `group_fidelity.gini.gini` |
| confusion matrix | `persona_identification.confusion_matrix` |

It also pulls the **per-persona fidelity medians** (one per persona per chat) for
finer-grained analysis.

If a report is malformed or missing any of these keys, that chat is skipped with
a warning — the batch continues with the remaining ones.

---

## Step 3 — Aggregating statistics (`metrics_batch.py`)

For each of the scalar metrics (accuracy, fidelity, Gini), the batch pipeline
computes:

- **mean** across chats
- **variance** and **standard deviation** across chats
- **95% confidence interval** on the mean

The confidence interval method depends on how many chats you have.

### Confidence interval: bootstrap vs. CLT

The central question is: *how reliable is our estimate of the mean accuracy?*
The answer depends on sample size.

#### When n < 20 chats → Bootstrap

Bootstrap resampling is used. The idea is simple:

1. Take your list of n accuracy values.
2. Randomly draw n values from it **with replacement** (some will appear more than
   once, some not at all). This is one "resample".
3. Compute the mean of that resample.
4. Repeat 10,000 times.
5. The 95% CI is the 2.5th and 97.5th percentiles of those 10,000 means.

This makes **no assumptions** about the distribution of accuracies. It works even
if the distribution is skewed or weird — which is likely when you only have a handful
of chats.

The `bootstrap_ci()` function in `bootstrap.py` does the resampling. It already
existed before this feature (used for per-chat Gini and Spearman CIs); batch eval
just reuses it.

#### When n ≥ 20 chats → CLT (normal approximation)

With enough chats, the Central Limit Theorem tells us that the sampling distribution
of the mean is approximately normal, regardless of what the underlying distribution
looks like. The CI becomes:

```
CI = mean ± 1.96 × (std / sqrt(n))
```

where `std` is the standard deviation of the per-chat values and `1.96` corresponds
to the 95% level of a normal distribution.

This is cheaper to compute and easier to reason about. The trade-off: it can be
slightly inaccurate for small n (especially if the distribution is skewed), which
is why we fall back to bootstrap below the threshold.

**Why 20 as the threshold?**
For bounded metrics like accuracy [0, 1] or fidelity [1, 5], the distribution of
per-chat values is rarely extremely skewed. The normal approximation holds reasonably
well at n=20 for these kinds of metrics. A more conservative choice would be n=30
(the textbook CLT rule of thumb), but 20 is a practical compromise.

> **Note:** If you ever want to *compare two batches* (e.g., chats on topic A vs.
> topic B), the threshold for a two-sample test should be raised to 30.
> That is not implemented yet — the note is in the code as a comment.

---

## Step 4 — Pooling confusion matrices

Each chat produces an 8×8 confusion matrix: rows are the true persona, columns
are what judges predicted. The batch pipeline sums these matrices element-wise
to get a **pooled confusion matrix** across all chats.

From the pooled matrix, it recomputes:

- **Per-persona precision, recall, F1** (one-vs-rest)
- **Macro F1** (mean F1 across all personas)
- **Cohen's Kappa** (agreement corrected for chance)

The pooled matrix is more stable than any individual chat's matrix because it
has more total observations. It answers questions like: "Which persona do judges
consistently confuse with which other persona?"

If different chats involve different sets of personas (or use different labels),
the pool takes the **union** of all labels and zero-fills missing entries.

---

## Output format (`batch_report.json`)

```json
{
  "n_chats": 12,
  "chat_ids": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],

  "accuracy": {
    "n": 12,
    "mean": 0.4125,
    "variance": 0.0184,
    "std": 0.1356,
    "ci_95": [0.3359, 0.4891],
    "method": "bootstrap"
  },

  "fidelity_median": {
    "n": 12,
    "mean": 3.82,
    "variance": 0.1764,
    "std": 0.42,
    "ci_95": [3.58, 4.06],
    "method": "bootstrap"
  },

  "gini": {
    "n": 12,
    "mean": 0.341,
    "variance": 0.0039,
    "std": 0.0624,
    "ci_95": [0.306, 0.376],
    "method": "bootstrap"
  },

  "per_persona_fidelity": {
    "PersonaA": {
      "n": 12, "mean": 3.9, "variance": 0.2, "std": 0.45,
      "ci_95": [3.6, 4.2], "method": "bootstrap"
    }
  },

  "pooled_confusion_matrix": {
    "labels": ["PersonaA", "PersonaB", "..."],
    "matrix": [[...], [...]],
    "per_persona": {
      "PersonaA": {"precision": 0.52, "recall": 0.48, "f1": 0.50}
    },
    "macro_f1": 0.49,
    "kappa": 0.34
  }
}
```

Every scalar block carries `"method": "bootstrap"` or `"method": "clt"` so you
always know which path was taken.

---

## How to run it

```bash
# Aggregate all chats found under data/eval/
.venv/bin/python -m angry_agents.src.eval.batch --base-dir data/eval/

# Only specific chats
.venv/bin/python -m angry_agents.src.eval.batch --base-dir data/eval/ --chats 1,2,5,7

# Custom output path
.venv/bin/python -m angry_agents.src.eval.batch \
    --base-dir data/eval/ \
    --out results/batch_report.json
```

The script prints a short summary to stdout:

```
Batch report: 12 chats → data/eval/batch_report.json
  Accuracy  : mean=41.2%  std=0.136  CI=[0.3359, 0.4891]  [bootstrap]
  Fidelity  : mean=3.82   std=0.420  CI=[3.58, 4.06]  [bootstrap]
  Gini      : mean=0.341  std=0.062  CI=[0.306, 0.376]  [bootstrap]
```

---

## Prerequisites

Each chat must already have a `metrics_report.json`. These are produced by the
judging pipeline (triggered through the UI) or manually via:

```bash
.venv/bin/python -m angry_agents.src.eval.report \
    --eval-dir data/eval/chat_<id>/ \
    --judge-evals data/eval/chat_<id>/judge_evals.jsonl \
    --personas-dir data/personas/
```

The batch script never re-runs judging — it only reads what is already saved.

---

## File map

| File | Role |
|---|---|
| `angry_agents/src/eval/metrics_batch.py` | Pure aggregation functions (no I/O) |
| `angry_agents/src/eval/batch.py` | Discovery, loading, orchestration, CLI |
| `angry_agents/src/eval/bootstrap.py` | `bootstrap_ci()` — reused by both per-chat and batch eval |
| `angry_agents/src/eval/report.py` | Per-chat eval — prerequisite for batch |
| `angry_agents/tests/eval/test_batch.py` | Unit + integration tests (no DB needed) |
