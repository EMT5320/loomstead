from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class EvalScenario:
    scenario_id: str
    level: str
    description: str
    npc_id: str
    expected_need_ids: tuple[str, ...]
    expected_tool_prefixes: tuple[str, ...]
    status_overrides: dict[str, int] = field(default_factory=dict)
    location_id: str | None = None
    anchor_id: str | None = None
    today_goals: tuple[str, ...] | None = None
    active_focus: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenarioId": self.scenario_id,
            "level": self.level,
            "description": self.description,
            "npcId": self.npc_id,
            "expectedNeedIds": list(self.expected_need_ids),
            "expectedToolPrefixes": list(self.expected_tool_prefixes),
            "statusOverrides": dict(self.status_overrides),
            "locationId": self.location_id,
            "anchorId": self.anchor_id,
            "todayGoals": list(self.today_goals) if self.today_goals is not None else None,
            "activeFocus": dict(self.active_focus) if isinstance(self.active_focus, dict) else None,
        }


DEFAULT_L1_SCENARIOS = (
    EvalScenario(
        scenario_id="l1.energy_routes_to_rest",
        level="L1",
        description="低体力 NPC 应把 energy 识别为主要需求，并路由到 life.* 工具。",
        npc_id="kai",
        expected_need_ids=("energy",),
        expected_tool_prefixes=("life.",),
        status_overrides={"energy": 5, "money": 80, "social": 80},
        today_goals=(),
    ),
    EvalScenario(
        scenario_id="l1.money_routes_to_shop_at_plaza",
        level="L1",
        description="低金钱压力且位于广场的 NPC 应路由到 shop.* 工具。",
        npc_id="mira",
        expected_need_ids=("money_anxiety",),
        expected_tool_prefixes=("shop.",),
        status_overrides={"energy": 85, "money": 5, "social": 85},
        location_id="plaza",
        anchor_id="market_stall",
        today_goals=(),
    ),
    EvalScenario(
        scenario_id="l1.money_routes_to_farm_at_farm",
        level="L1",
        description="低金钱压力且位于农场的 NPC 应路由到 farm.* 工具。",
        npc_id="bram",
        expected_need_ids=("money_anxiety",),
        expected_tool_prefixes=("farm.",),
        status_overrides={"energy": 85, "money": 5, "social": 85},
        location_id="farm",
        anchor_id="farm_field",
        today_goals=(),
    ),
    EvalScenario(
        scenario_id="l1.low_social_routes_to_social",
        level="L1",
        description="低社交满足的 NPC 应把 affiliation 识别为主要需求，并路由到 social.* 工具。",
        npc_id="lena",
        expected_need_ids=("affiliation",),
        expected_tool_prefixes=("social.",),
        status_overrides={"energy": 90, "money": 90, "social": 5},
        location_id="plaza",
        anchor_id="plaza_fountain",
        today_goals=(),
    ),
    EvalScenario(
        scenario_id="l1.director_bias_routes_to_social",
        level="L1",
        description="Director 临时偏置命中目标 NPC 时，应把 affiliation 提升到可解释决策源。",
        npc_id="kai",
        expected_need_ids=("affiliation",),
        expected_tool_prefixes=("social.",),
        status_overrides={"energy": 95, "money": 95, "social": 50},
        location_id="plaza",
        anchor_id="plaza_fountain",
        today_goals=(),
        active_focus={"targetAgents": ["kai"], "brief": "验证 Director motivation_bias 是否进入决策。"},
    ),
)
