"""
token_tracker.py — Thread-safe token usage tracker for the judging pipeline.

Usage:
    tracker = TokenTracker(chat_id=1, model="gpt-4o-mini")

    # Inside a judge call (or any LLM call):
    tracker.record(
        judge_name="style_1",
        judge_role="style",
        call_type="main",          # "main" | "tool_followup" | "force_final"
        prompt_tokens=27260,
        completion_tokens=800,
    )

    # After all judges complete:
    tracker.write(out_dir / "token_report.json")

Cost rates (USD per 1M tokens) are keyed by model name prefix so that versioned
model IDs (e.g. "gpt-4o-mini-2024-07-18") still resolve.
"""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path


# ── Pricing table (USD / 1M tokens) ──────────────────────────────────────────
# Keys are matched by prefix — most specific prefix wins.
_RATES: list[tuple[str, float, float]] = [
    # prefix                   input/1M   output/1M
    ("gpt-5",                  1.25,      10.00),
    ("gpt-4o-mini",            0.15,      0.60),
    ("gpt-4o-2024-08-06",      2.50,      10.00),
    ("gpt-4o",                 2.50,      10.00),
    ("gpt-4-turbo",            10.00,     30.00),
    ("gpt-4",                  30.00,     60.00),
    ("gpt-3.5-turbo",          0.50,      1.50),
    # ollama / unknown — no cost
    ("",                       0.00,      0.00),
]


def _lookup_rates(model: str) -> tuple[float, float]:
    """Return (input_per_1m, output_per_1m) for the given model string."""
    model_lower = model.lower()
    for prefix, inp, out in _RATES:
        if model_lower.startswith(prefix):
            return inp, out
    return 0.0, 0.0


# ── Call record ───────────────────────────────────────────────────────────────

class CallRecord:
    __slots__ = ("judge_name", "judge_role", "call_type", "prompt_tokens", "completion_tokens")

    def __init__(
        self,
        judge_name: str,
        judge_role: str,
        call_type: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> None:
        self.judge_name = judge_name
        self.judge_role = judge_role
        self.call_type = call_type
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    def to_dict(self) -> dict:
        return {
            "judge_name": self.judge_name,
            "judge_role": self.judge_role,
            "call_type": self.call_type,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }


# ── Tracker ───────────────────────────────────────────────────────────────────

class TokenTracker:
    """Thread-safe accumulator for one judging run."""

    def __init__(self, chat_id: int, model: str) -> None:
        self.chat_id = chat_id
        self.model = model
        self._lock = threading.Lock()
        self._calls: list[CallRecord] = []
        self._started_at = datetime.now(timezone.utc).isoformat()

    # ------------------------------------------------------------------
    def record(
        self,
        judge_name: str,
        judge_role: str,
        call_type: str,
        prompt_tokens: int,
        completion_tokens: int,
    ) -> None:
        """Append one API call's token counts. Thread-safe."""
        rec = CallRecord(
            judge_name=judge_name,
            judge_role=judge_role,
            call_type=call_type,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
        with self._lock:
            self._calls.append(rec)

    # ------------------------------------------------------------------
    def summary(self) -> dict:
        """Build the full report dict (does not write to disk)."""
        with self._lock:
            calls_snapshot = list(self._calls)

        total_prompt = sum(c.prompt_tokens for c in calls_snapshot)
        total_completion = sum(c.completion_tokens for c in calls_snapshot)
        total_tokens = total_prompt + total_completion
        n_calls = len(calls_snapshot)

        # Per-call-type breakdown
        call_type_totals: dict[str, dict] = {}
        for c in calls_snapshot:
            if c.call_type not in call_type_totals:
                call_type_totals[c.call_type] = {
                    "prompt_tokens": 0, "completion_tokens": 0,
                    "total_tokens": 0, "n_calls": 0,
                }
            call_type_totals[c.call_type]["prompt_tokens"] += c.prompt_tokens
            call_type_totals[c.call_type]["completion_tokens"] += c.completion_tokens
            call_type_totals[c.call_type]["total_tokens"] += c.total_tokens
            call_type_totals[c.call_type]["n_calls"] += 1

        # Per-role breakdown
        role_totals: dict[str, dict] = {}
        for c in calls_snapshot:
            if c.judge_role not in role_totals:
                role_totals[c.judge_role] = {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "n_calls": 0,
                }
            role_totals[c.judge_role]["prompt_tokens"] += c.prompt_tokens
            role_totals[c.judge_role]["completion_tokens"] += c.completion_tokens
            role_totals[c.judge_role]["total_tokens"] += c.total_tokens
            role_totals[c.judge_role]["n_calls"] += 1

        # Per-judge breakdown
        judge_totals: dict[str, dict] = {}
        for c in calls_snapshot:
            if c.judge_name not in judge_totals:
                judge_totals[c.judge_name] = {
                    "role": c.judge_role,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                    "n_calls": 0,
                }
            judge_totals[c.judge_name]["prompt_tokens"] += c.prompt_tokens
            judge_totals[c.judge_name]["completion_tokens"] += c.completion_tokens
            judge_totals[c.judge_name]["total_tokens"] += c.total_tokens
            judge_totals[c.judge_name]["n_calls"] += 1

        # Cost
        inp_rate, out_rate = _lookup_rates(self.model)
        input_cost = (total_prompt / 1_000_000) * inp_rate
        output_cost = (total_completion / 1_000_000) * out_rate
        total_cost = input_cost + output_cost

        return {
            "chat_id": self.chat_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "started_at": self._started_at,
            "model": self.model,
            "n_judges": len({c.judge_name for c in calls_snapshot}),
            "totals": {
                "n_calls": n_calls,
                "prompt_tokens": total_prompt,
                "completion_tokens": total_completion,
                "total_tokens": total_tokens,
            },
            "cost_usd": {
                "model": self.model,
                "rates": {
                    "input_per_1m": inp_rate,
                    "output_per_1m": out_rate,
                },
                "input_cost": round(input_cost, 6),
                "output_cost": round(output_cost, 6),
                "total_cost": round(total_cost, 6),
                "total_cost_readable": f"${total_cost:.4f}",
            },
            "by_call_type": call_type_totals,
            "by_role": role_totals,
            "by_judge": judge_totals,
            "calls": [c.to_dict() for c in calls_snapshot],
        }

    # ------------------------------------------------------------------
    def write(self, path: Path) -> None:
        """Write the token report JSON to *path*. Creates parent dirs."""
        report = self.summary()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        cost = report["cost_usd"]["total_cost_readable"]
        total = report["totals"]["total_tokens"]
        print(f"  Token report → {path}  ({total:,} tokens, {cost})")
