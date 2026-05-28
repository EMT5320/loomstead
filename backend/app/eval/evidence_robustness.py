from __future__ import annotations

import hashlib
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable

from app.eval.domain_adapter import BASELINE_CROSS_DOMAIN, run_cross_domain_adapter_scenarios
from app.eval.process_fidelity import metric_summary
from app.eval.runner import (
    BASELINE_FULL,
    _artifact_record,
    _git_snapshot,
    _summary_only,
    _timestamp_slug,
    _unique_run_dir,
    _utc_timestamp,
    _write_eval_manifest,
    _write_json,
    _write_jsonl,
    run_process_fidelity_scenarios,
)
from app.eval.scenarios import DEFAULT_PROCESS_GOALS, ProcessGoalSpec


PERTURBATION_IDS = (
    "source_order_shuffle",
    "source_variation_weak_noise",
    "source_variation_duplicate",
    "source_variation_irrelevant",
)
STRICT_GATE_VERSION = "phase2.evidence_robustness.strict_gate.v1"
DOMAIN_SIGNATURE_VERSION = "phase2.evidence_robustness.domain_signature.v2"
EXPECTED_DOMAIN_GROUPS = ("loomstead.coding.v0", "loomstead.town.v0")
SOURCE_LIST_KEYS = {
    "sourceEventIds",
    "subjectiveMemoryRefs",
    "relationshipSourceIds",
    "heuristicSourceIds",
}


def run_evidence_robustness_scenarios(
    *,
    process_scenarios: tuple[ProcessGoalSpec, ...] = DEFAULT_PROCESS_GOALS,
    process_seed_count: int = 1,
    domain_seed_count: int = 1,
    export_dir: str | Path | None = None,
) -> dict[str, Any]:
    """运行 process/domain 的 source perturbation 自动鲁棒性闭环。"""
    process_seed_count = max(1, int(process_seed_count))
    domain_seed_count = max(1, int(domain_seed_count))

    process_result = run_process_fidelity_scenarios(
        scenarios=process_scenarios,
        provider_mode="rule",
        seed_count=process_seed_count,
    )
    domain_result = run_cross_domain_adapter_scenarios(seed_count=domain_seed_count)

    process_items = list(process_result.get("baselines", {}).get(BASELINE_FULL, {}).get("items", []))
    domain_items = list(domain_result.get("items", []))

    process_probe = _probe_items(
        suite_id="process",
        items=process_items,
        signature_builder=_process_signature,
    )
    domain_probe = _probe_items(
        suite_id="domain",
        items=domain_items,
        signature_builder=_domain_signature,
    )

    metrics: list[dict[str, Any]] = []
    metrics.extend(_invariance_metrics(process_probe, suite_prefix="process", baseline=BASELINE_FULL))
    metrics.extend(_invariance_metrics(domain_probe, suite_prefix="domain", baseline=BASELINE_CROSS_DOMAIN))
    metrics.extend(_group_robustness_metrics(domain_probe, baseline=BASELINE_CROSS_DOMAIN))
    metrics.extend(
        [
            metric_summary(
                "process_evidence_robustness_score",
                [float(process_probe.get("overallInvarianceRate", 0.0))],
                baseline=BASELINE_FULL,
            ),
            metric_summary(
                "domain_evidence_robustness_score",
                [float(domain_probe.get("overallInvarianceRate", 0.0))],
                baseline=BASELINE_CROSS_DOMAIN,
            ),
            metric_summary(
                "evidence_robustness_score",
                [
                    float(process_probe.get("overallInvarianceRate", 0.0)),
                    float(domain_probe.get("overallInvarianceRate", 0.0)),
                ],
                baseline=BASELINE_FULL,
            ),
        ]
    )

    passed = int(process_probe.get("stableCount", 0)) + int(domain_probe.get("stableCount", 0))
    total = int(process_probe.get("totalChecks", 0)) + int(domain_probe.get("totalChecks", 0))
    robustness_checks_pass = total > 0 and bool(process_probe.get("allStable")) and bool(domain_probe.get("allStable"))
    strict_gate = _build_strict_gate(
        process_result=process_result,
        domain_result=domain_result,
        process_probe=process_probe,
        domain_probe=domain_probe,
        total_checks=total,
        robustness_checks_pass=robustness_checks_pass,
    )
    result = {
        "ok": bool(strict_gate.get("pass")),
        "suite": "evidence_robustness",
        "baseline": BASELINE_FULL,
        "providerMode": "rule",
        "robustnessChecksPass": robustness_checks_pass,
        "strictGate": strict_gate,
        "seedCount": {
            "process": process_seed_count,
            "domain": domain_seed_count,
        },
        "passed": passed,
        "total": total,
        "metrics": metrics,
        "process": {
            "baseEvalOk": bool(process_result.get("ok")),
            "scenarioCount": len(process_items),
            "selectedScenarioIds": [item.scenario_id for item in process_scenarios],
            **process_probe,
        },
        "domain": {
            "baseEvalOk": bool(domain_result.get("ok")),
            "scenarioCount": len(domain_items),
            **domain_probe,
        },
    }
    if export_dir is not None:
        result["export"] = _export_evidence_robustness_eval(result, Path(export_dir))
    return result


