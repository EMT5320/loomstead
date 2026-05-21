from __future__ import annotations

from app.tools.tool_schema import FailureMode, ToolDefinition, WorldEffect

DEFAULT_TOOLS: tuple[ToolDefinition, ...] = (
    ToolDefinition(
        tool_id="life.move_to",
        tier="physiological",
        input_schema={"type": "object", "required": ["anchorId"], "properties": {"anchorId": {"type": "string"}}},
        duration_seconds=180.0,
        interruptible=True,
        interrupt_priority_threshold=0.9,
        world_effects=(WorldEffect(kind="presence", target="npc.anchor"),),
        event_emissions=("tool.life.move_to.completed",),
        observer_visibility="all_in_location",
    ),
    ToolDefinition(
        tool_id="life.rest",
        tier="physiological",
        input_schema={"type": "object", "properties": {}},
        duration_seconds=900.0,
        interruptible=True,
        interrupt_priority_threshold=0.95,
        world_effects=(WorldEffect(kind="status", target="npc.energy", delta={"energy": 18, "stress": -8}),),
        event_emissions=("tool.life.rest.completed",),
        observer_visibility="private",
    ),
    ToolDefinition(
        tool_id="farm.water_crop",
        tier="vocational",
        input_schema={"type": "object", "required": ["farmPlotId"], "properties": {"farmPlotId": {"type": "string"}}},
        duration_seconds=420.0,
        interruptible=True,
        world_effects=(WorldEffect(kind="farm", target="farmPlot.stage", delta={"stage": "watered"}),),
        event_emissions=("tool.farm.water_crop.completed",),
        observer_visibility="all_in_location",
    ),
    ToolDefinition(
        tool_id="shop.open_shop",
        tier="vocational",
        input_schema={"type": "object", "properties": {}},
        duration_seconds=1200.0,
        interruptible=True,
        world_effects=(WorldEffect(kind="town_stat", target="economy", delta={"economy": 1}),),
        event_emissions=("tool.shop.open_shop.completed",),
        observer_visibility="all_in_location",
    ),
    ToolDefinition(
        tool_id="social.chat_with",
        tier="social_strategic",
        input_schema={"type": "object", "required": ["targetNpcId"], "properties": {"targetNpcId": {"type": "string"}}},
        duration_seconds=360.0,
        interruptible=True,
        world_effects=(WorldEffect(kind="relation", target="npc_pair", delta={"affection": 2, "trust": 1}),),
        event_emissions=("tool.social.chat_with.completed", "dialogue"),
        observer_visibility="participants_only",
        llm_eligible=True,
        failure_modes=(FailureMode(code="target_unavailable", reason="目标 NPC 当前不可见。", emotional_charge=0.4),),
    ),
    ToolDefinition(
        tool_id="strategic.spread_rumor",
        tier="social_strategic",
        input_schema={"type": "object", "required": ["hookId"], "properties": {"hookId": {"type": "string"}}},
        duration_seconds=600.0,
        interruptible=True,
        interrupt_priority_threshold=0.7,
        event_emissions=("tool.strategic.spread_rumor.completed", "gossip.propagation_validated"),
        observer_visibility="participants_only",
        llm_eligible=True,
        failure_modes=(FailureMode(code="forbidden_state_fields", reason="谣言不能直接修改权威世界状态。", emotional_charge=0.7),),
    ),
)


class ToolRegistry:
    def __init__(self, tools: tuple[ToolDefinition, ...] = DEFAULT_TOOLS) -> None:
        self._tools = {tool.tool_id: tool for tool in tools}

    def list_tools(self) -> list[ToolDefinition]:
        return list(self._tools.values())

    def get(self, tool_id: str) -> ToolDefinition | None:
        return self._tools.get(tool_id)

    def by_namespace(self, namespace: str) -> list[ToolDefinition]:
        prefix = f"{namespace}."
        return [tool for tool in self._tools.values() if tool.tool_id.startswith(prefix)]

    def to_debug_payload(self) -> dict[str, object]:
        tools = [tool.to_dict() for tool in self.list_tools()]
        return {
            "count": len(tools),
            "tiers": sorted({tool["tier"] for tool in tools}),
            "items": tools,
        }
