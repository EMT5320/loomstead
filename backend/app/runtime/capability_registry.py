from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.runtime.decision_budget import DecisionBudgetStore
from app.runtime.schema_registry import require_schema_version
from app.tools import Precondition, ToolDefinition, ToolRegistry

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
    day: int
    phase: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "npcId": self.npc_id,
            "needId": self.need_id,
            "locationId": self.location_id,
            "anchorId": self.anchor_id,
            "inventoryCount": len(self.inventory),
            "relationshipIds": list(self.relationship_ids),
            "day": self.day,
            "phase": self.phase,
        }


@dataclass(frozen=True)
class CapabilityResolution:
    context: CapabilityContext | None
    allowed_tools: tuple[ToolDefinition, ...]
    filter_trace: tuple[dict[str, Any], ...]
    rejected_tools: tuple[dict[str, Any], ...]
    decision_budgets: tuple[dict[str, Any], ...] = ()

    def to_debug_dict(self) -> dict[str, Any]:
        return {
            "version": require_schema_version("capability_resolution"),
            "context": self.context.to_dict() if self.context else None,
            "layers": [dict(layer) for layer in self.filter_trace],
            "allowedToolIds": [tool.tool_id for tool in self.allowed_tools],
            "rejectedTools": [dict(item) for item in self.rejected_tools],
            "decisionBudgets": [dict(item) for item in self.decision_budgets],
        }


