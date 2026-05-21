from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EvalScenario:
    scenario_id: str
    level: str
    description: str
    npc_id: str
    expected_need_ids: tuple[str, ...]
    expected_tool_prefixes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenarioId": self.scenario_id,
            "level": self.level,
            "description": self.description,
            "npcId": self.npc_id,
            "expectedNeedIds": list(self.expected_need_ids),
            "expectedToolPrefixes": list(self.expected_tool_prefixes),
        }


DEFAULT_L1_SCENARIOS = (
    EvalScenario(
        scenario_id="l1.energy_routes_to_rest",
        level="L1",
        description="低体力 NPC 应把 energy 识别为主要需求，并路由到 life.* 工具。",
        npc_id="kai",
        expected_need_ids=("energy",),
        expected_tool_prefixes=("life.",),
    ),
)
