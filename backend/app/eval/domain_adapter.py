from __future__ import annotations

from pathlib import Path
from typing import Any

from app.domain.base import DomainAdapter, DomainIntervention
from app.domain.coding import CODING_GOAL_IDS, CodingDomainAdapter
from app.domain.narrative import NARRATIVE_GOAL_IDS, NarrativeDomainAdapter
from app.eval.runner import (
    _artifact_record,
    _summary_only,
    _timestamp_slug,
    _unique_run_dir,
    _utc_timestamp,
    _write_eval_manifest,
    _write_json,
    _write_jsonl,
)
from app.eval.process_fidelity import PROCESS_METRIC_IDS, metric_summary


BASELINE_CROSS_DOMAIN = "full_motivational_delegation"


def run_cross_domain_adapter_scenarios(*, export_dir: str | Path | None = None) -> dict[str, Any]:
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
    result = {
        "ok": all(bool(item.get("ok")) for item in items),
        "suite": "cross_domain_adapter",
        "baseline": BASELINE_CROSS_DOMAIN,
        "passed": sum(1 for item in items if item.get("ok")),
        "total": len(items),
        "domains": domain_summaries,
        "metrics": metrics,
        "items": items,
    }
    if export_dir is not None:
        result["export"] = _export_cross_domain_adapter_eval(result, Path(export_dir))
    return result


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
        "domainEvidence": _extract_domain_evidence(world),
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


def _extract_domain_evidence(world: Any) -> dict[str, Any]:
    if not isinstance(world, dict):
        return {}
    evidence_keys = (
        "repoFixture",
        "artifacts",
        "prePatchTestReports",
        "partialPatchTestReports",
        "testReports",
        "reviewReports",
        "counterfactualReplays",
        "dependencies",
    )
    # 只抽取跨域 dry-run 的可审计工件，避免把完整 world 快照塞进 Eval item。
    return {
        key: world.get(key, {})
        for key in evidence_keys
        if isinstance(world.get(key), dict) and world.get(key)
    }


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


def _export_cross_domain_adapter_eval(result: dict[str, Any], base_dir: Path) -> dict[str, Any]:
    """导出跨域 adapter 证据，复用 Eval manifest 字段保持归档格式一致。"""
    created_at = _utc_timestamp()
    run_dir = _unique_run_dir(base_dir / f"domain_{_timestamp_slug(created_at)}")
    per_scenario_dir = run_dir / "per_scenario"
    per_scenario_dir.mkdir(parents=True, exist_ok=True)
    artifacts: list[dict[str, Any]] = []

    summary_path = run_dir / "summary.json"
    _write_json(summary_path, _summary_only(result))
    artifacts.append(_artifact_record(summary_path, run_dir, kind="summary_json"))

    domain_summary_path = run_dir / "domain_summaries.json"
    _write_json(domain_summary_path, result.get("domains", {}))
    artifacts.append(_artifact_record(domain_summary_path, run_dir, kind="domain_summaries_json"))

    items = [item for item in result.get("items", []) if isinstance(item, dict)]
    for item in items:
        scenario_id = str(item.get("scenarioId") or "unknown_scenario")
        scenario_path = per_scenario_dir / f"{scenario_id}.json"
        _write_json(scenario_path, item)
        artifacts.append(
            _artifact_record(
                scenario_path,
                run_dir,
                kind="per_scenario_json",
                scenario_id=scenario_id,
                baseline=str(item.get("baseline") or ""),
            )
        )
        artifacts.extend(_write_domain_evidence_files(run_dir, item))

    trace_specs = (
        ("domain_metrics.jsonl", "domain_metrics_jsonl", _domain_metric_trace_items(items)),
        ("observation_trace.jsonl", "observation_trace_jsonl", _domain_observation_trace_items(items)),
        ("intervention_trace.jsonl", "intervention_trace_jsonl", _domain_intervention_trace_items(items)),
        ("domain_evidence.jsonl", "domain_evidence_jsonl", _domain_evidence_trace_items(items)),
    )
    for filename, kind, trace_items in trace_specs:
        trace_path = run_dir / filename
        _write_jsonl(trace_path, trace_items)
        artifacts.append(_artifact_record(trace_path, run_dir, kind=kind, row_count=len(trace_items)))

    manifest_path = _write_eval_manifest(
        run_dir=run_dir,
        result=result,
        artifacts=artifacts,
        created_at=created_at,
        export_kind="cross_domain_adapter_dataset",
    )
    return {
        "runDir": str(run_dir),
        "manifest": str(manifest_path),
        "artifactCount": len(artifacts) + 1,
    }


def _domain_metric_trace_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in items:
        metrics = item.get("metrics", {}) if isinstance(item.get("metrics"), dict) else {}
        for metric_id in PROCESS_METRIC_IDS:
            rows.append(
                {
                    "domainId": item.get("domainId"),
                    "scenarioId": item.get("scenarioId"),
                    "baseline": item.get("baseline"),
                    "metric": metric_id,
                    "value": float(metrics.get(metric_id, 0.0)),
                }
            )
    return rows


