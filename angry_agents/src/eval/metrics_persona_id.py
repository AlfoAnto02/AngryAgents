"""
metrics_persona_id.py — Persona identification accuracy metrics.

Inputs:
  judge_evals : list of judge dicts (eval_test_1.json format)
  ground_truth: {msg_id: persona_id}         (secret file from simulate_transcript)
  author_map  : {author_tag: persona_id}     (secret file from simulate_transcript)

What is computed:
  - Per-judge and aggregate accuracy vs 12.5% random baseline (1/8 personas)
  - Binomial exact 95% CI via scipy.stats.binomtest
  - p-value against H0: true rate = 1/8
  - 8x8 confusion matrix (predicted persona vs true persona)
  - Chi-square test on confusion matrix vs uniform error distribution

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
from scipy.stats import binomtest, chi2_contingency

RANDOM_BASELINE = 1 / 8  # 8 personas


# ---------------------------------------------------------------------------
# Loading helpers
# ---------------------------------------------------------------------------

def load_judge_evals(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


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
    pid_to_name = {p["persona_id"]: p["persona_name"] for p in personas}
    return {pid_to_name[pid]: tag for tag, pid in author_map.items() if pid in pid_to_name}


# ---------------------------------------------------------------------------
# Core accuracy computation
# ---------------------------------------------------------------------------

def _judge_accuracy(
    judge: dict,
    name_to_author: dict[str, str],
) -> tuple[int, int, list[tuple[str, str]]]:
    """
    Returns (n_correct, n_total, [(true_persona_name, predicted_persona_name), ...]).
    predicted_persona_name is resolved via author_tag → name lookup.
    """
    author_to_name = {v: k for k, v in name_to_author.items()}
    correct = 0
    pairs: list[tuple[str, str]] = []
    for match in judge["persona_identification"]:
        true_name: str = match["persona_name"]
        predicted_tag: str = match["predicted"]
        predicted_name = author_to_name.get(predicted_tag, "<unknown>")
        hit = predicted_name == true_name
        if hit:
            correct += 1
        pairs.append((true_name, predicted_name))
    return correct, len(judge["persona_identification"]), pairs


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
        "per_judge": per_judge,
        "all_pairs": all_pairs,  # kept for confusion matrix
    }


# ---------------------------------------------------------------------------
# Confusion matrix
# ---------------------------------------------------------------------------

def confusion_matrix(
    pairs: list[tuple[str, str]],
    persona_names: list[str],
) -> dict:
    """
    Build NxN confusion matrix where entry [i][j] = count of true=i predicted=j.
    Also runs chi-square test vs uniform off-diagonal distribution.
    """
    n = len(persona_names)
    idx = {name: i for i, name in enumerate(persona_names)}
    matrix = np.zeros((n, n), dtype=int)

    for true_name, pred_name in pairs:
        i = idx.get(true_name)
        j = idx.get(pred_name)
        if i is not None and j is not None:
            matrix[i, j] += 1

    # Chi-square: does confusion pattern differ from uniform error distribution?
    # Expected: correct on diagonal, errors spread uniformly off-diagonal.
    off_diag = matrix.copy()
    np.fill_diagonal(off_diag, 0)
    total_errors = off_diag.sum()

    chi2_p = None
    if total_errors > 0 and n > 1:
        # Compare observed off-diagonal counts vs uniform expected
        expected_per_cell = total_errors / (n * (n - 1))
        expected = np.full((n, n), expected_per_cell)
        np.fill_diagonal(expected, 0)
        # Use only off-diagonal cells
        obs_flat = off_diag[off_diag > 0].astype(float)
        exp_flat = expected[off_diag > 0].astype(float)
        if len(obs_flat) > 1:
            _, chi2_p, _, _ = chi2_contingency(
                np.vstack([obs_flat, exp_flat])
            )

    return {
        "labels": persona_names,
        "matrix": matrix.tolist(),
        "chi2_p_value": round(float(chi2_p), 6) if chi2_p is not None else None,
        "non_uniform_errors": bool(chi2_p < 0.05) if chi2_p is not None else None,
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
    parser.add_argument("--judge-evals", type=Path, required=True, help="Path to judge eval JSON (eval_test_1.json).")
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


if __name__ == "__main__":
    _cli()
