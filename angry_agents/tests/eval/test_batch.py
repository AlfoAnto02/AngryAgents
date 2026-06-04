"""
Tests for metrics_batch.py and batch.py.

All tests are pure / in-memory — no DB, no external files required.
"""

from __future__ import annotations

import json
import math
import tempfile
from pathlib import Path

import pytest

from angry_agents.src.eval import metrics_batch
from angry_agents.src.eval.batch import discover_reports, run_batch, _extract


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MINIMAL_REPORT = {
    "persona_identification": {
        "aggregate": {"accuracy": 0.5, "correct": 10, "total": 20},
        "confusion_matrix": {
            "labels": ["A", "B"],
            "matrix": [[8, 2], [3, 7]],
            "precision_recall_f1": {},
            "cohen_kappa": 0.5,
        },
        "per_judge": [],
        "judge_accuracy_variance": {},
    },
    "individual_fidelity": {
        "aggregate": {"median": 3.5, "mean": 3.4, "n": 20, "iqr": 1.0, "variance": 0.5, "std": 0.7, "ci_95": [3.0, 4.0]},
        "per_persona": {
            "A": {"overall": {"median": 3.8, "mean": 3.7, "n": 10, "iqr": 0.8, "variance": 0.3, "std": 0.5, "ci_95": [3.2, 4.2]}, "per_judge_type": {}},
            "B": {"overall": {"median": 3.2, "mean": 3.1, "n": 10, "iqr": 1.0, "variance": 0.4, "std": 0.6, "ci_95": [2.8, 3.6]}, "per_judge_type": {}},
        },
        "judge_type_agreement": {},
    },
    "group_fidelity": {
        "gini": {"gini": 0.33, "ci_95": [0.28, 0.38], "within_reference_range": True, "z_vs_reference": 0.0},
        "judge_scores": {"mean": 3.7, "median": 4.0, "n": 20, "iqr": 1.0, "ci_95": [3.5, 4.0]},
    },
}


def _write_report(base_dir: Path, chat_id: int, report: dict) -> None:
    chat_dir = base_dir / f"chat_{chat_id}"
    chat_dir.mkdir(parents=True, exist_ok=True)
    (chat_dir / "metrics_report.json").write_text(json.dumps(report), encoding="utf-8")


# ---------------------------------------------------------------------------
# metrics_batch unit tests
# ---------------------------------------------------------------------------

class TestAggregateScalar:
    def test_bootstrap_for_small_n(self):
        values = [0.4, 0.5, 0.6]
        result = metrics_batch.aggregate_scalar(values)
        assert result["method"] == "bootstrap"
        assert result["n"] == 3
        assert math.isclose(result["mean"], 0.5, abs_tol=1e-4)

    def test_clt_for_n_gte_threshold(self):
        values = [float(i) / 100 for i in range(20, 60)]  # 40 values
        result = metrics_batch.aggregate_scalar(values)
        assert result["method"] == "clt"
        assert result["n"] == 40

    def test_ci_is_ordered(self):
        values = [0.3, 0.4, 0.5, 0.6, 0.7] * 4  # 20 values → CLT
        result = metrics_batch.aggregate_scalar(values)
        lo, hi = result["ci_95"]
        assert lo <= result["mean"] <= hi

    def test_single_value(self):
        result = metrics_batch.aggregate_scalar([0.5])
        assert result["n"] == 1
        assert result["variance"] == 0.0
        assert result["std"] == 0.0


class TestPoolConfusionMatrices:
    def test_same_labels(self):
        labels = ["A", "B"]
        m1 = [[8, 2], [3, 7]]
        m2 = [[6, 4], [2, 8]]
        result = metrics_batch.pool_confusion_matrices([(labels, m1), (labels, m2)])
        assert result["matrix"] == [[14, 6], [5, 15]]
        assert set(result["labels"]) == {"A", "B"}
        assert 0.0 <= result["kappa"] <= 1.0
        assert 0.0 <= result["macro_f1"] <= 1.0

    def test_different_labels_union(self):
        m1 = [[5, 1], [2, 4]]
        m2 = [[3]]
        result = metrics_batch.pool_confusion_matrices(
            [(["A", "B"], m1), (["C"], m2)]
        )
        assert set(result["labels"]) == {"A", "B", "C"}

    def test_per_persona_keys_match_labels(self):
        labels = ["X", "Y", "Z"]
        m = [[3, 1, 0], [0, 4, 1], [1, 0, 5]]
        result = metrics_batch.pool_confusion_matrices([(labels, m)])
        assert set(result["per_persona"].keys()) == set(labels)



