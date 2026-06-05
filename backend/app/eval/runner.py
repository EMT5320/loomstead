from __future__ import annotations

import hashlib
import json
import subprocess
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.eval.process_fidelity import build_process_metrics, metric_summary, process_metric_summaries
from app.eval.scenarios import DEFAULT_L1_SCENARIOS, DEFAULT_PROCESS_GOALS, EvalScenario, ProcessGoalSpec
from app.memory.subjective_memory import SubjectiveMemoryRecord
from app.runtime.agent_runtime import AgentRuntime
from app.runtime.motivation_engine import MotivationEngine
from app.runtime.schema_registry import require_schema_version, schema_registry_snapshot
from app.world.seed_data import DAY1_NPC_IDS
from app.world.world_state import create_initial_world, relation_key


BASELINE_FULL = "full_motivational_delegation"
BASELINE_HARD_DELEGATION = "hard_delegation"
ABLATION_NO_SUBJECTIVE_MEMORY = "no_subjective_memory"
ABLATION_NO_RELATIONSHIP_EDGE = "no_relationship_edge"
ABLATION_SHUFFLED_MEMORY_OWNER = "shuffled_memory_owner"
ABLATION_EVIDENCE_LINK_REMOVAL = "evidence_link_removal"


PROCESS_BASELINES = (
    BASELINE_FULL,
    BASELINE_HARD_DELEGATION,
    ABLATION_NO_SUBJECTIVE_MEMORY,
    ABLATION_NO_RELATIONSHIP_EDGE,
    ABLATION_SHUFFLED_MEMORY_OWNER,
    ABLATION_EVIDENCE_LINK_REMOVAL,
)
SUBJECTIVE_MEMORY_ABLATION_NONE = "none"
SUBJECTIVE_MEMORY_ABLATION_NO_MEMORY = "no_subjective_memory"
RELATIONSHIP_ABLATION_NONE = "none"
RELATIONSHIP_ABLATION_NO_EDGE = "no_relationship_edge"
RELATIONSHIP_ABLATION_SHUFFLED_OWNER = "shuffled_memory_owner"
RELATIONSHIP_ABLATION_EVIDENCE_LINK_REMOVAL = "evidence_link_removal"
BASELINE_STABILITY_24H = "rule_24h_stability"
DEFAULT_STABILITY_HOURS = 24
COUNTERFACTUAL_REPLAY_DECISION_CYCLES = 24
PROCESS_PROVIDER_MODES = ("rule", "cloud", "mixed")
PROCESS_LLM_EVIDENCE_VERSION = "process_llm_evidence.v1"
PROCESS_LLM_EVIDENCE_CACHE_PATH = Path(".run") / "process-llm-evidence" / "latest.json"
STABILITY_TRACE_TYPES = {
    "budget.decision_consumed",
    "budget.decision_fallback",
    "motivation.decision_made",
    "tool.execution_completed",
    "tool.execution_failed",
    "tool.execution_interrupted",
    "memory.result_observed",
}


def run_rule_scenarios(scenarios: tuple[EvalScenario, ...] = DEFAULT_L1_SCENARIOS) -> dict[str, Any]:
    # Full baseline：当前 Motivational Delegation 逻辑。
    full_run = _run_baseline_with_engine(scenarios, baseline=BASELINE_FULL)
    # Hard Delegation baseline：用显式规则模拟强任务委派。
    hard_run = _run_hard_delegation_baseline(scenarios)
    # 最小 ablation：移除关系边，再跑一遍同样的 rule scenario。
    no_relationship_run = _run_baseline_with_engine(
        scenarios,
        baseline=ABLATION_NO_RELATIONSHIP_EDGE,
        clear_relationship_edges=True,
    )

    comparison = _build_ablation_comparison(full_run, hard_run, no_relationship_run)
    all_metrics = [full_run["metric"], hard_run["metric"], no_relationship_run["metric"]]

    return {
        # eval:rule 继续以 full baseline 作为门禁。
        "ok": full_run["ok"],
        "baseline": BASELINE_FULL,
        "passed": full_run["passed"],
        "total": len(scenarios),
        "metrics": all_metrics,
        "items": full_run["items"],
        "baselines": {
            BASELINE_FULL: _export_baseline_result(full_run),
            BASELINE_HARD_DELEGATION: _export_baseline_result(hard_run),
            ABLATION_NO_RELATIONSHIP_EDGE: _export_baseline_result(no_relationship_run),
        },
        "ablation_comparison": comparison,
    }


def run_process_fidelity_scenarios(
    scenarios: tuple[ProcessGoalSpec, ...] = DEFAULT_PROCESS_GOALS,
    *,
    export_dir: str | Path | None = None,
    provider_mode: str = "rule",
    seed_count: int = 1,
    attach_latest_llm_evidence: bool = False,
) -> dict[str, Any]:
    """运行 Phase 2 Process Fidelity 规则级评估。"""
    provider_mode = _normalize_process_provider_mode(provider_mode)
    seed_count = max(1, int(seed_count))
    runs = {
        BASELINE_FULL: _run_process_baseline(scenarios, baseline=BASELINE_FULL, provider_mode=provider_mode, seed_count=seed_count),
        BASELINE_HARD_DELEGATION: _run_process_baseline(scenarios, baseline=BASELINE_HARD_DELEGATION, provider_mode="rule", seed_count=seed_count),
        ABLATION_NO_SUBJECTIVE_MEMORY: _run_process_baseline(scenarios, baseline=ABLATION_NO_SUBJECTIVE_MEMORY, provider_mode=provider_mode, seed_count=seed_count),
        ABLATION_NO_RELATIONSHIP_EDGE: _run_process_baseline(scenarios, baseline=ABLATION_NO_RELATIONSHIP_EDGE, provider_mode=provider_mode, seed_count=seed_count),
        ABLATION_SHUFFLED_MEMORY_OWNER: _run_process_baseline(scenarios, baseline=ABLATION_SHUFFLED_MEMORY_OWNER, provider_mode=provider_mode, seed_count=seed_count),
        ABLATION_EVIDENCE_LINK_REMOVAL: _run_process_baseline(scenarios, baseline=ABLATION_EVIDENCE_LINK_REMOVAL, provider_mode=provider_mode, seed_count=seed_count),
    }
    comparison = _build_process_ablation_comparison(runs)
    metrics = [metric for baseline in PROCESS_BASELINES for metric in runs[baseline]["metrics"]]
    llm_evidence = _build_process_llm_evidence(
        runs,
        provider_mode=provider_mode,
        seed_count=seed_count,
        source="current_run",
    )
    if provider_mode in {"cloud", "mixed"}:
        _cache_latest_process_llm_evidence(llm_evidence)
    elif attach_latest_llm_evidence and not llm_evidence.get("recordCount"):
        llm_evidence = _load_cached_process_llm_evidence() or llm_evidence
    result = {
        "ok": bool(runs[BASELINE_FULL]["ok"]),
        "suite": "process_fidelity",
        "baseline": BASELINE_FULL,
        "providerMode": provider_mode,
        "seedCount": seed_count,
        "passed": runs[BASELINE_FULL]["passed"],
        "total": len(scenarios) * seed_count,
        "metrics": metrics,
        "baselines": runs,
        "ablation_comparison": comparison,
        "llmEvidence": llm_evidence,
    }
    if export_dir is not None:
        result["export"] = _export_process_eval(result, Path(export_dir))
    return result