def _domain_observation_trace_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in items:
        for stage in ("initialObservation", "finalObservation"):
            observation = item.get(stage, {}) if isinstance(item.get(stage), dict) else {}
            rows.append(
                {
                    "domainId": item.get("domainId"),
                    "scenarioId": item.get("scenarioId"),
                    "baseline": item.get("baseline"),
                    "stage": stage,
                    "tick": observation.get("tick"),
                    "goalProgress": observation.get("goalProgress", {}),
                    "evalSignals": observation.get("evalSignals", {}),
                    "recentEventCount": len(observation.get("recentEvents", []))
                    if isinstance(observation.get("recentEvents"), list)
                    else 0,
                }
            )
    return rows


def _domain_intervention_trace_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in items:
        rows.append(
            {
                "domainId": item.get("domainId"),
                "scenarioId": item.get("scenarioId"),
                "baseline": item.get("baseline"),
                "allowedInterventions": item.get("allowedInterventions", []),
                "appliedInterventionCount": item.get("appliedInterventionCount", 0),
                "appliedEventCount": item.get("appliedEventCount", 0),
                "stepEventCount": item.get("stepEventCount", 0),
                "milestones": item.get("milestones", []),
            }
        )
    return rows


def _domain_evidence_trace_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in items:
        evidence = item.get("domainEvidence", {}) if isinstance(item.get("domainEvidence"), dict) else {}
        if not evidence:
            continue
        rows.append(
            {
                "domainId": item.get("domainId"),
                "scenarioId": item.get("scenarioId"),
                "baseline": item.get("baseline"),
                "domainEvidence": evidence,
            }
        )
    return rows


def _write_domain_evidence_files(run_dir: Path, item: dict[str, Any]) -> list[dict[str, Any]]:
    """把 coding fixture 的 patch / test / review 证据写成独立 artifact。"""
    evidence = item.get("domainEvidence", {}) if isinstance(item.get("domainEvidence"), dict) else {}
    if not evidence:
        return []
    scenario_id = str(item.get("scenarioId") or "unknown_scenario")
    baseline = str(item.get("baseline") or "")
    evidence_dir = run_dir / "domain_evidence" / _safe_path_part(scenario_id)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    artifacts: list[dict[str, Any]] = []

    repo_fixture = evidence.get("repoFixture", {})
    if isinstance(repo_fixture, dict) and repo_fixture:
        repo_path = evidence_dir / "repo_fixture.json"
        _write_json(repo_path, repo_fixture)
        artifacts.append(
            _artifact_record(
                repo_path,
                run_dir,
                kind="domain_evidence_repo_fixture_json",
                scenario_id=scenario_id,
                baseline=baseline,
            )
        )
        derived_graph = repo_fixture.get("derivedDependencyGraph", {})
        if isinstance(derived_graph, dict) and derived_graph:
            # 依赖图单独导出，方便审查 cross-file fixture 是否真的来自源码 import。
            graph_path = evidence_dir / "derived_dependency_graph.json"
            _write_json(graph_path, derived_graph)
            artifacts.append(
                _artifact_record(
                    graph_path,
                    run_dir,
                    kind="domain_evidence_derived_dependency_graph_json",
                    scenario_id=scenario_id,
                    baseline=baseline,
                )
            )

    artifact_map = evidence.get("artifacts", {})
    if isinstance(artifact_map, dict):
        for artifact_id, artifact in sorted(artifact_map.items()):
            if not isinstance(artifact, dict):
                continue
            patch_text = str(artifact.get("patchText", ""))
            if not patch_text:
                continue
            patch_name = _safe_path_part(str(artifact_id))
            if not patch_name.endswith(".patch"):
                patch_name = f"{patch_name}.patch"
            patch_path = evidence_dir / patch_name
            patch_path.write_text(patch_text + "\n", encoding="utf-8")
            artifacts.append(
                _artifact_record(
                    patch_path,
                    run_dir,
                    kind="domain_evidence_patch_diff",
                    scenario_id=scenario_id,
                    baseline=baseline,
                )
            )

    for report_key, filename_prefix, kind in (
        ("prePatchTestReports", "pre_patch_test_report", "domain_evidence_pre_patch_test_report_json"),
        ("partialPatchTestReports", "partial_patch_test_report", "domain_evidence_partial_patch_test_report_json"),
        ("testReports", "test_report", "domain_evidence_test_report_json"),
        ("reviewReports", "review_report", "domain_evidence_review_report_json"),
        ("counterfactualReplays", "counterfactual_replay", "domain_evidence_counterfactual_replay_json"),
    ):
        report_map = evidence.get(report_key, {})
        if not isinstance(report_map, dict):
            continue
        for report_id, report in sorted(report_map.items()):
            if not isinstance(report, dict):
                continue
            report_path = evidence_dir / f"{filename_prefix}_{_safe_path_part(str(report_id))}.json"
            _write_json(report_path, report)
            artifacts.append(
                _artifact_record(
                    report_path,
                    run_dir,
                    kind=kind,
                    scenario_id=scenario_id,
                    baseline=baseline,
                )
            )

    return artifacts


def _safe_path_part(value: str) -> str:
    return "".join(char if char.isalnum() or char in {"-", "_", "."} else "_" for char in value)
