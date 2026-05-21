from __future__ import annotations

from typing import Any

from app.eval.process_fidelity import metric_summary
from app.eval.scenarios import DEFAULT_L1_SCENARIOS, EvalScenario
from app.runtime.motivation_engine import MotivationEngine
from app.world.world_state import create_initial_world


BASELINE_FULL = "full_motivational_delegation"
BASELINE_HARD_DELEGATION = "hard_delegation"
ABLATION_NO_RELATIONSHIP_EDGE = "no_relationship_edge"


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