def _probe_items(
    *,
    suite_id: str,
    items: list[dict[str, Any]],
    signature_builder: Callable[[dict[str, Any]], dict[str, Any]],
) -> dict[str, Any]:
    details: list[dict[str, Any]] = []
    stable_count = 0
    total_checks = 0
    perturbation_stats: dict[str, dict[str, Any]] = {
        perturbation_id: {"stable": 0, "total": 0}
        for perturbation_id in PERTURBATION_IDS
    }
    group_stats: dict[str, dict[str, Any]] = {}

    for item in items:
        scenario_id = _scenario_id(item)
        group_id = _probe_group_id(suite_id, item)
        group = group_stats.setdefault(group_id, {"stable": 0, "total": 0, "perturbations": _empty_perturbation_stats()})
        base_signature = signature_builder(item)
        row = {
            "suite": suite_id,
            "scenarioId": scenario_id,
            "groupId": group_id,
            "domainId": str(item.get("domainId") or ""),
            "baseline": str(item.get("baseline") or ""),
            "seed": item.get("seed"),
            "baseSignature": base_signature,
            "perturbations": [],
        }

        for perturbation_id in PERTURBATION_IDS:
            mutated = _apply_perturbation(item, perturbation_id=perturbation_id, scenario_id=scenario_id)
            mutated_signature = signature_builder(mutated)
            stable = mutated_signature == base_signature
            total_checks += 1
            perturbation_stats[perturbation_id]["total"] += 1
            group["total"] += 1
            group["perturbations"][perturbation_id]["total"] += 1
            if stable:
                stable_count += 1
                perturbation_stats[perturbation_id]["stable"] += 1
                group["stable"] += 1
                group["perturbations"][perturbation_id]["stable"] += 1
            row["perturbations"].append(
                {
                    "perturbationId": perturbation_id,
                    "stable": stable,
                    "signature": mutated_signature,
                }
            )

        details.append(row)

    perturbations = []
    for perturbation_id in PERTURBATION_IDS:
        stats = perturbation_stats[perturbation_id]
        total = int(stats["total"])
        stable = int(stats["stable"])
        perturbations.append(
            {
                "perturbationId": perturbation_id,
                "stableCount": stable,
                "total": total,
                "invarianceRate": round(_safe_ratio(stable, total), 6),
            }
        )

    return {
        "perturbations": perturbations,
        "stableCount": stable_count,
        "totalChecks": total_checks,
        "overallInvarianceRate": round(_safe_ratio(stable_count, total_checks), 6),
        "allStable": stable_count == total_checks,
        "groups": _format_groups(group_stats),
        "signatureKinds": _signature_kinds(details),
        "items": details,
    }


def _process_signature(item: dict[str, Any]) -> dict[str, Any]:
    evidence = item.get("evidence", {}) if isinstance(item.get("evidence"), dict) else {}
    goal_event_ids = {
        str(event.get("eventId") or "")
        for event in evidence.get("goalToolEvents", [])
        if isinstance(event, dict) and str(event.get("eventId") or "")
    }
    subjective_ids = _to_id_set(evidence.get("subjectiveMemoryRefs", []))
    relationship_ids = _to_id_set(evidence.get("relationshipSourceIds", []))
    memory_trace_links = [
        event
        for event in evidence.get("memoryTraceLinks", [])
        if isinstance(event, dict)
    ]
    linked_memory_count = sum(
        1
        for event in memory_trace_links
        if str(event.get("sourceEventId") or "") in goal_event_ids
    )
    counterfactual = evidence.get("counterfactualReplay", {}) if isinstance(evidence.get("counterfactualReplay"), dict) else {}
    return {
        "goalEventCount": len(goal_event_ids),
        "subjectiveGoalLinkCount": len(goal_event_ids & subjective_ids),
        "relationshipGoalLinkCount": len(goal_event_ids & relationship_ids),
        "memoryTraceGoalLinkCount": linked_memory_count,
        "futureBehaviorReference": bool(counterfactual.get("effect")),
        "subjectiveMemoryCausalEffect": bool(counterfactual.get("subjectiveMemoryEffect")),
        "counterfactualToolSelectionChanged": bool(counterfactual.get("toolSelectionChanged")),
    }


