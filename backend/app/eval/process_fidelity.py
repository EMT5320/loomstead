from __future__ import annotations

from math import sqrt
from typing import Any


def metric_summary(metric_id: str, values: list[float], *, baseline: str, scenario_id: str = "aggregate") -> dict[str, Any]:
    """输出 Phase 2 Eval 要求的 mean/std/n 统计形态。"""
    n = len(values)
    mean = sum(values) / n if n else 0.0
    variance = sum((value - mean) ** 2 for value in values) / n if n else 0.0
    return {
        "metric": metric_id,
        "mean": round(mean, 6),
        "std": round(sqrt(variance), 6),
        "n": n,
        "baseline": baseline,
        "scenarioId": scenario_id,
    }
