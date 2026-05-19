"""bootstrap.py — non-parametric CI estimation via resampling."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import numpy as np


def bootstrap_ci(
    data: list[Any] | np.ndarray,
    stat_fn: Callable[[np.ndarray], float],
    *,
    n: int = 10_000,
    ci: float = 0.95,
    seed: int | None = None,
) -> tuple[float, float]:
    """
    Return (lo, hi) bootstrap confidence interval for stat_fn applied to data.

    Works for any statistic (median, mean, Gini, Spearman, ...).
    Does not assume a parametric distribution — safe for n < 30.
    """
    rng = np.random.default_rng(seed)
    arr = np.asarray(data, dtype=float)
    stats = np.empty(n, dtype=float)
    for i in range(n):
        sample = rng.choice(arr, size=len(arr), replace=True)
        stats[i] = stat_fn(sample)
    alpha = (1.0 - ci) / 2.0
    return float(np.nanpercentile(stats, alpha * 100)), float(np.nanpercentile(stats, (1 - alpha) * 100))
