from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Literal

from app.runtime.schema_registry import require_schema_version

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
    source_kind: str = "observed_event"
    narrative: str | None = None

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
            "sourceKind": self.source_kind,
            "narrative": self.narrative,
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

    def add(
        self,
        *,
        agent_id: str,
        trigger_pattern: str,
        adjustment: dict[str, Any],
        confidence: float,
        source_event_id: str | None,
        world_tick: int | None = None,
        heuristic_id: str | None = None,
        source_kind: str = "observed_event",
        narrative: str | None = None,
    ) -> HeuristicMemory:
        heuristic_id = heuristic_id or f"{agent_id}:{trigger_pattern}"
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
            source_kind=source_kind,
            narrative=narrative,
        )
        self._items[heuristic_id] = item
        return item

    def inject_designer_seeds(self, *, agent_id: str, seeds: Iterable[Any], world_tick: int | None = None) -> list[HeuristicMemory]:
        """把 NPC 深度卡中的设计师启发式种子注入运行时库。"""
        injected: list[HeuristicMemory] = []
        for seed in seeds:
            seed_id = self._seed_value(seed, "heuristic_id", "heuristicId", "id")
            adjustment = self._normalize_adjustment(self._seed_value(seed, "adjustment"))
            if not seed_id or not adjustment or adjustment.get("weightDelta") is None:
                continue
            trigger_pattern = self._designer_trigger_pattern(seed_id, self._seed_value(seed, "trigger_pattern", "triggerPattern"))
            item = self.add(
                agent_id=agent_id,
                heuristic_id=f"{agent_id}:designer:{seed_id}",
                trigger_pattern=trigger_pattern,
                adjustment=adjustment,
                confidence=self._safe_float(self._seed_value(seed, "confidence"), 0.5),
                source_event_id=f"designer_seed:{agent_id}:{seed_id}",
                world_tick=world_tick,
                source_kind="designer_seed",
                narrative=str(self._seed_value(seed, "narrative") or ""),
            )
            injected.append(item)
        return injected

    def list(self, agent_id: str | None = None, limit: int = 20) -> list[HeuristicMemory]:
        items = [item for item in self._items.values() if agent_id is None or item.agent_id == agent_id]
        items.sort(key=lambda item: (item.confidence, item.heuristic_id), reverse=True)
        return items[:limit]

    def debug_snapshot(self, agent_id: str | None = None, limit: int = 20, world_tick: int | None = None) -> dict[str, Any]:
        items = self.list(agent_id=agent_id, limit=limit)
        return {
            "version": require_schema_version("heuristic_library"),
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

    def _seed_value(self, seed: Any, *names: str) -> Any:
        for name in names:
            if isinstance(seed, dict) and name in seed:
                return seed.get(name)
            if hasattr(seed, name):
                return getattr(seed, name)
        return None

    def _normalize_adjustment(self, raw: Any) -> dict[str, Any]:
        if not isinstance(raw, dict):
            return {}
        normalized = dict(raw)
        aliases = {"tool_id": "toolId", "need_id": "needId", "weight_delta": "weightDelta"}
        for source_key, target_key in aliases.items():
            if source_key in normalized and target_key not in normalized:
                normalized[target_key] = normalized[source_key]
        if normalized.get("toolId") is not None:
            normalized["toolId"] = str(normalized.get("toolId"))
        if normalized.get("needId") is not None:
            normalized["needId"] = str(normalized.get("needId"))
        if normalized.get("weightDelta") is not None:
            normalized["weightDelta"] = self._safe_number(normalized.get("weightDelta"), 0.0)
        if not normalized.get("toolId") and not normalized.get("needId"):
            return {}
        return {key: value for key, value in normalized.items() if key in {"toolId", "needId", "weightDelta"}}

    def _designer_trigger_pattern(self, seed_id: str, trigger_pattern: Any) -> str:
        if isinstance(trigger_pattern, dict):
            need_id = str(trigger_pattern.get("needId") or trigger_pattern.get("need_id") or "")
            tool_id = str(trigger_pattern.get("toolId") or trigger_pattern.get("tool_id") or "")
            parts = [f"designer_seed:{seed_id}"]
            if need_id:
                parts.append(f"need={need_id}")
            if tool_id:
                parts.append(f"tool={tool_id}")
            return "|".join(parts)
        return f"designer_seed:{seed_id}"

    def _safe_float(self, value: Any, fallback: float) -> float:
        try:
            return max(0.0, min(1.0, float(value)))
        except (TypeError, ValueError):
            return fallback

    def _safe_number(self, value: Any, fallback: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return fallback
