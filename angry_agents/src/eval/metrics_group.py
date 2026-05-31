"""
metrics_group.py — Group fidelity metrics.

Inputs:
  transcript_meta : transcript_meta dict (speaker_stats per persona)
  transcript      : transcript.jsonl (one JSON object per line)
  author_map      : author_map.json {author_tag: persona_id}
  embeddings_path : optional JSON {author_tag: [float, ...]} pre-computed embeddings
                    (one embedding per agent = mean of all their message embeddings)

Metrics:
  1. Gini coefficient — already in transcript_meta; we add bootstrap CI and test
     against real-chat reference range [0.28, 0.42].
  2. Pairwise cosine distance matrix (8x8) from per-agent embeddings.
  3. Spearman rank correlation between simulated and reference distance matrix
     (if reference provided). Bootstrap CI on rho.

Embeddings note:
  If embeddings_path is not provided, cosine/Spearman metrics are skipped and
  a note is included in the output explaining how to generate them.
  Use simulate_transcript.py --embed-model nomic-embed-text to produce them,
  or point at any external embedding file in the expected format.
"""

from __future__ import annotations

import json
from itertools import combinations
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr

from angry_agents.src.eval.bootstrap import bootstrap_ci


def _gini(counts: list[float] | np.ndarray) -> float:
    """Gini coefficient of a distribution. 0 = equal, 1 = one agent dominates."""
    arr = np.sort(np.asarray(counts, dtype=float))
    n = len(arr)
    if n == 0 or arr.sum() == 0:
        return 0.0
    idx = np.arange(1, n + 1)
    return float((2 * np.dot(idx, arr)) / (n * arr.sum()) - (n + 1) / n)


REAL_CHAT_GINI_LO = 0.28
REAL_CHAT_GINI_HI = 0.42
REAL_CHAT_GINI_MEAN = 0.33
REAL_CHAT_GINI_STD = 0.05


# ---------------------------------------------------------------------------
# Gini metrics
# ---------------------------------------------------------------------------

def _gini_metrics(speaker_stats: dict) -> dict:
    """
    speaker_stats: the speaker_stats dict from transcript_meta.json.
    {persona_id: {turns: int, ...}}
    """
    counts = [v["turns"] for v in speaker_stats.values()]
    gini_val = _gini(counts)

    # Bootstrap CI on Gini using the raw counts as our sample
    ci = bootstrap_ci(counts, _gini, n=10_000)

    # Is simulated Gini within the reference range?
    within_range = REAL_CHAT_GINI_LO <= gini_val <= REAL_CHAT_GINI_HI
    # Z-score vs reference distribution
    z = (gini_val - REAL_CHAT_GINI_MEAN) / REAL_CHAT_GINI_STD

    return {
        "gini": round(gini_val, 4),
        "ci_95": [round(ci[0], 4), round(ci[1], 4)],
        "reference_range": [REAL_CHAT_GINI_LO, REAL_CHAT_GINI_HI],
        "within_reference_range": within_range,
        "z_vs_reference": round(z, 3),
    }


# ---------------------------------------------------------------------------
# Cosine distance matrix from embeddings
# ---------------------------------------------------------------------------

def _cosine_dist(a: np.ndarray, b: np.ndarray) -> float:
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    sim = float(np.dot(a, b) / denom) if denom else 0.0
    return 1.0 - sim


def _cosine_distance_matrix(
    embeddings: dict[str, np.ndarray],
    labels: list[str],
) -> np.ndarray:
    n = len(labels)
    mat = np.zeros((n, n), dtype=float)
    for i, a in enumerate(labels):
        for j, b in enumerate(labels):
            if i != j:
                mat[i, j] = _cosine_dist(embeddings[a], embeddings[b])
    return mat


# ---------------------------------------------------------------------------
# Spearman correlation between two distance matrices
# ---------------------------------------------------------------------------

def _upper_triangle(mat: np.ndarray) -> np.ndarray:
    n = mat.shape[0]
    return mat[np.triu_indices(n, k=1)]


