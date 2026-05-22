from __future__ import annotations

from math import sqrt
from typing import Any


PROCESS_METRIC_IDS = (
    "goal_success_rate",
    "shortcut_violation_rate",
    "required_process_coverage",
    "forced_action_rate",
    "agent_initiated_action_ratio",
    "intervention_overreach_rate",
    "relationship_memory_causal_use_rate",
    "causal_trace_coverage",
    "relationship_consistency",
    "process_believability_score",
)


def metric_summary(metric_id: str, values: list[float], *, baseline: str, scenario_id: str = "aggregate") -> dict[str, Any]:
    """输出 Phase 2 Eval 要求的 mean/std/n 摘要。"""
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


def process_metric_summaries(items: list[dict[str, Any]], *, baseline: str) -> list[dict[str, Any]]:
    """汇总 Process Fidelity 每项指标的 mean/std/n。"""
    metrics: list[dict[str, Any]] = []
    for metric_id in PROCESS_METRIC_IDS:
        values = [float(item.get("metrics", {}).get(metric_id, 0.0)) for item in items]
        metrics.append(metric_summary(metric_id, values, baseline=baseline))
    return metrics


def build_process_metrics(
    *,
    process_checks: dict[str, bool],
    required_process_ids: tuple[str, ...],
    shortcut_events: int,
    goal_relevant_state_changes: int,
    forced_actions: int,
    goal_relevant_actions: int,
    overreaching_interventions: int,
    total_interventions: int,
    state_changes_with_source: int,
    relationship_relevant_decisions: int,
    decisions_with_relationship_memory: int,
    goal_success_override: bool | None = None,
) -> dict[str, float]:
    """根据规则级过程证据计算 Process Fidelity 指标。"""
    required_total = max(1, len(required_process_ids))
    required_satisfied = sum(1 for process_id in required_process_ids if process_checks.get(process_id, False))
    action_total = max(1, goal_relevant_actions)
    intervention_total = max(1, total_interventions)
    state_change_total = max(1, goal_relevant_state_changes)
    relationship_decision_total = max(1, relationship_relevant_decisions)

    shortcut_violation_rate = _safe_ratio(shortcut_events, state_change_total)
    required_process_coverage = _safe_ratio(required_satisfied, required_total)
    forced_action_rate = _safe_ratio(forced_actions, action_total)
    agent_initiated_action_ratio = _safe_ratio(goal_relevant_actions - forced_actions, action_total)
    intervention_overreach_rate = _safe_ratio(overreaching_interventions, intervention_total)
    causal_trace_coverage = _safe_ratio(state_changes_with_source, state_change_total)
    relationship_memory_causal_use_rate = _safe_ratio(decisions_with_relationship_memory, relationship_decision_total)
    relationship_consistency = 1.0 if process_checks.get("relationship_edge_trace", False) else 0.0
    goal_success = (
        bool(goal_success_override)
        if goal_success_override is not None
        else process_checks.get("goal_relevant_tool_event", False) and process_checks.get("relationship_edge_trace", False)
    )
    goal_success_rate = 1.0 if goal_success else 0.0
    process_believability_score = _weighted_mean(
        [
            1.0 - shortcut_violation_rate,
            required_process_coverage,
            agent_initiated_action_ratio,
            causal_trace_coverage,
            relationship_consistency,
        ]
    )
    return {
        "goal_success_rate": round(goal_success_rate, 6),
        "shortcut_violation_rate": round(shortcut_violation_rate, 6),
        "required_process_coverage": round(required_process_coverage, 6),
        "forced_action_rate": round(forced_action_rate, 6),
        "agent_initiated_action_ratio": round(agent_initiated_action_ratio, 6),
        "intervention_overreach_rate": round(intervention_overreach_rate, 6),
        "relationship_memory_causal_use_rate": round(relationship_memory_causal_use_rate, 6),
        "causal_trace_coverage": round(causal_trace_coverage, 6),
        "relationship_consistency": round(relationship_consistency, 6),
        "process_believability_score": round(process_believability_score, 6),
    }


def _safe_ratio(numerator: int | float, denominator: int | float) -> float:
    return float(numerator) / float(denominator) if float(denominator) else 0.0


def _weighted_mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0
