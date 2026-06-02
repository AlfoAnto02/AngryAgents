"""
report.py — Aggregate metrics CLI entry point.

Calls all three metrics modules and writes a single metrics_report.json.

Usage:
  python -m angry_agents.src.eval.report \\
    --eval-dir data/eval/ \\
    --judge-evals data/eval/judge_evals.json \\
    --personas-dir data/personas/ \\
    [--embeddings data/eval/agent_embeddings.json] \\
    [--reference-matrix data/eval/reference_distance_matrix.json] \\
    [--out data/eval/metrics_report.json]

Required files:
  eval-dir/author_map.json         ← from simulate_transcript (secret)
  eval-dir/ground_truth.json       ← from simulate_transcript (secret)
  eval-dir/transcript_meta.json    ← from simulate_transcript

  judge-evals                      ← Phase 1 judge output JSON
  personas-dir/*_profile.json      ← persona profiles

Optional:
  embeddings                       ← {author_tag: [float]} for cosine matrix
  reference-matrix                 ← reference distance matrix for Spearman
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from angry_agents.src.eval import metrics_persona_id, metrics_fidelity, metrics_group
from angry_agents.src.eval.simulate_transcript import load_personas as _load_personas_from_dir


class _NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.bool_):
            return bool(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super().default(obj)


def _load_json(path: Path) -> dict | list:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _load_personas(personas_dir: Path) -> list[dict]:
    # Reuse simulate_transcript logic: derives persona_id from filename when missing.
    return _load_personas_from_dir(personas_dir)


def run_all(
    eval_dir: Path,
    judge_evals_path: Path,
    personas_dir: Path,
    embeddings_path: Path | None = None,
    reference_matrix_path: Path | None = None,
) -> dict:
    author_map = _load_json(eval_dir / "author_map.json")
    transcript_meta = _load_json(eval_dir / "transcript_meta.json")
    judge_evals = _load_json(judge_evals_path)
    personas = _load_personas(personas_dir)

    report: dict = {}

    # --- Persona identification ---
    print("Computing persona identification metrics...")
    report.update(metrics_persona_id.run(judge_evals, author_map, personas))

    # --- Individual fidelity ---
    print("Computing individual fidelity metrics...")
    report.update(metrics_fidelity.run(judge_evals, author_map, personas))

    # --- Group fidelity ---
    print("Computing group fidelity metrics...")
    report.update(metrics_group.run(transcript_meta, embeddings_path, reference_matrix_path))

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Aggregate evaluation metrics report.")
    parser.add_argument("--eval-dir", type=Path, required=True, help="Dir with author_map.json, transcript_meta.json.")
    parser.add_argument("--judge-evals", type=Path, required=True, help="Phase 1 judge eval JSON.")
    parser.add_argument("--personas-dir", type=Path, required=True, help="Dir with *_profile.json files.")
    parser.add_argument("--embeddings", type=Path, default=None, help="{author_tag: [float]} JSON.")
    parser.add_argument("--reference-matrix", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=None, help="Output path (default: eval-dir/metrics_report.json).")
    args = parser.parse_args()

    out_path = args.out or (args.eval_dir / "metrics_report.json")

    report = run_all(
        eval_dir=args.eval_dir,
        judge_evals_path=args.judge_evals,
        personas_dir=args.personas_dir,
        embeddings_path=args.embeddings,
        reference_matrix_path=args.reference_matrix,
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, cls=_NumpyEncoder)

    print(f"\nReport written → {out_path}")

    # Quick summary to stdout
    pi = report.get("persona_identification", {}).get("aggregate", {})
    if pi:
        acc = pi.get("accuracy")
        ci = pi.get("ci_95")
        sig = pi.get("significant")
        print(f"  Persona ID accuracy : {acc:.1%}  CI={ci}  significant={sig}")

    fi = report.get("individual_fidelity", {}).get("aggregate", {})
    if fi:
        print(f"  Fidelity median     : {fi.get('median')}  IQR={fi.get('iqr')}")

    gini = report.get("group_fidelity", {}).get("gini", {})
    if gini and "gini" in gini:
        print(f"  Gini                : {gini['gini']}  CI={gini.get('ci_95')}  in_range={gini.get('within_reference_range')}")


if __name__ == "__main__":
    main()
