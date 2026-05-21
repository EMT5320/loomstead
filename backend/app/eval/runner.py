from __future__ import annotations

from typing import Any

from app.eval.process_fidelity import metric_summary
from app.eval.scenarios import DEFAULT_L1_SCENARIOS, EvalScenario
from app.runtime.motivation_engine import MotivationEngine
from app.world.world_state import create_initial_world


BASELINE_FULL = "full_motivational_delegation"


def run_rule_scenarios(scenarios: tuple[EvalScenario, ...] = DEFAULT_L1_SCENARIOS) -> dict[str, Any]:
    results = []
    pass_values: list[float] = []
    for scenario in scenarios:
        world = create_initial_world()
        apply_scenario_setup(world, scenario)
        decision = MotivationEngine().evaluate_npc(world, scenario.npc_id)
        primary_need = decision.get("primaryNeed", {}).get("needId")
        selected_tool = decision.get("decision", {}).get("selectedToolId") or ""
        ok = primary_need in scenario.expected_need_ids and any(selected_tool.startswith(prefix) for prefix in scenario.expected_tool_prefixes)
        pass_values.append(1.0 if ok else 0.0)
        results.append(
            {
                "scenario": scenario.to_dict(),
                "ok": ok,
                "primaryNeed": primary_need,
                "selectedToolId": selected_tool,
                "decision": decision.get("decision"),
            }
        )
    passed = int(sum(pass_values))
    return {
        "ok": passed == len(scenarios),
        "baseline": BASELINE_FULL,
        "passed": passed,
        "total": len(scenarios),
        "metrics": [metric_summary("l1_rule_pass_rate", pass_values, baseline=BASELINE_FULL)],
        "items": results,
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
