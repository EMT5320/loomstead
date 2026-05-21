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


@dataclass(frozen=True)
class ProcessGoalSpec:
    scenario_id: str
    description: str
    npc_id: str
    target_npc_id: str
    expected_tool_prefixes: tuple[str, ...]
    required_process_ids: tuple[str, ...]
    status_overrides: dict[str, int] = field(default_factory=dict)
    location_id: str = "plaza"
    anchor_id: str = "plaza_fountain"
    max_game_hours: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenarioId": self.scenario_id,
            "description": self.description,
            "npcId": self.npc_id,
            "targetNpcId": self.target_npc_id,
            "expectedToolPrefixes": list(self.expected_tool_prefixes),
            "requiredProcessIds": list(self.required_process_ids),
            "statusOverrides": dict(self.status_overrides),
            "locationId": self.location_id,
            "anchorId": self.anchor_id,
            "maxGameHours": self.max_game_hours,
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


DEFAULT_REQUIRED_PROCESS_IDS = (
    "goal_relevant_tool_event",
    "subjective_memory_refs",
    "relationship_edge_trace",
    "causal_trace",
    "future_behavior_reference",
)


DEFAULT_PROCESS_GOALS = (
    ProcessGoalSpec(
        scenario_id="pf.shared_chat_builds_traceable_trust",
        description="Mira 通过一次自主社交与 Tomas 产生可追踪的信任边。",
        npc_id="mira",
        target_npc_id="tomas",
        expected_tool_prefixes=("social.",),
        required_process_ids=DEFAULT_REQUIRED_PROCESS_IDS,
        status_overrides={"energy": 90, "money": 90, "social": 5},
    ),
    ProcessGoalSpec(
        scenario_id="pf.repair_talk_requires_memory_trace",
        description="Tomas 的修复式交谈必须产生主观记忆和带 source_event_ids 的关系边。",
        npc_id="tomas",
        target_npc_id="mira",
        expected_tool_prefixes=("social.",),
        required_process_ids=DEFAULT_REQUIRED_PROCESS_IDS,
        status_overrides={"energy": 90, "money": 90, "social": 5},
    ),
    ProcessGoalSpec(
        scenario_id="pf.affiliation_bias_remains_agent_initiated",
        description="Lena 在 affiliation 偏置下仍由 Arbitration 选择社交工具，并保留 trace。",
        npc_id="lena",
        target_npc_id="mira",
        expected_tool_prefixes=("social.",),
        required_process_ids=DEFAULT_REQUIRED_PROCESS_IDS,
        status_overrides={"energy": 90, "money": 90, "social": 5},
    ),
)
