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

DEFAULT_DAILY_FEATURE_LIMITS = {
    "dialogue": 4,
    "gift_exchange": 4,
    "gossip_propagation": 3,
    "vocational_action": 6,
    "heuristic_extraction": 2,
}

DEFAULT_TOOL_COSTS = {
    "social.chat_with": {
        "feature": "dialogue",
        "channel": "social_strategic_layer",
        "cost": 2,
        "estimatedPromptTokens": 900,
        "estimatedCompletionTokens": 220,
    },
    "social.give_gift": {
        "feature": "gift_exchange",
        "channel": "social_strategic_layer",
        "cost": 2,
        "estimatedPromptTokens": 780,
        "estimatedCompletionTokens": 180,
    },
    "strategic.spread_rumor": {
        "feature": "gossip_propagation",
        "channel": "social_strategic_layer",
        "cost": 3,
        "estimatedPromptTokens": 1200,
        "estimatedCompletionTokens": 260,
    },
}


@dataclass(frozen=True)
class DecisionBudgetSnapshot:
    """单个工具在当前 NPC 决策预算下的路由结果。"""

    tool_id: str
    channel: str | None
    feature: str | None
    route: str
    reason: str
    limit: int
    consumed: int
    remaining: int
    feature_limit: int
    feature_consumed: int
    feature_remaining: int
    cost: int
    unit: str
    cost_breakdown: dict[str, Any]
    llm_eligible: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": "decision_budget.v1",
            "toolId": self.tool_id,
            "channel": self.channel,
            "feature": self.feature,
            "route": self.route,
            "reason": self.reason,
            "limit": self.limit,
            "consumed": self.consumed,
            "remaining": self.remaining,
            "featureLimit": self.feature_limit,
            "featureConsumed": self.feature_consumed,
            "featureRemaining": self.feature_remaining,
            "cost": self.cost,
            "unit": self.unit,
            "costBreakdown": dict(self.cost_breakdown),
            "llmEligible": self.llm_eligible,
        }