def _domain_signature(item: dict[str, Any]) -> dict[str, Any]:
    domain_id = str(item.get("domainId") or "")
    if domain_id == "loomstead.town.v0":
        return _narrative_domain_signature(item)
    if domain_id == "loomstead.coding.v0":
        return _coding_domain_signature(item)
    return _generic_domain_signature(item)


def _generic_domain_signature(item: dict[str, Any]) -> dict[str, Any]:
    sources = _collect_source_ids(item)
    events = _collect_event_ids(item)
    anchored = sorted(source_id for source_id in sources if source_id in events)
    return {
        "signatureId": f"{DOMAIN_SIGNATURE_VERSION}.generic",
        "eventIdCount": len(events),
        "anchoredSourceLinkCount": len(anchored),
        "hasAnchoredSourceLink": bool(anchored),
    }


def _narrative_domain_signature(item: dict[str, Any]) -> dict[str, Any]:
    common = _generic_domain_signature(item)
    domain_evidence = _domain_evidence(item)
    replays = _counterfactual_replays(domain_evidence, version_contains="narrative")
    goal_progress = _goal_progress_signature(item)
    eval_signals = _final_eval_signals(item)
    return {
        **{key: value for key, value in common.items() if key != "signatureId"},
        "signatureId": f"{DOMAIN_SIGNATURE_VERSION}.narrative",
        "replayCount": len(replays),
        "goalEventCount": sum(len(_list_value(replay.get("goalEventIds"))) for replay in replays),
        "relationshipEvidenceCount": sum(len(_list_value(replay.get("goalRelationshipEdgeIds"))) for replay in replays),
        "subjectiveMemoryEvidenceCount": sum(len(_list_value(replay.get("goalSubjectiveMemoryRecordIds"))) for replay in replays),
        "heuristicEvidenceCount": sum(len(_list_value(replay.get("goalHeuristicIds"))) for replay in replays),
        "comparisonCount": sum(int(replay.get("comparisonCount") or 0) for replay in replays),
        "changedDecisionCount": sum(int(replay.get("changedDecisionCount") or 0) for replay in replays),
        "scoreChangedCount": sum(_score_changed_count(replay) for replay in replays),
        "changeRateBuckets": sorted({_rounded(replay.get("changeRate")) for replay in replays}),
        "goalSuccess": goal_progress.get("goal_success_rate"),
        "requiredProcessCoverage": goal_progress.get("required_process_coverage"),
        "counterfactualChangeRate": goal_progress.get("counterfactual_tool_selection_change_rate"),
        "recentTraceEventCount": int(float(eval_signals.get("recentTraceEventCount") or 0.0)),
        "relationshipEdgeCount": int(float(eval_signals.get("relationshipEdgeCount") or 0.0)),
    }