def run_stability_scenarios(
    *,
    hours: int = DEFAULT_STABILITY_HOURS,
    export_dir: str | Path | None = None,
) -> dict[str, Any]:
    """连续推进规则版 AgentRuntime，用可配置游戏小时数验证 tick 主路径稳定性。"""
    hours = max(1, int(hours))
    baseline = _stability_baseline(hours)
    suite = f"stability_{hours}h"
    runtime = AgentRuntime(provider_mode="rule")
    initial_clock = dict(runtime.world.get("clock", {}))
    tick_items: list[dict[str, Any]] = []
    tick_success_values: list[float] = []
    event_type_counts: Counter[str] = Counter()
    trace_event_count = 0
    trace_schema_ok_count = 0
    completed_tool_count = 0
    failed_tool_count = 0
    interrupted_tool_count = 0
    memory_observation_count = 0
    motivation_decision_count = 0
    budget_decision_count = 0
    budget_trace_schema_ok_count = 0
    budget_source_link_count = 0
    budget_trace_ref_count = 0
    heuristic_decision_count = 0
    active_agent_ids: set[str] = set()

    for hour_index in range(1, hours + 1):
        try:
            tick_result = runtime.tick(3600.0, speed=1.0)
            events = [event for event in tick_result.get("events", []) if isinstance(event, dict)]
            tick_counts = Counter(str(event.get("type") or "") for event in events)
            event_type_counts.update(tick_counts)
            for event in events:
                event_type = str(event.get("type") or "")
                payload = event.get("payload", {}) if isinstance(event.get("payload"), dict) else {}
                npc_id = str(payload.get("npcId") or event.get("npcId") or "")
                if npc_id:
                    active_agent_ids.add(npc_id)
                if event_type in STABILITY_TRACE_TYPES:
                    trace_event_count += 1
                    if payload.get("traceSchemaVersion") == require_schema_version("phase2_trace"):
                        trace_schema_ok_count += 1
                if event_type in {"budget.decision_consumed", "budget.decision_fallback"}:
                    budget_decision_count += 1
                    if payload.get("traceSchemaVersion") == require_schema_version("phase2_trace"):
                        budget_trace_schema_ok_count += 1
                    if payload.get("sourceEventIds"):
                        budget_source_link_count += 1
                    if _budget_event_has_decision_trace_ref(payload):
                        budget_trace_ref_count += 1
                if event_type == "motivation.decision_made":
                    motivation_decision_count += 1
                    if payload.get("heuristicRefs"):
                        heuristic_decision_count += 1
                if event_type == "tool.execution_completed":
                    completed_tool_count += 1
                elif event_type == "tool.execution_failed":
                    failed_tool_count += 1
                elif event_type == "tool.execution_interrupted":
                    interrupted_tool_count += 1
                elif event_type == "memory.result_observed":
                    memory_observation_count += 1
            tick_items.append(
                {
                    "hourIndex": hour_index,
                    "ok": True,
                    "clock": tick_result.get("clock", {}),
                    "eventCounts": dict(sorted(tick_counts.items())),
                    "agentDiffCount": len(tick_result.get("agents", [])) if isinstance(tick_result.get("agents"), list) else 0,
                }
            )
            tick_success_values.append(1.0)
        except Exception as exc:  # noqa: BLE001 - Eval 要把失败转成证据，方便 CI 和人工复盘。
            tick_items.append({"hourIndex": hour_index, "ok": False, "error": repr(exc)})
            tick_success_values.append(0.0)
            break

    subjective_memory_count = len(runtime.subjective_memory_store.list(limit=10000))
    relationship_edge_count = len(runtime.relationship_edge_store.list(limit=10000))
    heuristic_count = len(runtime.heuristic_library.list(limit=10000))
    tool_result_count = completed_tool_count + failed_tool_count + interrupted_tool_count
    trace_schema_coverage = _safe_ratio(trace_schema_ok_count, trace_event_count)
    memory_observation_ratio = _safe_ratio(memory_observation_count, tool_result_count)
    heuristic_decision_ratio = _safe_ratio(heuristic_decision_count, motivation_decision_count)
    budget_source_link_ratio = _safe_ratio(budget_source_link_count, budget_decision_count)
    budget_trace_ref_ratio = _safe_ratio(budget_trace_ref_count, budget_decision_count)
    checks = {
        "tick_successful": sum(tick_success_values) == float(hours),
        "clock_reached_expected_tick": int(runtime.world.get("clock", {}).get("tick", 0)) >= hours,
        "no_tool_failures": failed_tool_count == 0,
        "trace_schema_complete": trace_event_count > 0 and trace_schema_coverage >= 1.0,
        "budget_trace_links_decision": budget_decision_count > 0
        and budget_trace_schema_ok_count == budget_decision_count
        and budget_source_link_count == budget_decision_count
        and budget_trace_ref_count == budget_decision_count,
        "memory_observations_follow_tools": tool_result_count > 0 and memory_observation_count >= tool_result_count,
        "relationship_edges_created": relationship_edge_count > 0,
        "heuristics_created": heuristic_count > 0,
        "heuristics_influence_decisions": heuristic_decision_count > 0,
        "multi_agent_participation": len(active_agent_ids) >= 4,
    }
    metrics = [
        metric_summary("stability_tick_success_rate", tick_success_values, baseline=baseline),
        metric_summary("trace_schema_coverage", [trace_schema_coverage], baseline=baseline),
        metric_summary("memory_observation_per_tool_result", [memory_observation_ratio], baseline=baseline),
        metric_summary("tool_failure_rate", [_safe_ratio(failed_tool_count, tool_result_count)], baseline=baseline),
        metric_summary("tool_interruption_rate", [_safe_ratio(interrupted_tool_count, tool_result_count)], baseline=baseline),
        metric_summary("active_agent_count", [float(len(active_agent_ids))], baseline=baseline),
        metric_summary("relationship_edge_count", [float(relationship_edge_count)], baseline=baseline),
        metric_summary("heuristic_count", [float(heuristic_count)], baseline=baseline),
        metric_summary("heuristic_decision_ref_rate", [heuristic_decision_ratio], baseline=baseline),
        metric_summary("budget_decision_source_link_rate", [budget_source_link_ratio], baseline=baseline),
        metric_summary("budget_decision_trace_ref_rate", [budget_trace_ref_ratio], baseline=baseline),
    ]
    result = {
        "ok": all(checks.values()),
        "suite": suite,
        "baseline": baseline,
        "hours": hours,
        "ticksCompleted": int(sum(tick_success_values)),
        "checks": checks,
        "metrics": metrics,
        "evidence": {
            "initialClock": initial_clock,
            "finalClock": dict(runtime.world.get("clock", {})),
            "eventTypeCounts": dict(sorted(event_type_counts.items())),
            "completedToolCount": completed_tool_count,
            "failedToolCount": failed_tool_count,
            "interruptedToolCount": interrupted_tool_count,
            "memoryObservationCount": memory_observation_count,
            "subjectiveMemoryCount": subjective_memory_count,
            "relationshipEdgeCount": relationship_edge_count,
            "heuristicCount": heuristic_count,
            "motivationDecisionCount": motivation_decision_count,
            "budgetDecisionCount": budget_decision_count,
            "budgetTraceSchemaOkCount": budget_trace_schema_ok_count,
            "budgetSourceLinkCount": budget_source_link_count,
            "budgetTraceRefCount": budget_trace_ref_count,
            "heuristicDecisionCount": heuristic_decision_count,
            "activeAgentIds": sorted(active_agent_ids),
            "retainedEventStoreCount": len(runtime.event_store.list()),
        },
        "items": tick_items,
    }
    if export_dir is not None:
        result["export"] = _export_stability_eval(result, Path(export_dir))
    return result


def run_stability_determinism_check(
    *,
    hours: int = DEFAULT_STABILITY_HOURS,
    repeats: int = 3,
) -> dict[str, Any]:
    """连续运行 stability suite，比较硬门禁不变量，并暴露 run-specific 计数漂移。"""
    hours = max(1, int(hours))
    repeats = max(2, int(repeats))
    runs = [run_stability_scenarios(hours=hours) for _ in range(repeats)]
    signatures = [_stability_invariant_signature(run) for run in runs]
    expected_signature = signatures[0] if signatures else {}
    mismatches = [
        {
            "runIndex": index,
            "expected": expected_signature,
            "actual": signature,
        }
        for index, signature in enumerate(signatures[1:], start=1)
        if signature != expected_signature
    ]
    run_specific_evidence = [
        _stability_run_specific_evidence(index, run)
        for index, run in enumerate(runs)
    ]
    return {
        "ok": all(bool(run.get("ok")) for run in runs) and not mismatches,
        "suite": f"stability_{hours}h_determinism",
        "baseline": _stability_baseline(hours),
        "hours": hours,
        "repeats": repeats,
        "invariantSignature": expected_signature,
        "mismatches": mismatches,
        "runSpecificEvidence": run_specific_evidence,
        "notes": [
            "invariantSignature 是 stability 的硬门禁护栏。",
            "runSpecificEvidence 记录受运行路径影响的计数证据，精确值以单次导出 artifact 为准。",
        ],
    }


def _stability_invariant_signature(result: dict[str, Any]) -> dict[str, Any]:
    """提取跨连续运行应保持一致的 stability 门禁字段。"""
    evidence = result.get("evidence", {}) if isinstance(result.get("evidence"), dict) else {}
    checks = result.get("checks", {}) if isinstance(result.get("checks"), dict) else {}
    return {
        "ok": bool(result.get("ok")),
        "ticksCompleted": int(result.get("ticksCompleted") or 0),
        "completedToolCount": int(evidence.get("completedToolCount") or 0),
        "failedToolCount": int(evidence.get("failedToolCount") or 0),
        "relationshipEdgeCount": int(evidence.get("relationshipEdgeCount") or 0),
        "activeAgentIds": list(evidence.get("activeAgentIds") or []),
        "checks": {key: bool(checks.get(key)) for key in sorted(checks)},
    }


def _stability_run_specific_evidence(index: int, result: dict[str, Any]) -> dict[str, Any]:
    """汇总 stability 单次运行计数字段，便于审查非门禁型漂移。"""
    evidence = result.get("evidence", {}) if isinstance(result.get("evidence"), dict) else {}
    metrics = {
        str(item.get("metric")): item.get("mean")
        for item in result.get("metrics", [])
        if isinstance(item, dict) and item.get("metric")
    }
    return {
        "runIndex": index,
        "ok": bool(result.get("ok")),
        "ticksCompleted": int(result.get("ticksCompleted") or 0),
        "interruptedToolCount": int(evidence.get("interruptedToolCount") or 0),
        "memoryObservationCount": int(evidence.get("memoryObservationCount") or 0),
        "subjectiveMemoryCount": int(evidence.get("subjectiveMemoryCount") or 0),
        "heuristicCount": int(evidence.get("heuristicCount") or 0),
        "motivationDecisionCount": int(evidence.get("motivationDecisionCount") or 0),
        "heuristicDecisionCount": int(evidence.get("heuristicDecisionCount") or 0),
        "heuristicDecisionRefRate": metrics.get("heuristic_decision_ref_rate"),
        "toolInterruptionRate": metrics.get("tool_interruption_rate"),
    }


def _stability_baseline(hours: int) -> str:
    if int(hours) == DEFAULT_STABILITY_HOURS:
        return BASELINE_STABILITY_24H
    return f"rule_{int(hours)}h_stability"


def _budget_event_has_decision_trace_ref(payload: dict[str, Any]) -> bool:
    """确认预算事件可通过 traceRefs 回跳到 motivation.decision_made。"""
    source_ids = {str(item) for item in payload.get("sourceEventIds", []) if str(item)}
    if not source_ids:
        return False
    for ref in payload.get("traceRefs", []):
        if not isinstance(ref, dict):
            continue
        if ref.get("type") == "motivation_decision_trace" and str(ref.get("eventId") or "") in source_ids:
            return True
    return False


def _summarize_budget_trace_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    """压缩 Process Eval 中的预算 trace 证据，避免 artifact 带入完整事件流。"""
    schema_version = require_schema_version("phase2_trace")
    compact_events: list[dict[str, Any]] = []
    trace_schema_ok_count = 0
    source_link_count = 0
    trace_ref_count = 0
    for event in events:
        details = event.get("details", {}) if isinstance(event.get("details"), dict) else {}
        source_event_ids = [str(item) for item in details.get("sourceEventIds", []) if str(item)]
        if not source_event_ids and event.get("sourceEventId"):
            source_event_ids = [str(event.get("sourceEventId"))]
        trace_refs = [dict(ref) for ref in details.get("traceRefs", []) if isinstance(ref, dict)]
        trace_schema_ok = event.get("traceSchemaVersion") == schema_version
        has_source_link = bool(source_event_ids)
        has_trace_ref = _budget_event_has_decision_trace_ref(
            {"sourceEventIds": source_event_ids, "traceRefs": trace_refs}
        )
        trace_schema_ok_count += 1 if trace_schema_ok else 0
        source_link_count += 1 if has_source_link else 0
        trace_ref_count += 1 if has_trace_ref else 0
        compact_events.append(
            {
                "eventId": event.get("eventId"),
                "eventType": event.get("eventType"),
                "agentId": event.get("agentId"),
                "toolId": details.get("toolId"),
                "route": details.get("route"),
                "sourceEventIds": source_event_ids,
                "traceSchemaOk": trace_schema_ok,
                "hasDecisionTraceRef": has_trace_ref,
            }
        )
    event_count = len(events)
    return {
        "eventCount": event_count,
        "traceSchemaOkCount": trace_schema_ok_count,
        "sourceLinkCount": source_link_count,
        "traceRefCount": trace_ref_count,
        "sourceLinkRate": round(_safe_ratio(source_link_count, event_count), 6),
        "traceRefRate": round(_safe_ratio(trace_ref_count, event_count), 6),
        "events": compact_events,
    }


def apply_scenario_setup(world: dict[str, Any], scenario: EvalScenario) -> None:
    agent = world["agents"][scenario.npc_id]
    for field, value in scenario.status_overrides.items():
        agent["status"][field] = value
    if scenario.location_id:
        agent["locationId"] = scenario.location_id
    if scenario.anchor_id:
        agent["anchorId"] = scenario.anchor_id
    if scenario.today_goals is not None:
        agent["todayGoals"] = list(scenario.today_goals)
    if scenario.active_focus is not None:
        world["activeFocus"] = dict(scenario.active_focus)


