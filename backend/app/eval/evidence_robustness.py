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
    result = {
        "ok": bool(process_result.get("ok")) and bool(domain_result.get("ok")) and robustness_checks_pass,
        "suite": "evidence_robustness",
        "baseline": BASELINE_FULL,
        "providerMode": "rule",
        "robustnessChecksPass": robustness_checks_pass,
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

    for item in items:
        scenario_id = _scenario_id(item)
        base_signature = signature_builder(item)
        row = {
            "suite": suite_id,
            "scenarioId": scenario_id,
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
            if stable:
                stable_count += 1
                perturbation_stats[perturbation_id]["stable"] += 1
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
    sources = _collect_source_ids(item)
    events = _collect_event_ids(item)
    anchored = sorted(source_id for source_id in sources if source_id in events)
    return {
        "eventIdCount": len(events),
        "anchoredSourceLinkCount": len(anchored),
        "hasAnchoredSourceLink": bool(anchored),
    }


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
                        "baseline": item.get("baseline"),
                        "domainId": item.get("domainId"),
                        "seed": item.get("seed"),
                        "perturbationId": perturbation.get("perturbationId"),
                        "stable": perturbation.get("stable"),
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
    )
    return {
        "runDir": str(run_dir),
        "manifest": str(manifest_path),
        "artifactCount": len(artifacts) + 1,
    }
