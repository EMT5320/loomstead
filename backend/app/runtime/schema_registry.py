from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Literal


SCHEMA_REGISTRY_VERSION = "schema_registry.v1"
SchemaStatus = Literal["active", "legacy_compat"]


@dataclass(frozen=True)
class RuntimeSchemaDefinition:
    """Phase 2 调试与评估链路使用的 schema 元数据。"""

    schema_id: str
    version: str
    owner: str
    status: SchemaStatus
    description: str
    producer: str
    debug_surface: str
    required_fields: tuple[str, ...]
    notes: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.schema_id,
            "version": self.version,
            "owner": self.owner,
            "status": self.status,
            "description": self.description,
            "producer": self.producer,
            "debugSurface": self.debug_surface,
            "requiredFields": list(self.required_fields),
            "notes": list(self.notes),
        }


# 先集中治理 Phase 2 主路径会暴露给 Debug / Eval / Godot 的版本号。
SCHEMA_DEFINITIONS: dict[str, RuntimeSchemaDefinition] = {
    "schema_registry": RuntimeSchemaDefinition(
        schema_id="schema_registry",
        version=SCHEMA_REGISTRY_VERSION,
        owner="runtime",
        status="active",
        description="Runtime schema registry snapshot exposed by /api/debug.phase2.",
        producer="app.runtime.schema_registry",
        debug_surface="phase2.schemaRegistry",
        required_fields=("registryVersion", "schemas", "versions"),
    ),
    "phase2_trace": RuntimeSchemaDefinition(
        schema_id="phase2_trace",
        version="phase2.trace.v1",
        owner="runtime",
        status="active",
        description="Unified trace envelope for Phase 2 decision, tool, budget, and memory events.",
        producer="app.runtime.trace_schema",
        debug_surface="phase2.traceSchemaVersion + phase2.recentTraceEvents[]",
        required_fields=("traceId", "spanId", "worldTime", "eventType", "summary"),
    ),
    "capability_resolution": RuntimeSchemaDefinition(
        schema_id="capability_resolution",
        version="capability_resolution.v1",
        owner="runtime",
        status="active",
        description="Five-layer tool capability filtering and routing evidence.",
        producer="app.runtime.capability_registry",
        debug_surface="phase2.motivation.items[].capabilityFilters",
        required_fields=("context", "layers", "allowedToolIds", "rejectedTools", "decisionBudgets"),
    ),
    "decision_budget": RuntimeSchemaDefinition(
        schema_id="decision_budget",
        version="decision_budget.v1",
        owner="runtime",
        status="active",
        description="NPC / feature / tool-cost decision budget policy and usage snapshot.",
        producer="app.runtime.decision_budget",
        debug_surface="phase2.decisionBudget",
        required_fields=("policy", "items", "providerActuals"),
    ),
    "provider_usage_actual": RuntimeSchemaDefinition(
        schema_id="provider_usage_actual",
        version="provider_usage_actual.v1",
        owner="runtime",
        status="active",
        description="Actual provider usage record for tokens, latency, and cost aggregation.",
        producer="app.runtime.decision_budget",
        debug_surface="phase2.decisionBudget.providerActuals + providerUsageRecord",
        required_fields=("tick", "npcId", "feature", "provider", "tokens", "latencyMs", "cost"),
    ),
    "observer_scope": RuntimeSchemaDefinition(
        schema_id="observer_scope",
        version="observer_scope.v1",
        owner="memory",
        status="active",
        description="Result observer visibility scope with participants, location, and exclusions.",
        producer="app.memory.observer",
        debug_surface="phase2.recentTraceEvents[].details.observerScope",
        required_fields=("visibility", "actorId", "participantIds", "observerIds", "excludedObserverIds"),
    ),
    "observer_spatial_model": RuntimeSchemaDefinition(
        schema_id="observer_spatial_model",
        version="observer_spatial_model.v1",
        owner="memory",
        status="active",
        description="Normalized anchor-distance model used by all_in_location visibility.",
        producer="app.memory.observer",
        debug_surface="phase2.recentTraceEvents[].details.observerScope.spatialModel",
        required_fields=("distanceUnit", "hearingRadius"),
    ),
    "motivation_plan": RuntimeSchemaDefinition(
        schema_id="motivation_plan",
        version="motivation_plan.v1",
        owner="runtime",
        status="active",
        description="Read-only Godot-compatible life action plan produced by MotivationEngine.",
        producer="app.runtime.agent_runtime",
        debug_surface="world.lifeActionPlan + world.slice.scheduleSnapshotVersion",
        required_fields=("day", "phase", "selectedActions", "locationBuckets", "policy"),
    ),
    "legacy_life_action_plan": RuntimeSchemaDefinition(
        schema_id="legacy_life_action_plan",
        version="life_action_plan.v1",
        owner="simulation",
        status="legacy_compat",
        description="Legacy life action plan snapshot kept for direct world_state callers.",
        producer="app.simulation.life_action_planner",
        debug_surface="world.lifeActionPlan before AgentRuntime Phase 2 override",
        required_fields=("day", "phase", "selectedActions", "locationBuckets", "policy"),
        notes=("AgentRuntime replaces this with motivation_plan.v1 on the current tick/state path.",),
    ),
    "motivation_engine": RuntimeSchemaDefinition(
        schema_id="motivation_engine",
        version="motivation_engine.v0",
        owner="runtime",
        status="legacy_compat",
        description="MotivationEngine decision snapshot; v0 kept for current debug compatibility.",
        producer="app.runtime.motivation_engine",
        debug_surface="phase2.motivation",
        required_fields=("items",),
        notes=("v0 remains stable until decision snapshot shape is promoted after Phase 2 trace hardening.",),
    ),
    "need_accumulator": RuntimeSchemaDefinition(
        schema_id="need_accumulator",
        version="need_accumulator.v0",
        owner="runtime",
        status="legacy_compat",
        description="Need scoring snapshot used by MotivationEngine.",
        producer="app.runtime.need_accumulator",
        debug_surface="phase2.needAccumulator",
        required_fields=("items",),
    ),
    "tool_runtime": RuntimeSchemaDefinition(
        schema_id="tool_runtime",
        version="tool_runtime.v1",
        owner="runtime",
        status="active",
        description="Current ToolExecutor action runtime snapshot for selected NPCs.",
        producer="app.runtime.agent_runtime",
        debug_surface="phase2.toolRuntime",
        required_fields=("items",),
    ),
    "world_entities": RuntimeSchemaDefinition(
        schema_id="world_entities",
        version="world_entities.v1",
        owner="world",
        status="active",
        description="Typed WorldEntity snapshot for FarmPlot, Item, Inventory, Shop, Building, Time, and Weather.",
        producer="app.world.entities.schema",
        debug_surface="phase2.worldEntities",
        required_fields=("count", "byKind", "items"),
    ),
    "subjective_memory_store": RuntimeSchemaDefinition(
        schema_id="subjective_memory_store",
        version="subjective_memory_store.v1",
        owner="memory",
        status="active",
        description="Subjective memory debug store snapshot with decay and archive metadata.",
        producer="app.memory.subjective_memory",
        debug_surface="phase2.subjectiveMemory",
        required_fields=("agentId", "count", "activeCount", "archivedCount", "items"),
    ),
    "subjective_memory_recall": RuntimeSchemaDefinition(
        schema_id="subjective_memory_recall",
        version="subjective_memory_recall.v2",
        owner="runtime",
        status="active",
        description="Subjective memory recall evidence injected into decision scoring, including salience after decay.",
        producer="app.runtime.motivation_engine",
        debug_surface="phase2.motivation.items[].subjectiveMemoryRecall",
        required_fields=("query", "worldTick", "count", "activeCount", "recordIds", "sourceEventIds"),
    ),
    "relationship_edge_store": RuntimeSchemaDefinition(
        schema_id="relationship_edge_store",
        version="relationship_edge_store.v0",
        owner="memory",
        status="legacy_compat",
        description="Relationship edge debug store snapshot with event and trace refs.",
        producer="app.memory.relationship_edges",
        debug_surface="phase2.relationshipEdges",
        required_fields=("agentId", "count", "items"),
    ),
    "heuristic_library": RuntimeSchemaDefinition(
        schema_id="heuristic_library",
        version="heuristic_library.v0",
        owner="memory",
        status="legacy_compat",
        description="Heuristic memory library snapshot with confidence decay.",
        producer="app.memory.heuristic",
        debug_surface="phase2.heuristics",
        required_fields=("agentId", "worldTick", "count", "items"),
    ),
    "heuristic_recall": RuntimeSchemaDefinition(
        schema_id="heuristic_recall",
        version="heuristic_recall.v1",
        owner="runtime",
        status="active",
        description="Heuristic recall evidence injected into decision scoring.",
        producer="app.runtime.motivation_engine",
        debug_surface="phase2.motivation.items[].heuristicRecall",
        required_fields=("worldTick", "count", "activeCount", "heuristicIds", "sourceEventIds"),
    ),
    "event_skill_outcome": RuntimeSchemaDefinition(
        schema_id="event_skill_outcome",
        version="event_skill_outcome.v1",
        owner="event_skill",
        status="active",
        description="Event skill outcome record shared by API result, event stream, and completed events.",
        producer="app.skills.event_skill_schema",
        debug_surface="eventResult + completedEvents[].resolution.outcomeRecord",
        required_fields=("recordVersion", "skillId", "eventId", "choice", "summary"),
    ),
}


def require_schema_version(schema_id: str) -> str:
    """按稳定 id 读取版本号，避免生产者散落硬编码字符串。"""
    definition = SCHEMA_DEFINITIONS.get(schema_id)
    if definition is None:
        raise KeyError(f"Unknown runtime schema id: {schema_id}")
    return definition.version


def schema_version_map() -> dict[str, str]:
    """返回 id -> version 映射，供 smoke test 和调试面板快速比对。"""
    return {schema_id: definition.version for schema_id, definition in SCHEMA_DEFINITIONS.items()}


def schema_registry_snapshot() -> dict[str, Any]:
    """生成可序列化 registry 快照，保持外部消费者只读。"""
    return {
        "registryVersion": SCHEMA_REGISTRY_VERSION,
        "schemas": [definition.to_dict() for definition in SCHEMA_DEFINITIONS.values()],
        "versions": deepcopy(schema_version_map()),
    }
