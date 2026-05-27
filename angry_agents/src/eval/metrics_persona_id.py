"""
metrics_persona_id.py — Persona identification accuracy metrics.

Inputs:
  judge_evals : list of judge dicts (eval_test_1.json format)
  ground_truth: {msg_id: persona_id}         (secret file from simulate_transcript)
  author_map  : {author_tag: persona_id}     (secret file from simulate_transcript)

What is computed:
  - Per-judge and aggregate accuracy vs 12.5% random baseline (1/8 personas)
  - Variance and std of per-judge accuracies
  - Binomial exact 95% CI via scipy.stats.binomtest
  - p-value against H0: true rate = 1/8
  - 8x8 confusion matrix (predicted persona vs true persona)
  - Precision, Recall, F1 per persona + macro F1
  - Cohen's Kappa (agreement corrected for chance)

The judge eval format expected (from base_judge.py / eval_test_1.json):
  [
    {
      "judge_name": "style",
      "persona_identification": [
        {
          "persona_name": "VADER",         ← true persona name
          "predicted": "Agent G fc8c...",  ← author_tag judge thinks played this persona
          "scores": [{"author": ..., "score": 1-5}, ...]
        },
        ...
      ]
    },
    ...
  ]

Ground truth linkage:
  author_map["Agent G fc8c..."] → persona_id
  We need a separate personas_names map: persona_id → persona_name
  OR we accept that persona_name in judge eval == persona_name in personas list.
  Here we key by persona_name directly (simpler, matches the JSON).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment
from scipy.stats import binomtest

RANDOM_BASELINE = 1 / 8  # 8 personas


# ---------------------------------------------------------------------------
# Loading helpers
# ---------------------------------------------------------------------------

def load_judge_evals(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Build ground-truth persona_name → author_tag mapping
#
# author_map : {author_tag: persona_id}
# personas   : [{persona_id, persona_name, ...}]  (from *_profile.json files)
#
# We produce: persona_name → author_tag  (the true author for each persona)
# ---------------------------------------------------------------------------

def build_name_to_author(author_map: dict[str, str], personas: list[dict]) -> dict[str, str]:
    """Map persona_name → author_tag using the secret author_map."""
    pid_to_name = {
        "p_" + p["persona_name"].lower().replace(" ", "_"): p["persona_name"]
        for p in personas
    }
    return {pid_to_name[pid]: tag for tag, pid in author_map.items() if pid in pid_to_name}


# ---------------------------------------------------------------------------
# Core accuracy computation
# ---------------------------------------------------------------------------

def _hungarian_assignment(
    judge: dict,
    name_to_author: dict[str, str],
) -> dict[str, str]:
    """
    Compute the bijective persona→author assignment for one judge using the
    Hungarian algorithm (scipy.optimize.linear_sum_assignment).

    The greedy argmax stored in each record's "predicted" field collapses
    everything onto a single high-confidence author (the attractor problem):
    if Lewis Hamilton scores 5 for 6 different authors, argmax assigns him to
    all 6, violating the one-author-per-persona constraint.

    Hungarian assignment enforces the bijection: each actual persona maps to
    exactly one author and each author is claimed by at most one persona.
    This guarantees that even when one author dominates in raw scores, the
    algorithm redistributes the remaining personas to their next-best matches.

    Only actual chat participants (personas present in name_to_author) are
    included in the matching — distractor candidates are ignored.

    Returns {persona_name: author_tag} for every actual participant.
    """
    actual_names = list(name_to_author.keys())
    actual_authors = list(name_to_author.values())
    n = len(actual_names)

    persona_to_row = {name: i for i, name in enumerate(actual_names)}
    author_to_col = {author: j for j, author in enumerate(actual_authors)}

    # Build n×n score matrix: rows=actual personas, cols=actual authors
    score_matrix = np.zeros((n, n))
    for match in judge["persona_identification"]:
        pname = match["persona_name"]
        if pname not in persona_to_row:
            continue
        row = persona_to_row[pname]
        for entry in match["scores"]:
            col = author_to_col.get(entry["author"])
            if col is not None:
                score_matrix[row, col] = entry["score"]

    # Maximise total score (linear_sum_assignment minimises, so negate)
    row_ind, col_ind = linear_sum_assignment(-score_matrix)
    return {actual_names[r]: actual_authors[c] for r, c in zip(row_ind, col_ind)}


def _judge_accuracy(
    judge: dict,
    name_to_author: dict[str, str],
) -> tuple[int, int, list[tuple[str, str]]]:
    """
    Returns (n_correct, n_total, [(true_persona_name, predicted_persona_name), ...]).
    Uses Hungarian bijective assignment instead of greedy per-persona argmax
    to prevent the attractor problem.
    """
    author_to_name = {v: k for k, v in name_to_author.items()}
    optimal = _hungarian_assignment(judge, name_to_author)

    correct = 0
    pairs: list[tuple[str, str]] = []
    for match in judge["persona_identification"]:
        true_name: str = match["persona_name"]
        if true_name not in name_to_author:
            continue  # persona was not played in this chat — skip
        predicted_tag = optimal.get(true_name)
        predicted_name = author_to_name.get(predicted_tag, "<unknown>")
        if predicted_name == true_name:
            correct += 1
        pairs.append((true_name, predicted_name))
    return correct, len(pairs), pairs


def compute_accuracy(
    judge_evals: list[dict],
    name_to_author: dict[str, str],
) -> dict:
    """
    Returns aggregate + per-judge accuracy stats.
    """
    total_correct = 0
    total_attempts = 0
    per_judge: list[dict] = []
    all_pairs: list[tuple[str, str]] = []

    for judge in judge_evals:
        c, n, pairs = _judge_accuracy(judge, name_to_author)
        total_correct += c
        total_attempts += n
        all_pairs.extend(pairs)
        per_judge.append({
            "judge_name": judge["judge_name"],
            "correct": c,
            "total": n,
            "accuracy": round(c / n, 4) if n else None,
        })

    result = binomtest(total_correct, total_attempts, RANDOM_BASELINE, alternative="greater")
    ci_lo, ci_hi = result.proportion_ci(confidence_level=0.95, method="exact")

    judge_accs = [j["accuracy"] for j in per_judge if j["accuracy"] is not None]
    acc_arr = np.array(judge_accs)
    acc_mean = float(np.mean(acc_arr)) if len(acc_arr) else None
    acc_var = float(np.var(acc_arr, ddof=1)) if len(acc_arr) > 1 else None
    acc_std = float(np.std(acc_arr, ddof=1)) if len(acc_arr) > 1 else None

    return {
        "aggregate": {
            "correct": total_correct,
            "total": total_attempts,
            "accuracy": round(total_correct / total_attempts, 4) if total_attempts else None,
            "random_baseline": RANDOM_BASELINE,
            "ci_95": [round(ci_lo, 4), round(ci_hi, 4)],
            "p_value": round(result.pvalue, 6),
            "significant": result.pvalue < 0.05,
        },
        "judge_accuracy_variance": {
            "mean": round(acc_mean, 4) if acc_mean is not None else None,
            "variance": round(acc_var, 6) if acc_var is not None else None,
            "std": round(acc_std, 4) if acc_std is not None else None,
        },
        "per_judge": per_judge,
        "all_pairs": all_pairs,  # kept for confusion matrix
    }


# ---------------------------------------------------------------------------
# Confusion matrix
# ---------------------------------------------------------------------------

def _per_class_metrics(matrix: np.ndarray, labels: list[str]) -> dict:
    """Precision, Recall, F1 per persona (one-vs-rest) + macro F1."""
    per_persona: dict[str, dict] = {}
    for i, label in enumerate(labels):
        tp = int(matrix[i, i])
        fp = int(matrix[:, i].sum()) - tp
        fn = int(matrix[i, :].sum()) - tp
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        per_persona[label] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
        }
    macro_f1 = float(np.mean([v["f1"] for v in per_persona.values()]))
    return {"per_persona": per_persona, "macro_f1": round(macro_f1, 4)}


def _cohen_kappa(matrix: np.ndarray) -> float:
    """Cohen's Kappa: agreement corrected for chance from marginal distributions."""
    total = matrix.sum()
    if total == 0:
        return 0.0
    p_o = np.trace(matrix) / total
    p_e = float(np.dot(matrix.sum(axis=0), matrix.sum(axis=1))) / (total ** 2)
    if p_e >= 1.0:
        return 1.0
    return float((p_o - p_e) / (1.0 - p_e))


