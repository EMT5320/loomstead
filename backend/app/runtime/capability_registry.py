from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.tools import ToolDefinition, ToolRegistry

NEED_TO_TOOL_PREFIXES = {
    "energy": ("life.rest",),
    "sleep_pressure": ("life.rest",),
    "hunger": ("life.eat_food", "cook."),
    "money_anxiety": ("shop.", "farm."),
    "affiliation": ("social.",),
    "recognition": ("social.", "shop.", "farm.", "craft.", "cook."),
    "goal_progress": ("farm.", "shop.", "social.", "craft.", "cook."),
}


@dataclass(frozen=True)
class CapabilityContext:
    npc_id: str
    need_id: str
    location_id: str
    anchor_id: str | None
    inventory: tuple[dict[str, Any], ...]
    relationship_ids: tuple[str, ...]


class CapabilityRegistry:
    def __init__(self, tool_registry: ToolRegistry | None = None) -> None:
        self.tool_registry = tool_registry or ToolRegistry()

    def resolve(self, world: dict[str, Any], npc_id: str, need_id: str) -> list[ToolDefinition]:
        agent = world.get("agents", {}).get(npc_id)
        if not isinstance(agent, dict):
            return []
        prefixes = NEED_TO_TOOL_PREFIXES.get(need_id, ("life.",))
        tools = [tool for tool in self.tool_registry.list_tools() if any(tool.tool_id.startswith(prefix) for prefix in prefixes)]
        return self._filter_by_context(world, agent, tools)

    def build_context(self, world: dict[str, Any], npc_id: str, need_id: str) -> CapabilityContext | None:
        agent = world.get("agents", {}).get(npc_id)
        if not isinstance(agent, dict):
            return None
        relation_ids = []
        for key in world.get("relations", {}):
            parts = str(key).split("::")
            if npc_id in parts:
                relation_ids.extend(part for part in parts if part != npc_id)
        return CapabilityContext(
            npc_id=npc_id,
            need_id=need_id,
            location_id=str(agent.get("locationId") or ""),
            anchor_id=str(agent.get("anchorId")) if agent.get("anchorId") else None,
            inventory=tuple(agent.get("inventory", []) if isinstance(agent.get("inventory"), list) else []),
            relationship_ids=tuple(sorted(set(relation_ids))),
        )

    def _filter_by_context(self, world: dict[str, Any], agent: dict[str, Any], tools: list[ToolDefinition]) -> list[ToolDefinition]:
        location_id = str(agent.get("locationId") or "")
        has_farm_context = location_id == "farm" or any(plot.get("locationId") == location_id for plot in world.get("farmPlots", {}).values())
        has_shop_context = location_id in {"plaza", "tavern"}
        has_cook_context = location_id in {"tavern", "farm"}
        has_craft_context = location_id in {"plaza", "farm"}
        filtered: list[ToolDefinition] = []
        for tool in tools:
            if tool.tool_id.startswith("farm.") and not has_farm_context:
                continue
            if tool.tool_id.startswith("shop.") and not has_shop_context:
                continue
            if tool.tool_id.startswith("cook.") and not has_cook_context:
                continue
            if tool.tool_id.startswith("craft.") and not has_craft_context:
                continue
            filtered.append(tool)
        return filtered