# ---------------------------------------------------------------------------
# batch.py integration tests (filesystem, no DB)
# ---------------------------------------------------------------------------

class TestDiscoverReports:
    def test_finds_chat_dirs(self, tmp_path):
        _write_report(tmp_path, 1, MINIMAL_REPORT)
        _write_report(tmp_path, 7, MINIMAL_REPORT)
        found = discover_reports(tmp_path)
        assert {cid for cid, _ in found} == {1, 7}

    def test_ignores_non_matching_dirs(self, tmp_path):
        (tmp_path / "other_dir").mkdir()
        (tmp_path / "other_dir" / "metrics_report.json").write_text("{}", encoding="utf-8")
        found = discover_reports(tmp_path)
        assert found == []

    def test_sorted_by_chat_id(self, tmp_path):
        for cid in [5, 2, 9]:
            _write_report(tmp_path, cid, MINIMAL_REPORT)
        found = discover_reports(tmp_path)
        ids = [cid for cid, _ in found]
        assert ids == sorted(ids)


class TestExtract:
    def test_extracts_all_fields(self):
        row = _extract(MINIMAL_REPORT, chat_id=1)
        assert row is not None
        assert row["chat_id"] == 1
        assert row["accuracy"] == 0.5
        assert row["fidelity_median"] == 3.5
        assert row["gini"] == 0.33
        assert row["confusion"] == (["A", "B"], [[8, 2], [3, 7]])

    def test_returns_none_on_missing_key(self):
        row = _extract({"persona_identification": {}}, chat_id=99)
        assert row is None


class TestRunBatch:
    def test_smoke_small_n_uses_bootstrap(self, tmp_path):
        for cid in range(3):
            report = {**MINIMAL_REPORT, "group_fidelity": {"gini": {"gini": 0.30 + cid * 0.02}}}
            _write_report(tmp_path, cid, MINIMAL_REPORT)

        result = run_batch(tmp_path, out=tmp_path / "out.json")
        assert result["n_chats"] == 3
        assert result["accuracy"]["method"] == "bootstrap"
        assert (tmp_path / "out.json").exists()

    def test_large_n_uses_clt(self, tmp_path):
        for cid in range(20):
            _write_report(tmp_path, cid, MINIMAL_REPORT)

        result = run_batch(tmp_path)
        assert result["n_chats"] == 20
        assert result["accuracy"]["method"] == "clt"

    def test_filter_by_chat_ids(self, tmp_path):
        for cid in range(5):
            _write_report(tmp_path, cid, MINIMAL_REPORT)

        result = run_batch(tmp_path, chat_ids=[0, 2, 4])
        assert result["n_chats"] == 3
        assert set(result["chat_ids"]) == {0, 2, 4}

    def test_raises_when_no_reports(self, tmp_path):
        with pytest.raises(ValueError):
            run_batch(tmp_path)

    def test_skips_invalid_reports(self, tmp_path, caplog):
        _write_report(tmp_path, 1, MINIMAL_REPORT)
        bad_dir = tmp_path / "chat_2"
        bad_dir.mkdir()
        (bad_dir / "metrics_report.json").write_text("{}", encoding="utf-8")

        result = run_batch(tmp_path)
        assert result["n_chats"] == 1  # only the valid one

    def test_output_contains_all_keys(self, tmp_path):
        _write_report(tmp_path, 1, MINIMAL_REPORT)
        result = run_batch(tmp_path)
        for key in ("n_chats", "chat_ids", "accuracy", "fidelity_median", "gini",
                    "group_fidelity", "pooled_confusion_matrix"):
            assert key in result
