# How Angry Agents Evaluation Works

### Perturbation — Preventing Groupthink

Every N turns for a given agent (N is randomized between 10 and 15 per agent), the system injects a **perturbation** into that agent's system prompt only. The other agents don't see it. It looks like:

> "The conversation is moving toward consensus. React in a way that reflects your genuine position, even if it means disagreeing..."

This forces character-consistent friction and prevents all agents from converging into generic agreement.

### Drift Detection (optional)

If an embedding model is enabled, after each turn the system computes the pairwise **cosine similarity** across all agents' last-turn message embeddings:

```
drift_score = mean of cosine_sim(agent_i_last_msg, agent_j_last_msg) for all pairs i ≠ j
```

If `drift_score > threshold` (default 0.85), agents are sounding too similar — a perturbation fires early regardless of the N-turn schedule.

---

## Step 1 — Persona Identification (`metrics_persona_id.py`)

**Question:** Can judges correctly guess which anonymous author tag corresponds to which persona?

There are 8 personas and 8 author tags. Random guessing would be right 1/8 = **12.5%** of the time. That's the baseline.

### Accuracy

For each judge, for each persona, we check: did the judge's predicted author tag match the true author tag?

```
accuracy = number of correct guesses / total guesses
```

This is computed per judge and also aggregated across all judges.

### Variance Across Judges

Each judge gets a per-judge accuracy (score from 0 to 1, with 8 guesses each). We compute variance and std across those 20 per-judge accuracies:

```
mean_acc   = Σ accuracy_j / 20
variance   = Σ (accuracy_j - mean_acc)² / (20 - 1)   [sample variance, ddof=1]
std        = sqrt(variance)
```

This is separate from the binomial CI: variance tells you how much judges *disagree with each other* on the task difficulty. High variance = some judges identified personas well, others failed — the task is inconsistently hard or some judges are outliers. Low variance = all judges performed similarly.

### Binomial Exact Confidence Interval

We use a **binomial exact test** (Clopper-Pearson method) to build a 95% confidence interval around the aggregate accuracy.

If judges got `k` correct out of `n` total guesses, the CI is computed via `scipy.stats.binomtest`:

```
H₀: true accuracy = 1/8 = 0.125
alternative: true accuracy > 0.125 (one-sided)
```

If `p-value < 0.05`, we reject H₀ and conclude judges are doing better than random.

### Confusion Matrix

We build an 8×8 matrix where entry `[i][j]` = how many times the true persona was `i` but the judge predicted `j`. The diagonal = correct guesses, off-diagonal = mistakes.

### Precision, Recall, F1 (per persona)

For each persona `i`, treating it as the positive class vs all others:

```
Precision(i) = TP_i / (TP_i + FP_i)
```
Of all times judges predicted persona `i`, how many were actually persona `i`.

```
Recall(i) = TP_i / (TP_i + FN_i)
```
Of all times the true persona was `i`, how many did judges correctly identify.

```
F1(i) = 2 × Precision(i) × Recall(i) / (Precision(i) + Recall(i))
```
Harmonic mean of Precision and Recall. Penalizes large gaps between the two.

We report **macro F1** (unweighted average across all 8 personas) as the aggregate score. This treats every persona equally regardless of how often it appeared.

### Cohen's Kappa (κ)

Accuracy alone is misleading — a judge who guesses randomly still gets ~12.5% correct. Cohen's Kappa corrects for chance agreement:

```
κ = (p_o - p_e) / (1 - p_e)
```

- **`p_o`** (observed agreement) = fraction of guesses where the judge's prediction matched the true persona = raw accuracy.
- **`p_e`** (expected agreement by chance) = probability that judge and ground truth would agree even if the judge guessed randomly, computed from the marginal distributions of predicted labels and true labels:

```
p_e = Σ_i (n_predicted_i / n) × (n_true_i / n)
```

Where `n_predicted_i` = how many times judges predicted persona `i`, `n_true_i` = how many times persona `i` was the true answer, and `n` = total guesses. If all personas appear equally (ideal case), `p_e = 1/8 = 0.125`.

Interpretation:

