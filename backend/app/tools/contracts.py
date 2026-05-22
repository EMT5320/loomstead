from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.tools.tool_schema import ToolDefinition


@dataclass(frozen=True)
class ToolContractViolation(Exception):
    """工具契约违规，使用稳定 code 进入失败 trace。"""

    code: str
    details: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return self.code


class ToolContractValidator:
    """校验 ToolDefinition 输入 schema 与权威世界前置条件。"""

    def validate_completion(self, *, world: dict[str, Any], completion: dict[str, Any], tool: ToolDefinition) -> None:
        raw_input = completion.get("input") if "input" in completion else {}
        tool_input = raw_input if isinstance(raw_input, dict) else {}
        self.validate_input_schema(tool=tool, tool_input=raw_input)
        self.validate_world_preconditions(world=world, completion=completion, tool=tool, tool_input=tool_input)

    def validate_input_schema(self, *, tool: ToolDefinition, tool_input: Any) -> None:
        schema = tool.input_schema if isinstance(tool.input_schema, dict) else {}
        if schema.get("type") == "object" and not isinstance(tool_input, dict):
            raise ToolContractViolation("input_not_object", {"toolId": tool.tool_id})
        if not isinstance(tool_input, dict):
            return

        for field_name in schema.get("required", []) if isinstance(schema.get("required"), list) else []:
            if not str(field_name) or str(field_name) not in tool_input or tool_input.get(str(field_name)) in (None, ""):
                raise ToolContractViolation(
                    f"missing_required_input:{field_name}",
                    {"toolId": tool.tool_id, "field": str(field_name)},
                )

        properties = schema.get("properties", {}) if isinstance(schema.get("properties"), dict) else {}
        for field_name, value in tool_input.items():
            field_schema = properties.get(field_name)
            if not isinstance(field_schema, dict):
                continue
            expected_type = str(field_schema.get("type") or "")
            if expected_type and not self._matches_json_type(value, expected_type):
                raise ToolContractViolation(
                    f"input_type_mismatch:{field_name}",
                    {
                        "toolId": tool.tool_id,
                        "field": field_name,
                        "expectedType": expected_type,
                        "actualType": type(value).__name__,
                    },
                )

    def validate_world_preconditions(
        self,
        *,
        world: dict[str, Any],
        completion: dict[str, Any],
        tool: ToolDefinition,
        tool_input: dict[str, Any],
    ) -> None:
        tool_id = tool.tool_id
        npc_id = str(completion.get("npcId") or "")
        if tool_id == "life.move_to":
            self._require_anchor(world, str(tool_input.get("anchorId") or ""), tool_id=tool_id, field="anchorId")
        if tool_id == "farm.water_crop":
            self._require_farm_plot(world, str(tool_input.get("farmPlotId") or ""), tool_id=tool_id)
        if tool_id == "craft.repair_stall":
            anchor_id = str(tool_input.get("anchorId") or "")
            if anchor_id:
                self._require_anchor(world, anchor_id, tool_id=tool_id, field="anchorId")
        if tool_id in {"social.chat_with", "social.give_gift"}:
            self._require_target_npc(world, npc_id=npc_id, target_id=str(tool_input.get("targetNpcId") or ""), tool_id=tool_id)
        if tool_id == "strategic.spread_rumor":
            if tool_input.get("forbiddenStateMutation"):
                raise ToolContractViolation("forbidden_state_fields", {"toolId": tool_id, "field": "forbiddenStateMutation"})
            hook_id = str(tool_input.get("hookId") or "")
            if hook_id and not self._has_gossip_hook(world, npc_id=npc_id, hook_id=hook_id):
                raise ToolContractViolation("gossip_hook_unavailable", {"toolId": tool_id, "hookId": hook_id})

    def _matches_json_type(self, value: Any, expected_type: str) -> bool:
        if expected_type == "string":
            return isinstance(value, str)
        if expected_type == "number":
            return isinstance(value, (int, float)) and not isinstance(value, bool)
        if expected_type == "integer":
            return isinstance(value, int) and not isinstance(value, bool)
        if expected_type == "boolean":
            return isinstance(value, bool)
        if expected_type == "object":
            return isinstance(value, dict)
        if expected_type == "array":
            return isinstance(value, list)
        return True

    def _require_anchor(self, world: dict[str, Any], anchor_id: str, *, tool_id: str, field: str) -> None:
        if not anchor_id or anchor_id not in world.get("anchors", {}):
            raise ToolContractViolation("anchor_unavailable", {"toolId": tool_id, "field": field, "anchorId": anchor_id})

    def _require_farm_plot(self, world: dict[str, Any], farm_plot_id: str, *, tool_id: str) -> None:
        if not farm_plot_id or farm_plot_id not in world.get("farmPlots", {}):
            raise ToolContractViolation("farm_plot_unavailable", {"toolId": tool_id, "farmPlotId": farm_plot_id})

    def _require_target_npc(self, world: dict[str, Any], *, npc_id: str, target_id: str, tool_id: str) -> None:
        if not target_id or target_id not in world.get("agents", {}):
            raise ToolContractViolation("target_unavailable", {"toolId": tool_id, "targetNpcId": target_id})
        if npc_id and target_id == npc_id:
            raise ToolContractViolation("target_self_unavailable", {"toolId": tool_id, "targetNpcId": target_id})

    def _has_gossip_hook(self, world: dict[str, Any], *, npc_id: str, hook_id: str) -> bool:
        agent = world.get("agents", {}).get(npc_id)
        hooks = agent.get("deepCard", {}).get("gossipHooks", []) if isinstance(agent, dict) and isinstance(agent.get("deepCard"), dict) else []
        if not isinstance(hooks, list):
            return False
        return any(isinstance(hook, dict) and str(hook.get("id") or "") == hook_id for hook in hooks)