def confusion_matrix(
    pairs: list[tuple[str, str]],
    persona_names: list[str],
) -> dict:
    """
    Build NxN confusion matrix where entry [i][j] = count of true=i predicted=j.
    Computes per-persona precision/recall/F1, macro F1, and Cohen's Kappa.
    """
    n = len(persona_names)
    idx = {name: i for i, name in enumerate(persona_names)}
    matrix = np.zeros((n, n), dtype=int)

    for true_name, pred_name in pairs:
        i = idx.get(true_name)
        j = idx.get(pred_name)
        if i is not None and j is not None:
            matrix[i, j] += 1

    prf = _per_class_metrics(matrix, persona_names)
    kappa = _cohen_kappa(matrix)

    return {
        "labels": persona_names,
        "matrix": matrix.tolist(),
        "precision_recall_f1": prf,
        "cohen_kappa": round(kappa, 4),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run(
    judge_evals: list[dict],
    author_map: dict[str, str],
    personas: list[dict],
) -> dict:
    """
    Full persona identification metrics.

    Returns a dict ready for JSON serialisation.
    """
    name_to_author = build_name_to_author(author_map, personas)
    acc = compute_accuracy(judge_evals, name_to_author)
    persona_names = sorted({m["persona_name"] for j in judge_evals for m in j["persona_identification"]})
    cm = confusion_matrix(acc.pop("all_pairs"), persona_names)

    return {
        "persona_identification": {
            **acc,
            "confusion_matrix": cm,
        }
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _cli() -> None:
    import argparse, pprint

    parser = argparse.ArgumentParser(description="Persona identification accuracy metrics.")
    parser.add_argument("--judge-evals", type=Path, required=True, help="Path to judge eval JSON (eval_20j_1.jsonl).")
    parser.add_argument("--author-map", type=Path, required=True, help="Path to author_map.json (secret file).")
    parser.add_argument("--personas-dir", type=Path, required=True, help="Dir with *_profile.json persona files.")
    args = parser.parse_args()

    judge_evals = load_judge_evals(args.judge_evals)
    author_map = load_json(args.author_map)
    personas = [
        json.loads(p.read_text(encoding="utf-8"))
        for p in sorted(args.personas_dir.glob("*_profile.json"))
    ]

    result = run(judge_evals, author_map, personas)
    pprint.pprint(result)

    stem = args.judge_evals.stem.replace("eval_", "")
    out_path = args.judge_evals.parent / f"report_persona_id_{stem}.json"
    out_path.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(f"\nSaved → {out_path}")


if __name__ == "__main__":
    _cli()
