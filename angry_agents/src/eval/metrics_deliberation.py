"""
metrics_deliberation.py — Phase 2 deliberation metrics.

Input format (one JSON file, list of round-by-round judge ratings):
[
  {
    "case_id": "persona_VADER_judge_style",
    "judge_id": "style",
    "round": 0,          ← 0 = Phase 1 (pre-deliberation)
    "rating": 3,         ← revised fidelity or identification score (int 1–5)
    "confidence": 4      ← judge self-reported confidence (int 1–5)
  },
  ...
]

Metrics:
  1. Variance per round — F-test between round 0 and final round per case.
  2. Convergence rate — fraction of high-disagreement cases with variance reduction.
     Binomial CI via scipy.stats.binomtest.
  3. Confidence calibration —
       a. Pearson correlation of Δconfidence and Δaccuracy across judges × cases.
       b. Calibration curve: accuracy at each confidence level 1–5.

For (3b) accuracy, we need ground truth ratings per case (the "correct" answer).
If not available, we skip the accuracy-based calibration and only compute the
Δconfidence distribution.

Expected optional ground_truth_ratings: {case_id: correct_rating (int 1–5)}
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import binomtest, f_oneway, pearsonr

from angry_agents.src.eval.bootstrap import bootstrap_ci


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

def _load_rounds(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _group_by_case(rounds: list[dict]) -> dict[str, list[dict]]:
    """Returns {case_id: [round_entry, ...]} sorted by round."""
    by_case: dict[str, list[dict]] = defaultdict(list)
    for r in rounds:
        by_case[r["case_id"]].append(r)
    for entries in by_case.values():
        entries.sort(key=lambda x: x["round"])
    return dict(by_case)


# ---------------------------------------------------------------------------
# 1. Variance per round + F-test
# ---------------------------------------------------------------------------

def _variance_per_round(case_entries: list[dict]) -> dict:
    """
    For a single case, compute variance of ratings at each round.
    Return round_variances and F-test p-value between round 0 and last round.
    """
    by_round: dict[int, list[int]] = defaultdict(list)
    for e in case_entries:
        by_round[e["round"]].append(e["rating"])

    rounds_sorted = sorted(by_round.keys())
    round_variances = {}
    for r in rounds_sorted:
        ratings = by_round[r]
        var = float(np.var(ratings, ddof=1)) if len(ratings) > 1 else 0.0
        round_variances[r] = {"ratings": ratings, "variance": round(var, 4), "n": len(ratings)}

    # F-test: round 0 vs final round
    f_p = None
    converged = None
    if len(rounds_sorted) >= 2:
        r0_ratings = by_round[rounds_sorted[0]]
        rf_ratings = by_round[rounds_sorted[-1]]
        if len(r0_ratings) > 1 and len(rf_ratings) > 1:
            _, f_p = f_oneway(r0_ratings, rf_ratings)
            f_p = round(float(f_p), 6)
        var_r0 = round_variances[rounds_sorted[0]]["variance"]
        var_rf = round_variances[rounds_sorted[-1]]["variance"]
        converged = var_rf < var_r0

    return {
        "round_variances": round_variances,
        "f_test_p_value": f_p,
        "converged": converged,
    }


def variance_reduction(
    by_case: dict[str, list[dict]],
) -> dict:
    per_case = {cid: _variance_per_round(entries) for cid, entries in by_case.items()}

    converged_cases = [cid for cid, v in per_case.items() if v["converged"] is True]
    total_cases = len(per_case)
    n_converged = len(converged_cases)

    conv_rate = n_converged / total_cases if total_cases else None
    conv_ci = None
    if total_cases > 0:
        bt = binomtest(n_converged, total_cases, alternative="two-sided")
        ci = bt.proportion_ci(confidence_level=0.95, method="exact")
        conv_ci = [round(ci.low, 4), round(ci.high, 4)]

    return {
        "per_case": per_case,
        "convergence_rate": round(conv_rate, 4) if conv_rate is not None else None,
        "convergence_ci_95": conv_ci,
        "n_converged": n_converged,
        "n_total": total_cases,
        "converged_cases": converged_cases,
    }


# ---------------------------------------------------------------------------
# 2. Confidence calibration
# ---------------------------------------------------------------------------

def _delta(entries: list[dict], key: str) -> float | None:
    """Final round value minus round 0 value for a judge × case pair."""
    rounds = sorted(set(e["round"] for e in entries))
    if len(rounds) < 2:
        return None
    r0 = next((e[key] for e in entries if e["round"] == rounds[0]), None)
    rf = next((e[key] for e in entries if e["round"] == rounds[-1]), None)
    if r0 is None or rf is None:
        return None
    return rf - r0


def confidence_calibration(
    by_case: dict[str, list[dict]],
    ground_truth_ratings: dict[str, int] | None = None,
) -> dict:
    """
    a. Δconfidence vs Δaccuracy correlation (if ground_truth_ratings provided).
    b. Calibration curve: per confidence level, actual accuracy.
    c. Δconfidence distribution (always available).
    """
    # Group by (case_id, judge_id)
    by_judge_case: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for case_id, entries in by_case.items():
        for e in entries:
            by_judge_case[(case_id, e["judge_id"])].append(e)

    delta_conf_list: list[float] = []
    delta_acc_list: list[float] = []  # only populated if ground truth available

    for (case_id, _), entries in by_judge_case.items():
        dc = _delta(entries, "confidence")
        if dc is None:
            continue
        delta_conf_list.append(dc)

        if ground_truth_ratings and case_id in ground_truth_ratings:
            gt = ground_truth_ratings[case_id]
            r0 = next((e["rating"] for e in entries if e["round"] == min(e["round"] for e in entries)), None)
            rf = next((e["rating"] for e in entries if e["round"] == max(e["round"] for e in entries)), None)
            if r0 is not None and rf is not None:
                acc_before = 1 if r0 == gt else 0
                acc_after = 1 if rf == gt else 0
                delta_acc_list.append(acc_after - acc_before)

    result: dict = {}

    # Δconfidence stats
    if delta_conf_list:
        arr = np.array(delta_conf_list)
        result["delta_confidence"] = {
            "mean": round(float(np.mean(arr)), 4),
            "std": round(float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0, 4),
            "n": len(arr),
        }
    else:
        result["delta_confidence"] = {"note": "no multi-round data found"}

    # Δconfidence vs Δaccuracy correlation
    if delta_acc_list and len(delta_acc_list) == len(delta_conf_list) and len(delta_conf_list) >= 3:
        r, p = pearsonr(delta_conf_list, delta_acc_list)
        ci = bootstrap_ci(
            np.column_stack([delta_conf_list, delta_acc_list]).flatten(),
            lambda arr: float(pearsonr(arr[: len(arr) // 2], arr[len(arr) // 2:])[0]),
            n=5_000,
        )
        result["delta_conf_vs_delta_acc"] = {
            "pearson_r": round(float(r), 4),
            "p_value": round(float(p), 6),
            "ci_95": [round(ci[0], 4), round(ci[1], 4)],
            "flag_overconfidence": float(r) < 0,
        }
    elif ground_truth_ratings:
        result["delta_conf_vs_delta_acc"] = {"note": "insufficient data (need ≥3 cases with ground truth)"}
    else:
        result["delta_conf_vs_delta_acc"] = {"note": "ground_truth_ratings not provided"}

    # Calibration curve: group final-round entries by confidence, compute accuracy
    if ground_truth_ratings:
        conf_bins: dict[int, list[int]] = defaultdict(list)
        for case_id, entries in by_case.items():
            if case_id not in ground_truth_ratings:
                continue
            gt = ground_truth_ratings[case_id]
            final_round = max(e["round"] for e in entries)
            for e in entries:
                if e["round"] == final_round and "confidence" in e:
                    correct = 1 if e["rating"] == gt else 0
                    conf_bins[e["confidence"]].append(correct)

        calibration_curve = {}
        for level in range(1, 6):
            hits = conf_bins.get(level, [])
            calibration_curve[level] = {
                "n": len(hits),
                "accuracy": round(float(np.mean(hits)), 4) if hits else None,
            }
        result["calibration_curve"] = calibration_curve
    else:
        result["calibration_curve"] = {"note": "requires ground_truth_ratings"}

    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run(
    rounds: list[dict],
    ground_truth_ratings: dict[str, int] | None = None,
) -> dict:
    by_case = _group_by_case(rounds)
    vr = variance_reduction(by_case)
    calib = confidence_calibration(by_case, ground_truth_ratings)
    return {
        "deliberation": {
            "variance_reduction": vr,
            "confidence_calibration": calib,
        }
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _cli() -> None:
    import argparse, pprint

    parser = argparse.ArgumentParser(description="Phase 2 deliberation metrics.")
    parser.add_argument("--rounds", type=Path, required=True, help="JSON list of round-by-round judge entries.")
    parser.add_argument("--ground-truth-ratings", type=Path, default=None, help="JSON {case_id: correct_rating}.")
    args = parser.parse_args()

    rounds = _load_rounds(args.rounds)
    gt = None
    if args.ground_truth_ratings:
        with open(args.ground_truth_ratings, encoding="utf-8") as f:
            gt = json.load(f)

    result = run(rounds, gt)
    pprint.pprint(result)


if __name__ == "__main__":
    _cli()
