"""metrics_batch.py — Aggregate statistics across a batch of per-chat eval reports.

Pure functions: no I/O, no CLI. All CI logic lives here.

Bootstrap threshold: n < 20 → bootstrap_ci (assumption-free).
n >= 20 → CLT: mean ± 1.96 * std / sqrt(n).
# If comparing two batches (topic A vs B) the CLT threshold should be 30; raise it then.
"""

from __future__ import annotations

from collections import defaultdict

import numpy as np

from angry_agents.src.eval.bootstrap import bootstrap_ci

BOOTSTRAP_THRESHOLD = 20


def aggregate_scalar(
    values: list[float],
    *,
    bootstrap_stat_fn=np.mean,
) -> dict:
    """
    Descriptive stats + 95% CI for a list of per-chat scalar values.

    bootstrap_stat_fn: statistic to bootstrap when n < BOOTSTRAP_THRESHOLD.
    CLT path always centers CI on the sample mean.
    """
    n = len(values)
    arr = np.array(values, dtype=float)
    mean = float(np.mean(arr))
    variance = float(np.var(arr, ddof=1)) if n > 1 else 0.0
    std = float(np.std(arr, ddof=1)) if n > 1 else 0.0

    if n < BOOTSTRAP_THRESHOLD:
        ci = bootstrap_ci(arr, bootstrap_stat_fn)
        method = "bootstrap"
    else:
        se = std / (n ** 0.5)
        ci = (mean - 1.96 * se, mean + 1.96 * se)
        method = "clt"

    return {
        "n": n,
        "mean": round(mean, 4),
        "variance": round(variance, 6),
        "std": round(std, 4),
        "ci_95": [round(ci[0], 4), round(ci[1], 4)],
        "method": method,
    }


def aggregate_accuracy(per_chat_accuracies: list[float]) -> dict:
    return aggregate_scalar(per_chat_accuracies, bootstrap_stat_fn=np.mean)


def aggregate_fidelity(per_chat_medians: list[float]) -> dict:
    return aggregate_scalar(per_chat_medians, bootstrap_stat_fn=np.median)


def aggregate_gini(per_chat_ginis: list[float]) -> dict:
    return aggregate_scalar(per_chat_ginis, bootstrap_stat_fn=np.mean)


def aggregate_group_fidelity(per_chat_means: list[float]) -> dict:
    return aggregate_scalar(per_chat_means, bootstrap_stat_fn=np.mean)


def pool_confusion_matrices(
    matrices_with_labels: list[tuple[list[str], list[list[int]]]],
) -> dict:
    """
    Element-wise sum of per-chat confusion matrices.
    Labels are unioned and sorted; missing entries zero-filled.
    Returns pooled matrix + per-persona precision/recall/F1 + macro F1 + Cohen's Kappa.
    """
    all_labels = sorted({lbl for labels, _ in matrices_with_labels for lbl in labels})
    n = len(all_labels)
    idx = {lbl: i for i, lbl in enumerate(all_labels)}
    pooled = np.zeros((n, n), dtype=int)

    for labels, matrix in matrices_with_labels:
        for i, row_lbl in enumerate(labels):
            for j, col_lbl in enumerate(labels):
                pi = idx.get(row_lbl)
                pj = idx.get(col_lbl)
                if pi is not None and pj is not None:
                    pooled[pi, pj] += matrix[i][j]

    per_persona: dict[str, dict] = {}
    for i, label in enumerate(all_labels):
        tp = int(pooled[i, i])
        fp = int(pooled[:, i].sum()) - tp
        fn = int(pooled[i, :].sum()) - tp
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        per_persona[label] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
        }

    macro_f1 = float(np.mean([v["f1"] for v in per_persona.values()]))

    total = int(pooled.sum())
    if total > 0:
        p_o = float(np.trace(pooled)) / total
        p_e = float(np.dot(pooled.sum(axis=0), pooled.sum(axis=1))) / (total ** 2)
        kappa = float((p_o - p_e) / (1.0 - p_e)) if p_e < 1.0 else 1.0
    else:
        kappa = 0.0

    return {
        "labels": all_labels,
        "matrix": pooled.tolist(),
        "per_persona": per_persona,
        "macro_f1": round(macro_f1, 4),
        "kappa": round(kappa, 4),
    }