class DecisionBudgetStore:
    """维护 Phase 2 的 NPC 决策预算，覆盖 NPC、feature 与工具级 LLM 路由。"""

    def __init__(
        self,
        daily_limits: dict[str, int] | None = None,
        feature_limits: dict[str, int] | None = None,
        tool_costs: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        self.daily_limits = dict(daily_limits or DEFAULT_DAILY_DECISION_LIMITS)
        self.feature_limits = dict(feature_limits or DEFAULT_DAILY_FEATURE_LIMITS)
        self.tool_costs = {key: dict(value) for key, value in (tool_costs or DEFAULT_TOOL_COSTS).items()}

    def snapshot_for_tool(self, world: dict[str, Any], npc_id: str, tool: ToolDefinition) -> dict[str, Any]:
        policy = self.cost_policy_for_tool(tool)
        channel = str(policy.get("channel") or "") or None
        feature = str(policy.get("feature") or "") or None
        cost = int(policy.get("cost") or 0)
        cost_breakdown = self._cost_breakdown(tool, policy)
        if not channel:
            return DecisionBudgetSnapshot(
                tool_id=tool.tool_id,
                channel=None,
                feature=None,
                route="rule",
                reason="no_llm_budget_required",
                limit=0,
                consumed=0,
                remaining=0,
                feature_limit=0,
                feature_consumed=0,
                feature_remaining=0,
                cost=0,
                unit="decision_unit",
                cost_breakdown=cost_breakdown,
                llm_eligible=bool(tool.llm_eligible),
            ).to_dict()

        agent_budget = self._agent_budget(world, npc_id)
        limit = int(agent_budget.get("limits", {}).get(channel, self.daily_limits.get(channel, 0)))
        consumed = int(agent_budget.get("consumed", {}).get(channel, 0))
        feature_limit = int(agent_budget.get("featureLimits", {}).get(feature or "", self.feature_limits.get(feature or "", limit)))
        feature_consumed = int(agent_budget.get("featureConsumed", {}).get(feature or "", 0))
        remaining = max(0, limit - consumed)
        feature_remaining = max(0, feature_limit - feature_consumed)
        if remaining >= cost and feature_remaining >= cost:
            route = "llm"
            reason = "budget_available"
        elif feature_remaining < cost:
            route = "rule_fallback"
            reason = "llm_feature_budget_exhausted_rule_fallback"
        else:
            route = "rule_fallback"
            reason = "llm_budget_exhausted_rule_fallback"
        return DecisionBudgetSnapshot(
            tool_id=tool.tool_id,
            channel=channel,
            feature=feature,
            route=route,
            reason=reason,
            limit=limit,
            consumed=consumed,
            remaining=remaining,
            feature_limit=feature_limit,
            feature_consumed=feature_consumed,
            feature_remaining=feature_remaining,
            cost=cost,
            unit="decision_unit",
            cost_breakdown=cost_breakdown,
            llm_eligible=bool(tool.llm_eligible),
        ).to_dict()

    def consume_for_tool(self, world: dict[str, Any], npc_id: str, tool: ToolDefinition) -> dict[str, Any] | None:
        snapshot = self.snapshot_for_tool(world, npc_id, tool)
        channel = snapshot.get("channel")
        if not channel:
            return None
        if str(snapshot.get("route") or "") == "rule_fallback":
            return {
                **snapshot,
                "eventType": "budget.decision_fallback",
                "consumedDelta": 0,
                "remainingBefore": int(snapshot.get("remaining") or 0),
                "featureRemainingBefore": int(snapshot.get("featureRemaining") or 0),
            }
        agent_budget = self._agent_budget(world, npc_id)
        consumed = agent_budget.setdefault("consumed", {})
        feature_consumed = agent_budget.setdefault("featureConsumed", {})
        cost = int(snapshot.get("cost") or 1)
        feature = str(snapshot.get("feature") or "")
        consumed[channel] = int(consumed.get(channel, 0)) + cost
        if feature:
            feature_consumed[feature] = int(feature_consumed.get(feature, 0)) + cost
        self._record_usage(world, npc_id=npc_id, snapshot=snapshot, cost=cost)
        updated = self.snapshot_for_tool(world, npc_id, tool)
        return {
            **updated,
            "eventType": "budget.decision_consumed",
            "consumedDelta": cost,
            "remainingBefore": int(snapshot.get("remaining") or 0),
            "featureRemainingBefore": int(snapshot.get("featureRemaining") or 0),
        }

    def exhaust(self, world: dict[str, Any], npc_id: str, channel: str) -> dict[str, Any]:
        """测试和调试用：把指定 NPC 的某个预算通道打满。"""
        agent_budget = self._agent_budget(world, npc_id)
        limit = int(agent_budget.get("limits", {}).get(channel, self.daily_limits.get(channel, 0)))
        agent_budget.setdefault("consumed", {})[channel] = limit
        return self.debug_snapshot(world, npc_ids=[npc_id])

    def exhaust_feature(self, world: dict[str, Any], npc_id: str, feature: str) -> dict[str, Any]:
        """测试和调试用：把指定 NPC 的某个 feature 预算打满。"""
        agent_budget = self._agent_budget(world, npc_id)
        limit = int(agent_budget.get("featureLimits", {}).get(feature, self.feature_limits.get(feature, 0)))
        agent_budget.setdefault("featureConsumed", {})[feature] = limit
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
                    "featureLimits": dict(budget.get("featureLimits", {})),
                    "featureConsumed": dict(budget.get("featureConsumed", {})),
                    "featureRemaining": {
                        feature: max(0, int(limit) - int(budget.get("featureConsumed", {}).get(feature, 0)))
                        for feature, limit in budget.get("featureLimits", {}).items()
                    },
                    "recentUsage": [dict(item) for item in budget.get("recentUsage", [])[-8:] if isinstance(item, dict)],
                }
            )
        return {
            "version": "decision_budget.v1",
            "policy": {
                "unit": "decision_unit",
                "channels": dict(self.daily_limits),
                "features": dict(self.feature_limits),
                "toolCosts": {tool_id: dict(policy) for tool_id, policy in self.tool_costs.items()},
            },
            "day": root.get("day"),
            "items": items,
        }

    def channel_for_tool(self, tool: ToolDefinition) -> str | None:
        return self.cost_policy_for_tool(tool).get("channel")

    def cost_policy_for_tool(self, tool: ToolDefinition) -> dict[str, Any]:
        if not tool.llm_eligible:
            return {"channel": None, "feature": None, "cost": 0}
        configured = dict(self.tool_costs.get(tool.tool_id) or {})
        if configured:
            configured.setdefault("channel", self._default_channel(tool))
            configured.setdefault("feature", self._default_feature(tool))
            configured.setdefault("cost", 1)
            return configured
        return {"channel": self._default_channel(tool), "feature": self._default_feature(tool), "cost": 1}

    def _default_channel(self, tool: ToolDefinition) -> str | None:
        if tool.tier == "social_strategic":
            return "social_strategic_layer"
        if tool.tier == "vocational":
            return "vocational_local_llm"
        return None

    def _default_feature(self, tool: ToolDefinition) -> str | None:
        namespace = tool.tool_id.split(".", 1)[0]
        if namespace == "strategic":
            return "gossip_propagation"
        if namespace == "social":
            return "dialogue"
        if tool.tier == "vocational":
            return "vocational_action"
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
        budget = agents.setdefault(
            npc_id,
            {
                "limits": dict(self.daily_limits),
                "consumed": {},
                "featureLimits": dict(self.feature_limits),
                "featureConsumed": {},
                "recentUsage": [],
            },
        )
        if not isinstance(budget, dict):
            budget = {
                "limits": dict(self.daily_limits),
                "consumed": {},
                "featureLimits": dict(self.feature_limits),
                "featureConsumed": {},
                "recentUsage": [],
            }
            agents[npc_id] = budget
        budget.setdefault("limits", dict(self.daily_limits))
        budget.setdefault("consumed", {})
        budget.setdefault("featureLimits", dict(self.feature_limits))
        budget.setdefault("featureConsumed", {})
        budget.setdefault("recentUsage", [])
        return budget

    def _cost_breakdown(self, tool: ToolDefinition, policy: dict[str, Any]) -> dict[str, Any]:
        prompt_tokens = int(policy.get("estimatedPromptTokens") or 0)
        completion_tokens = int(policy.get("estimatedCompletionTokens") or 0)
        return {
            "unit": "decision_unit",
            "baseCost": int(policy.get("cost") or 0),
            "estimatedPromptTokens": prompt_tokens,
            "estimatedCompletionTokens": completion_tokens,
            "estimatedTotalTokens": prompt_tokens + completion_tokens,
            "llmEligible": bool(tool.llm_eligible),
        }

    def _record_usage(self, world: dict[str, Any], *, npc_id: str, snapshot: dict[str, Any], cost: int) -> None:
        agent_budget = self._agent_budget(world, npc_id)
        clock = world.get("clock", {}) if isinstance(world.get("clock"), dict) else {}
        usage = agent_budget.setdefault("recentUsage", [])
        usage.append(
            {
                "tick": int(clock.get("tick", 0)),
                "toolId": snapshot.get("toolId"),
                "channel": snapshot.get("channel"),
                "feature": snapshot.get("feature"),
                "route": snapshot.get("route"),
                "cost": cost,
                "estimatedTotalTokens": snapshot.get("costBreakdown", {}).get("estimatedTotalTokens") if isinstance(snapshot.get("costBreakdown"), dict) else 0,
            }
        )
        if len(usage) > 40:
            del usage[:-40]