class CapabilityRegistry:
    def __init__(self, tool_registry: ToolRegistry | None = None, decision_budget: DecisionBudgetStore | None = None) -> None:
        self.tool_registry = tool_registry or ToolRegistry()
        self.decision_budget = decision_budget or DecisionBudgetStore()

    def resolve(self, world: dict[str, Any], npc_id: str, need_id: str) -> list[ToolDefinition]:
        return list(self.resolve_with_debug(world, npc_id, need_id).allowed_tools)

    def resolve_with_debug(self, world: dict[str, Any], npc_id: str, need_id: str) -> CapabilityResolution:
        context = self.build_context(world, npc_id, need_id)
        if context is None:
            return CapabilityResolution(
                context=None,
                allowed_tools=(),
                filter_trace=(
                    {
                        "layer": "agent_context",
                        "inputCount": 0,
                        "allowedCount": 0,
                        "rejectedCount": 1,
                        "decisions": [{"toolId": None, "allowed": False, "reason": "unknown_npc"}],
                    },
                ),
                rejected_tools=(),
            )
        all_tools = self.tool_registry.list_tools()
        active_tools = list(all_tools)
        rejected: list[dict[str, Any]] = []
        layers: list[dict[str, Any]] = []

        for layer_name, evaluator in (
            ("need_relevance", self._need_relevance_decision),
            ("preconditions", self._precondition_decision),
            ("npc_profile", self._npc_profile_decision),
            ("event_scope", self._event_scope_decision),
            ("decision_budget", self._decision_budget_decision),
        ):
            next_active: list[ToolDefinition] = []
            decisions: list[dict[str, Any]] = []
            for tool in active_tools:
                allowed, reason, metadata = evaluator(world, context, tool)
                item = {"toolId": tool.tool_id, "allowed": allowed, "reason": reason}
                if metadata:
                    item["metadata"] = metadata
                decisions.append(item)
                if allowed:
                    next_active.append(tool)
                else:
                    rejected.append({"toolId": tool.tool_id, "rejectedBy": layer_name, "reason": reason})
            layers.append(
                {
                    "layer": layer_name,
                    "inputCount": len(active_tools),
                    "allowedCount": len(next_active),
                    "rejectedCount": len(active_tools) - len(next_active),
                    "decisions": decisions,
                }
            )
            active_tools = next_active
        return CapabilityResolution(
            context=context,
            allowed_tools=tuple(active_tools),
            filter_trace=tuple(layers),
            rejected_tools=tuple(rejected),
            decision_budgets=tuple(
                self.decision_budget.snapshot_for_tool(world, context.npc_id, tool)
                for tool in active_tools
            ),
        )

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
            day=int(world.get("clock", {}).get("day", 1)) if isinstance(world.get("clock"), dict) else 1,
            phase=str(world.get("clock", {}).get("phase") or "morning") if isinstance(world.get("clock"), dict) else "morning",
        )

    def _need_relevance_decision(self, world: dict[str, Any], context: CapabilityContext, tool: ToolDefinition) -> tuple[bool, str, dict[str, Any]]:
        prefixes = NEED_TO_TOOL_PREFIXES.get(context.need_id, ("life.",))
        matched_prefix = next((prefix for prefix in prefixes if tool.tool_id.startswith(prefix)), None)
        if matched_prefix:
            return True, "matches_need_prefix", {"needId": context.need_id, "prefix": matched_prefix}
        return False, "need_mismatch", {"needId": context.need_id, "allowedPrefixes": list(prefixes)}

    def _precondition_decision(self, world: dict[str, Any], context: CapabilityContext, tool: ToolDefinition) -> tuple[bool, str, dict[str, Any]]:
        location_reason = self._location_precondition_reason(world, context, tool)
        if location_reason:
            return False, location_reason, {"locationId": context.location_id}
        for precondition in tool.preconditions:
            allowed, reason = self._evaluate_precondition(context, precondition)
            if not allowed:
                return False, reason, {"precondition": precondition.__dict__}
        if tool.tool_id.startswith("social.") and not context.relationship_ids:
            return False, "requires_relationship_target", {}
        if tool.tool_id == "strategic.spread_rumor" and not self._has_gossip_hook(world, context.npc_id):
            return False, "requires_gossip_hook", {}
        return True, "preconditions_met", {"locationId": context.location_id, "anchorId": context.anchor_id}

    def _npc_profile_decision(self, world: dict[str, Any], context: CapabilityContext, tool: ToolDefinition) -> tuple[bool, str, dict[str, Any]]:
        agent = world.get("agents", {}).get(context.npc_id)
        preferences = agent.get("deepCard", {}).get("capabilityPreferences", {}) if isinstance(agent, dict) and isinstance(agent.get("deepCard"), dict) else {}
        preference = self._preference_for_tool(preferences, tool.tool_id)
        if not preference:
            return True, "neutral_profile_default", {}
        if preference.get("blocked") is True or preference.get("enabled") is False:
            return False, "blocked_by_npc_profile", {"preference": dict(preference)}
        return True, "profile_preference_applied", {"preference": dict(preference)}

    def _event_scope_decision(self, world: dict[str, Any], context: CapabilityContext, tool: ToolDefinition) -> tuple[bool, str, dict[str, Any]]:
        active_focus = world.get("activeFocus") if isinstance(world.get("activeFocus"), dict) else {}
        blocked_ids = {str(item) for item in active_focus.get("blockedToolIds", []) if str(item)}
        blocked_prefixes = tuple(str(item) for item in active_focus.get("blockedToolPrefixes", []) if str(item))
        if tool.tool_id in blocked_ids or any(tool.tool_id.startswith(prefix) for prefix in blocked_prefixes):
            return False, "blocked_by_event_scope", {"activeFocus": self._event_scope_debug(active_focus)}
        allowed_ids = {str(item) for item in active_focus.get("allowedToolIds", []) if str(item)}
        allowed_prefixes = tuple(str(item) for item in active_focus.get("allowedToolPrefixes", []) if str(item))
        if allowed_ids or allowed_prefixes:
            allowed = tool.tool_id in allowed_ids or any(tool.tool_id.startswith(prefix) for prefix in allowed_prefixes)
            return allowed, "allowed_by_event_scope" if allowed else "outside_event_scope", {"activeFocus": self._event_scope_debug(active_focus)}
        return True, "no_event_scope_constraint", {}

    def _decision_budget_decision(self, world: dict[str, Any], context: CapabilityContext, tool: ToolDefinition) -> tuple[bool, str, dict[str, Any]]:
        budget = self.decision_budget.snapshot_for_tool(world, context.npc_id, tool)
        route = str(budget.get("route") or "rule")
        if route == "rule_fallback":
            return True, "llm_budget_exhausted_rule_fallback", budget
        if route == "llm":
            return True, "budget_available", budget
        return True, "no_llm_budget_required", budget

    def _location_precondition_reason(self, world: dict[str, Any], context: CapabilityContext, tool: ToolDefinition) -> str | None:
        location_id = context.location_id
        has_farm_context = location_id == "farm" or any(plot.get("locationId") == location_id for plot in world.get("farmPlots", {}).values())
        has_shop_context = location_id in {"plaza", "tavern"}
        has_cook_context = location_id in {"tavern", "farm"}
        has_craft_context = location_id in {"plaza", "farm"}
        if tool.tool_id.startswith("farm.") and not has_farm_context:
            return "requires_farm_context"
        if tool.tool_id.startswith("shop.") and not has_shop_context:
            return "requires_shop_context"
        if tool.tool_id.startswith("cook.") and not has_cook_context:
            return "requires_cook_context"
        if tool.tool_id.startswith("craft.") and not has_craft_context:
            return "requires_craft_context"
        return None

    def _evaluate_precondition(self, context: CapabilityContext, precondition: Precondition) -> tuple[bool, str]:
        if precondition.kind == "location":
            return context.location_id == str(precondition.expected), "location_precondition_failed"
        if precondition.kind == "anchor":
            return context.anchor_id == str(precondition.expected), "anchor_precondition_failed"
        return True, "precondition_kind_not_enforced"

    def _has_gossip_hook(self, world: dict[str, Any], npc_id: str) -> bool:
        agent = world.get("agents", {}).get(npc_id)
        hooks = agent.get("deepCard", {}).get("gossipHooks", []) if isinstance(agent, dict) and isinstance(agent.get("deepCard"), dict) else []
        return isinstance(hooks, list) and bool(hooks)

    def _preference_for_tool(self, preferences: Any, tool_id: str) -> dict[str, Any]:
        if not isinstance(preferences, dict):
            return {}
        exact = preferences.get(tool_id)
        if isinstance(exact, dict):
            return exact
        namespace = f"{tool_id.split('.', 1)[0]}.*" if "." in tool_id else ""
        wildcard = preferences.get(namespace) if namespace else None
        return dict(wildcard) if isinstance(wildcard, dict) else {}

    def _event_scope_debug(self, active_focus: dict[str, Any]) -> dict[str, Any]:
        return {
            "targetAgents": list(active_focus.get("targetAgents", [])) if isinstance(active_focus.get("targetAgents"), list) else [],
            "allowedToolIds": list(active_focus.get("allowedToolIds", [])) if isinstance(active_focus.get("allowedToolIds"), list) else [],
            "blockedToolIds": list(active_focus.get("blockedToolIds", [])) if isinstance(active_focus.get("blockedToolIds"), list) else [],
            "allowedToolPrefixes": list(active_focus.get("allowedToolPrefixes", [])) if isinstance(active_focus.get("allowedToolPrefixes"), list) else [],
            "blockedToolPrefixes": list(active_focus.get("blockedToolPrefixes", [])) if isinstance(active_focus.get("blockedToolPrefixes"), list) else [],
        }
