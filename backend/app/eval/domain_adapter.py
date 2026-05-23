from __future__ import annotations

from typing import Any

from app.domain.base import DomainAdapter, DomainIntervention
from app.domain.coding import CODING_GOAL_IDS, CodingDomainAdapter
from app.domain.narrative import NARRATIVE_GOAL_IDS, NarrativeDomainAdapter
from app.eval.process_fidelity import PROCESS_METRIC_IDS, metric_summary


BASELINE_CROSS_DOMAIN = "full_motivational_delegation"


def run_cross_domain_adapter_scenarios() -> dict[str, Any]:
    """运行 narrative primary + coding secondary 的最小跨域 adapter dry-run。"""
    suites: tuple[tuple[DomainAdapter, tuple[str, ...]], ...] = (
        (NarrativeDomainAdapter(), NARRATIVE_GOAL_IDS),
        (CodingDomainAdapter(), CODING_GOAL_IDS),
    )
    items: list[dict[str, Any]] = []
    for adapter, goal_ids in suites:
        for index, goal_id in enumerate(goal_ids, start=1):
            items.append(_run_adapter_goal(adapter, goal_id=goal_id, seed=index))

    domain_ids = sorted({str(item["domainId"]) for item in items})
    metrics = _domain_metric_summaries(items, domain_ids)
    domain_summaries = {
        domain_id: _domain_summary([item for item in items if item["domainId"] == domain_id])
        for domain_id in domain_ids
    }
    return {
        "ok": all(bool(item.get("ok")) for item in items),
        "suite": "cross_domain_adapter",
        "baseline": BASELINE_CROSS_DOMAIN,
        "passed": sum(1 for item in items if item.get("ok")),
        "total": len(items),
        "domains": domain_summaries,
        "metrics": metrics,
        "items": items,
    }


def _run_adapter_goal(adapter: DomainAdapter, *, goal_id: str, seed: int) -> dict[str, Any]:
    goal = adapter.parse_goal(goal_id)
    world = adapter.build_initial_world(goal.goal_id, seed)
    initial_observation = adapter.observe(world, goal)
    allowed_interventions = adapter.list_allowed_interventions(initial_observation, goal)
    interventions = _build_interventions(goal_id, goal.to_dict(), allowed_interventions)
    applied_events: list[dict[str, Any]] = []
    for intervention in interventions:
        applied_events.extend(adapter.apply_intervention(world, intervention))
    step_events = adapter.step_world(world, ticks=goal.max_steps or 1)
    final_observation = adapter.observe(world, goal)
    metrics = adapter.evaluate(world, goal)
    return {
        "domainId": adapter.domain_id,
        "scenarioId": goal.goal_id,
        "baseline": BASELINE_CROSS_DOMAIN,
        "ok": metrics.get("goal_success_rate", 0.0) >= 1.0
        and metrics.get("required_process_coverage", 0.0) >= 0.8,
        "metrics": metrics,
        "allowedInterventions": [str(item) for item in allowed_interventions],
        "appliedInterventionCount": len(interventions),
        "appliedEventCount": len(applied_events),
        "stepEventCount": len(step_events),
        "milestones": adapter.propose_default_milestones(goal),
        "initialObservation": initial_observation.to_dict(),
        "finalObservation": final_observation.to_dict(),
    }


def _build_interventions(
    goal_id: str,
    goal_payload: dict[str, Any],
    allowed_interventions: list[str],
) -> list[DomainIntervention]:
    target_agents = _target_agents(goal_payload)
    interventions: list[DomainIntervention] = []
    for index, intervention_type in enumerate(allowed_interventions, start=1):
        interventions.append(
            DomainIntervention(
                intervention_id=f"{goal_id}.intervention.{index:02d}",
                intervention_type=intervention_type,  # type: ignore[arg-type]
                target_agents=target_agents,
                payload={
                    "goalId": goal_id,
                    "constraintId": "must_run_tests" if intervention_type == "constraint_injection" else None,
                },
                expires_at_tick=None,
                reason=f"Cross-domain adapter dry-run for {goal_id}",
            )
        )
    return interventions


def _target_agents(goal_payload: dict[str, Any]) -> list[str]:
    outcome = goal_payload.get("desiredOutcome", {}) if isinstance(goal_payload.get("desiredOutcome"), dict) else {}
    agents = [
        str(outcome.get("npcId") or ""),
        str(outcome.get("targetNpcId") or ""),
    ]
    return [agent_id for agent_id in agents if agent_id] or ["pm", "architect", "implementer", "reviewer"]


def _domain_metric_summaries(items: list[dict[str, Any]], domain_ids: list[str]) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for scenario_id, scoped_items in [("aggregate", items)] + [
        (domain_id, [item for item in items if item["domainId"] == domain_id])
        for domain_id in domain_ids
    ]:
        for metric_id in PROCESS_METRIC_IDS:
            summaries.append(
                metric_summary(
                    metric_id,
                    [float(item.get("metrics", {}).get(metric_id, 0.0)) for item in scoped_items],
                    baseline=BASELINE_CROSS_DOMAIN,
                    scenario_id=scenario_id,
                )
            )
    return summaries


def _domain_summary(items: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "passed": sum(1 for item in items if item.get("ok")),
        "total": len(items),
        "scenarioIds": [str(item.get("scenarioId") or "") for item in items],
    }
