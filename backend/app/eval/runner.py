from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.eval.process_fidelity import build_process_metrics, metric_summary, process_metric_summaries
from app.eval.scenarios import DEFAULT_L1_SCENARIOS, DEFAULT_PROCESS_GOALS, EvalScenario, ProcessGoalSpec
from app.runtime.agent_runtime import AgentRuntime
from app.runtime.motivation_engine import MotivationEngine
from app.world.world_state import create_initial_world


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
STABILITY_TRACE_TYPES = {"motivation.decision_made", "tool.execution_completed", "tool.execution_failed", "memory.result_observed"}


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
) -> dict[str, Any]:
    """运行 Phase 2 Process Fidelity 规则级评估。"""
    runs = {
        BASELINE_FULL: _run_process_baseline(scenarios, baseline=BASELINE_FULL),
        BASELINE_HARD_DELEGATION: _run_process_baseline(scenarios, baseline=BASELINE_HARD_DELEGATION),
        ABLATION_NO_SUBJECTIVE_MEMORY: _run_process_baseline(scenarios, baseline=ABLATION_NO_SUBJECTIVE_MEMORY),
        ABLATION_NO_RELATIONSHIP_EDGE: _run_process_baseline(scenarios, baseline=ABLATION_NO_RELATIONSHIP_EDGE),
        ABLATION_SHUFFLED_MEMORY_OWNER: _run_process_baseline(scenarios, baseline=ABLATION_SHUFFLED_MEMORY_OWNER),
        ABLATION_EVIDENCE_LINK_REMOVAL: _run_process_baseline(scenarios, baseline=ABLATION_EVIDENCE_LINK_REMOVAL),
    }
    comparison = _build_process_ablation_comparison(runs)
    metrics = [metric for baseline in PROCESS_BASELINES for metric in runs[baseline]["metrics"]]
    result = {
        "ok": bool(runs[BASELINE_FULL]["ok"]),
        "suite": "process_fidelity",
        "baseline": BASELINE_FULL,
        "passed": runs[BASELINE_FULL]["passed"],
        "total": len(scenarios),
        "metrics": metrics,
        "baselines": runs,
        "ablation_comparison": comparison,
    }
    if export_dir is not None:
        result["export"] = _export_process_eval(result, Path(export_dir))
    return result


def run_stability_scenarios(
    *,
    hours: int = DEFAULT_STABILITY_HOURS,
    export_dir: str | Path | None = None,
) -> dict[str, Any]:
    """连续推进规则版 AgentRuntime，用 24 游戏小时验证 tick 主路径稳定性。"""
    hours = max(1, int(hours))
    runtime = AgentRuntime(provider_mode="rule")
    initial_clock = dict(runtime.world.get("clock", {}))
    tick_items: list[dict[str, Any]] = []
    tick_success_values: list[float] = []
    event_type_counts: Counter[str] = Counter()
    trace_event_count = 0
    trace_schema_ok_count = 0
    completed_tool_count = 0
    failed_tool_count = 0
    memory_observation_count = 0
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
                    if payload.get("traceSchemaVersion") == "phase2.trace.v1":
                        trace_schema_ok_count += 1
                if event_type == "tool.execution_completed":
                    completed_tool_count += 1
                elif event_type == "tool.execution_failed":
                    failed_tool_count += 1
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
    trace_schema_coverage = _safe_ratio(trace_schema_ok_count, trace_event_count)
    memory_observation_ratio = _safe_ratio(memory_observation_count, completed_tool_count)
    checks = {
        "tick_successful": sum(tick_success_values) == float(hours),
        "clock_reached_expected_tick": int(runtime.world.get("clock", {}).get("tick", 0)) >= hours,
        "no_tool_failures": failed_tool_count == 0,
        "trace_schema_complete": trace_event_count > 0 and trace_schema_coverage >= 1.0,
        "memory_observations_follow_tools": completed_tool_count > 0 and memory_observation_count >= completed_tool_count,
        "relationship_edges_created": relationship_edge_count > 0,
        "multi_agent_participation": len(active_agent_ids) >= 4,
    }
    metrics = [
        metric_summary("stability_tick_success_rate", tick_success_values, baseline=BASELINE_STABILITY_24H),
        metric_summary("trace_schema_coverage", [trace_schema_coverage], baseline=BASELINE_STABILITY_24H),
        metric_summary("memory_observation_per_completed_tool", [memory_observation_ratio], baseline=BASELINE_STABILITY_24H),
        metric_summary("tool_failure_rate", [_safe_ratio(failed_tool_count, max(1, completed_tool_count + failed_tool_count))], baseline=BASELINE_STABILITY_24H),
        metric_summary("active_agent_count", [float(len(active_agent_ids))], baseline=BASELINE_STABILITY_24H),
        metric_summary("relationship_edge_count", [float(relationship_edge_count)], baseline=BASELINE_STABILITY_24H),
    ]
    result = {
        "ok": all(checks.values()),
        "suite": "stability_24h",
        "baseline": BASELINE_STABILITY_24H,
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
            "memoryObservationCount": memory_observation_count,
            "subjectiveMemoryCount": subjective_memory_count,
            "relationshipEdgeCount": relationship_edge_count,
            "heuristicCount": heuristic_count,
            "activeAgentIds": sorted(active_agent_ids),
            "retainedEventStoreCount": len(runtime.event_store.list()),
        },
        "items": tick_items,
    }
    if export_dir is not None:
        result["export"] = _export_stability_eval(result, Path(export_dir))
    return result


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
    for npc_id in (scenario.npc_id, scenario.target_npc_id):
        agent = world["agents"][npc_id]
        agent["locationId"] = scenario.location_id
        agent["anchorId"] = scenario.anchor_id
    agent = world["agents"][scenario.npc_id]
    for field, value in scenario.status_overrides.items():
        agent["status"][field] = value
    world["activeFocus"] = {
        "targetAgents": [scenario.npc_id],
        "brief": f"Process Fidelity Eval: {scenario.scenario_id}",
    }


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


