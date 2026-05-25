"""校验 Phase 2 runtime schema registry 的覆盖与迁移护栏。"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BACKEND_APP = ROOT / "backend" / "app"
VERSION_LITERAL_PATTERN = re.compile(r"""["']([a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)*\.v\d+)["']""")
REQUIRE_SCHEMA_PATTERN = re.compile(r"""require_schema_version\(["']([a-z][a-z0-9_]*)["']\)""")
VERSION_PATTERN = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)*\.v\d+$")
REQUIRED_DEFINITION_FIELDS = {
    "id",
    "version",
    "owner",
    "status",
    "description",
    "producer",
    "debugSurface",
    "requiredFields",
    "notes",
}


def main() -> None:
    sys.path.insert(0, str(ROOT / "backend"))
    from app.main import create_town_app  # noqa: PLC0415
    from app.runtime.schema_registry import (  # noqa: PLC0415
        SCHEMA_DEFINITIONS,
        SCHEMA_REGISTRY_VERSION,
        RuntimeSchemaDefinition,
        schema_registry_snapshot,
        schema_version_map,
    )
    from app.runtime.trace_schema import build_trace_envelope, with_trace_payload, world_time_payload  # noqa: PLC0415

    errors: list[str] = []
    warnings: list[str] = []

    _check_registry_shape(
        SCHEMA_DEFINITIONS,
        RuntimeSchemaDefinition,
        SCHEMA_REGISTRY_VERSION,
        schema_registry_snapshot(),
        schema_version_map(),
        errors,
    )
    _check_source_usage(SCHEMA_DEFINITIONS, errors, warnings)
    _check_phase2_debug_contract(
        app=create_town_app(provider_mode="rule"),
        definitions=SCHEMA_DEFINITIONS,
        registry_version=SCHEMA_REGISTRY_VERSION,
        versions=schema_version_map(),
        build_trace_envelope_fn=build_trace_envelope,
        with_trace_payload_fn=with_trace_payload,
        world_time_payload_fn=world_time_payload,
        errors=errors,
    )

    result = {
        "ok": not errors,
        "registryVersion": SCHEMA_REGISTRY_VERSION,
        "schemaCount": len(SCHEMA_DEFINITIONS),
        "errors": errors,
        "warnings": warnings,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if errors:
        raise SystemExit(1)


def _check_registry_shape(
    definitions: dict[str, Any],
    definition_type: type,
    registry_version: str,
    snapshot: dict[str, Any],
    versions: dict[str, str],
    errors: list[str],
) -> None:
    """校验 registry 内部结构，防止版本表和快照分叉。"""
    if registry_version != "schema_registry.v1":
        errors.append(f"SCHEMA_REGISTRY_VERSION 应为 schema_registry.v1，实际为 {registry_version}")
    if set(definitions) != set(versions):
        errors.append("SCHEMA_DEFINITIONS 与 schema_version_map key 不一致")
    if snapshot.get("registryVersion") != registry_version:
        errors.append("schema_registry_snapshot.registryVersion 与 SCHEMA_REGISTRY_VERSION 不一致")
    if snapshot.get("versions") != versions:
        errors.append("schema_registry_snapshot.versions 与 schema_version_map 不一致")

    schemas = snapshot.get("schemas")
    if not isinstance(schemas, list) or len(schemas) != len(definitions):
        errors.append("schema_registry_snapshot.schemas 数量应等于 SCHEMA_DEFINITIONS")
    else:
        for index, schema in enumerate(schemas):
            _check_snapshot_schema(index, schema, errors)

    for schema_id, definition in definitions.items():
        if not isinstance(definition, definition_type):
            errors.append(f"{schema_id}: registry definition 类型错误")
            continue
        if schema_id != definition.schema_id:
            errors.append(f"{schema_id}: dict key 与 schema_id 不一致：{definition.schema_id}")
        if not VERSION_PATTERN.match(definition.version):
            errors.append(f"{schema_id}: version 格式非法：{definition.version}")
        if not definition.owner:
            errors.append(f"{schema_id}: owner 不能为空")
        if definition.status not in {"active", "legacy_compat"}:
            errors.append(f"{schema_id}: status 非法：{definition.status}")
        if not definition.description or not definition.producer or not definition.debug_surface:
            errors.append(f"{schema_id}: description / producer / debug_surface 不能为空")
        if not definition.required_fields:
            errors.append(f"{schema_id}: required_fields 不能为空")
        if len(set(definition.required_fields)) != len(definition.required_fields):
            errors.append(f"{schema_id}: required_fields 存在重复字段")


def _check_snapshot_schema(index: int, schema: Any, errors: list[str]) -> None:
    """校验对外快照条目，避免 Debug / Eval 消费者拿到缺字段对象。"""
    if not isinstance(schema, dict):
        errors.append(f"schemas[{index}] 应为对象")
        return
    missing = sorted(REQUIRED_DEFINITION_FIELDS - set(schema))
    if missing:
        errors.append(f"schemas[{index}] 缺少字段：{missing}")
    if not isinstance(schema.get("id"), str) or not schema.get("id"):
        errors.append(f"schemas[{index}].id 应为非空字符串")
    if not isinstance(schema.get("version"), str) or not schema.get("version"):
        errors.append(f"schemas[{index}].version 应为非空字符串")
    if not isinstance(schema.get("description"), str) or not schema.get("description"):
        errors.append(f"schemas[{index}].description 应为非空字符串")
    if not isinstance(schema.get("requiredFields"), list) or not schema.get("requiredFields"):
        errors.append(f"schemas[{index}].requiredFields 应为非空数组")
    elif not all(isinstance(field, str) and field for field in schema.get("requiredFields", [])):
        errors.append(f"schemas[{index}].requiredFields 只能包含非空字符串")
    if not isinstance(schema.get("notes"), list):
        errors.append(f"schemas[{index}].notes 应为数组")


def _check_phase2_debug_contract(
    *,
    app: Any,
    definitions: dict[str, Any],
    registry_version: str,
    versions: dict[str, str],
    build_trace_envelope_fn: Any,
    with_trace_payload_fn: Any,
    world_time_payload_fn: Any,
    errors: list[str],
) -> None:
    """验证 /api/debug.phase2 与 schema registry 的实时对齐，防止 Debug 输出契约漂移。"""
    runtime = getattr(app, "runtime", None)
    if runtime is None:
        errors.append("create_town_app 未返回可用 runtime，无法校验 /api/debug.phase2")
        return

    probe_trace = build_trace_envelope_fn(
        event_type="schema.contract_probe",
        summary="schema registry contract probe",
        world_time=world_time_payload_fn(runtime.world),
        agent_id="kai",
    )
    probe_payload = with_trace_payload_fn({"reason": "schema registry contract probe"}, probe_trace)
    runtime.event_store.append("schema.contract_probe", probe_payload)

    phase2 = app.debug_phase2({"eventType": "schema.contract_probe", "limit": "5"})
    if not isinstance(phase2, dict):
        errors.append("/api/debug.phase2 应返回对象")
        return

    for field in ("traceSchemaVersion", "schemaRegistry", "recentTraceEvents"):
        if field not in phase2:
            errors.append(f"/api/debug.phase2 缺少字段：{field}")
    if phase2.get("traceSchemaVersion") != versions.get("phase2_trace"):
        errors.append("/api/debug.phase2.traceSchemaVersion 与 schema registry 不一致")

    live_registry = phase2.get("schemaRegistry")
    if not isinstance(live_registry, dict):
        errors.append("/api/debug.phase2.schemaRegistry 应为对象")
    else:
        if live_registry.get("registryVersion") != registry_version:
            errors.append("/api/debug.phase2.schemaRegistry.registryVersion 与 SCHEMA_REGISTRY_VERSION 不一致")
        if live_registry.get("versions") != versions:
            errors.append("/api/debug.phase2.schemaRegistry.versions 与 schema_version_map 不一致")

    trace_events = phase2.get("recentTraceEvents")
    if not isinstance(trace_events, list) or not trace_events:
        errors.append("/api/debug.phase2.recentTraceEvents 应返回至少一条 trace 事件")
        return
    probe_event = trace_events[-1] if isinstance(trace_events[-1], dict) else None
    if not isinstance(probe_event, dict):
        errors.append("/api/debug.phase2.recentTraceEvents 条目应为对象")
        return

    definition = definitions.get("phase2_trace")
    required_fields = list(getattr(definition, "required_fields", ()))
    missing_fields = [field for field in required_fields if field not in probe_event]
    if missing_fields:
        errors.append(f"/api/debug.phase2.recentTraceEvents 条目缺少 phase2_trace 字段：{missing_fields}")
    if probe_event.get("traceSchemaVersion") != versions.get("phase2_trace"):
        errors.append("/api/debug.phase2.recentTraceEvents.traceSchemaVersion 与 schema registry 不一致")
    if not isinstance(probe_event.get("details"), dict):
        errors.append("/api/debug.phase2.recentTraceEvents.details 应稳定返回对象")
    elif probe_event.get("eventType") == "schema.contract_probe" and probe_event.get("details") != {}:
        errors.append("/api/debug.phase2.recentTraceEvents.details 对未知事件应回退为空对象")

    _check_phase2_trace_focus_contract(
        app=app,
        runtime=runtime,
        versions=versions,
        build_trace_envelope_fn=build_trace_envelope_fn,
        with_trace_payload_fn=with_trace_payload_fn,
        world_time_payload_fn=world_time_payload_fn,
        errors=errors,
    )


def _check_phase2_trace_focus_contract(
    *,
    app: Any,
    runtime: Any,
    versions: dict[str, str],
    build_trace_envelope_fn: Any,
    with_trace_payload_fn: Any,
    world_time_payload_fn: Any,
    errors: list[str],
) -> None:
    """校验 trace sourceLinks / traceFocus 的跳转契约。"""
    decision_trace = build_trace_envelope_fn(
        event_type="motivation.decision_made",
        summary="trace focus decision",
        world_time=world_time_payload_fn(runtime.world),
        agent_id="kai",
        target_ids=["mira"],
    )
    decision_event = runtime.event_store.append(
        "motivation.decision_made",
        with_trace_payload_fn(
            {
                "npcId": "kai",
                "selectedToolId": "social.chat_with",
                "decisionReason": "trace focus check",
                "candidateScores": [{"toolId": "social.chat_with", "score": 1.0}],
            },
            decision_trace,
        ),
    )
    tool_trace = build_trace_envelope_fn(
        event_type="tool.execution_completed",
        summary="trace focus tool completed",
        world_time=world_time_payload_fn(runtime.world),
        source_event_id=str(decision_event.get("id") or ""),
        agent_id="kai",
        target_ids=["mira"],
    )
    tool_event = runtime.event_store.append(
        "tool.execution_completed",
        with_trace_payload_fn(
            {
                "npcId": "kai",
                "toolId": "social.chat_with",
                "targetNpcId": "mira",
                "sourceEventIds": [decision_event.get("id")],
                "traceRefs": [
                    {
                        "type": "motivation_decision_trace",
                        "eventId": decision_event.get("id"),
                        "traceId": decision_trace.get("traceId"),
                    }
                ],
            },
            tool_trace,
        ),
    )
    memory_trace = build_trace_envelope_fn(
        event_type="memory.result_observed",
        summary="trace focus memory observed",
        world_time=world_time_payload_fn(runtime.world),
        source_event_id=str(tool_event.get("id") or ""),
        agent_id="kai",
        target_ids=["kai", "mira"],
    )
    memory_event = runtime.event_store.append(
        "memory.result_observed",
        with_trace_payload_fn(
            {
                "sourceEventId": tool_event.get("id"),
                "observerVisibility": "participants_only",
                "observerCount": 2,
                "observerScope": {"observers": ["kai", "mira"], "observerIds": ["kai", "mira"]},
                "observers": ["kai", "mira"],
                "memories": [{"recordId": "memory.trace_focus"}],
            },
            memory_trace,
        ),
    )

    focus = app.debug_phase2({"focusEventId": str(memory_event.get("id") or ""), "agentId": "mira", "limit": "8"})
    focus_items = focus.get("recentTraceEvents") if isinstance(focus, dict) else None
    if not isinstance(focus_items, list) or not focus_items:
        errors.append("/api/debug.phase2 focus 查询应返回 recentTraceEvents")
        return
    memory_snapshot = next((item for item in focus_items if isinstance(item, dict) and item.get("eventId") == memory_event.get("id")), None)
    if not isinstance(memory_snapshot, dict):
        errors.append("/api/debug.phase2 focusEventId 应把聚焦事件注入 recentTraceEvents")
        return
    source_links = memory_snapshot.get("sourceLinks")
    if not isinstance(source_links, list) or not source_links:
        errors.append("/api/debug.phase2.recentTraceEvents.sourceLinks 应返回直接来源")
    elif not any(isinstance(link, dict) and link.get("eventId") == tool_event.get("id") and link.get("eventType") == "tool.execution_completed" for link in source_links):
        errors.append("/api/debug.phase2.recentTraceEvents.sourceLinks 应解析 memory -> tool 来源")
    trace_focus = focus.get("traceFocus")
    if not isinstance(trace_focus, dict) or not trace_focus.get("matched"):
        errors.append("/api/debug.phase2.traceFocus 应标记 focusEventId 命中")
    elif trace_focus.get("eventId") != memory_event.get("id"):
        errors.append("/api/debug.phase2.traceFocus.eventId 应等于请求的 focusEventId")

    tool_focus = app.debug_phase2({"focusEventId": str(tool_event.get("id") or ""), "agentId": "mira", "limit": "8"})
    tool_focus_payload = tool_focus.get("traceFocus") if isinstance(tool_focus, dict) else None
    if not isinstance(tool_focus_payload, dict) or int(tool_focus_payload.get("downstreamObservedCount") or 0) < 1:
        errors.append("/api/debug.phase2.traceFocus.downstreamObservedCount 应统计直接下游观察记忆")

    missing_focus = app.debug_phase2({"focusEventId": "evt_missing_trace_focus", "limit": "3"})
    missing_payload = missing_focus.get("traceFocus") if isinstance(missing_focus, dict) else None
    if not isinstance(missing_payload, dict) or missing_payload.get("matched") is not False or missing_payload.get("status") != "missing":
        errors.append("/api/debug.phase2.traceFocus 对未知 focusEventId 应稳定返回 missing")


def _check_source_usage(definitions: dict[str, Any], errors: list[str], warnings: list[str]) -> None:
    """扫描源码中的 schema 使用，禁止生产者绕过 registry 写版本字面量。"""
    registry_path = (BACKEND_APP / "runtime" / "schema_registry.py").resolve()
    schema_ids = set(definitions)
    managed_versions = {str(definition.version) for definition in definitions.values()}
    managed_prefixes = {version.rsplit(".v", 1)[0] for version in managed_versions}
    referenced_ids: set[str] = set()
    stray_version_literals: list[str] = []

    for path in sorted(BACKEND_APP.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        relative = path.relative_to(ROOT)
        for match in REQUIRE_SCHEMA_PATTERN.finditer(text):
            schema_id = match.group(1)
            referenced_ids.add(schema_id)
            if schema_id not in schema_ids:
                line_no = text[: match.start()].count("\n") + 1
                errors.append(f"{relative}:{line_no}: require_schema_version 引用了未知 schema id：{schema_id}")

        if path.resolve() == registry_path:
            continue
        for match in VERSION_LITERAL_PATTERN.finditer(text):
            version_literal = match.group(1)
            version_prefix = version_literal.rsplit(".v", 1)[0]
            if version_literal not in managed_versions and version_prefix not in managed_prefixes:
                continue
            line_no = text[: match.start()].count("\n") + 1
            stray_version_literals.append(f"{relative}:{line_no}: {version_literal}")

    if stray_version_literals:
        errors.append("schema version 字面量只能出现在 backend/app/runtime/schema_registry.py")
        errors.extend(stray_version_literals)

    unused_ids = sorted(schema_ids - referenced_ids - {"schema_registry"})
    if unused_ids:
        warnings.append(f"registry 中存在当前源码未直接 require 的 schema id：{unused_ids}")


if __name__ == "__main__":
    main()
