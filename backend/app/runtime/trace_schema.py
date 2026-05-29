from __future__ import annotations

from copy import deepcopy
from typing import Any
from uuid import uuid4

from app.runtime.schema_registry import require_schema_version

TRACE_SCHEMA_VERSION = require_schema_version("phase2_trace")


def world_time_payload(world: dict[str, Any]) -> dict[str, Any]:
    """提取统一世界时间字段，给调试链路复用。"""
    clock = world.get("clock", {}) if isinstance(world.get("clock"), dict) else {}
    return {
        "tick": int(clock.get("tick", 0)),
        "day": int(clock.get("day", 1)),
        "hour": int(clock.get("hour", 8)),
        "minute": int(clock.get("minute", 0)),
        "phase": str(clock.get("phase") or "morning"),
    }


def build_trace_envelope(
    *,
    event_type: str,
    summary: str | None = None,
    world_time: dict[str, Any] | None = None,
    trace_id: str | None = None,
    span_id: str | None = None,
    source_event_id: str | None = None,
    agent_id: str | None = None,
    target_ids: list[str] | None = None,
) -> dict[str, Any]:
    """生成稳定的 Phase 2 trace envelope。"""
    normalized_source_event_id = _none_if_empty(source_event_id)
    normalized_trace_id = _none_if_empty(trace_id) or normalized_source_event_id or f"trace_{uuid4().hex}"
    normalized_span_id = _none_if_empty(span_id) or f"span_{uuid4().hex[:16]}"
    normalized_event_type = str(event_type or "unknown")
    normalized_summary = str(summary or normalized_event_type)
    return {
        "traceId": normalized_trace_id,
        "spanId": normalized_span_id,
        "sourceEventId": normalized_source_event_id,
        "agentId": _none_if_empty(agent_id),
        "targetIds": _normalize_target_ids(target_ids),
        "worldTime": _normalize_world_time(world_time),
        "eventType": normalized_event_type,
        "summary": normalized_summary,
    }


def with_trace_payload(payload: dict[str, Any] | None, trace: dict[str, Any]) -> dict[str, Any]:
    """把 trace 字段写回事件 payload，保持调试消费结构稳定。"""
    enriched = dict(payload) if isinstance(payload, dict) else {}
    enriched["traceSchemaVersion"] = TRACE_SCHEMA_VERSION
    enriched["trace"] = deepcopy(trace)
    enriched["traceId"] = trace.get("traceId")
    enriched["spanId"] = trace.get("spanId")
    enriched["sourceEventId"] = trace.get("sourceEventId")
    enriched["agentId"] = trace.get("agentId")
    enriched["targetIds"] = _normalize_target_ids(trace.get("targetIds"))
    enriched["worldTime"] = _normalize_world_time(trace.get("worldTime"))
    enriched["eventType"] = trace.get("eventType")
    enriched["summary"] = trace.get("summary")
    return enriched


def trace_event_snapshot(event: dict[str, Any]) -> dict[str, Any]:
    """把 EventStore 事件压成可直接给 /api/debug.phase2 使用的 trace 快照。"""
    payload = event.get("payload", {}) if isinstance(event.get("payload"), dict) else {}
    trace = payload.get("trace") if isinstance(payload.get("trace"), dict) else {}
    event_type = str(payload.get("eventType") or event.get("type") or "unknown")
    summary = str(payload.get("summary") or payload.get("reason") or event_type)
    target_ids = payload.get("targetIds") if isinstance(payload.get("targetIds"), list) else _derive_target_ids(payload)
    envelope = build_trace_envelope(
        event_type=event_type,
        summary=summary,
        world_time=payload.get("worldTime") if isinstance(payload.get("worldTime"), dict) else None,
        trace_id=str(trace.get("traceId") or payload.get("traceId") or event.get("id") or ""),
        span_id=str(trace.get("spanId") or payload.get("spanId") or _span_from_event_id(event.get("id")) or ""),
        source_event_id=str(trace.get("sourceEventId") or payload.get("sourceEventId") or _first_source_event_id(payload) or ""),
        agent_id=str(trace.get("agentId") or payload.get("agentId") or payload.get("npcId") or ""),
        target_ids=target_ids,
    )
    return {
        "eventId": event.get("id"),
        "createdAt": event.get("createdAt"),
        "traceSchemaVersion": TRACE_SCHEMA_VERSION,
        **envelope,
        "details": _trace_event_details(event_type, payload),
    }


