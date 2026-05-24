"""
metrics_fidelity.py — Individual fidelity score statistics.

Input: judge_evals list (eval_test_1.json format).

The `scores` array inside each `persona_identification` entry holds 1–5 ratings
per agent. The score assigned to the *true* author of that persona is the
individual fidelity score from that judge's perspective.

If individual_fidelity() is separately populated in the judge output it would
live at a different key; this module handles the current schema where fidelity
signal comes from the persona_identification scores.

Metrics computed per (persona_name × judge_type) and per persona overall:
  - median
  - IQR (Q3 - Q1)
  - variance, std
  - bootstrap 95% CI on the median
  - within-type vs cross-type agreement (mean absolute deviation)

author_map is needed to identify which score entry is the true persona's score.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from angry_agents.src.eval.bootstrap import bootstrap_ci


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _iqr(arr: np.ndarray) -> float:
    return float(np.percentile(arr, 75) - np.percentile(arr, 25))


def _fidelity_scores_for_persona(
    judge_evals: list[dict],
    name_to_author: dict[str, str],
) -> dict[str, dict[str, list[int]]]:
    """
    Returns {persona_name: {judge_name: [score, ...]}}.
    Score = the rating the judge assigned to the true author for that persona.
    """
    result: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(list))

    for judge in judge_evals:
        judge_name = judge["judge_name"]
        for match in judge["persona_identification"]:
            pname = match["persona_name"]
            true_author = name_to_author.get(pname)
            if true_author is None:
                continue
            for s in match["scores"]:
                if s["author"] == true_author:
                    result[pname][judge_name].append(s["score"])
                    break

    return result


def _stats(scores: list[int]) -> dict:
    if not scores:
        return {"n": 0, "median": None, "iqr": None, "variance": None, "std": None, "ci_95": None}
    arr = np.array(scores, dtype=float)
    median = float(np.median(arr))
    ci = bootstrap_ci(arr, np.median, n=10_000)
    return {
        "n": len(scores),
        "median": round(median, 4),
        "iqr": round(_iqr(arr), 4),
        "variance": round(float(np.var(arr, ddof=1)) if len(arr) > 1 else 0.0, 4),
        "std": round(float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0, 4),
        "ci_95": [round(ci[0], 4), round(ci[1], 4)],
    }


# ---------------------------------------------------------------------------
# Within-type vs cross-type agreement
# ---------------------------------------------------------------------------

def _judge_type_agreement(
    all_scores_by_judge: dict[str, list[int]],
) -> dict:
    """
    For each pair of judge types, compute mean absolute deviation of their
    per-persona median scores. Lower MAD = more agreement.
    """
    judge_types = sorted(all_scores_by_judge.keys())
    if len(judge_types) < 2:
        return {}

    medians: dict[str, float] = {
        jt: float(np.median(all_scores_by_judge[jt])) if all_scores_by_judge[jt] else float("nan")
        for jt in judge_types
    }

    agreement: dict[str, float] = {}
    for i, a in enumerate(judge_types):
        for b in judge_types[i + 1:]:
            key = f"{a}_vs_{b}"
            agreement[key] = round(abs(medians[a] - medians[b]), 4)

    return {"judge_median_scores": {k: round(v, 4) for k, v in medians.items()}, "mad_between_types": agreement}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run(
    judge_evals: list[dict],
    author_map: dict[str, str],
    personas: list[dict],
) -> dict:
    """
    Full individual fidelity metrics.
    """
    pid_to_name = {p["persona_id"]: p["persona_name"] for p in personas}
    name_to_author = {pid_to_name[pid]: tag for tag, pid in author_map.items() if pid in pid_to_name}

    raw = _fidelity_scores_for_persona(judge_evals, name_to_author)

    # Per-persona breakdown
    per_persona: dict[str, dict] = {}
    for pname, by_judge in raw.items():
        all_scores = [s for ss in by_judge.values() for s in ss]
        per_judge_stats = {jt: _stats(scores) for jt, scores in by_judge.items()}
        per_persona[pname] = {
            "overall": _stats(all_scores),
            "per_judge_type": per_judge_stats,
        }

    # Cross-type agreement: pool all personas, compute per judge_type
    all_scores_by_judge: dict[str, list[int]] = defaultdict(list)
    for by_judge in raw.values():
        for jt, scores in by_judge.items():
            all_scores_by_judge[jt].extend(scores)

    agreement = _judge_type_agreement(dict(all_scores_by_judge))

    # Aggregate across all personas and judges
    all_scores_flat = [s for by_judge in raw.values() for ss in by_judge.values() for s in ss]

    return {
        "individual_fidelity": {
            "aggregate": _stats(all_scores_flat),
            "per_persona": per_persona,
            "judge_type_agreement": agreement,
        }
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _cli() -> None:
    import argparse, pprint

    parser = argparse.ArgumentParser(description="Individual fidelity score statistics.")
    parser.add_argument("--judge-evals", type=Path, required=True)
    parser.add_argument("--author-map", type=Path, required=True)
    parser.add_argument("--personas-dir", type=Path, required=True)
    args = parser.parse_args()

    with open(args.judge_evals, encoding="utf-8") as f:
        judge_evals = [json.loads(line) for line in f if line.strip()]
    with open(args.author_map, encoding="utf-8") as f:
        author_map = json.load(f)
    personas = [
        json.loads(p.read_text(encoding="utf-8"))
        for p in sorted(args.personas_dir.glob("*_profile.json"))
    ]

    result = run(judge_evals, author_map, personas)
    pprint.pprint(result)


if __name__ == "__main__":
    _cli()
