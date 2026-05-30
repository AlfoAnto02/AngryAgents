"""
batch.py — Aggregate evaluation statistics across a batch of chats.

Discovers chat_<id>/metrics_report.json files under --base-dir,
loads them, and writes a batch_report.json with cross-chat statistics.

Usage:
  python -m angry_agents.src.eval.batch --base-dir data/eval/
  python -m angry_agents.src.eval.batch --base-dir data/eval/ --chats 1,2,5,7
  python -m angry_agents.src.eval.batch --base-dir data/eval/ --out data/eval/batch_report.json

Prerequisites: each chat must already have a metrics_report.json produced by
  python -m angry_agents.src.eval.report (or the UI judging pipeline).
"""

from __future__ import annotations

import argparse
import json
import logging
import re
from pathlib import Path

from angry_agents.src.eval import metrics_batch

log = logging.getLogger(__name__)


def discover_reports(base_dir: Path) -> list[tuple[int, Path]]:
    """Return (chat_id, path) pairs for all chat_<id>/metrics_report.json under base_dir."""
    results = []
    for report_path in sorted(base_dir.glob("chat_*/metrics_report.json")):
        m = re.match(r"chat_(\d+)$", report_path.parent.name)
        if not m:
            continue
        results.append((int(m.group(1)), report_path))
    return results


def load_report(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _extract(report: dict, chat_id: int) -> dict | None:
    """Pull the scalars we need from one per-chat metrics_report.json."""
    try:
        pi = report["persona_identification"]
        fi = report["individual_fidelity"]
        gf = report["group_fidelity"]

        accuracy = pi["aggregate"]["accuracy"]
        fidelity_median = fi["aggregate"]["median"]
        gini = gf["gini"]["gini"]

        cm = pi["confusion_matrix"]
        confusion = (cm["labels"], cm["matrix"])

        per_persona = {
            pname: data["overall"]["median"]
            for pname, data in fi["per_persona"].items()
            if data["overall"]["median"] is not None
        }

        return {
            "chat_id": chat_id,
            "accuracy": accuracy,
            "fidelity_median": fidelity_median,
            "gini": gini,
            "confusion": confusion,
            "per_persona": per_persona,
        }
    except (KeyError, TypeError) as exc:
        log.warning("chat_%d: skipped — missing key in metrics_report: %s", chat_id, exc)
        return None


def run_batch(
    base_dir: Path,
    chat_ids: list[int] | None = None,
    out: Path | None = None,
) -> dict:
    """
    Discover, load, and aggregate per-chat metrics_report.json files.

    chat_ids: restrict to these IDs; None = all discovered under base_dir.
    out: output path; default is base_dir/batch_report.json.
    """
    found = discover_reports(base_dir)
    if chat_ids is not None:
        wanted = set(chat_ids)
        found = [(cid, p) for cid, p in found if cid in wanted]

    if not found:
        raise ValueError(f"No chat_*/metrics_report.json found under {base_dir}")

    rows = []
    for chat_id, path in found:
        try:
            report = load_report(path)
        except Exception as exc:
            log.warning("chat_%d: failed to load %s — %s", chat_id, path, exc)
            continue
        row = _extract(report, chat_id)
        if row is not None:
            rows.append(row)

    if not rows:
        raise ValueError("No valid metrics_report.json files found after loading.")

    n = len(rows)
    batch_report = {
        "n_chats": n,
        "chat_ids": [r["chat_id"] for r in rows],
        "accuracy": metrics_batch.aggregate_accuracy([r["accuracy"] for r in rows]),
        "fidelity_median": metrics_batch.aggregate_fidelity([r["fidelity_median"] for r in rows]),
        "gini": metrics_batch.aggregate_gini([r["gini"] for r in rows]),
        "per_persona_fidelity": metrics_batch.aggregate_per_persona_fidelity(
            [r["per_persona"] for r in rows]
        ),
        "pooled_confusion_matrix": metrics_batch.pool_confusion_matrices(
            [r["confusion"] for r in rows]
        ),
    }

    out_path = out or (base_dir / "batch_report.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(batch_report, f, indent=2, ensure_ascii=False)

    acc = batch_report["accuracy"]
    fi = batch_report["fidelity_median"]
    gi = batch_report["gini"]
    print(f"Batch report: {n} chats → {out_path}")
    print(f"  Accuracy  : mean={acc['mean']:.1%}  std={acc['std']:.3f}  CI={acc['ci_95']}  [{acc['method']}]")
    print(f"  Fidelity  : mean={fi['mean']:.2f}   std={fi['std']:.3f}  CI={fi['ci_95']}  [{fi['method']}]")
    print(f"  Gini      : mean={gi['mean']:.3f}  std={gi['std']:.3f}  CI={gi['ci_95']}  [{gi['method']}]")

    return batch_report


def main() -> None:
    parser = argparse.ArgumentParser(description="Aggregate evaluation stats across a batch of chats.")
    parser.add_argument("--base-dir", type=Path, required=True,
                        help="Directory containing chat_<id>/metrics_report.json files.")
    parser.add_argument("--chats", type=str, default=None,
                        help="Comma-separated chat IDs to include (default: all discovered).")
    parser.add_argument("--out", type=Path, default=None,
                        help="Output path (default: base-dir/batch_report.json).")
    args = parser.parse_args()

    chat_ids = [int(x.strip()) for x in args.chats.split(",")] if args.chats else None
    run_batch(args.base_dir, chat_ids=chat_ids, out=args.out)


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    main()
