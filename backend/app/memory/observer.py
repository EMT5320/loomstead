from __future__ import annotations

from typing import Any

from app.memory.heuristic import HeuristicLibrary
from app.memory.memory_store import remember
from app.memory.relationship_edges import RelationshipEdgeStore
from app.memory.subjective_memory import SubjectiveMemoryRecord, SubjectiveMemoryStore
from app.runtime.trace_schema import build_trace_envelope, with_trace_payload, world_time_payload


class BiasFilter:
    """首版主观滤镜：按观察者关系、工具类型和执行状态生成情绪色彩。"""

    def build_record(self, *, observer_id: str, world: dict[str, Any], event: dict[str, Any]) -> SubjectiveMemoryRecord:
        payload = event.get("payload", {}) if isinstance(event.get("payload"), dict) else {}
        event_type = str(event.get("type") or "")
        actor_id = str(payload.get("npcId") or "")
        tool_id = str(payload.get("toolId") or "")
        summary = str(payload.get("summary") or payload.get("reason") or tool_id).rstrip("。.!！")
        valence = self._valence(observer_id=observer_id, actor_id=actor_id, tool_id=tool_id, event_type=event_type)
        text = self._memory_text(observer_id=observer_id, actor_id=actor_id, tool_id=tool_id, summary=summary, valence=valence, world=world)
        return SubjectiveMemoryRecord(
            record_id=f"{event.get('id')}:{observer_id}",
            agent_id=observer_id,
            source_event_id=str(event.get("id") or ""),
            perspective="subjective",
            text=text,
            emotional_valence=valence,
            confidence=0.72 if observer_id != actor_id else 0.9,
            tags=("tool_result", tool_id, event_type),
        )

    def _valence(self, *, observer_id: str, actor_id: str, tool_id: str, event_type: str) -> float:
        if event_type == "tool.execution_failed":
            return -0.55
        if observer_id == actor_id:
            return 0.25
        if tool_id.startswith("social."):
            return 0.35
        if tool_id.startswith("strategic."):
            return -0.15
        return 0.08

    def _memory_text(self, *, observer_id: str, actor_id: str, tool_id: str, summary: str, valence: float, world: dict[str, Any]) -> str:
        observer_name = world.get("agents", {}).get(observer_id, {}).get("name", observer_id)
        actor_name = world.get("agents", {}).get(actor_id, {}).get("name", actor_id)
        tone = "留下了积极印象" if valence > 0.2 else ("让我有些警惕" if valence < -0.1 else "成为一条可回想的线索")
        if observer_id == actor_id:
            return f"{observer_name} 记得自己完成了 {tool_id}：{summary}。这件事{tone}。"
        return f"{observer_name} 注意到 {actor_name} 完成了 {tool_id}：{summary}。这件事{tone}。"


class ResultObserver:
    """把 ToolExecutor 的客观结果分发为在场 NPC 的主观记忆与关系证据。"""

    def __init__(self, bias_filter: BiasFilter | None = None) -> None:
        self.bias_filter = bias_filter or BiasFilter()

    def distribute(
        self,
        *,
        world: dict[str, Any],
        event: dict[str, Any],
        subjective_memory: SubjectiveMemoryStore,
        relationship_edges: RelationshipEdgeStore,
        heuristic_library: HeuristicLibrary,
    ) -> dict[str, Any]:
        observer_ids = self._observer_ids(world, event)
        memory_items = []
        for observer_id in observer_ids:
            record = self.bias_filter.build_record(observer_id=observer_id, world=world, event=event)
            subjective_memory.add(record)
            memory_items.append(record.to_dict())
            agent = world.get("agents", {}).get(observer_id)
            if isinstance(agent, dict):
                # 同步一条短记忆到旧 memory list，保证现有 RAG-lite 和 Debug 页面继续能看到新证据。
                remember(agent, record.text, tick=int(world.get("clock", {}).get("tick", 0)), importance=0.58, tags=["subjective", "tool_result"])

        relationship_items = [edge.to_dict() for edge in relationship_edges.apply_tool_event(world, event)]
        heuristic = heuristic_library.extract_from_event(event)
        payload = {
            "sourceEventId": event.get("id"),
            "observers": observer_ids,
            "memories": memory_items,
            "relationshipEdges": relationship_items,
            "heuristic": heuristic.to_dict() if heuristic else None,
        }
        source_payload = event.get("payload", {}) if isinstance(event.get("payload"), dict) else {}
        summary = f"观察到 {len(memory_items)} 条主观记忆，{len(relationship_items)} 条关系边"
        return with_trace_payload(
            payload,
            build_trace_envelope(
                event_type="memory.result_observed",
                summary=summary,
                world_time=world_time_payload(world),
                trace_id=str(source_payload.get("traceId") or event.get("id") or ""),
                source_event_id=str(event.get("id") or ""),
                agent_id=str(source_payload.get("agentId") or source_payload.get("npcId") or ""),
                target_ids=[str(observer_id) for observer_id in observer_ids],
            ),
        )

    def _observer_ids(self, world: dict[str, Any], event: dict[str, Any]) -> list[str]:
        payload = event.get("payload", {}) if isinstance(event.get("payload"), dict) else {}
        actor_id = str(payload.get("npcId") or "")
        target_id = str(payload.get("targetNpcId") or "")
        visibility = str(payload.get("observerVisibility") or "participants_only")
        location_id = str(payload.get("targetLocationId") or world.get("agents", {}).get(actor_id, {}).get("locationId") or "")
        observers: set[str] = set()
        if actor_id:
            observers.add(actor_id)
        if target_id:
            observers.add(target_id)
        if visibility == "all_in_location" and location_id:
            for presence in world.get("npcPresence", []):
                if isinstance(presence, dict) and str(presence.get("locationId") or "") == location_id:
                    observers.add(str(presence.get("agentId") or ""))
        return sorted(observer_id for observer_id in observers if observer_id in world.get("agents", {}))