def _trace_event_details(event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    """为观察者面板提供轻量可展开字段，避免返回完整事件 payload。"""
    if event_type == "motivation.decision_made":
        primary_need = payload.get("primaryNeed") if isinstance(payload.get("primaryNeed"), dict) else {}
        return {
            "npcId": payload.get("npcId"),
            "needId": primary_need.get("needId"),
            "urgency": primary_need.get("urgency"),
            "selectedToolId": payload.get("selectedToolId"),
            "decisionReason": payload.get("decisionReason"),
            "capabilityCount": payload.get("capabilityCount"),
            "capabilityFilters": _compact_capability_filters(payload.get("capabilityFilters")),
            "subjectiveMemoryRecall": _compact_subjective_memory_recall(payload.get("subjectiveMemoryRecall")),
            "heuristicRecall": _compact_heuristic_recall(payload.get("heuristicRecall")),
            "candidateScores": _compact_list(payload.get("candidateScores"), 5),
            "relationshipEdgeRefs": _compact_list(payload.get("relationshipEdgeRefs"), 4),
            "subjectiveMemoryRefs": _compact_list(payload.get("subjectiveMemoryRefs"), 4),
            "heuristicRefs": _compact_list(payload.get("heuristicRefs"), 4),
            "contributingSources": _compact_list(payload.get("contributingSources"), 6),
        }
    if event_type in {"tool.execution_completed", "tool.execution_failed", "tool.execution_interrupted"}:
        return {
            "npcId": payload.get("npcId"),
            "toolId": payload.get("toolId"),
            "interruptedToolId": payload.get("interruptedToolId"),
            "replacementToolId": payload.get("replacementToolId"),
            "targetNpcId": payload.get("targetNpcId"),
            "targetAnchorId": payload.get("targetAnchorId"),
            "targetLocationId": payload.get("targetLocationId"),
            "replacementTargetAnchorId": payload.get("replacementTargetAnchorId"),
            "replacementTargetLocationId": payload.get("replacementTargetLocationId"),
            "reason": payload.get("reason"),
            "interruptUrgency": payload.get("interruptUrgency"),
            "interruptPriorityThreshold": payload.get("interruptPriorityThreshold"),
            "worldEffectCount": len(payload.get("worldEffects", [])) if isinstance(payload.get("worldEffects"), list) else 0,
            "sourceEventIds": _compact_list(payload.get("sourceEventIds"), 4),
            "traceRefs": _compact_list(payload.get("traceRefs"), 6),
        }
    if event_type == "memory.result_observed":
        heuristic = payload.get("heuristic") if isinstance(payload.get("heuristic"), dict) else None
        return {
            "sourceEventId": payload.get("sourceEventId"),
            "observerVisibility": payload.get("observerVisibility"),
            "observerCount": payload.get("observerCount"),
            "observerScope": _compact_observer_scope(payload.get("observerScope")),
            "observers": _compact_list(payload.get("observers"), 8),
            "memoryCount": len(payload.get("memories", [])) if isinstance(payload.get("memories"), list) else 0,
            "relationshipEdgeCount": len(payload.get("relationshipEdges", [])) if isinstance(payload.get("relationshipEdges"), list) else 0,
            "heuristicId": heuristic.get("heuristicId") if heuristic else None,
        }
    if event_type in {"budget.decision_consumed", "budget.decision_fallback"}:
        return {
            "version": payload.get("version"),
            "npcId": payload.get("npcId"),
            "toolId": payload.get("toolId"),
            "channel": payload.get("channel"),
            "feature": payload.get("feature"),
            "route": payload.get("route"),
            "reason": payload.get("reason"),
            "cost": payload.get("cost"),
            "unit": payload.get("unit"),
            "consumedDelta": payload.get("consumedDelta"),
            "remaining": payload.get("remaining"),
            "remainingBefore": payload.get("remainingBefore"),
            "featureRemaining": payload.get("featureRemaining"),
            "featureRemainingBefore": payload.get("featureRemainingBefore"),
            "costBreakdown": _compact_cost_breakdown(payload.get("costBreakdown")),
            "sourceEventIds": _compact_list(payload.get("sourceEventIds"), 4),
            "traceRefs": _compact_list(payload.get("traceRefs"), 6),
        }
    return {}


def _compact_list(value: Any, limit: int) -> list[Any]:
    if not isinstance(value, list):
        return []
    compacted = []
    for item in value[:limit]:
        compacted.append(deepcopy(item) if isinstance(item, (dict, list)) else item)
    return compacted


def _compact_capability_filters(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    layers = value.get("layers") if isinstance(value.get("layers"), list) else []
    return {
        "version": value.get("version"),
        "allowedToolIds": _compact_list(value.get("allowedToolIds"), 8),
        "layers": [
            {
                "layer": layer.get("layer"),
                "inputCount": layer.get("inputCount"),
                "allowedCount": layer.get("allowedCount"),
                "rejectedCount": layer.get("rejectedCount"),
                "sampleDecisions": _compact_list(layer.get("decisions"), 3),
            }
            for layer in layers[:6]
            if isinstance(layer, dict)
        ],
    }


def _compact_subjective_memory_recall(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {
        "version": value.get("version"),
        "query": value.get("query"),
        "worldTick": value.get("worldTick"),
        "count": value.get("count"),
        "activeCount": value.get("activeCount"),
        "recordIds": _compact_list(value.get("recordIds"), 6),
        "sourceEventIds": _compact_list(value.get("sourceEventIds"), 6),
        "recordSalience": _compact_list(value.get("recordSalience"), 6),
    }


def _compact_heuristic_recall(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {
        "version": value.get("version"),
        "worldTick": value.get("worldTick"),
        "count": value.get("count"),
        "activeCount": value.get("activeCount"),
        "heuristicIds": _compact_list(value.get("heuristicIds"), 6),
        "sourceEventIds": _compact_list(value.get("sourceEventIds"), 6),
    }


def _compact_observer_scope(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {
        "version": value.get("version"),
        "visibility": value.get("visibility"),
        "actorId": value.get("actorId"),
        "participantIds": _compact_list(value.get("participantIds"), 8),
        "locationId": value.get("locationId"),
        "eventAnchorId": value.get("eventAnchorId"),
        "locationObserverIds": _compact_list(value.get("locationObserverIds"), 10),
        "spatialModel": _compact_spatial_model(value.get("spatialModel")),
        "spatialEvidence": _compact_spatial_evidence(value.get("spatialEvidence"), 10),
        "observerIds": _compact_list(value.get("observerIds"), 10),
        "excludedObserverIds": _compact_list(value.get("excludedObserverIds"), 10),
    }


def _compact_spatial_model(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {
        "version": value.get("version"),
        "distanceUnit": value.get("distanceUnit"),
        "hearingRadius": value.get("hearingRadius"),
    }


def _compact_spatial_evidence(value: Any, limit: int) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    compacted: list[dict[str, Any]] = []
    for item in value[:limit]:
        if not isinstance(item, dict):
            continue
        compacted.append(
            {
                "observerId": item.get("observerId"),
                "observerLocationId": item.get("observerLocationId"),
                "observerAnchorId": item.get("observerAnchorId"),
                "sameLocation": item.get("sameLocation"),
                "distanceToEvent": item.get("distanceToEvent"),
                "distanceBand": item.get("distanceBand"),
                "isActor": item.get("isActor"),
                "isParticipant": item.get("isParticipant"),
                "visible": item.get("visible"),
                "reason": item.get("reason"),
            }
        )
    return compacted


def _compact_cost_breakdown(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    return {
        "unit": value.get("unit"),
        "baseCost": value.get("baseCost"),
        "estimatedPromptTokens": value.get("estimatedPromptTokens"),
        "estimatedCompletionTokens": value.get("estimatedCompletionTokens"),
        "estimatedTotalTokens": value.get("estimatedTotalTokens"),
        "llmEligible": value.get("llmEligible"),
    }


def _normalize_target_ids(target_ids: Any) -> list[str]:
    if not isinstance(target_ids, list):
        return []
    normalized: list[str] = []
    for item in target_ids:
        value = str(item or "").strip()
        if value and value not in normalized:
            normalized.append(value)
    return normalized


def _normalize_world_time(world_time: Any) -> dict[str, Any]:
    if not isinstance(world_time, dict):
        return {}
    return {
        "tick": int(world_time.get("tick", 0)),
        "day": int(world_time.get("day", 1)),
        "hour": int(world_time.get("hour", 8)),
        "minute": int(world_time.get("minute", 0)),
        "phase": str(world_time.get("phase") or "morning"),
    }


def _none_if_empty(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _first_source_event_id(payload: dict[str, Any]) -> str | None:
    source_event_ids = payload.get("sourceEventIds")
    if isinstance(source_event_ids, list):
        for event_id in source_event_ids:
            text = _none_if_empty(event_id)
            if text:
                return text
    return None


def _derive_target_ids(payload: dict[str, Any]) -> list[str]:
    target_ids: list[str] = []
    direct_target = _none_if_empty(payload.get("targetNpcId"))
    if direct_target:
        target_ids.append(direct_target)
    observers = payload.get("observers")
    if isinstance(observers, list):
        for observer in observers:
            observer_id = _none_if_empty(observer)
            if observer_id and observer_id not in target_ids:
                target_ids.append(observer_id)
    return target_ids


def _span_from_event_id(event_id: Any) -> str | None:
    text = _none_if_empty(event_id)
    if not text:
        return None
    suffix = text.replace("evt_", "")[-16:]
    return f"span_{suffix}"
