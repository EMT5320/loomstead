from __future__ import annotations

from typing import Any

from app.eval.scenarios import DEFAULT_L1_SCENARIOS, EvalScenario
from app.runtime.motivation_engine import MotivationEngine
from app.world.world_state import create_initial_world


def run_rule_scenarios(scenarios: tuple[EvalScenario, ...] = DEFAULT_L1_SCENARIOS) -> dict[str, Any]:
    results = []
    passed = 0
    for scenario in scenarios:
        world = create_initial_world()
        if scenario.scenario_id == "l1.energy_routes_to_rest":
            world["agents"][scenario.npc_id]["status"]["energy"] = 5
            world["agents"][scenario.npc_id]["status"]["money"] = 80
            world["agents"][scenario.npc_id]["status"]["social"] = 80
        decision = MotivationEngine().evaluate_npc(world, scenario.npc_id)
        primary_need = decision.get("primaryNeed", {}).get("needId")
        selected_tool = decision.get("decision", {}).get("selectedToolId") or ""
        ok = primary_need in scenario.expected_need_ids and any(selected_tool.startswith(prefix) for prefix in scenario.expected_tool_prefixes)
        passed += int(ok)
        results.append(
            {
                "scenario": scenario.to_dict(),
                "ok": ok,
                "primaryNeed": primary_need,
                "selectedToolId": selected_tool,
                "decision": decision.get("decision"),
            }
        )
    return {"ok": passed == len(scenarios), "passed": passed, "total": len(scenarios), "items": results}
