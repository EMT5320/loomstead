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
        if event_type == "tool.execution_interrupted":
            return -0.35
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
        if tool_id and summary == "higher_priority_need":
            summary = "被更紧迫的需求打断"
        verb = "中断了" if tool_id and summary == "被更紧迫的需求打断" else "完成了"
        if observer_id == actor_id:
            return f"{observer_name} 记得自己{verb} {tool_id}：{summary}。这件事{tone}。"
        return f"{observer_name} 注意到 {actor_name} {verb} {tool_id}：{summary}。这件事{tone}。"


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
        observer_scope = self._observer_scope(world, event)
        observer_ids = list(observer_scope["observerIds"])
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
            "observerVisibility": observer_scope["visibility"],
            "observerScope": observer_scope,
            "observerCount": len(observer_ids),
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
        return list(self._observer_scope(world, event)["observerIds"])

    def _observer_scope(self, world: dict[str, Any], event: dict[str, Any]) -> dict[str, Any]:
        """按工具可见性解析本次结果应分发给哪些 NPC。"""
        payload = event.get("payload", {}) if isinstance(event.get("payload"), dict) else {}
        agents = world.get("agents", {}) if isinstance(world.get("agents"), dict) else {}
        actor_id = self._clean_id(payload.get("npcId") or payload.get("agentId"))
        visibility = self._normalize_visibility(payload.get("observerVisibility"))
        participant_ids = self._participant_ids(payload, actor_id)
        location_id = self._location_id(world, payload, actor_id)
        location_observer_ids = self._location_observer_ids(world, location_id)

        observers: set[str] = set()
        if actor_id:
            observers.add(actor_id)
        if visibility == "participants_only":
            observers.update(participant_ids)
        elif visibility == "all_in_location":
            observers.update(participant_ids)
            observers.update(location_observer_ids)

        observer_ids = sorted(observer_id for observer_id in observers if observer_id in agents)
        valid_location_ids = {observer_id for observer_id in location_observer_ids if observer_id in agents}
        excluded_observer_ids = sorted(valid_location_ids - set(observer_ids))
        return {
            "version": "observer_scope.v1",
            "visibility": visibility,
            "actorId": actor_id or None,
            "participantIds": [participant_id for participant_id in participant_ids if participant_id in agents],
            "locationId": location_id or None,
            "locationObserverIds": [observer_id for observer_id in location_observer_ids if observer_id in agents],
            "observerIds": observer_ids,
            "excludedObserverIds": excluded_observer_ids,
        }

    def _participant_ids(self, payload: dict[str, Any], actor_id: str) -> list[str]:
        """从工具结果和 input 中收集明确参与者，避免只认顶层 targetNpcId。"""
        participant_ids: list[str] = []
        self._append_id(participant_ids, actor_id)
        for key in ("targetNpcId", "replacementTargetNpcId"):
            self._append_id(participant_ids, payload.get(key))
        for key in ("targetNpcIds", "targetIds", "participantIds", "participants", "relatedNpcIds"):
            self._extend_ids(participant_ids, payload.get(key))
        tool_input = payload.get("input") if isinstance(payload.get("input"), dict) else {}
        for key in ("targetNpcId", "replacementTargetNpcId"):
            self._append_id(participant_ids, tool_input.get(key))
        for key in ("targetNpcIds", "targetIds", "participantIds", "participants", "relatedNpcIds"):
            self._extend_ids(participant_ids, tool_input.get(key))
        return participant_ids

    def _location_id(self, world: dict[str, Any], payload: dict[str, Any], actor_id: str) -> str:
        for key in ("targetLocationId", "locationId"):
            location_id = self._clean_id(payload.get(key))
            if location_id:
                return location_id
        tool_input = payload.get("input") if isinstance(payload.get("input"), dict) else {}
        input_location_id = self._clean_id(tool_input.get("targetLocationId") or tool_input.get("locationId"))
        if input_location_id:
            return input_location_id
        for key in ("targetAnchorId", "anchorId"):
            location_id = self._anchor_location_id(world, self._clean_id(payload.get(key)))
            if location_id:
                return location_id
        input_anchor_id = self._clean_id(tool_input.get("targetAnchorId") or tool_input.get("anchorId"))
        location_id = self._anchor_location_id(world, input_anchor_id)
        if location_id:
            return location_id
        actor = world.get("agents", {}).get(actor_id) if actor_id else None
        return self._clean_id(actor.get("locationId")) if isinstance(actor, dict) else ""

    def _location_observer_ids(self, world: dict[str, Any], location_id: str) -> list[str]:
        if not location_id:
            return []
        observer_ids: list[str] = []
        for presence in world.get("npcPresence", []):
            if isinstance(presence, dict) and str(presence.get("locationId") or "") == location_id:
                self._append_id(observer_ids, presence.get("agentId"))
        agents = world.get("agents", {}) if isinstance(world.get("agents"), dict) else {}
        for agent_id, agent in agents.items():
            if isinstance(agent, dict) and str(agent.get("locationId") or "") == location_id:
                self._append_id(observer_ids, agent_id)
        return observer_ids

    def _anchor_location_id(self, world: dict[str, Any], anchor_id: str) -> str:
        if not anchor_id:
            return ""
        anchor = world.get("anchors", {}).get(anchor_id)
        return self._clean_id(anchor.get("locationId")) if isinstance(anchor, dict) else ""

    def _normalize_visibility(self, value: Any) -> str:
        visibility = str(value or "participants_only")
        if visibility not in {"all_in_location", "participants_only", "private"}:
            return "participants_only"
        return visibility

    def _extend_ids(self, target: list[str], value: Any) -> None:
        if isinstance(value, list):
            for item in value:
                self._append_id(target, item)
        elif isinstance(value, tuple):
            for item in value:
                self._append_id(target, item)

    def _append_id(self, target: list[str], value: Any) -> None:
        if isinstance(value, dict):
            value = value.get("agentId") or value.get("npcId") or value.get("id")
        normalized = self._clean_id(value)
        if normalized and normalized not in target:
            target.append(normalized)

    def _clean_id(self, value: Any) -> str:
        return str(value or "").strip()
