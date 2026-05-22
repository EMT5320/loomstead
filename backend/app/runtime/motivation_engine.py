from __future__ import annotations

from typing import Any

from app.runtime.arbitration import ArbitrationInput, ArbitrationLayer
from app.runtime.capability_registry import CapabilityRegistry
from app.runtime.need_accumulator import NeedAccumulator


class MotivationEngine:
    def __init__(self, capability_registry: CapabilityRegistry | None = None, arbitration_layer: ArbitrationLayer | None = None, need_accumulator: NeedAccumulator | None = None) -> None:
        self.capability_registry = capability_registry or CapabilityRegistry()
        self.arbitration_layer = arbitration_layer or ArbitrationLayer()
        self.need_accumulator = need_accumulator or NeedAccumulator()

    def evaluate_npc(
        self,
        world: dict[str, Any],
        npc_id: str,
        delta_minutes: float = 20.0,
        relationship_edges: list[dict[str, Any]] | None = None,
        subjective_memory_records: list[dict[str, Any]] | None = None,
        heuristics: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        agent = world.get("agents", {}).get(npc_id)
        if not isinstance(agent, dict):
            return {"npcId": npc_id, "decision": None, "reason": "unknown_npc"}
        relationship_edges = relationship_edges or []
        subjective_memory_records = [dict(item) for item in subjective_memory_records or [] if isinstance(item, dict)]
        heuristics = [dict(item) for item in heuristics or [] if isinstance(item, dict)]
        world_tick = int(world.get("clock", {}).get("tick", 0)) if isinstance(world.get("clock"), dict) else 0
        needs = self.need_accumulator.score(world, agent, delta_minutes)
        primary_need = max(needs, key=lambda need: need.urgency)
        capability_resolution = self.capability_registry.resolve_with_debug(world, npc_id, primary_need.need_id)
        candidates = list(capability_resolution.allowed_tools)
        decision = self.arbitration_layer.decide(
            ArbitrationInput(
                npc_id=npc_id,
                need_id=primary_need.need_id,
                urgency=primary_need.urgency,
                candidates=tuple(candidates),
                contributing_sources=primary_need.sources,
                relationship_edges=tuple(relationship_edges),
                subjective_memories=tuple(subjective_memory_records),
                heuristics=tuple(heuristics),
                decision_budgets=capability_resolution.decision_budgets,
                world_tick=world_tick,
            )
        )
        return {
            "npcId": npc_id,
            "npcName": agent.get("name", npc_id),
            "decisionIntervalMinutes": delta_minutes,
            "primaryNeed": primary_need.to_dict(),
            "needs": [need.to_dict() for need in sorted(needs, key=lambda item: item.urgency, reverse=True)],
            "capabilities": [tool.to_dict() for tool in candidates],
            "capabilityFilters": capability_resolution.to_debug_dict(),
            "subjectiveMemoryRecall": self._subjective_memory_recall_debug(subjective_memory_records),
            "heuristicRecall": self._heuristic_recall_debug(heuristics, world_tick),
            "decision": decision.to_dict(),
        }

    def debug_snapshot(self, world: dict[str, Any], npc_ids: list[str] | None = None, limit: int = 6) -> dict[str, Any]:
        candidate_ids = npc_ids or list(world.get("agents", {}).keys())[:limit]
        items = [self.evaluate_npc(world, npc_id) for npc_id in candidate_ids[:limit]]
        return {"version": "motivation_engine.v0", "items": items}

    def _subjective_memory_recall_debug(self, records: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "version": "subjective_memory_recall.v1",
            "query": "tool_result",
            "count": len(records),
            "recordIds": [str(item.get("recordId") or "") for item in records[:8] if str(item.get("recordId") or "")],
            "sourceEventIds": [str(item.get("sourceEventId") or "") for item in records[:8] if str(item.get("sourceEventId") or "")],
        }

    def _heuristic_recall_debug(self, heuristics: list[dict[str, Any]], world_tick: int) -> dict[str, Any]:
        active_items = [item for item in heuristics if str(item.get("status") or "active") == "active"]
        return {
            "version": "heuristic_recall.v1",
            "worldTick": world_tick,
            "count": len(heuristics),
            "activeCount": len(active_items),
            "heuristicIds": [str(item.get("heuristicId") or "") for item in active_items[:8] if str(item.get("heuristicId") or "")],
            "sourceEventIds": [str(item.get("sourceEventId") or "") for item in active_items[:8] if str(item.get("sourceEventId") or "")],
        }