def apply_process_goal_setup(world: dict[str, Any], scenario: ProcessGoalSpec) -> None:
    """让目标 NPC 和目标对象处在同一可见场景，保证规则 Eval 可复现。"""
    if scenario.target_npc_id == "player":
        _ensure_player_eval_agent(world, location_id=scenario.location_id, anchor_id=scenario.anchor_id)
    for npc_id in (scenario.npc_id, scenario.target_npc_id):
        agent = world["agents"][npc_id]
        agent["locationId"] = scenario.location_id
        agent["anchorId"] = scenario.anchor_id
    for npc_id in DAY1_NPC_IDS:
        if npc_id in {scenario.npc_id, scenario.target_npc_id}:
            continue
        agent = world["agents"].get(npc_id)
        if isinstance(agent, dict):
            # Process Eval 固定社交目标，避免同地点默认扫描让目标对象随初始站位漂移。
            agent["locationId"] = "farm" if scenario.location_id != "farm" else "plaza"
            agent["anchorId"] = "farm_house_door" if scenario.location_id != "farm" else "plaza_fountain"
    agent = world["agents"][scenario.npc_id]
    for field, value in scenario.status_overrides.items():
        agent["status"][field] = value
    world.setdefault("relations", {})[relation_key(scenario.npc_id, scenario.target_npc_id)] = {
        "affection": 28,
        "trust": 24,
        "conflict": 42 if scenario.setup_kind == "forgiveness_memory" else 8,
        "kind": "strained" if scenario.setup_kind == "forgiveness_memory" else "goal_fixture",
    }
    active_focus = {
        "targetAgents": [scenario.npc_id],
        "brief": f"Process Fidelity Eval: {scenario.scenario_id}",
        "preferredSocialTargets": {scenario.npc_id: scenario.target_npc_id},
    }
    if scenario.setup_kind == "forgiveness_memory":
        # 修复失信关系的 fixture 固定为一次确认谈话，避免礼物动作遮蔽“谈清楚”的过程证据。
        active_focus["allowedToolIds"] = ["social.chat_with"]
    world["activeFocus"] = active_focus


def _ensure_player_eval_agent(world: dict[str, Any], *, location_id: str, anchor_id: str) -> None:
    """把玩家临时投影成可被 NPC 工具引用的 eval 目标，不让玩家进入 NPC tick 队列。"""
    player = dict(world.get("player", {})) if isinstance(world.get("player"), dict) else {"id": "player", "name": "玩家"}
    player.setdefault("id", "player")
    player.setdefault("name", "新来的农场主")
    player["locationId"] = location_id
    player["anchorId"] = anchor_id
    player.setdefault("status", {"energy": 80, "money": 80, "social": 60, "mood": 50, "stress": 10, "health": 90})
    player.setdefault("inventory", list(world.get("player", {}).get("inventory", [])) if isinstance(world.get("player"), dict) else [])
    player.setdefault("deepCard", {})
    player.setdefault("alive", True)
    world.setdefault("agents", {})["player"] = player


def _run_baseline_with_engine(
    scenarios: tuple[EvalScenario, ...],
    *,
    baseline: str,
    clear_relationship_edges: bool = False,
) -> dict[str, Any]:
    engine = MotivationEngine()
    results = []
    pass_values: list[float] = []
    for scenario in scenarios:
        world = create_initial_world()
        apply_scenario_setup(world, scenario)
        if clear_relationship_edges:
            world["relations"] = {}
        decision = engine.evaluate_npc(world, scenario.npc_id)
        result_item = _build_result_item(scenario, decision)
        pass_values.append(1.0 if result_item["ok"] else 0.0)
        results.append(result_item)
    metric = metric_summary("l1_rule_pass_rate", pass_values, baseline=baseline)
    passed = int(sum(pass_values))
    return {
        "ok": passed == len(scenarios),
        "passed": passed,
        "items": results,
        "metric": metric,
    }


def _run_hard_delegation_baseline(scenarios: tuple[EvalScenario, ...]) -> dict[str, Any]:
    results = []
    pass_values: list[float] = []
    for scenario in scenarios:
        world = create_initial_world()
        apply_scenario_setup(world, scenario)
        decision = _evaluate_hard_delegation(world, scenario)
        result_item = _build_result_item(scenario, decision)
        pass_values.append(1.0 if result_item["ok"] else 0.0)
        results.append(result_item)
    metric = metric_summary("l1_rule_pass_rate", pass_values, baseline=BASELINE_HARD_DELEGATION)
    passed = int(sum(pass_values))
    return {
        "ok": passed == len(scenarios),
        "passed": passed,
        "items": results,
        "metric": metric,
    }


def _evaluate_hard_delegation(world: dict[str, Any], scenario: EvalScenario) -> dict[str, Any]:
    agent = world["agents"][scenario.npc_id]
    status = agent.get("status", {}) if isinstance(agent.get("status"), dict) else {}
    # Hard Delegation：Director 直接按状态阈值给任务，不依赖主观记忆或关系边。
    energy_score = 1.0 - min(100.0, float(status.get("energy", 70))) / 100.0
    money_score = 1.0 - min(100.0, float(status.get("money", 50))) / 100.0
    social_score = 1.0 - min(100.0, float(status.get("social", 50))) / 100.0
    if energy_score >= money_score and energy_score >= social_score:
        primary_need = "energy"
        selected_tool_id = "life.rest"
    elif money_score >= social_score:
        primary_need = "money_anxiety"
        selected_tool_id = "farm.water_crop" if str(agent.get("locationId") or "") == "farm" else "shop.open_shop"
    else:
        primary_need = "affiliation"
        selected_tool_id = "social.chat_with"
    return {
        "npcId": scenario.npc_id,
        "primaryNeed": {"needId": primary_need},
        "decision": {
            "selectedToolId": selected_tool_id,
            "arbitrationTrace": {"policy": "hard_delegation"},
        },
    }


def _build_result_item(scenario: EvalScenario, decision: dict[str, Any]) -> dict[str, Any]:
    primary_need = decision.get("primaryNeed", {}).get("needId")
    selected_tool = decision.get("decision", {}).get("selectedToolId") or ""
    ok = primary_need in scenario.expected_need_ids and any(selected_tool.startswith(prefix) for prefix in scenario.expected_tool_prefixes)
    return {
        "scenario": scenario.to_dict(),
        "ok": ok,
        "primaryNeed": primary_need,
        "selectedToolId": selected_tool,
        "decision": decision.get("decision"),
    }


def _export_baseline_result(result: dict[str, Any]) -> dict[str, Any]:
    metric = result["metric"]
    return {
        "ok": result["ok"],
        "passed": result["passed"],
        "total": len(result["items"]),
        "mean": metric["mean"],
        "std": metric["std"],
        "n": metric["n"],
        "metric": metric,
        "items": result["items"],
    }


def _build_ablation_comparison(full_run: dict[str, Any], hard_run: dict[str, Any], no_relationship_run: dict[str, Any]) -> dict[str, Any]:
    full_mean = float(full_run["metric"]["mean"])
    hard_mean = float(hard_run["metric"]["mean"])
    no_relation_mean = float(no_relationship_run["metric"]["mean"])
    return {
        "metric": "l1_rule_pass_rate",
        "full_baseline": BASELINE_FULL,
        "comparison": {
            BASELINE_FULL: _metric_triplet(full_run["metric"]),
            BASELINE_HARD_DELEGATION: _metric_triplet(hard_run["metric"]),
            ABLATION_NO_RELATIONSHIP_EDGE: _metric_triplet(no_relationship_run["metric"]),
        },
        "delta_vs_full": {
            BASELINE_HARD_DELEGATION: round(hard_mean - full_mean, 6),
            ABLATION_NO_RELATIONSHIP_EDGE: round(no_relation_mean - full_mean, 6),
        },
    }


def _metric_triplet(metric: dict[str, Any]) -> dict[str, Any]:
    return {"mean": metric["mean"], "std": metric["std"], "n": metric["n"]}