def _coding_domain_signature(item: dict[str, Any]) -> dict[str, Any]:
    common = _generic_domain_signature(item)
    domain_evidence = _domain_evidence(item)
    repo_fixture = domain_evidence.get("repoFixture", {}) if isinstance(domain_evidence.get("repoFixture"), dict) else {}
    artifacts = domain_evidence.get("artifacts", {}) if isinstance(domain_evidence.get("artifacts"), dict) else {}
    pre_patch_reports = domain_evidence.get("prePatchTestReports", {}) if isinstance(domain_evidence.get("prePatchTestReports"), dict) else {}
    partial_patch_reports = domain_evidence.get("partialPatchTestReports", {}) if isinstance(domain_evidence.get("partialPatchTestReports"), dict) else {}
    test_reports = domain_evidence.get("testReports", {}) if isinstance(domain_evidence.get("testReports"), dict) else {}
    review_reports = domain_evidence.get("reviewReports", {}) if isinstance(domain_evidence.get("reviewReports"), dict) else {}
    derived_graph = repo_fixture.get("derivedDependencyGraph", {}) if isinstance(repo_fixture.get("derivedDependencyGraph"), dict) else {}
    declared_graph = repo_fixture.get("importGraph", {}) if isinstance(repo_fixture.get("importGraph"), dict) else {}
    replays = _counterfactual_replays(domain_evidence, version_contains="coding")
    goal_progress = _goal_progress_signature(item)
    return {
        **{key: value for key, value in common.items() if key != "signatureId"},
        "signatureId": f"{DOMAIN_SIGNATURE_VERSION}.coding",
        "repoFixtureLoaded": bool(repo_fixture.get("fixtureId")),
        "sourceRepoKind": str(repo_fixture.get("sourceRepoKind") or ""),
        "fixtureFileCount": len(repo_fixture.get("files", {})) if isinstance(repo_fixture.get("files"), dict) else 0,
        "declaredImportNodeCount": len(_list_value(declared_graph.get("nodes"))),
        "declaredImportEdgeCount": len(_list_value(declared_graph.get("edges"))),
        "derivedDependencyNodeCount": len(_list_value(derived_graph.get("nodes"))),
        "derivedDependencyEdgeCount": len(_list_value(derived_graph.get("edges"))),
        "missingDeclaredDependencyCount": len(_list_value(derived_graph.get("missingDeclaredEdges"))),
        "artifactCount": len(artifacts),
        "changedFileCount": sum(len(_list_value(artifact.get("changedFiles"))) for artifact in artifacts.values() if isinstance(artifact, dict)),
        "patchCoverageFileCount": sum(int(artifact.get("patchCoverageFileCount") or 0) for artifact in artifacts.values() if isinstance(artifact, dict)),
        "prePatchReportCount": len(pre_patch_reports),
        "partialPatchReportCount": len(partial_patch_reports),
        "postPatchReportCount": len(test_reports),
        "postPatchPassCount": sum(1 for report in test_reports.values() if isinstance(report, dict) and bool(report.get("passed"))),
        "reviewReportCount": len(review_reports),
        "approvedReviewCount": sum(1 for report in review_reports.values() if isinstance(report, dict) and report.get("status") == "approved"),
        "reviewsWithMemoryCitations": sum(1 for report in review_reports.values() if isinstance(report, dict) and _list_value(report.get("citedMemoryIds"))),
        "reviewConflictCount": sum(1 for report in review_reports.values() if isinstance(report, dict) and _review_conflict_detected(report)),
        "arbitrationSourceCount": sum(_arbitration_source_count(report) for report in review_reports.values() if isinstance(report, dict)),
        "finalTraceRefCount": sum(1 for report in review_reports.values() if isinstance(report, dict) and isinstance(report.get("finalDecisionTraceRef"), dict) and report.get("finalDecisionTraceRef", {}).get("eventId")),
        "replayCount": len(replays),
        "criticalComparisonCount": sum(_comparison_count(replay, kind="critical") for replay in replays),
        "controlComparisonCount": sum(_comparison_count(replay, kind="control") for replay in replays),
        "criticalChangeCount": sum(int(replay.get("criticalChangeCount") or 0) for replay in replays),
        "controlStableCount": sum(int(replay.get("controlStableCount") or 0) for replay in replays),
        "criticalChangeRateBuckets": sorted({_rounded(replay.get("criticalChangeRate")) for replay in replays}),
        "controlStabilityRateBuckets": sorted({_rounded(replay.get("controlStabilityRate")) for replay in replays}),
        "goalSuccess": goal_progress.get("goal_success_rate"),
        "requiredProcessCoverage": goal_progress.get("required_process_coverage"),
        "counterfactualChangeRate": goal_progress.get("counterfactual_tool_selection_change_rate"),
    }


def _domain_evidence(item: dict[str, Any]) -> dict[str, Any]:
    evidence = item.get("domainEvidence", {})
    return evidence if isinstance(evidence, dict) else {}


def _counterfactual_replays(domain_evidence: dict[str, Any], *, version_contains: str) -> list[dict[str, Any]]:
    replay_map = domain_evidence.get("counterfactualReplays", {})
    if not isinstance(replay_map, dict):
        return []
    replays: list[dict[str, Any]] = []
    for replay in replay_map.values():
        if not isinstance(replay, dict):
            continue
        replay_version = str(replay.get("replayVersion") or "")
        if version_contains and version_contains not in replay_version:
            continue
        replays.append(replay)
    return replays


