from __future__ import annotations

from dataclasses import dataclass, field
import json
import math
import re
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
        self._validate_schema_value(tool_id=tool.tool_id, schema=schema, value=tool_input, path="", root=True)

    def _validate_schema_value(self, *, tool_id: str, schema: dict[str, Any], value: Any, path: str, root: bool = False) -> None:
        """校验 Runtime 支持的 JSON Schema 子集。"""
        if not isinstance(schema, dict):
            return

        expected_types = self._expected_types(schema.get("type"))
        if expected_types and not any(self._matches_json_type(value, expected_type) for expected_type in expected_types):
            if root and expected_types == ["object"]:
                raise ToolContractViolation("input_not_object", {"toolId": tool_id, "path": path or "input"})
            raise ToolContractViolation(
                f"input_type_mismatch:{self._field_path(path)}",
                {
                    "toolId": tool_id,
                    "field": self._field_path(path),
                    "path": path or "input",
                    "keyword": "type",
                    "expectedType": expected_types[0] if len(expected_types) == 1 else expected_types,
                    "actualType": self._json_type_name(value),
                },
            )

        if "const" in schema and value != schema.get("const"):
            raise ToolContractViolation(
                f"input_const_mismatch:{self._field_path(path)}",
                {"toolId": tool_id, "field": self._field_path(path), "path": path or "input", "keyword": "const"},
            )

        enum_values = schema.get("enum")
        if isinstance(enum_values, list) and value not in enum_values:
            raise ToolContractViolation(
                f"input_enum_mismatch:{self._field_path(path)}",
                {
                    "toolId": tool_id,
                    "field": self._field_path(path),
                    "path": path or "input",
                    "keyword": "enum",
                    "allowedValues": enum_values,
                },
            )

        if isinstance(value, dict):
            self._validate_object(tool_id=tool_id, schema=schema, value=value, path=path)
        elif isinstance(value, list):
            self._validate_array(tool_id=tool_id, schema=schema, value=value, path=path)
        elif isinstance(value, str):
            self._validate_string(tool_id=tool_id, schema=schema, value=value, path=path)
        elif isinstance(value, (int, float)) and not isinstance(value, bool):
            self._validate_number(tool_id=tool_id, schema=schema, value=value, path=path)

    def _validate_object(self, *, tool_id: str, schema: dict[str, Any], value: dict[str, Any], path: str) -> None:
        min_properties = schema.get("minProperties")
        if isinstance(min_properties, int) and len(value) < min_properties:
            raise ToolContractViolation(
                f"input_object_too_small:{self._field_path(path)}",
                {"toolId": tool_id, "field": self._field_path(path), "path": path or "input", "keyword": "minProperties", "limit": min_properties},
            )
        max_properties = schema.get("maxProperties")
        if isinstance(max_properties, int) and len(value) > max_properties:
            raise ToolContractViolation(
                f"input_object_too_large:{self._field_path(path)}",
                {"toolId": tool_id, "field": self._field_path(path), "path": path or "input", "keyword": "maxProperties", "limit": max_properties},
            )

        for field_name in schema.get("required", []) if isinstance(schema.get("required"), list) else []:
            normalized_field = str(field_name)
            child_path = self._child_path(path, normalized_field)
            if not normalized_field or normalized_field not in value or value.get(normalized_field) in (None, ""):
                raise ToolContractViolation(
                    f"missing_required_input:{self._field_path(child_path)}",
                    {"toolId": tool_id, "field": self._field_path(child_path), "path": child_path, "keyword": "required"},
                )

        properties = schema.get("properties", {}) if isinstance(schema.get("properties"), dict) else {}
        additional_properties = schema.get("additionalProperties", True)
        for field_name, child_value in value.items():
            child_path = self._child_path(path, str(field_name))
            field_schema = properties.get(field_name)
            if isinstance(field_schema, dict):
                self._validate_schema_value(tool_id=tool_id, schema=field_schema, value=child_value, path=child_path)
                continue
            if additional_properties is False:
                raise ToolContractViolation(
                    f"unexpected_input_field:{self._field_path(child_path)}",
                    {"toolId": tool_id, "field": self._field_path(child_path), "path": child_path, "keyword": "additionalProperties"},
                )
            if isinstance(additional_properties, dict):
                self._validate_schema_value(tool_id=tool_id, schema=additional_properties, value=child_value, path=child_path)

    def _validate_array(self, *, tool_id: str, schema: dict[str, Any], value: list[Any], path: str) -> None:
        min_items = schema.get("minItems")
        if isinstance(min_items, int) and len(value) < min_items:
            raise ToolContractViolation(
                f"input_array_too_short:{self._field_path(path)}",
                {"toolId": tool_id, "field": self._field_path(path), "path": path or "input", "keyword": "minItems", "limit": min_items},
            )
        max_items = schema.get("maxItems")
        if isinstance(max_items, int) and len(value) > max_items:
            raise ToolContractViolation(
                f"input_array_too_long:{self._field_path(path)}",
                {"toolId": tool_id, "field": self._field_path(path), "path": path or "input", "keyword": "maxItems", "limit": max_items},
            )
        if schema.get("uniqueItems") is True and self._has_duplicate_items(value):
            raise ToolContractViolation(
                f"input_array_duplicate_items:{self._field_path(path)}",
                {"toolId": tool_id, "field": self._field_path(path), "path": path or "input", "keyword": "uniqueItems"},
            )
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                self._validate_schema_value(tool_id=tool_id, schema=item_schema, value=item, path=f"{path}[{index}]" if path else f"[{index}]")

    def _validate_string(self, *, tool_id: str, schema: dict[str, Any], value: str, path: str) -> None:
        min_length = schema.get("minLength")
        if isinstance(min_length, int) and len(value) < min_length:
            raise ToolContractViolation(
                f"input_string_too_short:{self._field_path(path)}",
                {"toolId": tool_id, "field": self._field_path(path), "path": path or "input", "keyword": "minLength", "limit": min_length},
            )
        max_length = schema.get("maxLength")
        if isinstance(max_length, int) and len(value) > max_length:
            raise ToolContractViolation(
                f"input_string_too_long:{self._field_path(path)}",
                {"toolId": tool_id, "field": self._field_path(path), "path": path or "input", "keyword": "maxLength", "limit": max_length},
            )
        pattern = schema.get("pattern")
        if isinstance(pattern, str):
            try:
                matched = re.search(pattern, value) is not None
            except re.error:
                matched = True
            if not matched:
                raise ToolContractViolation(
                    f"input_pattern_mismatch:{self._field_path(path)}",
                    {"toolId": tool_id, "field": self._field_path(path), "path": path or "input", "keyword": "pattern", "pattern": pattern},
                )

    def _validate_number(self, *, tool_id: str, schema: dict[str, Any], value: int | float, path: str) -> None:
        numeric_value = float(value)
        if not math.isfinite(numeric_value):
            raise ToolContractViolation(
                f"input_number_not_finite:{self._field_path(path)}",
                {"toolId": tool_id, "field": self._field_path(path), "path": path or "input", "keyword": "type"},
            )
        if "minimum" in schema and numeric_value < float(schema.get("minimum")):
            raise ToolContractViolation(
                f"input_number_too_small:{self._field_path(path)}",
                {"toolId": tool_id, "field": self._field_path(path), "path": path or "input", "keyword": "minimum", "limit": schema.get("minimum")},
            )
        if "maximum" in schema and numeric_value > float(schema.get("maximum")):
            raise ToolContractViolation(
                f"input_number_too_large:{self._field_path(path)}",
                {"toolId": tool_id, "field": self._field_path(path), "path": path or "input", "keyword": "maximum", "limit": schema.get("maximum")},
            )
        if "exclusiveMinimum" in schema and numeric_value <= float(schema.get("exclusiveMinimum")):
            raise ToolContractViolation(
                f"input_number_too_small:{self._field_path(path)}",
                {"toolId": tool_id, "field": self._field_path(path), "path": path or "input", "keyword": "exclusiveMinimum", "limit": schema.get("exclusiveMinimum")},
            )
        if "exclusiveMaximum" in schema and numeric_value >= float(schema.get("exclusiveMaximum")):
            raise ToolContractViolation(
                f"input_number_too_large:{self._field_path(path)}",
                {"toolId": tool_id, "field": self._field_path(path), "path": path or "input", "keyword": "exclusiveMaximum", "limit": schema.get("exclusiveMaximum")},
            )
        multiple_of = schema.get("multipleOf")
        if isinstance(multiple_of, (int, float)) and not isinstance(multiple_of, bool) and float(multiple_of) > 0:
            quotient = numeric_value / float(multiple_of)
            if abs(quotient - round(quotient)) > 1e-9:
                raise ToolContractViolation(
                    f"input_number_not_multiple:{self._field_path(path)}",
                    {"toolId": tool_id, "field": self._field_path(path), "path": path or "input", "keyword": "multipleOf", "limit": multiple_of},
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
        if expected_type == "null":
            return value is None
        return True

    def _expected_types(self, raw_type: Any) -> list[str]:
        if isinstance(raw_type, str) and raw_type:
            return [raw_type]
        if isinstance(raw_type, list):
            return [str(item) for item in raw_type if isinstance(item, str) and item]
        return []

    def _json_type_name(self, value: Any) -> str:
        if value is None:
            return "null"
        if isinstance(value, bool):
            return "boolean"
        if isinstance(value, str):
            return "string"
        if isinstance(value, int):
            return "integer"
        if isinstance(value, float):
            return "number"
        if isinstance(value, dict):
            return "object"
        if isinstance(value, list):
            return "array"
        return type(value).__name__

    def _child_path(self, parent: str, child: str) -> str:
        return f"{parent}.{child}" if parent else child

    def _field_path(self, path: str) -> str:
        return path or "input"

    def _has_duplicate_items(self, value: list[Any]) -> bool:
        seen: set[str] = set()
        for item in value:
            fingerprint = json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            if fingerprint in seen:
                return True
            seen.add(fingerprint)
        return False

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
