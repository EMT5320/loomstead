from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from app.runtime.schema_registry import require_schema_version
from app.world.world_state import relation_key

RelationshipEdgeType = Literal["affection", "trust", "conflict", "respect", "suspicion"]


@dataclass
class RelationshipEdge:
    source_agent_id: str
    target_agent_id: str
    edge_type: RelationshipEdgeType
    strength: float
    first_seen_tick: int
    updated_tick: int
    source_event_ids: list[str] = field(default_factory=list)
    trace_refs: list[dict[str, Any]] = field(default_factory=list)

    @property
    def edge_id(self) -> str:
        return f"{relation_key(self.source_agent_id, self.target_agent_id)}::{self.edge_type}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "edgeId": self.edge_id,
            "sourceAgentId": self.source_agent_id,
            "targetAgentId": self.target_agent_id,
            "edgeType": self.edge_type,
            "strength": round(self.strength, 4),
            "firstSeenTick": self.first_seen_tick,
            "updatedTick": self.updated_tick,
            "sourceEventIds": list(self.source_event_ids),
            "traceRefs": [dict(ref) for ref in self.trace_refs],
        }


class RelationshipEdgeStore:
    """Phase 2 关系边存储：为关系变化保留 source_event_ids 与 trace_refs。"""

    def __init__(self) -> None:
        self._edges: dict[str, RelationshipEdge] = {}

    def upsert(
        self,
        *,
        source_agent_id: str,
        target_agent_id: str,
        edge_type: RelationshipEdgeType,
        delta: float,
        tick: int,
        source_event_id: str | None,
        trace_refs: list[dict[str, Any]] | None = None,
    ) -> RelationshipEdge:
        key = f"{relation_key(source_agent_id, target_agent_id)}::{edge_type}"
        edge = self._edges.get(key)
        if edge is None:
            edge = RelationshipEdge(
                source_agent_id=source_agent_id,
                target_agent_id=target_agent_id,
                edge_type=edge_type,
                strength=0.5,
                first_seen_tick=tick,
                updated_tick=tick,
            )
            self._edges[key] = edge
        edge.strength = max(0.0, min(1.0, edge.strength + delta))
        edge.updated_tick = tick
        if source_event_id and source_event_id not in edge.source_event_ids:
            edge.source_event_ids.append(source_event_id)
        if trace_refs:
            edge.trace_refs.extend(dict(ref) for ref in trace_refs)
            edge.trace_refs = edge.trace_refs[-8:]
        return edge

    def apply_tool_event(self, world: dict[str, Any], event: dict[str, Any]) -> list[RelationshipEdge]:
        """根据工具执行事件提取首版关系边，复杂信念模型放到后续阶段。"""
        payload = event.get("payload", {}) if isinstance(event.get("payload"), dict) else {}
        npc_id = str(payload.get("npcId") or "")
        target_id = str(payload.get("targetNpcId") or "")
        tool_id = str(payload.get("toolId") or "")
        if not npc_id or not target_id or npc_id == target_id:
            return []

        tick = int(world.get("clock", {}).get("tick", 0))
        source_event_id = str(event.get("id") or "")
        trace_refs = [dict(ref) for ref in payload.get("traceRefs", []) if isinstance(ref, dict)]
        changes: list[tuple[RelationshipEdgeType, float]]
        if tool_id == "social.give_gift":
            changes = [("affection", 0.04), ("trust", 0.02)]
        elif tool_id == "social.chat_with":
            changes = [("affection", 0.03), ("trust", 0.02), ("conflict", -0.01)]
        elif tool_id == "strategic.spread_rumor":
            changes = [("suspicion", 0.04)]
        else:
            changes = [("respect", 0.01)]
        return [
            self.upsert(
                source_agent_id=npc_id,
                target_agent_id=target_id,
                edge_type=edge_type,
                delta=delta,
                tick=tick,
                source_event_id=source_event_id,
                trace_refs=trace_refs,
            )
            for edge_type, delta in changes
        ]

    def list(self, agent_id: str | None = None, limit: int = 30) -> list[RelationshipEdge]:
        items = [
            edge
            for edge in self._edges.values()
            if agent_id is None or edge.source_agent_id == agent_id or edge.target_agent_id == agent_id
        ]
        items.sort(key=lambda edge: (edge.updated_tick, edge.edge_id), reverse=True)
        return items[:limit]

    def debug_snapshot(self, agent_id: str | None = None, limit: int = 30) -> dict[str, Any]:
        items = self.list(agent_id=agent_id, limit=limit)
        return {"version": require_schema_version("relationship_edge_store"), "agentId": agent_id, "count": len(items), "items": [edge.to_dict() for edge in items]}
