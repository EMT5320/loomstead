from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

HeuristicStatus = Literal["active", "dormant"]


@dataclass(frozen=True)
class HeuristicMemory:
    heuristic_id: str
    agent_id: str
    trigger_pattern: str
    adjustment: dict[str, Any]
    confidence: float
    source_event_id: str | None
    status: HeuristicStatus = "active"

    def to_dict(self) -> dict[str, Any]:
        return {
            "heuristicId": self.heuristic_id,
            "agentId": self.agent_id,
            "triggerPattern": self.trigger_pattern,
            "adjustment": dict(self.adjustment),
            "confidence": round(self.confidence, 4),
            "sourceEventId": self.source_event_id,
            "status": self.status,
        }


class HeuristicLibrary:
    """Phase 2 启发式库骨架：先用规则抽取，后续再接 LLM 提炼。"""

    def __init__(self) -> None:
        self._items: dict[str, HeuristicMemory] = {}

    def extract_from_event(self, event: dict[str, Any]) -> HeuristicMemory | None:
        payload = event.get("payload", {}) if isinstance(event.get("payload"), dict) else {}
        event_type = str(event.get("type") or "")
        npc_id = str(payload.get("npcId") or "")
        tool_id = str(payload.get("toolId") or "")
        source_event_id = str(event.get("id") or "")
        if not npc_id or not tool_id:
            return None

        if event_type == "tool.execution_failed":
            return self.add(
                agent_id=npc_id,
                trigger_pattern=f"avoid_failed_tool:{tool_id}",
                adjustment={"toolId": tool_id, "weightDelta": -0.15},
                confidence=0.65,
                source_event_id=source_event_id,
            )
        if tool_id.startswith("social.") and event_type == "tool.execution_completed":
            return self.add(
                agent_id=npc_id,
                trigger_pattern="prefer_social_when_affiliation_high",
                adjustment={"needId": "affiliation", "weightDelta": 0.05},
                confidence=0.45,
                source_event_id=source_event_id,
            )
        return None

    def add(self, *, agent_id: str, trigger_pattern: str, adjustment: dict[str, Any], confidence: float, source_event_id: str | None) -> HeuristicMemory:
        heuristic_id = f"{agent_id}:{trigger_pattern}"
        item = HeuristicMemory(
            heuristic_id=heuristic_id,
            agent_id=agent_id,
            trigger_pattern=trigger_pattern,
            adjustment=dict(adjustment),
            confidence=max(0.0, min(1.0, confidence)),
            source_event_id=source_event_id,
        )
        self._items[heuristic_id] = item
        return item

    def list(self, agent_id: str | None = None, limit: int = 20) -> list[HeuristicMemory]:
        items = [item for item in self._items.values() if agent_id is None or item.agent_id == agent_id]
        items.sort(key=lambda item: (item.confidence, item.heuristic_id), reverse=True)
        return items[:limit]

    def debug_snapshot(self, agent_id: str | None = None, limit: int = 20) -> dict[str, Any]:
        items = self.list(agent_id=agent_id, limit=limit)
        return {"version": "heuristic_library.v0", "agentId": agent_id, "count": len(items), "items": [item.to_dict() for item in items]}