def _run_process_baseline(
    scenarios: tuple[ProcessGoalSpec, ...],
    *,
    baseline: str,
    provider_mode: str,
    seed_count: int,
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for seed_index in range(1, max(1, int(seed_count)) + 1):
        for scenario in scenarios:
            if baseline == BASELINE_HARD_DELEGATION:
                item = _run_hard_delegation_process_scenario(scenario)
            else:
                item = _run_runtime_process_scenario(
                    scenario,
                    baseline=baseline,
                    subjective_memory_ablation=_subjective_memory_ablation_for_baseline(baseline),
                    relationship_ablation=_relationship_ablation_for_baseline(baseline),
                    provider_mode=provider_mode,
                    seed_index=seed_index,
                    seed_count=seed_count,
                )
            if seed_count > 1 or provider_mode in {"cloud", "mixed"}:
                item["seed"] = _process_seed_payload(scenario, baseline=baseline, seed_index=seed_index)
            items.append(item)
    metrics = process_metric_summaries(items, baseline=baseline)
    passed = sum(1 for item in items if item.get("ok"))
    return {
        "ok": passed == len(items),
        "passed": passed,
        "total": len(items),
        "providerMode": provider_mode,
        "seedCount": max(1, int(seed_count)),
        "metrics": metrics,
        "items": items,
    }


def _relationship_ablation_for_baseline(baseline: str) -> str:
    return {
        ABLATION_NO_RELATIONSHIP_EDGE: RELATIONSHIP_ABLATION_NO_EDGE,
        ABLATION_SHUFFLED_MEMORY_OWNER: RELATIONSHIP_ABLATION_SHUFFLED_OWNER,
        ABLATION_EVIDENCE_LINK_REMOVAL: RELATIONSHIP_ABLATION_EVIDENCE_LINK_REMOVAL,
    }.get(baseline, RELATIONSHIP_ABLATION_NONE)


def _subjective_memory_ablation_for_baseline(baseline: str) -> str:
    return {
        ABLATION_NO_SUBJECTIVE_MEMORY: SUBJECTIVE_MEMORY_ABLATION_NO_MEMORY,
    }.get(baseline, SUBJECTIVE_MEMORY_ABLATION_NONE)


def _normalize_process_provider_mode(provider_mode: str) -> str:
    mode = str(provider_mode or "rule").strip().lower()
    if mode not in PROCESS_PROVIDER_MODES:
        raise ValueError(f"process provider 只支持 {', '.join(PROCESS_PROVIDER_MODES)}：{provider_mode}")
    return mode


def _process_seed_payload(scenario: ProcessGoalSpec, *, baseline: str, seed_index: int) -> dict[str, Any]:
    """生成可复核的 Eval seed 标识；真实云模型不强制支持供应商 seed 参数。"""
    seed_id = f"{scenario.scenario_id}:{baseline}:seed_{int(seed_index):02d}"
    digest = hashlib.sha256(seed_id.encode("utf-8")).hexdigest()[:16]
    return {
        "seedIndex": int(seed_index),
        "seedId": seed_id,
        "deterministicHash": digest,
    }


def _run_runtime_process_scenario(
    scenario: ProcessGoalSpec,
    *,
    baseline: str,
    subjective_memory_ablation: str = SUBJECTIVE_MEMORY_ABLATION_NONE,
    relationship_ablation: str = RELATIONSHIP_ABLATION_NONE,
    provider_mode: str = "rule",
    seed_index: int = 1,
    seed_count: int = 1,
) -> dict[str, Any]:
    runtime = AgentRuntime(provider_mode=provider_mode)
    runtime.world["processEvalSeed"] = _process_seed_payload(scenario, baseline=baseline, seed_index=seed_index)
    runtime.world["processEvalScenarioId"] = scenario.scenario_id
    apply_process_goal_setup(runtime.world, scenario)
    setup_evidence = _seed_process_goal_runtime(runtime, scenario)
    runtime_ablation = _apply_runtime_process_ablation(
        runtime,
        scenario=scenario,
        subjective_memory_ablation=subjective_memory_ablation,
        relationship_ablation=relationship_ablation,
    )
    runtime.tick(float(scenario.max_game_hours) * 3600.0, speed=1.0)
    llm_decision_evidence = _collect_process_llm_decision_evidence(
        runtime,
        scenario=scenario,
        baseline=baseline,
        provider_mode=provider_mode,
        seed_index=seed_index,
        seed_count=seed_count,
    )
    snapshot = runtime.get_phase2_debug_snapshot({"agentId": scenario.npc_id, "limit": 50})
    recent_trace_events = snapshot.get("recentTraceEvents", []) if isinstance(snapshot.get("recentTraceEvents"), list) else []
    decision_budget_trace = _summarize_budget_trace_events(
        [
            event
            for event in recent_trace_events
            if isinstance(event, dict)
            and str(event.get("eventType") or "") in {"budget.decision_consumed", "budget.decision_fallback"}
            and str(event.get("agentId") or "") == scenario.npc_id
        ]
    )
    subjective_items = _debug_items(snapshot.get("subjectiveMemory", {}))
    ablated_subjective_memory = _apply_subjective_memory_ablation(
        mode=subjective_memory_ablation,
        subjective_items=subjective_items,
    )
    subjective_items = ablated_subjective_memory["subjectiveItems"]
    relationship_items = _debug_items(snapshot.get("relationshipEdges", {}))
    heuristic_items = _debug_items(snapshot.get("heuristics", {}))
    relationship_edges_for_decision = [
        edge.to_dict()
        for edge in runtime.relationship_edge_store.list(agent_id=scenario.npc_id, limit=12)
    ]
    ablated_relationships = _apply_relationship_ablation(
        scenario=scenario,
        mode=relationship_ablation,
        relationship_items=relationship_items,
        decision_edges=relationship_edges_for_decision,
    )
    relationship_items = ablated_relationships["relationshipItems"]
    relationship_edges_for_decision = ablated_relationships["decisionEdges"]
    all_target_tool_events = [
        event
        for event in recent_trace_events
        if event.get("eventType") == "tool.execution_completed"
        and event.get("agentId") == scenario.npc_id
        and scenario.target_npc_id in event.get("targetIds", [])
    ]
    goal_tool_events = [
        event
        for event in all_target_tool_events
        if any(_event_tool_matches(runtime, event, prefix) for prefix in scenario.expected_tool_prefixes)
    ] or all_target_tool_events
    goal_event_ids = {str(event.get("eventId") or "") for event in goal_tool_events}
    goal_trace_ids = {str(event.get("traceId") or "") for event in goal_tool_events}
    memory_source_ids = {str(item.get("sourceEventId") or "") for item in subjective_items}
    subjective_memories_for_decision = [item for item in subjective_items if str(item.get("agentId") or "") == scenario.npc_id]
    heuristic_source_ids = {str(item.get("sourceEventId") or "") for item in heuristic_items}
    heuristics_for_decision = [item for item in heuristic_items if str(item.get("agentId") or "") == scenario.npc_id]
    relationship_source_ids = {
        str(source_id)
        for edge in relationship_items
        for source_id in edge.get("sourceEventIds", [])
        if _same_relationship_pair(edge, scenario.npc_id, scenario.target_npc_id)
    }
    memory_trace_links = [
        event
        for event in recent_trace_events
        if event.get("eventType") == "memory.result_observed"
        and str(event.get("sourceEventId") or "") in goal_event_ids
        and str(event.get("traceId") or "") in goal_trace_ids
    ]
    decision_with_relationship_memory = runtime.motivation_engine.evaluate_npc(
        runtime.world,
        scenario.npc_id,
        delta_minutes=20.0,
        relationship_edges=relationship_edges_for_decision,
        subjective_memory_records=subjective_memories_for_decision,
        heuristics=heuristics_for_decision,
    )
    decision_without_relationship_edges = runtime.motivation_engine.evaluate_npc(
        runtime.world,
        scenario.npc_id,
        delta_minutes=20.0,
        relationship_edges=[],
        subjective_memory_records=subjective_memories_for_decision,
        heuristics=heuristics_for_decision,
    )
    decision_without_relationship_memory = runtime.motivation_engine.evaluate_npc(
        runtime.world,
        scenario.npc_id,
        delta_minutes=20.0,
        relationship_edges=[],
        subjective_memory_records=[],
        heuristics=[],
    )
    tool_selection_replay = _build_counterfactual_tool_selection_replay(
        runtime=runtime,
        scenario=scenario,
        baseline_decision=decision_with_relationship_memory,
        relationship_edges=relationship_edges_for_decision,
        subjective_memory_records=subjective_memories_for_decision,
        heuristics=heuristics_for_decision,
        cycles=COUNTERFACTUAL_REPLAY_DECISION_CYCLES,
    )
    counterfactual_replay = _build_counterfactual_replay(
        scenario=scenario,
        decision_with_relationship_memory=decision_with_relationship_memory,
        decision_without_relationship_edges=decision_without_relationship_edges,
        decision_without_relationship_memory=decision_without_relationship_memory,
        relationship_source_ids=relationship_source_ids,
        subjective_memory_source_ids=memory_source_ids,
        heuristic_source_ids=heuristic_source_ids,
        tool_selection_replay=tool_selection_replay,
    )
    process_checks = {
        "goal_relevant_tool_event": bool(goal_tool_events),
        "subjective_memory_refs": bool(goal_event_ids & memory_source_ids),
        "relationship_edge_trace": bool(goal_event_ids & relationship_source_ids),
        "causal_trace": bool(memory_trace_links),
        "future_behavior_reference": bool(counterfactual_replay["effect"]),
        "counterfactual_tool_selection_change": bool(counterfactual_replay["toolSelectionChanged"]),
        "preexisting_harm_memory": _has_preexisting_harm_memory(subjective_items),
        "subjective_memory_causal_effect": bool(counterfactual_replay["subjectiveMemoryEffect"]),
        "decision_budget_trace": bool(decision_budget_trace["eventCount"])
        and decision_budget_trace["traceSchemaOkCount"] == decision_budget_trace["eventCount"],
        "decision_budget_source_link": bool(decision_budget_trace["eventCount"])
        and decision_budget_trace["sourceLinkCount"] == decision_budget_trace["eventCount"]
        and decision_budget_trace["traceRefCount"] == decision_budget_trace["eventCount"],
    }
    goal_relevant_state_changes = max(1, len(relationship_items))
    state_changes_with_source = sum(1 for edge in relationship_items if edge.get("sourceEventIds"))
    metrics = build_process_metrics(
        process_checks=process_checks,
        required_process_ids=scenario.required_process_ids,
        shortcut_events=_shortcut_events(relationship_items),
        goal_relevant_state_changes=goal_relevant_state_changes,
        forced_actions=0,
        goal_relevant_actions=max(1, len(goal_tool_events)),
        overreaching_interventions=0,
        total_interventions=1,
        state_changes_with_source=state_changes_with_source,
        relationship_relevant_decisions=1,
        decisions_with_relationship_memory=1 if counterfactual_replay["relationshipEffect"] else 0,
        counterfactual_tool_selection_change_rate=float(
            counterfactual_replay.get("counterfactualToolSelectionChangeRate", 0.0)
        ),
    )
    return {
        "scenario": scenario.to_dict(),
        "baseline": baseline,
        "ok": metrics["goal_success_rate"] >= 1.0 and metrics["required_process_coverage"] >= 0.75,
        "metrics": metrics,
        "processChecks": process_checks,
        "evidence": {
            "goalToolEvents": goal_tool_events,
            "subjectiveMemoryRefs": sorted(goal_event_ids & memory_source_ids),
            "relationshipSourceIds": sorted(relationship_source_ids),
            "heuristicSourceIds": sorted(heuristic_source_ids),
            "memoryTraceLinks": memory_trace_links,
            "counterfactualReplay": counterfactual_replay,
            "scenarioSetup": setup_evidence,
            "runtimeAblation": runtime_ablation,
            "subjectiveMemoryAblation": ablated_subjective_memory["evidence"],
            "relationshipAblation": ablated_relationships["evidence"],
            "traceSchemaVersion": snapshot.get("traceSchemaVersion"),
            "llmDecisionEvidence": llm_decision_evidence,
            "decisionBudgetTrace": decision_budget_trace,
        },
    }


def _collect_process_llm_decision_evidence(
    runtime: AgentRuntime,
    *,
    scenario: ProcessGoalSpec,
    baseline: str,
    provider_mode: str,
    seed_index: int,
    seed_count: int,
) -> dict[str, Any]:
    """从 runtime 事件流提取真实 LLM 仲裁证据，保持 manifest 可直接追溯 provider_usage_actual.v1。"""
    records: list[dict[str, Any]] = []
    for event in runtime.event_store.list():
        if event.get("type") != "debug.decision":
            continue
        payload = event.get("payload", {}) if isinstance(event.get("payload"), dict) else {}
        debug = payload.get("debug", {}) if isinstance(payload.get("debug"), dict) else {}
        if debug.get("arbitrationLayer") != "social_strategic":
            continue
        usage_record = debug.get("providerUsageRecord", {}) if isinstance(debug.get("providerUsageRecord"), dict) else {}
        executed = debug.get("executed", {}) if isinstance(debug.get("executed"), dict) else {}
        records.append(
            {
                "schemaVersion": PROCESS_LLM_EVIDENCE_VERSION,
                "providerUsageSchemaVersion": require_schema_version("provider_usage_actual"),
                "scenarioId": scenario.scenario_id,
                "baseline": baseline,
                "seedIndex": int(seed_index),
                "seedCount": int(seed_count),
                "eventId": event.get("id"),
                "npcId": usage_record.get("npcId") or scenario.npc_id,
                "feature": usage_record.get("feature") or debug.get("feature"),
                "channel": usage_record.get("channel"),
                "provider": usage_record.get("provider") or debug.get("provider"),
                "providerMode": usage_record.get("providerMode") or provider_mode,
                "profileName": usage_record.get("profileName") or debug.get("profileName"),
                "model": usage_record.get("model"),
                "tokens": int(usage_record.get("tokens") or 0),
                "promptTokens": int(usage_record.get("promptTokens") or 0),
                "completionTokens": int(usage_record.get("completionTokens") or 0),
                "cost": float(usage_record.get("cost") or 0.0),
                "currency": usage_record.get("currency"),
                "latencyMs": int(usage_record.get("latencyMs") or 0),
                "fallbackReason": usage_record.get("fallbackReason") or debug.get("fallbackReason"),
                "finalSelectedToolId": executed.get("selectedToolId") or debug.get("selectedToolId"),
                "ruleSelectedToolId": executed.get("ruleSelectedToolId") or debug.get("ruleSelectedToolId"),
                "candidateToolIds": list(executed.get("candidateToolIds", []))
                if isinstance(executed.get("candidateToolIds"), list)
                else list(debug.get("candidateToolIds", [])) if isinstance(debug.get("candidateToolIds"), list) else [],
                "providerUsageRecord": usage_record,
            }
        )
    budget_snapshot = runtime.decision_budget.debug_snapshot(runtime.world, npc_ids=[scenario.npc_id])
    return {
        "schemaVersion": PROCESS_LLM_EVIDENCE_VERSION,
        "providerUsageSchemaVersion": require_schema_version("provider_usage_actual"),
        "providerMode": provider_mode,
        "scenarioId": scenario.scenario_id,
        "baseline": baseline,
        "seedIndex": int(seed_index),
        "seedCount": int(seed_count),
        "recordCount": len(records),
        "records": records,
        "providerActuals": budget_snapshot.get("providerActuals", {}),
    }


def _build_process_llm_evidence(
    runs: dict[str, dict[str, Any]],
    *,
    provider_mode: str,
    seed_count: int,
    source: str,
) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for run in runs.values():
        for item in run.get("items", []) if isinstance(run, dict) else []:
            evidence = item.get("evidence", {}) if isinstance(item, dict) and isinstance(item.get("evidence"), dict) else {}
            llm_evidence = evidence.get("llmDecisionEvidence", {}) if isinstance(evidence.get("llmDecisionEvidence"), dict) else {}
            records.extend(
                dict(record)
                for record in llm_evidence.get("records", [])
                if isinstance(record, dict)
            )
    return {
        "schemaVersion": PROCESS_LLM_EVIDENCE_VERSION,
        "providerUsageSchemaVersion": require_schema_version("provider_usage_actual"),
        "source": source,
        "providerMode": provider_mode,
        "seedCount": int(seed_count),
        "recordCount": len(records),
        "cloudCallCount": sum(1 for record in records if record.get("provider") == "CloudApiProvider"),
        "fallbackCount": sum(1 for record in records if record.get("fallbackReason")),
        "totals": _llm_record_totals(records),
        "byScenario": _llm_records_by_field(records, "scenarioId"),
        "byBaseline": _llm_records_by_field(records, "baseline"),
        "records": records,
    }


def _llm_record_totals(records: list[dict[str, Any]]) -> dict[str, Any]:
    """汇总 token、latency 和 cost，供 manifest / PROMOTION 快速引用。"""
    totals = {
        "calls": len(records),
        "tokens": 0,
        "promptTokens": 0,
        "completionTokens": 0,
        "latencyTotalMs": 0,
        "latencyAvgMs": 0.0,
        "cost": 0.0,
        "currency": None,
    }
    for record in records:
        totals["tokens"] += int(record.get("tokens") or 0)
        totals["promptTokens"] += int(record.get("promptTokens") or 0)
        totals["completionTokens"] += int(record.get("completionTokens") or 0)
        totals["latencyTotalMs"] += int(record.get("latencyMs") or 0)
        totals["cost"] = round(float(totals["cost"]) + float(record.get("cost") or 0.0), 8)
        totals["currency"] = _merge_currency(totals["currency"], record.get("currency"))
    totals["latencyAvgMs"] = round(float(totals["latencyTotalMs"]) / max(1, len(records)), 2)
    return totals


def _llm_records_by_field(records: list[dict[str, Any]], field: str) -> dict[str, dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        groups.setdefault(str(record.get(field) or "unknown"), []).append(record)
    return {key: _llm_record_totals(items) for key, items in sorted(groups.items())}


def _merge_currency(current: Any, incoming: Any) -> str | None:
    current_text = str(current or "")
    incoming_text = str(incoming or "")
    if not current_text:
        return incoming_text or None
    if not incoming_text or incoming_text == current_text:
        return current_text
    return "mixed"


def _cache_latest_process_llm_evidence(llm_evidence: dict[str, Any]) -> None:
    """把手动 cloud eval 的证据缓存到 .run，便于随后 export manifest 引用同一批实际调用。"""
    if not int(llm_evidence.get("recordCount") or 0):
        return
    PROCESS_LLM_EVIDENCE_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _write_json(PROCESS_LLM_EVIDENCE_CACHE_PATH, llm_evidence)


def _load_cached_process_llm_evidence() -> dict[str, Any] | None:
    """读取最近一次手动 cloud process 证据；缓存路径位于 .run，不进入版本控制。"""
    if not PROCESS_LLM_EVIDENCE_CACHE_PATH.exists():
        return None
    try:
        cached = json.loads(PROCESS_LLM_EVIDENCE_CACHE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(cached, dict) or not int(cached.get("recordCount") or 0):
        return None
    evidence = dict(cached)
    evidence["source"] = "latest_cache"
    evidence["cache"] = {
        "loadedFrom": PROCESS_LLM_EVIDENCE_CACHE_PATH.as_posix(),
        "originalSource": cached.get("source"),
    }
    return evidence


def _seed_process_goal_runtime(runtime: AgentRuntime, scenario: ProcessGoalSpec) -> dict[str, Any]:
    """按 scenario 注入最小前史证据，让规则级 eval 能覆盖真实叙事前置条件。"""
    if scenario.setup_kind != "forgiveness_memory":
        return {"kind": scenario.setup_kind, "seeded": False}

    harm_event = runtime.event_store.append(
        "eval.precondition.harm_memory",
        {
            "scenarioId": scenario.scenario_id,
            "agentId": scenario.npc_id,
            "targetAgentId": scenario.target_npc_id,
            "summary": "玩家曾答应给布兰娜补交节前作物，却在约定时间失信。",
            "processTag": "forgiveness_harm",
        },
    )
    world_tick = int(runtime.world.get("clock", {}).get("tick", 0)) if isinstance(runtime.world.get("clock"), dict) else 0
    memory = SubjectiveMemoryRecord(
        record_id=f"{harm_event['id']}:{scenario.npc_id}:harm",
        agent_id=scenario.npc_id,
        source_event_id=str(harm_event.get("id") or ""),
        perspective="subjective",
        text="布兰娜记得玩家曾经失信；如果要修复关系，她需要亲眼确认补偿并重新谈一次。 social.chat_with",
        emotional_valence=-0.8,
        confidence=0.95,
        tags=("tool_result", "social.chat_with", "forgiveness_harm", "player_broken_promise"),
        created_tick=world_tick,
    )
    runtime.subjective_memory_store.add(memory, world_tick=world_tick)
    runtime.relationship_edge_store.upsert(
        source_agent_id=scenario.npc_id,
        target_agent_id=scenario.target_npc_id,
        edge_type="suspicion",
        delta=0.12,
        tick=world_tick,
        source_event_id=str(harm_event.get("id") or ""),
        trace_refs=[{"type": "eval_precondition", "scenarioId": scenario.scenario_id}],
    )
    return {
        "kind": scenario.setup_kind,
        "seeded": True,
        "harmEventId": harm_event.get("id"),
        "subjectiveMemoryRecordId": memory.record_id,
        "targetAgentId": scenario.target_npc_id,
    }


def _apply_runtime_process_ablation(
    runtime: AgentRuntime,
    *,
    scenario: ProcessGoalSpec,
    subjective_memory_ablation: str,
    relationship_ablation: str,
) -> dict[str, Any]:
    """把 ablation 条件写入 world，使 AgentRuntime.tick 内部的决策输入同步受控。"""
    runtime.world["processEvalAblation"] = {
        "agentId": scenario.npc_id,
        "targetAgentId": scenario.target_npc_id,
        "subjectiveMemory": subjective_memory_ablation,
        "relationshipEdges": relationship_ablation,
    }
    return dict(runtime.world["processEvalAblation"])


def _has_preexisting_harm_memory(subjective_items: list[dict[str, Any]]) -> bool:
    for item in subjective_items:
        tags = item.get("tags", []) if isinstance(item.get("tags"), list) else []
        if "forgiveness_harm" in {str(tag) for tag in tags}:
            return True
    return False


def _run_hard_delegation_process_scenario(scenario: ProcessGoalSpec) -> dict[str, Any]:
    process_checks = {
        "goal_relevant_tool_event": True,
        "subjective_memory_refs": False,
        "relationship_edge_trace": False,
        "causal_trace": False,
        "future_behavior_reference": False,
    }
    metrics = build_process_metrics(
        process_checks=process_checks,
        required_process_ids=scenario.required_process_ids,
        shortcut_events=1,
        goal_relevant_state_changes=1,
        forced_actions=1,
        goal_relevant_actions=1,
        overreaching_interventions=1,
        total_interventions=1,
        state_changes_with_source=0,
        relationship_relevant_decisions=1,
        decisions_with_relationship_memory=0,
        goal_success_override=True,
    )
    return {
        "scenario": scenario.to_dict(),
        "baseline": BASELINE_HARD_DELEGATION,
        "ok": True,
        "metrics": metrics,
        "processChecks": process_checks,
        "evidence": {
            "delegation": {
                "assignee": scenario.npc_id,
                "targetNpcId": scenario.target_npc_id,
                "requiredActions": ["social.chat_with"],
                "policy": "hard_delegation",
            }
        },
    }


def _debug_items(section: Any) -> list[dict[str, Any]]:
    if isinstance(section, dict) and isinstance(section.get("items"), list):
        return [item for item in section["items"] if isinstance(item, dict)]
    if isinstance(section, list):
        return [item for item in section if isinstance(item, dict)]
    return []


def _event_tool_matches(runtime: AgentRuntime, event: dict[str, Any], prefix: str) -> bool:
    event_id = str(event.get("eventId") or "")
    stored = next((item for item in runtime.event_store.list() if item.get("id") == event_id), {})
    payload = stored.get("payload", {}) if isinstance(stored.get("payload"), dict) else {}
    return str(payload.get("toolId") or "").startswith(prefix)


def _same_relationship_pair(edge: dict[str, Any], source_id: str, target_id: str) -> bool:
    return {str(edge.get("sourceAgentId") or ""), str(edge.get("targetAgentId") or "")} == {source_id, target_id}


def _apply_subjective_memory_ablation(
    *,
    mode: str,
    subjective_items: list[dict[str, Any]],
) -> dict[str, Any]:
    """构造主观记忆反事实输入，验证 process coverage 是否依赖 subjective memory。"""
    if mode == SUBJECTIVE_MEMORY_ABLATION_NO_MEMORY:
        return {
            "subjectiveItems": [],
            "evidence": {
                "mode": mode,
                "removedSubjectiveMemoryCount": len(subjective_items),
            },
        }
    return {
        "subjectiveItems": subjective_items,
        "evidence": {"mode": SUBJECTIVE_MEMORY_ABLATION_NONE},
    }


def _apply_relationship_ablation(
    *,
    scenario: ProcessGoalSpec,
    mode: str,
    relationship_items: list[dict[str, Any]],
    decision_edges: list[dict[str, Any]],
) -> dict[str, Any]:
    """构造关系记忆反事实输入，保持同一轮 goal trace 可复核。"""
    if mode == RELATIONSHIP_ABLATION_NO_EDGE:
        return {
            "relationshipItems": [],
            "decisionEdges": [],
            "evidence": {
                "mode": mode,
                "removedRelationshipCount": len(relationship_items),
                "removedDecisionEdgeCount": len(decision_edges),
            },
        }
    if mode == RELATIONSHIP_ABLATION_SHUFFLED_OWNER:
        shuffled_items = [_shuffle_relationship_owner(edge, scenario) for edge in relationship_items]
        shuffled_decision_edges = [_shuffle_relationship_owner(edge, scenario) for edge in decision_edges]
        return {
            "relationshipItems": shuffled_items,
            "decisionEdges": shuffled_decision_edges,
            "evidence": {
                "mode": mode,
                "changedRelationshipCount": _changed_edge_count(relationship_items, shuffled_items),
                "changedDecisionEdgeCount": _changed_edge_count(decision_edges, shuffled_decision_edges),
            },
        }
    if mode == RELATIONSHIP_ABLATION_EVIDENCE_LINK_REMOVAL:
        stripped_items = [_strip_relationship_evidence(edge) for edge in relationship_items]
        stripped_decision_edges = [_strip_relationship_evidence(edge) for edge in decision_edges]
        return {
            "relationshipItems": stripped_items,
            "decisionEdges": stripped_decision_edges,
            "evidence": {
                "mode": mode,
                "removedSourceEventIdCount": _source_event_id_count(relationship_items)
                + _source_event_id_count(decision_edges),
                "removedTraceRefCount": _trace_ref_count(relationship_items) + _trace_ref_count(decision_edges),
            },
        }
    return {
        "relationshipItems": relationship_items,
        "decisionEdges": decision_edges,
        "evidence": {"mode": RELATIONSHIP_ABLATION_NONE},
    }


def _shuffle_relationship_owner(edge: dict[str, Any], scenario: ProcessGoalSpec) -> dict[str, Any]:
    """保留边和证据数量，只替换记忆归属，用于验证 owner 是否真的参与决策。"""
    shuffled = dict(edge)
    source_id, target_id = _alternate_relationship_pair(scenario)
    edge_type = str(shuffled.get("edgeType") or "affection")
    shuffled["sourceAgentId"] = source_id
    shuffled["targetAgentId"] = target_id
    shuffled["edgeId"] = _relationship_edge_id(source_id, target_id, edge_type)
    return shuffled


def _alternate_relationship_pair(scenario: ProcessGoalSpec) -> tuple[str, str]:
    candidates = ["orren", "kai", "bram", "mira", "tomas", "lena"]
    picked = [npc_id for npc_id in candidates if npc_id not in {scenario.npc_id, scenario.target_npc_id}]
    if len(picked) >= 2:
        return picked[0], picked[1]
    return "orren", "kai"


def _relationship_edge_id(source_id: str, target_id: str, edge_type: str) -> str:
    left, right = sorted([source_id, target_id])
    return f"{left}::{right}::{edge_type}"


def _strip_relationship_evidence(edge: dict[str, Any]) -> dict[str, Any]:
    stripped = dict(edge)
    stripped["sourceEventIds"] = []
    stripped["traceRefs"] = []
    return stripped


def _changed_edge_count(before: list[dict[str, Any]], after: list[dict[str, Any]]) -> int:
    return sum(1 for left, right in zip(before, after) if left != right)


def _source_event_id_count(edges: list[dict[str, Any]]) -> int:
    return sum(len(edge.get("sourceEventIds", [])) for edge in edges if isinstance(edge.get("sourceEventIds"), list))


def _trace_ref_count(edges: list[dict[str, Any]]) -> int:
    return sum(len(edge.get("traceRefs", [])) for edge in edges if isinstance(edge.get("traceRefs"), list))


def _build_counterfactual_replay(
    *,
    scenario: ProcessGoalSpec,
    decision_with_relationship_memory: dict[str, Any],
    decision_without_relationship_edges: dict[str, Any],
    decision_without_relationship_memory: dict[str, Any],
    relationship_source_ids: set[str],
    subjective_memory_source_ids: set[str],
    heuristic_source_ids: set[str],
    tool_selection_replay: dict[str, Any],
) -> dict[str, Any]:
    with_decision = _decision_payload(decision_with_relationship_memory)
    without_relationship_decision = _decision_payload(decision_without_relationship_edges)
    without_decision = _decision_payload(decision_without_relationship_memory)
    selected_with = str(with_decision.get("selectedToolId") or "")
    selected_without_relationship = str(without_relationship_decision.get("selectedToolId") or "")
    selected_without = str(without_decision.get("selectedToolId") or "")
    relationship_refs = [ref for ref in with_decision.get("relationshipEdgeRefs", []) if isinstance(ref, dict)]
    relevant_refs = [
        ref
        for ref in relationship_refs
        if _relationship_ref_matches_pair(ref, scenario.npc_id, scenario.target_npc_id)
        and _relationship_ref_uses_sources(ref, relationship_source_ids)
    ]
    subjective_memory_refs = [ref for ref in with_decision.get("subjectiveMemoryRefs", []) if isinstance(ref, dict)]
    relevant_subjective_memory_refs = [
        ref
        for ref in subjective_memory_refs
        if _subjective_memory_ref_uses_sources(ref, subjective_memory_source_ids)
    ]
    heuristic_refs = [ref for ref in with_decision.get("heuristicRefs", []) if isinstance(ref, dict)]
    relevant_heuristic_refs = [
        ref
        for ref in heuristic_refs
        if _heuristic_ref_uses_sources(ref, heuristic_source_ids)
    ]
    score_effect = _candidate_scores_changed(
        list(with_decision.get("candidateScores", [])),
        list(without_decision.get("candidateScores", [])),
    )
    relationship_score_effect = _candidate_field_changed(
        list(with_decision.get("candidateScores", [])),
        list(without_relationship_decision.get("candidateScores", [])),
        "relationshipBonus",
    )
    subjective_memory_score_effect = _candidate_field_changed(
        list(with_decision.get("candidateScores", [])),
        list(without_decision.get("candidateScores", [])),
        "subjectiveMemoryBonus",
    )
    heuristic_score_effect = _candidate_field_changed(
        list(with_decision.get("candidateScores", [])),
        list(without_decision.get("candidateScores", [])),
        "heuristicBonus",
    )
    decision_effect = bool(selected_with) and bool(selected_without) and (selected_with != selected_without or score_effect)
    relationship_decision_effect = bool(selected_with) and bool(selected_without_relationship) and selected_with != selected_without_relationship
    tool_selection_changed = bool(tool_selection_replay.get("changedDecisionCount", 0))
    # 关系记忆的因果使用必须有目标关系引用，并且关系 bonus 在只移除关系边的反事实中发生变化；
    # 这样避免把主观记忆或启发式引起的分数变化误计为关系记忆贡献。
    relationship_effect = bool(relevant_refs) and relationship_score_effect
    subjective_memory_effect = bool(relevant_subjective_memory_refs) and subjective_memory_score_effect
    heuristic_effect = bool(relevant_heuristic_refs) and heuristic_score_effect
    return {
        "selectedWithRelationshipMemory": selected_with or None,
        "selectedWithoutRelationshipEdges": selected_without_relationship or None,
        "selectedWithoutRelationshipMemory": selected_without or None,
        "effect": relationship_effect or subjective_memory_effect or heuristic_effect,
        "relationshipEffect": relationship_effect,
        "subjectiveMemoryEffect": subjective_memory_effect,
        "heuristicEffect": heuristic_effect,
        "relationshipScoreEffect": relationship_score_effect,
        "relationshipDecisionEffect": relationship_decision_effect,
        "subjectiveMemoryScoreEffect": subjective_memory_score_effect,
        "heuristicScoreEffect": heuristic_score_effect,
        "subjectiveMemoryToolSelectionEffect": bool(relevant_subjective_memory_refs) and tool_selection_changed,
        "toolSelectionChanged": tool_selection_changed,
        "counterfactualToolSelectionChangeRate": tool_selection_replay.get("changeRate", 0.0),
        "toolSelectionReplay": tool_selection_replay,
        "relationshipEdgeRefs": relationship_refs,
        "relevantRelationshipEdgeRefs": relevant_refs,
        "subjectiveMemoryRefs": subjective_memory_refs,
        "relevantSubjectiveMemoryRefs": relevant_subjective_memory_refs,
        "heuristicRefs": heuristic_refs,
        "relevantHeuristicRefs": relevant_heuristic_refs,
        "candidateScoresWithRelationshipMemory": list(with_decision.get("candidateScores", [])),
        "candidateScoresWithoutRelationshipEdges": list(without_relationship_decision.get("candidateScores", [])),
        "candidateScoresWithoutRelationshipMemory": list(without_decision.get("candidateScores", [])),
        "reasonWithRelationshipMemory": with_decision.get("reason"),
        "reasonWithoutRelationshipEdges": without_relationship_decision.get("reason"),
        "reasonWithoutRelationshipMemory": without_decision.get("reason"),
    }


def _build_counterfactual_tool_selection_replay(
    *,
    runtime: AgentRuntime,
    scenario: ProcessGoalSpec,
    baseline_decision: dict[str, Any],
    relationship_edges: list[dict[str, Any]],
    subjective_memory_records: list[dict[str, Any]],
    heuristics: list[dict[str, Any]],
    cycles: int,
) -> dict[str, Any]:
    """逐条移除主观记忆，复算后续 24 个决策周期的 selectedToolId 变化。"""
    decision_payload = _decision_payload(baseline_decision)
    selected_ref_ids = {
        str(ref.get("recordId") or "")
        for ref in decision_payload.get("subjectiveMemoryRefs", [])
        if isinstance(ref, dict) and str(ref.get("recordId") or "")
    }
    candidate_records = [
        dict(record)
        for record in subjective_memory_records
        if str(record.get("recordId") or "") in selected_ref_ids
    ]
    if not candidate_records:
        candidate_records = [dict(record) for record in subjective_memory_records]

    cycle_count = max(1, int(cycles))
    comparisons: list[dict[str, Any]] = []
    changed_count = 0
    total_count = 0
    for cycle_index in range(1, cycle_count + 1):
        cycle_world = _counterfactual_cycle_world(runtime.world, cycle_index)
        base_decision = runtime.motivation_engine.evaluate_npc(
            cycle_world,
            scenario.npc_id,
            delta_minutes=20.0,
            relationship_edges=relationship_edges,
            subjective_memory_records=subjective_memory_records,
            heuristics=heuristics,
        )
        base_payload = _decision_payload(base_decision)
        selected_with_memory = str(base_payload.get("selectedToolId") or "")
        for record in candidate_records:
            removed_record_id = str(record.get("recordId") or "")
            ablated_records = [
                memory
                for memory in subjective_memory_records
                if str(memory.get("recordId") or "") != removed_record_id
            ]
            ablated_decision = runtime.motivation_engine.evaluate_npc(
                cycle_world,
                scenario.npc_id,
                delta_minutes=20.0,
                relationship_edges=relationship_edges,
                subjective_memory_records=ablated_records,
                heuristics=heuristics,
            )
            ablated_payload = _decision_payload(ablated_decision)
            selected_without_memory = str(ablated_payload.get("selectedToolId") or "")
            changed = bool(selected_with_memory) and bool(selected_without_memory) and (
                selected_with_memory != selected_without_memory
            )
            changed_count += 1 if changed else 0
            total_count += 1
            comparisons.append(
                {
                    "cycleIndex": cycle_index,
                    "npcId": scenario.npc_id,
                    "removedSubjectiveMemoryRecordId": removed_record_id,
                    "selectedWithMemory": selected_with_memory or None,
                    "selectedWithoutMemory": selected_without_memory or None,
                    "changed": changed,
                }
            )

    return {
        "cycleCount": cycle_count,
        "npcIdsConsidered": [scenario.npc_id],
        "removedSubjectiveMemoryRecordIds": [
            str(record.get("recordId") or "") for record in candidate_records if str(record.get("recordId") or "")
        ],
        "comparisonCount": total_count,
        "changedDecisionCount": changed_count,
        "changeRate": round(_safe_ratio(changed_count, total_count), 6),
        "comparisons": comparisons,
    }


def _counterfactual_cycle_world(world: dict[str, Any], cycle_index: int) -> dict[str, Any]:
    """复制 world 并推进 tick，保留原始运行证据不被 replay 污染。"""
    cycle_world = deepcopy(world)
    clock = dict(cycle_world.get("clock", {})) if isinstance(cycle_world.get("clock"), dict) else {}
    clock["tick"] = int(clock.get("tick", 0)) + max(0, int(cycle_index))
    cycle_world["clock"] = clock
    return cycle_world


def _decision_payload(decision: dict[str, Any]) -> dict[str, Any]:
    payload = decision.get("decision") if isinstance(decision, dict) else None
    return payload if isinstance(payload, dict) else {}


def _relationship_ref_matches_pair(ref: dict[str, Any], source_id: str, target_id: str) -> bool:
    ref_pair = {str(ref.get("sourceAgentId") or ""), str(ref.get("targetAgentId") or "")}
    if ref_pair == {source_id, target_id}:
        return True
    edge_id = str(ref.get("edgeId") or "")
    return source_id in edge_id.split("::") and target_id in edge_id.split("::")


def _relationship_ref_uses_sources(ref: dict[str, Any], relationship_source_ids: set[str]) -> bool:
    source_values = ref.get("sourceEventIds", [])
    if not isinstance(source_values, list):
        source_values = []
    source_event_ids = {str(source_id) for source_id in source_values if str(source_id)}
    return bool(source_event_ids & relationship_source_ids)


def _subjective_memory_ref_uses_sources(ref: dict[str, Any], subjective_memory_source_ids: set[str]) -> bool:
    source_event_id = str(ref.get("sourceEventId") or "")
    return bool(source_event_id and source_event_id in subjective_memory_source_ids)


def _heuristic_ref_uses_sources(ref: dict[str, Any], heuristic_source_ids: set[str]) -> bool:
    source_event_id = str(ref.get("sourceEventId") or "")
    return bool(source_event_id and source_event_id in heuristic_source_ids)


def _candidate_scores_changed(with_scores: list[Any], without_scores: list[Any]) -> bool:
    without_by_tool = {
        str(item.get("toolId") or ""): item
        for item in without_scores
        if isinstance(item, dict)
    }
    for item in with_scores:
        if not isinstance(item, dict):
            continue
        tool_id = str(item.get("toolId") or "")
        other = without_by_tool.get(tool_id, {})
        if round(float(item.get("score") or 0.0), 6) != round(float(other.get("score") or 0.0), 6):
            return True
        if round(float(item.get("subjectiveMemoryBonus") or 0.0), 6) != round(float(other.get("subjectiveMemoryBonus") or 0.0), 6):
            return True
        if round(float(item.get("heuristicBonus") or 0.0), 6) != round(float(other.get("heuristicBonus") or 0.0), 6):
            return True
    return False


def _candidate_field_changed(with_scores: list[Any], without_scores: list[Any], field: str) -> bool:
    """比较候选分数字段，给反事实 replay 提供单一信号的因果证据。"""
    without_by_tool = {
        str(item.get("toolId") or ""): item
        for item in without_scores
        if isinstance(item, dict)
    }
    for item in with_scores:
        if not isinstance(item, dict):
            continue
        tool_id = str(item.get("toolId") or "")
        other = without_by_tool.get(tool_id, {})
        if round(float(item.get(field) or 0.0), 6) != round(float(other.get(field) or 0.0), 6):
            return True
    return False


def _shortcut_events(relationship_items: list[dict[str, Any]]) -> int:
    if not relationship_items:
        return 0
    return sum(1 for edge in relationship_items if not edge.get("sourceEventIds"))


def _build_process_ablation_comparison(runs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    metric_ids = (
        "goal_success_rate",
        "required_process_coverage",
        "process_believability_score",
        "causal_trace_coverage",
        "relationship_memory_causal_use_rate",
        "counterfactual_tool_selection_change_rate",
        "shortcut_violation_rate",
    )
    comparison: dict[str, Any] = {
        "full_baseline": BASELINE_FULL,
        "comparison": {},
        "delta_vs_full": {},
    }
    full_metrics = _metric_index(runs[BASELINE_FULL]["metrics"])
    for baseline in PROCESS_BASELINES:
        metric_index = _metric_index(runs[baseline]["metrics"])
        comparison["comparison"][baseline] = {metric_id: _metric_triplet(metric_index[metric_id]) for metric_id in metric_ids}
        if baseline == BASELINE_FULL:
            continue
        comparison["delta_vs_full"][baseline] = {
            metric_id: round(float(metric_index[metric_id]["mean"]) - float(full_metrics[metric_id]["mean"]), 6)
            for metric_id in metric_ids
        }
    return comparison


def _metric_index(metrics: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(metric["metric"]): metric for metric in metrics}


def _safe_ratio(numerator: int | float, denominator: int | float) -> float:
    return float(numerator) / float(denominator) if float(denominator) else 0.0


def _export_process_eval(result: dict[str, Any], base_dir: Path) -> dict[str, Any]:
    created_at = _utc_timestamp()
    git_snapshot = _git_snapshot()
    run_dir = _unique_run_dir(base_dir / f"run_{_timestamp_slug(created_at)}")
    per_scenario_dir = run_dir / "per_scenario"
    per_scenario_dir.mkdir(parents=True, exist_ok=True)
    artifacts: list[dict[str, Any]] = []

    summary_path = run_dir / "summary.json"
    _write_json(summary_path, _summary_only(result))
    artifacts.append(_artifact_record(summary_path, run_dir, kind="summary_json"))

    comparison_path = run_dir / "ablation_comparison.json"
    _write_json(comparison_path, result["ablation_comparison"])
    artifacts.append(_artifact_record(comparison_path, run_dir, kind="ablation_comparison_json"))

    for baseline, run in result["baselines"].items():
        for item in run["items"]:
            scenario_id = item["scenario"]["scenarioId"]
            seed_suffix = _artifact_seed_suffix(item)
            scenario_path = per_scenario_dir / f"{scenario_id}_{baseline}{seed_suffix}.json"
            _write_json(scenario_path, item)
            artifacts.append(
                _artifact_record(
                    scenario_path,
                    run_dir,
                    kind="per_scenario_json",
                    scenario_id=scenario_id,
                    baseline=baseline,
                )
            )

    trace_specs = (
        (
            "intervention_trace.jsonl",
            "intervention_trace_jsonl",
            _baseline_items(result, BASELINE_HARD_DELEGATION),
            BASELINE_HARD_DELEGATION,
        ),
        (
            "goal_progress_trace.jsonl",
            "goal_progress_trace_jsonl",
            _baseline_items(result, BASELINE_FULL),
            BASELINE_FULL,
        ),
        (
            "counterfactual_replay.jsonl",
            "counterfactual_replay_jsonl",
            _counterfactual_replay_items(result, BASELINE_FULL),
            BASELINE_FULL,
        ),
        (
            "memory_ablation_trace.jsonl",
            "memory_ablation_trace_jsonl",
            _memory_ablation_trace_items(result),
            None,
        ),
    )
    for filename, kind, items, baseline in trace_specs:
        trace_path = run_dir / filename
        _write_jsonl(trace_path, items)
        artifacts.append(
            _artifact_record(trace_path, run_dir, kind=kind, row_count=len(items), baseline=baseline)
        )

    llm_evidence = result.get("llmEvidence", {}) if isinstance(result.get("llmEvidence"), dict) else {}
    if int(llm_evidence.get("recordCount") or 0):
        llm_evidence_path = run_dir / "llm_evidence.json"
        _write_json(llm_evidence_path, llm_evidence)
        artifacts.append(_artifact_record(llm_evidence_path, run_dir, kind="llm_evidence_json"))

    manifest_path = _write_eval_manifest(
        run_dir=run_dir,
        result=result,
        artifacts=artifacts,
        created_at=created_at,
        export_kind="process_fidelity_dataset",
        git_snapshot=git_snapshot,
    )
    return {
        "runDir": str(run_dir),
        "manifest": str(manifest_path),
        "artifactCount": len(artifacts) + 1,
    }


def _export_stability_eval(result: dict[str, Any], base_dir: Path) -> dict[str, Any]:
    created_at = _utc_timestamp()
    git_snapshot = _git_snapshot()
    run_dir = _unique_run_dir(base_dir / f"stability_{_timestamp_slug(created_at)}")
    run_dir.mkdir(parents=True, exist_ok=True)
    artifacts: list[dict[str, Any]] = []

    summary_path = run_dir / "summary.json"
    _write_json(summary_path, _summary_only(result))
    artifacts.append(_artifact_record(summary_path, run_dir, kind="summary_json"))

    trace_items = list(result.get("items", []))
    trace_path = run_dir / "stability_trace.jsonl"
    _write_jsonl(trace_path, trace_items)
    artifacts.append(
        _artifact_record(trace_path, run_dir, kind="stability_trace_jsonl", row_count=len(trace_items))
    )

    evidence = result.get("evidence", {}) if isinstance(result.get("evidence"), dict) else {}
    evidence_path = run_dir / "final_evidence.json"
    _write_json(evidence_path, evidence)
    artifacts.append(_artifact_record(evidence_path, run_dir, kind="final_evidence_json"))

    manifest_path = _write_eval_manifest(
        run_dir=run_dir,
        result=result,
        artifacts=artifacts,
        created_at=created_at,
        export_kind="stability_dataset",
        git_snapshot=git_snapshot,
    )
    return {
        "runDir": str(run_dir),
        "manifest": str(manifest_path),
        "artifactCount": len(artifacts) + 1,
    }


def _summary_only(result: dict[str, Any]) -> dict[str, Any]:
    summary = {
        "ok": result.get("ok"),
        "suite": result.get("suite"),
        "baseline": result.get("baseline"),
        "passed": result.get("passed"),
        "total": result.get("total"),
        "metrics": result.get("metrics"),
        "ablation_comparison": result.get("ablation_comparison"),
    }
    for key in (
        "providerMode",
        "seedCount",
        "llmEvidence",
        "hours",
        "ticksCompleted",
        "checks",
        "evidence",
        "domains",
        "robustnessChecksPass",
        "strictGate",
    ):
        if key in result:
            summary[key] = result.get(key)
    return summary


def _baseline_items(result: dict[str, Any], baseline: str) -> list[dict[str, Any]]:
    return list(result.get("baselines", {}).get(baseline, {}).get("items", []))


def _counterfactual_replay_items(result: dict[str, Any], baseline: str) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for item in _baseline_items(result, baseline):
        evidence = item.get("evidence", {}) if isinstance(item.get("evidence"), dict) else {}
        replay = evidence.get("counterfactualReplay")
        if isinstance(replay, dict):
            scenario = item.get("scenario", {}) if isinstance(item.get("scenario"), dict) else {}
            items.append(
                {
                    "scenarioId": scenario.get("scenarioId"),
                    "baseline": item.get("baseline"),
                    "seed": item.get("seed"),
                    "counterfactualReplay": replay,
                }
            )
    return items


def _memory_ablation_trace_items(result: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for baseline in (
        ABLATION_NO_SUBJECTIVE_MEMORY,
        ABLATION_NO_RELATIONSHIP_EDGE,
        ABLATION_SHUFFLED_MEMORY_OWNER,
        ABLATION_EVIDENCE_LINK_REMOVAL,
    ):
        for item in _baseline_items(result, baseline):
            scenario = item.get("scenario", {}) if isinstance(item.get("scenario"), dict) else {}
            evidence = item.get("evidence", {}) if isinstance(item.get("evidence"), dict) else {}
            replay = evidence.get("counterfactualReplay") if isinstance(evidence, dict) else {}
            items.append(
                {
                    "scenarioId": scenario.get("scenarioId"),
                    "baseline": baseline,
                    "seed": item.get("seed"),
                    "processChecks": item.get("processChecks", {}),
                    "metrics": item.get("metrics", {}),
                    "scenarioSetup": evidence.get("scenarioSetup", {}),
                    "runtimeAblation": evidence.get("runtimeAblation", {}),
                    "subjectiveMemoryAblation": evidence.get("subjectiveMemoryAblation", {}),
                    "relationshipAblation": evidence.get("relationshipAblation", {}),
                    "counterfactualEffect": replay.get("effect") if isinstance(replay, dict) else None,
                }
            )
    return items


def _artifact_seed_suffix(item: dict[str, Any]) -> str:
    """多 seed 导出时在文件名里追加 seed，避免同一 scenario/baseline 覆盖。"""
    seed = item.get("seed") if isinstance(item.get("seed"), dict) else {}
    seed_index = seed.get("seedIndex")
    if seed_index is None:
        return ""
    return f"_seed{int(seed_index):02d}"


def _write_eval_manifest(
    *,
    run_dir: Path,
    result: dict[str, Any],
    artifacts: list[dict[str, Any]],
    created_at: str,
    export_kind: str,
    git_snapshot: dict[str, Any] | None = None,
) -> Path:
    """写入 Eval 数据集 manifest，固定 run 元数据、schema 版本和 artifact 校验信息。"""
    manifest = {
        "manifestVersion": "phase2.eval_manifest.v1",
        "exportKind": export_kind,
        "createdAt": created_at,
        "suite": result.get("suite"),
        "baseline": result.get("baseline"),
        "providerMode": result.get("providerMode"),
        "seedCount": result.get("seedCount"),
        "ok": result.get("ok"),
        "runDirName": run_dir.name,
        "git": git_snapshot if git_snapshot is not None else _git_snapshot(),
        "schemaRegistry": schema_registry_snapshot(),
        "metricIds": _metric_ids(result.get("metrics")),
        "baselines": _baseline_names(result),
        "scenarioIds": _scenario_ids(result),
        "llmEvidence": result.get("llmEvidence", {}),
        "evalGates": _eval_gates(result),
        "artifacts": artifacts,
        "verification": {
            "summary": "每个 artifact 提供 bytes / sha256；JSONL artifact 额外提供 rowCount，便于后续复核导出完整性。",
            "localCommands": [
                "npm.cmd run eval:process",
                "npm.cmd run eval:process:export",
                "npm.cmd run eval:stability",
                "npm.cmd run eval:stability:export",
                "npm.cmd run eval:domain",
                "npm.cmd run eval:domain:export",
                "npm.cmd run eval:robustness",
                "npm.cmd run eval:robustness:export",
                "npm.cmd run eval:audit",
                "npm.cmd run eval:audit:export",
            ],
        },
    }
    manifest_path = run_dir / "manifest.json"
    _write_json(manifest_path, manifest)
    return manifest_path


def _artifact_record(
    path: Path,
    run_dir: Path,
    *,
    kind: str,
    row_count: int | None = None,
    baseline: str | None = None,
    scenario_id: str | None = None,
) -> dict[str, Any]:
    """生成稳定 artifact 索引；路径统一相对 run_dir，方便移动归档目录。"""
    record: dict[str, Any] = {
        "path": path.relative_to(run_dir).as_posix(),
        "kind": kind,
        "bytes": path.stat().st_size,
        "sha256": _sha256_file(path),
    }
    if row_count is not None:
        record["rowCount"] = row_count
    if baseline:
        record["baseline"] = baseline
    if scenario_id:
        record["scenarioId"] = scenario_id
    return record


def _unique_run_dir(path: Path) -> Path:
    """避免同一秒内连续导出互相覆盖。"""
    if not path.exists():
        return path
    for index in range(1, 100):
        candidate = path.with_name(f"{path.name}_{index:02d}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"无法创建唯一 Eval 导出目录：{path}")


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _timestamp_slug(timestamp: str) -> str:
    """把 ISO UTC 时间转为 Windows 友好的目录片段。"""
    return timestamp.replace("+00:00", "Z").replace(":", "-")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_snapshot() -> dict[str, Any]:
    """尽量记录当前 Git 状态；非 Git 环境下保持 manifest 可写。"""
    commit = _git_output("rev-parse", "HEAD")
    branch = _git_output("rev-parse", "--abbrev-ref", "HEAD")
    status = _git_output("status", "--short")
    return {
        "commit": commit,
        "shortCommit": commit[:7] if commit else None,
        "branch": branch,
        "dirty": bool(status),
        "statusShort": status.splitlines()[:20] if status else [],
    }


def _git_output(*args: str) -> str | None:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=Path.cwd(),
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError:
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def _metric_ids(metrics: Any) -> list[str]:
    if not isinstance(metrics, list):
        return []
    ids = [
        str(item.get("metric") or "")
        for item in metrics
        if isinstance(item, dict) and item.get("metric")
    ]
    return sorted(set(ids))


def _baseline_names(result: dict[str, Any]) -> list[str]:
    baselines = result.get("baselines")
    if isinstance(baselines, dict):
        return sorted(str(key) for key in baselines.keys())
    baseline = str(result.get("baseline") or "")
    return [baseline] if baseline else []


def _scenario_ids(result: dict[str, Any]) -> list[str]:
    ids: set[str] = set()
    baselines = result.get("baselines")
    if isinstance(baselines, dict):
        for run in baselines.values():
            if isinstance(run, dict):
                ids.update(_scenario_ids_from_items(run.get("items", [])))
    ids.update(_scenario_ids_from_items(result.get("items", [])))
    for section in ("process", "domain"):
        section_result = result.get(section, {}) if isinstance(result.get(section), dict) else {}
        ids.update(_scenario_ids_from_items(section_result.get("items", [])))
    return sorted(ids)


def _scenario_ids_from_items(items: Any) -> set[str]:
    ids: set[str] = set()
    if not isinstance(items, list):
        return ids
    for item in items:
        if not isinstance(item, dict):
            continue
        scenario = item.get("scenario", {}) if isinstance(item.get("scenario"), dict) else {}
        nested_scenario_id = str(scenario.get("scenarioId") or "")
        if nested_scenario_id:
            ids.add(nested_scenario_id)
        scenario_id = str(item.get("scenarioId") or "")
        if scenario_id:
            ids.add(scenario_id)
        if item.get("hourIndex") is not None:
            ids.add(f"hour_{int(item['hourIndex']):02d}")
    return ids


def _eval_gates(result: dict[str, Any]) -> dict[str, Any]:
    strict_gate = result.get("strictGate") if isinstance(result.get("strictGate"), dict) else None
    if strict_gate is None:
        return {}
    domain = result.get("domain", {}) if isinstance(result.get("domain"), dict) else {}
    process = result.get("process", {}) if isinstance(result.get("process"), dict) else {}
    return {
        "strictGate": {
            "gateVersion": strict_gate.get("gateVersion"),
            "pass": bool(strict_gate.get("pass")),
            "failedCheckCount": int(strict_gate.get("failedCheckCount") or 0),
            "failedCheckIds": [
                str(check.get("checkId") or "")
                for check in strict_gate.get("failedChecks", [])
                if isinstance(check, dict)
            ],
        },
        "signatureKinds": {
            "process": process.get("signatureKinds", []),
            "domain": domain.get("signatureKinds", []),
        },
        "domainGroups": domain.get("groups", []),
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, items: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in items), encoding="utf-8")