| κ | Agreement |
|---|---|
| < 0.2 | Poor |
| 0.2–0.4 | Fair |
| 0.4–0.6 | Moderate |
| 0.6–0.8 | Good |
| > 0.8 | Excellent |

κ = 0 means judges perform exactly at chance. κ = 1 means perfect identification. Negative κ means worse than random.

---

## Step 2 — Individual Fidelity (`metrics_fidelity.py`)

**Question:** For each persona, how convincingly did the agent portray that character? Judges give scores from 1 to 5.

The "true fidelity" score for a persona is the score a judge assigned to the **real author** of that persona (not the author the judge guessed — the actual one, resolved via `author_map`).

### Statistics per Persona

For each persona, across all judges and judge types, we compute:

```
median(scores)
IQR = Q3 - Q1 = 75th percentile - 25th percentile
variance = sum((x - mean)²) / (n - 1)   [sample variance, ddof=1]
std = sqrt(variance)
```

We report both **mean** and **median**. Mean is sensitive to outliers (one judge giving 1 drags it down); median is robust to them. For ordinal scores (1–5) with potentially skewed distributions, median is the primary measure — mean is reported for completeness.

**IQR** (Interquartile Range) = Q3 − Q1, where Q1 = 25th percentile and Q3 = 75th percentile of the scores. It captures the spread of the middle 50% of judges, ignoring extreme outliers. Small IQR = judges agreed. Large IQR = judges split.

### Bootstrap 95% CI on the Median

Because the median doesn't have a simple formula for confidence intervals, we use **non-parametric bootstrapping**:

1. Resample the scores with replacement 10,000 times
2. Compute the median of each resample
3. The 2.5th and 97.5th percentiles of those 10,000 medians = the 95% CI

```
CI = [percentile(bootstrap_medians, 2.5%), percentile(bootstrap_medians, 97.5%)]
```

This works even with small sample sizes and makes no assumption about the distribution shape.

### Judge Type Agreement

There are 4 judge types: `style`, `ideology`, `general`, `behavioral`. We check whether different judge types agree with each other using **Mean Absolute Deviation (MAD)** between their median scores:

```
MAD(style, ideology) = |median_score_style - median_score_ideology|
```

Lower MAD = more agreement between those two judge types. This is computed for every pair of judge types.

We also report the **mean score per judge type** across all personas:

```
mean_type = Σ scores_assigned_by_that_type / n_scores
```

This reveals systematic bias: if `style` judges consistently average 2.1 while `general` judges average 3.8, those two types are not measuring the same thing — or one type applies a harsher standard. MAD on medians tells you if they *disagree on a specific persona*; mean per type tells you if they *disagree on scale* across the board.

---

## Step 3 — Group Fidelity (`metrics_group.py`)

**Question:** Does the group chat look like a real group chat, in terms of turn distribution and topic diversity?

### Gini Coefficient

The Gini coefficient measures inequality in how many turns each agent took. It comes from economics (income inequality) but works perfectly here:

```
Gini = (2 × Σ(i × turn_count_i)) / (n × total_turns) - (n + 1) / n
```

Where the turn counts are sorted in ascending order and `i` goes from 1 to n.

- `Gini = 0` → all agents spoke equally
- `Gini = 1` → one agent spoke all turns
- Real group chats target range: **0.28–0.42** (from reference data)

The system checks whether the simulated Gini is within this range and computes a **z-score** vs the reference distribution (mean 0.33, std 0.05):

```
z = (gini - 0.33) / 0.05
```

Bootstrap CI on Gini is also computed (same 10,000-resample method as above).

## The Bootstrap Engine (`bootstrap.py`)

Nearly every module calls `bootstrap_ci()`. It's general-purpose: you pass it any array and any statistic function, and it returns a CI without assuming any particular distribution.

```python
for i in range(10_000):
    sample = resample(data, with_replacement=True)
    stats[i] = stat_fn(sample)

lo = percentile(stats, 2.5%)
hi = percentile(stats, 97.5%)
```

This is used for: median CI on fidelity scores, Gini CI, Spearman rho CI. All non-parametric, all safe for small samples.

---
