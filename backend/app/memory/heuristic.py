from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

HeuristicStatus = Literal["active", "dormant"]
HEURISTIC_DECAY_PER_TICK = 0.01
HEURISTIC_MIN_DECAY_FACTOR = 0.25


@dataclass(frozen=True)
class HeuristicMemory:
    heuristic_id: str
    agent_id: str
    trigger_pattern: str
    adjustment: dict[str, Any]
    confidence: float
    source_event_id: str | None
    status: HeuristicStatus = "active"
    created_tick: int | None = None
    updated_tick: int | None = None

    def to_dict(self, world_tick: int | None = None) -> dict[str, Any]:
        return {
            "heuristicId": self.heuristic_id,
            "agentId": self.agent_id,
            "triggerPattern": self.trigger_pattern,
            "adjustment": dict(self.adjustment),
            "confidence": round(self.confidence, 4),
            "effectiveConfidence": round(self.effective_confidence(world_tick), 4),
            "sourceEventId": self.source_event_id,
            "status": self.status,
            "createdTick": self.created_tick,
            "updatedTick": self.updated_tick,
        }

    def effective_confidence(self, world_tick: int | None = None) -> float:
        if world_tick is None or self.updated_tick is None:
            return max(0.0, min(1.0, self.confidence))
        age_ticks = max(0, int(world_tick) - int(self.updated_tick))
        decay_factor = max(HEURISTIC_MIN_DECAY_FACTOR, 1.0 - float(age_ticks) * HEURISTIC_DECAY_PER_TICK)
        return max(0.0, min(1.0, self.confidence * decay_factor))


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
        world_tick = self._event_tick(event)
        if not npc_id or not tool_id:
            return None

        if event_type == "tool.execution_failed":
            return self.add(
                agent_id=npc_id,
                trigger_pattern=f"avoid_failed_tool:{tool_id}",
                adjustment={"toolId": tool_id, "weightDelta": -0.15},
                confidence=0.65,
                source_event_id=source_event_id,
                world_tick=world_tick,
            )
        if event_type == "tool.execution_interrupted":
            return self.add(
                agent_id=npc_id,
                trigger_pattern=f"avoid_interrupted_tool:{tool_id}",
                adjustment={"toolId": tool_id, "weightDelta": -0.08},
                confidence=0.5,
                source_event_id=source_event_id,
                world_tick=world_tick,
            )
        if tool_id.startswith("social.") and event_type == "tool.execution_completed":
            self.add(
                agent_id=npc_id,
                trigger_pattern="prefer_social_when_affiliation_high",
                adjustment={"needId": "affiliation", "weightDelta": 0.05},
                confidence=0.45,
                source_event_id=source_event_id,
                world_tick=world_tick,
            )
        if event_type == "tool.execution_completed":
            return self.add(
                agent_id=npc_id,
                trigger_pattern=f"prefer_successful_tool:{tool_id}",
                adjustment={"toolId": tool_id, "weightDelta": 0.03},
                confidence=0.4,
                source_event_id=source_event_id,
                world_tick=world_tick,
            )
        return None

    def add(self, *, agent_id: str, trigger_pattern: str, adjustment: dict[str, Any], confidence: float, source_event_id: str | None, world_tick: int | None = None) -> HeuristicMemory:
        heuristic_id = f"{agent_id}:{trigger_pattern}"
        existing = self._items.get(heuristic_id)
        created_tick = existing.created_tick if existing else world_tick
        item = HeuristicMemory(
            heuristic_id=heuristic_id,
            agent_id=agent_id,
            trigger_pattern=trigger_pattern,
            adjustment=dict(adjustment),
            confidence=max(0.0, min(1.0, max(confidence, existing.confidence if existing else 0.0))),
            source_event_id=source_event_id,
            status="active",
            created_tick=created_tick,
            updated_tick=world_tick,
        )
        self._items[heuristic_id] = item
        return item

    def list(self, agent_id: str | None = None, limit: int = 20) -> list[HeuristicMemory]:
        items = [item for item in self._items.values() if agent_id is None or item.agent_id == agent_id]
        items.sort(key=lambda item: (item.confidence, item.heuristic_id), reverse=True)
        return items[:limit]

    def debug_snapshot(self, agent_id: str | None = None, limit: int = 20, world_tick: int | None = None) -> dict[str, Any]:
        items = self.list(agent_id=agent_id, limit=limit)
        return {
            "version": "heuristic_library.v0",
            "agentId": agent_id,
            "worldTick": world_tick,
            "count": len(items),
            "items": [item.to_dict(world_tick=world_tick) for item in items],
        }

    def _event_tick(self, event: dict[str, Any]) -> int | None:
        payload = event.get("payload", {}) if isinstance(event.get("payload"), dict) else {}
        world_time = payload.get("worldTime") if isinstance(payload.get("worldTime"), dict) else {}
        try:
            return int(world_time.get("tick"))
        except (TypeError, ValueError):
            return None