def _goal_progress_signature(item: dict[str, Any]) -> dict[str, float]:
    metrics = item.get("metrics") if isinstance(item.get("metrics"), dict) else None
    if metrics is None:
        final_observation = item.get("finalObservation", {}) if isinstance(item.get("finalObservation"), dict) else {}
        metrics = final_observation.get("goalProgress", {}) if isinstance(final_observation.get("goalProgress"), dict) else {}
    return {
        metric_id: _rounded(metrics.get(metric_id))
        for metric_id in (
            "goal_success_rate",
            "required_process_coverage",
            "counterfactual_tool_selection_change_rate",
        )
    }


def _final_eval_signals(item: dict[str, Any]) -> dict[str, Any]:
    final_observation = item.get("finalObservation", {}) if isinstance(item.get("finalObservation"), dict) else {}
    signals = final_observation.get("evalSignals", {}) if isinstance(final_observation.get("evalSignals"), dict) else {}
    return signals


def _list_value(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _rounded(value: Any) -> float:
    try:
        return round(float(value), 6)
    except (TypeError, ValueError):
        return 0.0


def _score_changed_count(replay: dict[str, Any]) -> int:
    comparisons = replay.get("comparisons", []) if isinstance(replay.get("comparisons"), list) else []
    return sum(1 for item in comparisons if isinstance(item, dict) and bool(item.get("scoreChanged")))


def _comparison_count(replay: dict[str, Any], *, kind: str) -> int:
    comparisons = replay.get("comparisons", []) if isinstance(replay.get("comparisons"), list) else []
    return sum(1 for item in comparisons if isinstance(item, dict) and item.get("kind") == kind)


def _review_conflict_detected(review_report: dict[str, Any]) -> bool:
    conflict = review_report.get("conflict", {})
    return isinstance(conflict, dict) and bool(conflict.get("conflictDetected"))


def _arbitration_source_count(review_report: dict[str, Any]) -> int:
    arbitration = review_report.get("arbitrationLayer", {})
    if not isinstance(arbitration, dict):
        return 0
    sources = arbitration.get("contributing_sources", [])
    return len(sources) if isinstance(sources, list) else 0


def _collect_source_ids(node: Any) -> set[str]:
    source_ids: set[str] = set()
    if isinstance(node, dict):
        source_event_id = node.get("sourceEventId")
        if isinstance(source_event_id, str) and source_event_id:
            source_ids.add(source_event_id)
        source_event_ids = node.get("sourceEventIds")
        if isinstance(source_event_ids, list):
            source_ids.update(str(item) for item in source_event_ids if str(item))
        for value in node.values():
            source_ids.update(_collect_source_ids(value))
    elif isinstance(node, list):
        for value in node:
            source_ids.update(_collect_source_ids(value))
    return source_ids


def _collect_event_ids(node: Any) -> set[str]:
    event_ids: set[str] = set()
    if isinstance(node, dict):
        event_id = node.get("eventId")
        if isinstance(event_id, str) and event_id:
            event_ids.add(event_id)
        for key in ("id", "traceId"):
            value = node.get(key)
            if isinstance(value, str) and value.startswith(("evt_", "coding_evt_")):
                event_ids.add(value)
        for value in node.values():
            event_ids.update(_collect_event_ids(value))
    elif isinstance(node, list):
        for value in node:
            event_ids.update(_collect_event_ids(value))
    return event_ids


def _apply_perturbation(item: dict[str, Any], *, perturbation_id: str, scenario_id: str) -> dict[str, Any]:
    mutated = deepcopy(item)
    noise_id = f"noise::{scenario_id}::{perturbation_id}"
    _walk_and_mutate_sources(mutated, perturbation_id=perturbation_id, noise_id=noise_id)
    if perturbation_id == "source_variation_irrelevant":
        # 主动加入无关 source，验证评估签名会过滤掉不锚定事件。
        evidence = mutated.get("evidence", {}) if isinstance(mutated.get("evidence"), dict) else None
        if isinstance(evidence, dict):
            evidence.setdefault("subjectiveMemoryRefs", [])
            if isinstance(evidence.get("subjectiveMemoryRefs"), list):
                evidence["subjectiveMemoryRefs"].append(noise_id)
            trace_rows = evidence.get("memoryTraceLinks", [])
            if isinstance(trace_rows, list):
                trace_rows.append({"eventId": f"evt_noise_{_stable_short_hash(noise_id)}", "sourceEventId": noise_id})
    return mutated


def _walk_and_mutate_sources(node: Any, *, perturbation_id: str, noise_id: str) -> None:
    if isinstance(node, dict):
        for key, value in list(node.items()):
            if key in SOURCE_LIST_KEYS and isinstance(value, list):
                node[key] = _mutate_source_list(value, perturbation_id=perturbation_id, noise_id=noise_id)
            else:
                _walk_and_mutate_sources(value, perturbation_id=perturbation_id, noise_id=noise_id)
        return
    if isinstance(node, list):
        for value in node:
            _walk_and_mutate_sources(value, perturbation_id=perturbation_id, noise_id=noise_id)


def _mutate_source_list(values: list[Any], *, perturbation_id: str, noise_id: str) -> list[Any]:
    source_values = [str(item) for item in values if str(item)]
    if perturbation_id == "source_order_shuffle":
        return list(reversed(source_values))
    if perturbation_id == "source_variation_weak_noise":
        return [*source_values, noise_id]
    if perturbation_id == "source_variation_duplicate":
        return [*source_values, source_values[0]] if source_values else source_values
    if perturbation_id == "source_variation_irrelevant":
        return [*source_values, noise_id]
    return source_values


def _invariance_metrics(probe: dict[str, Any], *, suite_prefix: str, baseline: str) -> list[dict[str, Any]]:
    metrics: list[dict[str, Any]] = []
    items = probe.get("items", []) if isinstance(probe.get("items"), list) else []
    for perturbation_id in PERTURBATION_IDS:
        values = []
        for item in items:
            perturbations = item.get("perturbations", []) if isinstance(item.get("perturbations"), list) else []
            matched = next(
                (
                    perturbation
                    for perturbation in perturbations
                    if isinstance(perturbation, dict) and perturbation.get("perturbationId") == perturbation_id
                ),
                None,
            )
            values.append(1.0 if isinstance(matched, dict) and matched.get("stable") else 0.0)
        metrics.append(
            metric_summary(
                f"{suite_prefix}_evidence_invariance.{perturbation_id}",
                values,
                baseline=baseline,
            )
        )
    return metrics


def _group_robustness_metrics(probe: dict[str, Any], *, baseline: str) -> list[dict[str, Any]]:
    metrics: list[dict[str, Any]] = []
    for group in probe.get("groups", []) if isinstance(probe.get("groups"), list) else []:
        if not isinstance(group, dict):
            continue
        group_id = str(group.get("groupId") or "unknown_group")
        metrics.append(
            metric_summary(
                "domain_evidence_robustness_score",
                [float(group.get("overallInvarianceRate") or 0.0)],
                baseline=baseline,
                scenario_id=group_id,
            )
        )
    return metrics


def _probe_group_id(suite_id: str, item: dict[str, Any]) -> str:
    if suite_id == "domain":
        return str(item.get("domainId") or "unknown_domain")
    return suite_id


def _empty_perturbation_stats() -> dict[str, dict[str, int]]:
    return {perturbation_id: {"stable": 0, "total": 0} for perturbation_id in PERTURBATION_IDS}


def _format_groups(group_stats: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    for group_id, stats in sorted(group_stats.items()):
        stable = int(stats.get("stable") or 0)
        total = int(stats.get("total") or 0)
        perturbation_stats = stats.get("perturbations", {}) if isinstance(stats.get("perturbations"), dict) else {}
        groups.append(
            {
                "groupId": group_id,
                "stableCount": stable,
                "total": total,
                "overallInvarianceRate": round(_safe_ratio(stable, total), 6),
                "allStable": stable == total and total > 0,
                "perturbations": _format_perturbation_stats(perturbation_stats),
            }
        )
    return groups


def _format_perturbation_stats(perturbation_stats: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for perturbation_id in PERTURBATION_IDS:
        stats = perturbation_stats.get(perturbation_id, {}) if isinstance(perturbation_stats, dict) else {}
        stable = int(stats.get("stable") or 0)
        total = int(stats.get("total") or 0)
        rows.append(
            {
                "perturbationId": perturbation_id,
                "stableCount": stable,
                "total": total,
                "invarianceRate": round(_safe_ratio(stable, total), 6),
            }
        )
    return rows


def _signature_kinds(details: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: dict[tuple[str, str], int] = {}
    for item in details:
        if not isinstance(item, dict):
            continue
        signature = item.get("baseSignature", {}) if isinstance(item.get("baseSignature"), dict) else {}
        signature_id = str(signature.get("signatureId") or "process_signature.v1")
        group_id = str(item.get("groupId") or "")
        key = (group_id, signature_id)
        counts[key] = counts.get(key, 0) + 1
    return [
        {"groupId": group_id, "signatureId": signature_id, "itemCount": count}
        for (group_id, signature_id), count in sorted(counts.items())
    ]


def _build_strict_gate(
    *,
    process_result: dict[str, Any],
    domain_result: dict[str, Any],
    process_probe: dict[str, Any],
    domain_probe: dict[str, Any],
    total_checks: int,
    robustness_checks_pass: bool,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def add_check(check_id: str, passed: bool, *, scope: str, observed: Any, expected: Any) -> None:
        checks.append(
            {
                "checkId": check_id,
                "scope": scope,
                "pass": bool(passed),
                "observed": observed,
                "expected": expected,
            }
        )

    add_check("base.process_eval_ok", bool(process_result.get("ok")), scope="process", observed=bool(process_result.get("ok")), expected=True)
    add_check("base.domain_eval_ok", bool(domain_result.get("ok")), scope="domain", observed=bool(domain_result.get("ok")), expected=True)
    add_check("robustness.total_checks_present", total_checks > 0, scope="aggregate", observed=total_checks, expected="> 0")
    add_check("robustness.all_stable", robustness_checks_pass, scope="aggregate", observed=robustness_checks_pass, expected=True)
    add_check("process.all_stable", bool(process_probe.get("allStable")), scope="process", observed=process_probe.get("overallInvarianceRate"), expected=1.0)
    add_check("domain.all_stable", bool(domain_probe.get("allStable")), scope="domain", observed=domain_probe.get("overallInvarianceRate"), expected=1.0)

    for section, probe in (("process", process_probe), ("domain", domain_probe)):
        for perturbation in probe.get("perturbations", []) if isinstance(probe.get("perturbations"), list) else []:
            if not isinstance(perturbation, dict):
                continue
            perturbation_id = str(perturbation.get("perturbationId") or "unknown")
            total = int(perturbation.get("total") or 0)
            rate = float(perturbation.get("invarianceRate") or 0.0)
            add_check(
                f"{section}.perturbation.{_safe_check_id(perturbation_id)}",
                total > 0 and rate >= 1.0,
                scope=section,
                observed={"total": total, "invarianceRate": rate},
                expected={"total": "> 0", "invarianceRate": 1.0},
            )

    domain_group_ids = {
        str(group.get("groupId") or "")
        for group in domain_probe.get("groups", [])
        if isinstance(group, dict)
    }
    for expected_group in EXPECTED_DOMAIN_GROUPS:
        add_check(
            f"domain.group_present.{_safe_check_id(expected_group)}",
            expected_group in domain_group_ids,
            scope="domain",
            observed=sorted(domain_group_ids),
            expected=expected_group,
        )
    for group in domain_probe.get("groups", []) if isinstance(domain_probe.get("groups"), list) else []:
        if not isinstance(group, dict):
            continue
        group_id = str(group.get("groupId") or "unknown_group")
        total = int(group.get("total") or 0)
        rate = float(group.get("overallInvarianceRate") or 0.0)
        add_check(
            f"domain.group_stable.{_safe_check_id(group_id)}",
            total > 0 and bool(group.get("allStable")) and rate >= 1.0,
            scope="domain",
            observed={"total": total, "invarianceRate": rate, "allStable": bool(group.get("allStable"))},
            expected={"total": "> 0", "invarianceRate": 1.0, "allStable": True},
        )

    failed_checks = [check for check in checks if not check.get("pass")]
    return {
        "gateVersion": STRICT_GATE_VERSION,
        "enabled": True,
        "pass": not failed_checks,
        "thresholds": {
            "overallInvarianceRate": 1.0,
            "perPerturbationInvarianceRate": 1.0,
            "perDomainInvarianceRate": 1.0,
            "expectedDomainGroups": list(EXPECTED_DOMAIN_GROUPS),
        },
        "checkCount": len(checks),
        "failedCheckCount": len(failed_checks),
        "failedChecks": failed_checks,
        "checks": checks,
    }


def _safe_check_id(value: str) -> str:
    return "".join(char if char.isalnum() else "_" for char in value).strip("_") or "unknown"


def _scenario_id(item: dict[str, Any]) -> str:
    if isinstance(item.get("scenario"), dict):
        scenario_id = str(item.get("scenario", {}).get("scenarioId") or "")
        if scenario_id:
            return scenario_id
    scenario_id = str(item.get("scenarioId") or "")
    return scenario_id or "unknown_scenario"


def _to_id_set(values: Any) -> set[str]:
    if not isinstance(values, list):
        return set()
    return {str(item) for item in values if str(item)}


def _safe_ratio(numerator: int | float, denominator: int | float) -> float:
    return float(numerator) / float(denominator) if float(denominator) else 0.0


def _stable_short_hash(value: str) -> str:
    # Python 内置 hash 带进程随机盐；artifact id 用稳定哈希避免跨次运行漂移。
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:8]


def _export_evidence_robustness_eval(result: dict[str, Any], base_dir: Path) -> dict[str, Any]:
    created_at = _utc_timestamp()
    git_snapshot = _git_snapshot()
    run_dir = _unique_run_dir(base_dir / f"robustness_{_timestamp_slug(created_at)}")
    run_dir.mkdir(parents=True, exist_ok=True)
    artifacts: list[dict[str, Any]] = []

    summary_path = run_dir / "summary.json"
    _write_json(summary_path, _summary_only(result))
    artifacts.append(_artifact_record(summary_path, run_dir, kind="summary_json"))

    process_path = run_dir / "process_robustness.json"
    _write_json(process_path, result.get("process", {}))
    artifacts.append(_artifact_record(process_path, run_dir, kind="process_robustness_json"))

    domain_path = run_dir / "domain_robustness.json"
    _write_json(domain_path, result.get("domain", {}))
    artifacts.append(_artifact_record(domain_path, run_dir, kind="domain_robustness_json"))

    strict_gate_path = run_dir / "strict_gate.json"
    _write_json(strict_gate_path, result.get("strictGate", {}))
    artifacts.append(_artifact_record(strict_gate_path, run_dir, kind="strict_gate_json"))

    signature_summary_path = run_dir / "signature_summary.json"
    _write_json(signature_summary_path, _signature_summary_payload(result))
    artifacts.append(_artifact_record(signature_summary_path, run_dir, kind="signature_summary_json"))

    detail_rows = []
    for section in ("process", "domain"):
        details = result.get(section, {}).get("items", []) if isinstance(result.get(section), dict) else []
        for item in details:
            if not isinstance(item, dict):
                continue
            for perturbation in item.get("perturbations", []):
                if not isinstance(perturbation, dict):
                    continue
                detail_rows.append(
                    {
                        "suite": section,
                        "scenarioId": item.get("scenarioId"),
                        "groupId": item.get("groupId"),
                        "baseline": item.get("baseline"),
                        "domainId": item.get("domainId"),
                        "seed": item.get("seed"),
                        "perturbationId": perturbation.get("perturbationId"),
                        "stable": perturbation.get("stable"),
                        "baseSignatureId": _signature_id(item.get("baseSignature")),
                        "perturbedSignatureId": _signature_id(perturbation.get("signature")),
                        "baseSignature": item.get("baseSignature"),
                        "perturbedSignature": perturbation.get("signature"),
                    }
                )

    detail_path = run_dir / "perturbation_details.jsonl"
    _write_jsonl(detail_path, detail_rows)
    artifacts.append(
        _artifact_record(
            detail_path,
            run_dir,
            kind="perturbation_details_jsonl",
            row_count=len(detail_rows),
        )
    )

    manifest_path = _write_eval_manifest(
        run_dir=run_dir,
        result=result,
        artifacts=artifacts,
        created_at=created_at,
        export_kind="evidence_robustness_dataset",
        git_snapshot=git_snapshot,
    )
    return {
        "runDir": str(run_dir),
        "manifest": str(manifest_path),
        "artifactCount": len(artifacts) + 1,
    }


def _signature_summary_payload(result: dict[str, Any]) -> dict[str, Any]:
    process = result.get("process", {}) if isinstance(result.get("process"), dict) else {}
    domain = result.get("domain", {}) if isinstance(result.get("domain"), dict) else {}
    return {
        "signatureSummaryVersion": DOMAIN_SIGNATURE_VERSION,
        "strictGate": {
            "gateVersion": result.get("strictGate", {}).get("gateVersion")
            if isinstance(result.get("strictGate"), dict)
            else None,
            "pass": result.get("strictGate", {}).get("pass")
            if isinstance(result.get("strictGate"), dict)
            else None,
            "failedCheckCount": result.get("strictGate", {}).get("failedCheckCount")
            if isinstance(result.get("strictGate"), dict)
            else None,
        },
        "process": {
            "groups": process.get("groups", []),
            "signatureKinds": process.get("signatureKinds", []),
        },
        "domain": {
            "groups": domain.get("groups", []),
            "signatureKinds": domain.get("signatureKinds", []),
        },
    }


def _signature_id(signature: Any) -> str | None:
    return str(signature.get("signatureId")) if isinstance(signature, dict) and signature.get("signatureId") else None