def _spearman_with_ci(
    sim_mat: np.ndarray,
    ref_mat: np.ndarray,
    n_bootstrap: int = 10_000,
) -> dict:
    sim_flat = _upper_triangle(sim_mat)
    ref_flat = _upper_triangle(ref_mat)

    rho, p_val = spearmanr(sim_flat, ref_flat)

    # Bootstrap CI: resample pairs of (sim_distance, ref_distance)
    pairs = np.column_stack([sim_flat, ref_flat])

    def _rho(sample: np.ndarray) -> float:
        # sample is 1D due to bootstrap_ci signature — we need pairs
        # rebuild as index-based resample
        return float(spearmanr(sample[: len(sample) // 2], sample[len(sample) // 2:])[0])

    # Interleave sim and ref so bootstrap_ci can resample rows together
    interleaved = np.concatenate([sim_flat, ref_flat])

    def _rho_interleaved(arr: np.ndarray) -> float:
        mid = len(arr) // 2
        return float(spearmanr(arr[:mid], arr[mid:])[0])

    ci = bootstrap_ci(interleaved, _rho_interleaved, n=n_bootstrap)

    return {
        "spearman_rho": round(float(rho), 4),
        "p_value": round(float(p_val), 6),
        "ci_95": [round(ci[0], 4), round(ci[1], 4)],
    }


# ---------------------------------------------------------------------------
# Load helpers
# ---------------------------------------------------------------------------

def _load_transcript(path: Path) -> list[dict]:
    lines = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                lines.append(json.loads(line))
    return lines


def _load_embeddings(path: Path) -> dict[str, np.ndarray]:
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    return {tag: np.array(vec, dtype=float) for tag, vec in raw.items()}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run(
    transcript_meta: dict,
    embeddings_path: Path | None = None,
    reference_matrix_path: Path | None = None,
) -> dict:
    """
    Group fidelity metrics.

    transcript_meta : loaded dict from transcript_meta.json
    embeddings_path : optional JSON {author_tag: [float]}
    reference_matrix_path : optional JSON {"labels": [...], "matrix": [[...]]}
    """
    result: dict = {}

    # 1. Gini
    speaker_stats = transcript_meta.get("speaker_stats", {})
    if speaker_stats:
        result["gini"] = _gini_metrics(speaker_stats)
    else:
        result["gini"] = {"error": "speaker_stats missing from transcript_meta"}

    # 2. Cosine distance matrix
    if embeddings_path is not None:
        embeddings = _load_embeddings(embeddings_path)
        labels = sorted(embeddings.keys())
        dist_mat = _cosine_distance_matrix(embeddings, labels)

        result["cosine_distance_matrix"] = {
            "labels": labels,
            "matrix": [[round(v, 4) for v in row] for row in dist_mat.tolist()],
        }

        # 3. Spearman vs reference
        if reference_matrix_path is not None:
            with open(reference_matrix_path, encoding="utf-8") as f:
                ref_data = json.load(f)
            ref_mat = np.array(ref_data["matrix"], dtype=float)
            ref_labels = ref_data["labels"]

            # Align matrices by label intersection
            common = [l for l in labels if l in ref_labels]
            if len(common) >= 3:
                sim_idx = [labels.index(l) for l in common]
                ref_idx = [ref_labels.index(l) for l in common]
                sim_sub = dist_mat[np.ix_(sim_idx, sim_idx)]
                ref_sub = ref_mat[np.ix_(ref_idx, ref_idx)]
                result["spearman_vs_reference"] = _spearman_with_ci(sim_sub, ref_sub)
            else:
                result["spearman_vs_reference"] = {"error": "too few common labels between sim and reference"}
        else:
            result["spearman_vs_reference"] = {"note": "no reference matrix provided — skip Spearman"}
    else:
        result["cosine_distance_matrix"] = {
            "note": "embeddings not provided — pass embeddings_path to enable cosine distance matrix"
        }
        result["spearman_vs_reference"] = {"note": "requires embeddings"}

    return {"group_fidelity": result}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _cli() -> None:
    import argparse, pprint

    parser = argparse.ArgumentParser(description="Group fidelity metrics.")
    parser.add_argument("--meta", type=Path, required=True, help="transcript_meta.json")
    parser.add_argument("--embeddings", type=Path, default=None, help="agent_embeddings.json {author_tag: [float]}")
    parser.add_argument("--reference-matrix", type=Path, default=None, help="reference_distance_matrix.json")
    args = parser.parse_args()

    with open(args.meta, encoding="utf-8") as f:
        meta = json.load(f)

    result = run(meta, args.embeddings, args.reference_matrix)
    pprint.pprint(result)


if __name__ == "__main__":
    _cli()
