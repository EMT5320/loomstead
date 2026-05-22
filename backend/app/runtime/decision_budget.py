from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.tools.tool_schema import ToolDefinition

DEFAULT_DAILY_DECISION_LIMITS = {
    "social_strategic_layer": 8,
    "vocational_local_llm": 6,
    "heuristic_extraction": 2,
}


@dataclass(frozen=True)
class DecisionBudgetSnapshot:
    """单个工具在当前 NPC 决策预算下的路由结果。"""

    tool_id: str
    channel: str | None
    route: str
    reason: str
    limit: int
    consumed: int
    remaining: int
    cost: int
    llm_eligible: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": "decision_budget.v1",
            "toolId": self.tool_id,
            "channel": self.channel,
            "route": self.route,
            "reason": self.reason,
            "limit": self.limit,
            "consumed": self.consumed,
            "remaining": self.remaining,
            "cost": self.cost,
            "llmEligible": self.llm_eligible,
        }


class DecisionBudgetStore:
    """维护 Phase 2 的 NPC 决策预算，先覆盖 LLM eligible 工具路由。"""

    def __init__(self, daily_limits: dict[str, int] | None = None) -> None:
        self.daily_limits = dict(daily_limits or DEFAULT_DAILY_DECISION_LIMITS)

    def snapshot_for_tool(self, world: dict[str, Any], npc_id: str, tool: ToolDefinition) -> dict[str, Any]:
        channel = self.channel_for_tool(tool)
        if not channel:
            return DecisionBudgetSnapshot(
                tool_id=tool.tool_id,
                channel=None,
                route="rule",
                reason="no_llm_budget_required",
                limit=0,
                consumed=0,
                remaining=0,
                cost=0,
                llm_eligible=bool(tool.llm_eligible),
            ).to_dict()

        agent_budget = self._agent_budget(world, npc_id)
        limit = int(agent_budget.get("limits", {}).get(channel, self.daily_limits.get(channel, 0)))
        consumed = int(agent_budget.get("consumed", {}).get(channel, 0))
        cost = 1
        remaining = max(0, limit - consumed)
        if remaining >= cost:
            route = "llm"
            reason = "budget_available"
        else:
            route = "rule_fallback"
            reason = "llm_budget_exhausted_rule_fallback"
        return DecisionBudgetSnapshot(
            tool_id=tool.tool_id,
            channel=channel,
            route=route,
            reason=reason,
            limit=limit,
            consumed=consumed,
            remaining=remaining,
            cost=cost,
            llm_eligible=bool(tool.llm_eligible),
        ).to_dict()

    def consume_for_tool(self, world: dict[str, Any], npc_id: str, tool: ToolDefinition) -> dict[str, Any] | None:
        snapshot = self.snapshot_for_tool(world, npc_id, tool)
        channel = snapshot.get("channel")
        if not channel:
            return None
        if str(snapshot.get("route") or "") == "rule_fallback":
            return {**snapshot, "eventType": "budget.decision_fallback"}
        agent_budget = self._agent_budget(world, npc_id)
        consumed = agent_budget.setdefault("consumed", {})
        consumed[channel] = int(consumed.get(channel, 0)) + int(snapshot.get("cost") or 1)
        updated = self.snapshot_for_tool(world, npc_id, tool)
        return {
            **updated,
            "eventType": "budget.decision_consumed",
            "consumedDelta": int(snapshot.get("cost") or 1),
            "remainingBefore": int(snapshot.get("remaining") or 0),
        }

    def exhaust(self, world: dict[str, Any], npc_id: str, channel: str) -> dict[str, Any]:
        """测试和调试用：把指定 NPC 的某个预算通道打满。"""
        agent_budget = self._agent_budget(world, npc_id)
        limit = int(agent_budget.get("limits", {}).get(channel, self.daily_limits.get(channel, 0)))
        agent_budget.setdefault("consumed", {})[channel] = limit
        return self.debug_snapshot(world, npc_ids=[npc_id])

    def debug_snapshot(self, world: dict[str, Any], npc_ids: list[str] | None = None) -> dict[str, Any]:
        root = self._root(world)
        agents = root.get("agents", {}) if isinstance(root.get("agents"), dict) else {}
        selected_ids = npc_ids or sorted(str(agent_id) for agent_id in agents.keys())
        items = []
        for npc_id in selected_ids:
            budget = self._agent_budget(world, str(npc_id))
            items.append(
                {
                    "npcId": str(npc_id),
                    "day": root.get("day"),
                    "limits": dict(budget.get("limits", {})),
                    "consumed": dict(budget.get("consumed", {})),
                    "remaining": {
                        channel: max(0, int(limit) - int(budget.get("consumed", {}).get(channel, 0)))
                        for channel, limit in budget.get("limits", {}).items()
                    },
                }
            )
        return {"version": "decision_budget.v1", "day": root.get("day"), "items": items}

    def channel_for_tool(self, tool: ToolDefinition) -> str | None:
        if not tool.llm_eligible:
            return None
        if tool.tier == "social_strategic":
            return "social_strategic_layer"
        if tool.tier == "vocational":
            return "vocational_local_llm"
        return None

    def _root(self, world: dict[str, Any]) -> dict[str, Any]:
        day = int(world.get("clock", {}).get("day", 1)) if isinstance(world.get("clock"), dict) else 1
        root = world.setdefault("decisionBudgets", {"version": "decision_budget.v1", "day": day, "agents": {}})
        if not isinstance(root, dict):
            root = {"version": "decision_budget.v1", "day": day, "agents": {}}
            world["decisionBudgets"] = root
        if int(root.get("day", day)) != day:
            root.clear()
            root.update({"version": "decision_budget.v1", "day": day, "agents": {}})
        root.setdefault("version", "decision_budget.v1")
        root.setdefault("day", day)
        root.setdefault("agents", {})
        return root

    def _agent_budget(self, world: dict[str, Any], npc_id: str) -> dict[str, Any]:
        root = self._root(world)
        agents = root.setdefault("agents", {})
        budget = agents.setdefault(npc_id, {"limits": dict(self.daily_limits), "consumed": {}})
        if not isinstance(budget, dict):
            budget = {"limits": dict(self.daily_limits), "consumed": {}}
            agents[npc_id] = budget
        budget.setdefault("limits", dict(self.daily_limits))
        budget.setdefault("consumed", {})
        return budget