def _run_process_baseline(scenarios: tuple[ProcessGoalSpec, ...], *, baseline: str) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for scenario in scenarios:
        if baseline == BASELINE_HARD_DELEGATION:
            item = _run_hard_delegation_process_scenario(scenario)
        else:
            item = _run_runtime_process_scenario(
                scenario,
                baseline=baseline,
                subjective_memory_ablation=_subjective_memory_ablation_for_baseline(baseline),
                relationship_ablation=_relationship_ablation_for_baseline(baseline),
            )
        items.append(item)
    metrics = process_metric_summaries(items, baseline=baseline)
    passed = sum(1 for item in items if item.get("ok"))
    return {
        "ok": passed == len(scenarios),
        "passed": passed,
        "total": len(scenarios),
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


def _run_runtime_process_scenario(
    scenario: ProcessGoalSpec,
    *,
    baseline: str,
    subjective_memory_ablation: str = SUBJECTIVE_MEMORY_ABLATION_NONE,
    relationship_ablation: str = RELATIONSHIP_ABLATION_NONE,
) -> dict[str, Any]:
    runtime = AgentRuntime(provider_mode="rule")
    apply_process_goal_setup(runtime.world, scenario)
    runtime.tick(float(scenario.max_game_hours) * 3600.0, speed=1.0)
    snapshot = runtime.get_phase2_debug_snapshot({"agentId": scenario.npc_id, "limit": 50})
    recent_trace_events = snapshot.get("recentTraceEvents", []) if isinstance(snapshot.get("recentTraceEvents"), list) else []
    subjective_items = _debug_items(snapshot.get("subjectiveMemory", {}))
    ablated_subjective_memory = _apply_subjective_memory_ablation(
        mode=subjective_memory_ablation,
        subjective_items=subjective_items,
    )
    subjective_items = ablated_subjective_memory["subjectiveItems"]
    relationship_items = _debug_items(snapshot.get("relationshipEdges", {}))
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
    )
    decision_without_relationship_memory = runtime.motivation_engine.evaluate_npc(
        runtime.world,
        scenario.npc_id,
        delta_minutes=20.0,
        relationship_edges=[],
        subjective_memory_records=[],
    )
    counterfactual_replay = _build_counterfactual_replay(
        scenario=scenario,
        decision_with_relationship_memory=decision_with_relationship_memory,
        decision_without_relationship_memory=decision_without_relationship_memory,
        relationship_source_ids=relationship_source_ids,
        subjective_memory_source_ids=memory_source_ids,
    )
    process_checks = {
        "goal_relevant_tool_event": bool(goal_tool_events),
        "subjective_memory_refs": bool(goal_event_ids & memory_source_ids),
        "relationship_edge_trace": bool(goal_event_ids & relationship_source_ids),
        "causal_trace": bool(memory_trace_links),
        "future_behavior_reference": bool(counterfactual_replay["effect"]),
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
            "memoryTraceLinks": memory_trace_links,
            "counterfactualReplay": counterfactual_replay,
            "subjectiveMemoryAblation": ablated_subjective_memory["evidence"],
            "relationshipAblation": ablated_relationships["evidence"],
            "traceSchemaVersion": snapshot.get("traceSchemaVersion"),
        },
    }


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
    decision_without_relationship_memory: dict[str, Any],
    relationship_source_ids: set[str],
    subjective_memory_source_ids: set[str],
) -> dict[str, Any]:
    with_decision = _decision_payload(decision_with_relationship_memory)
    without_decision = _decision_payload(decision_without_relationship_memory)
    selected_with = str(with_decision.get("selectedToolId") or "")
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
    score_effect = _candidate_scores_changed(
        list(with_decision.get("candidateScores", [])),
        list(without_decision.get("candidateScores", [])),
    )
    decision_effect = bool(selected_with) and bool(selected_without) and (selected_with != selected_without or score_effect)
    relationship_effect = bool(relevant_refs) and decision_effect
    subjective_memory_effect = bool(relevant_subjective_memory_refs) and decision_effect
    return {
        "selectedWithRelationshipMemory": selected_with or None,
        "selectedWithoutRelationshipMemory": selected_without or None,
        "effect": relationship_effect or subjective_memory_effect,
        "relationshipEffect": relationship_effect,
        "subjectiveMemoryEffect": subjective_memory_effect,
        "relationshipEdgeRefs": relationship_refs,
        "relevantRelationshipEdgeRefs": relevant_refs,
        "subjectiveMemoryRefs": subjective_memory_refs,
        "relevantSubjectiveMemoryRefs": relevant_subjective_memory_refs,
        "candidateScoresWithRelationshipMemory": list(with_decision.get("candidateScores", [])),
        "candidateScoresWithoutRelationshipMemory": list(without_decision.get("candidateScores", [])),
        "reasonWithRelationshipMemory": with_decision.get("reason"),
        "reasonWithoutRelationshipMemory": without_decision.get("reason"),
    }


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
    run_dir = base_dir / f"run_{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H-%M-%SZ')}"
    per_scenario_dir = run_dir / "per_scenario"
    per_scenario_dir.mkdir(parents=True, exist_ok=True)
    _write_json(run_dir / "summary.json", _summary_only(result))
    _write_json(run_dir / "ablation_comparison.json", result["ablation_comparison"])
    for baseline, run in result["baselines"].items():
        for item in run["items"]:
            scenario_id = item["scenario"]["scenarioId"]
            _write_json(per_scenario_dir / f"{scenario_id}_{baseline}.json", item)
    _write_jsonl(run_dir / "intervention_trace.jsonl", _baseline_items(result, BASELINE_HARD_DELEGATION))
    _write_jsonl(run_dir / "goal_progress_trace.jsonl", _baseline_items(result, BASELINE_FULL))
    _write_jsonl(run_dir / "counterfactual_replay.jsonl", _counterfactual_replay_items(result, BASELINE_FULL))
    _write_jsonl(run_dir / "memory_ablation_trace.jsonl", _memory_ablation_trace_items(result))
    return {"runDir": str(run_dir)}


def _export_stability_eval(result: dict[str, Any], base_dir: Path) -> dict[str, Any]:
    run_dir = base_dir / f"stability_{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H-%M-%SZ')}"
    run_dir.mkdir(parents=True, exist_ok=True)
    _write_json(run_dir / "summary.json", _summary_only(result))
    _write_jsonl(run_dir / "stability_trace.jsonl", list(result.get("items", [])))
    evidence = result.get("evidence", {}) if isinstance(result.get("evidence"), dict) else {}
    _write_json(run_dir / "final_evidence.json", evidence)
    return {"runDir": str(run_dir)}


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
    for key in ("hours", "ticksCompleted", "checks", "evidence"):
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
                    "processChecks": item.get("processChecks", {}),
                    "metrics": item.get("metrics", {}),
                    "subjectiveMemoryAblation": evidence.get("subjectiveMemoryAblation", {}),
                    "relationshipAblation": evidence.get("relationshipAblation", {}),
                    "counterfactualEffect": replay.get("effect") if isinstance(replay, dict) else None,
                }
            )
    return items


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_jsonl(path: Path, items: list[dict[str, Any]]) -> None:
    path.write_text("".join(json.dumps(item, ensure_ascii=False) + "\n" for item in items), encoding="utf-8")
