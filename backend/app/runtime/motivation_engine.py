from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.runtime.arbitration import ArbitrationInput, ArbitrationLayer
from app.runtime.capability_registry import CapabilityRegistry

DEFAULT_NEEDS = ("energy", "money_anxiety", "affiliation", "recognition")


@dataclass(frozen=True)
class NeedScore:
    need_id: str
    current: float
    weight: float
    urgency: float
    sources: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "needId": self.need_id,
            "current": round(self.current, 4),
            "weight": round(self.weight, 4),
            "urgency": round(self.urgency, 4),
            "sources": [dict(source) for source in self.sources],
        }


class MotivationEngine:
    def __init__(self, capability_registry: CapabilityRegistry | None = None, arbitration_layer: ArbitrationLayer | None = None) -> None:
        self.capability_registry = capability_registry or CapabilityRegistry()
        self.arbitration_layer = arbitration_layer or ArbitrationLayer()

    def evaluate_npc(self, world: dict[str, Any], npc_id: str, delta_minutes: float = 20.0) -> dict[str, Any]:
        agent = world.get("agents", {}).get(npc_id)
        if not isinstance(agent, dict):
            return {"npcId": npc_id, "decision": None, "reason": "unknown_npc"}
        needs = self._score_needs(world, agent, delta_minutes)
        primary_need = max(needs, key=lambda need: need.urgency)
        candidates = self.capability_registry.resolve(world, npc_id, primary_need.need_id)
        decision = self.arbitration_layer.decide(
            ArbitrationInput(
                npc_id=npc_id,
                need_id=primary_need.need_id,
                urgency=primary_need.urgency,
                candidates=tuple(candidates),
                contributing_sources=primary_need.sources,
            )
        )
        return {
            "npcId": npc_id,
            "npcName": agent.get("name", npc_id),
            "decisionIntervalMinutes": delta_minutes,
            "primaryNeed": primary_need.to_dict(),
            "needs": [need.to_dict() for need in sorted(needs, key=lambda item: item.urgency, reverse=True)],
            "capabilities": [tool.to_dict() for tool in candidates],
            "decision": decision.to_dict(),
        }

    def debug_snapshot(self, world: dict[str, Any], npc_ids: list[str] | None = None, limit: int = 6) -> dict[str, Any]:
        candidate_ids = npc_ids or list(world.get("agents", {}).keys())[:limit]
        items = [self.evaluate_npc(world, npc_id) for npc_id in candidate_ids[:limit]]
        return {"version": "motivation_engine.v0", "items": items}

    def _score_needs(self, world: dict[str, Any], agent: dict[str, Any], delta_minutes: float) -> list[NeedScore]:
        status = agent.get("status", {}) if isinstance(agent.get("status"), dict) else {}
        profile = agent.get("deepCard", {}).get("motivationProfile", {}) if isinstance(agent.get("deepCard"), dict) else {}
        weights = profile.get("weights", {}) if isinstance(profile, dict) and isinstance(profile.get("weights"), dict) else {}
        base_values = {
            "energy": 1.0 - min(100.0, float(status.get("energy", 70))) / 100.0,
            "money_anxiety": 1.0 - min(100.0, float(status.get("money", 50))) / 100.0,
            "affiliation": 1.0 - min(100.0, float(status.get("social", 50))) / 100.0,
            "recognition": min(1.0, len(agent.get("todayGoals", [])) / 4.0),
        }
        director_bias = self._director_bias(world, str(agent.get("id") or ""))
        interval_bias = max(0.0, float(delta_minutes)) / 1200.0
        scores: list[NeedScore] = []
        for need_id in DEFAULT_NEEDS:
            current = max(0.0, min(1.0, base_values.get(need_id, 0.0) + interval_bias))
            weight = float(weights.get(need_id, 1.0)) if isinstance(weights, dict) else 1.0
            bias = director_bias.get(need_id, 0.0)
            urgency = current * weight + bias
            sources = (
                {"type": "status", "field": need_id, "value": round(current, 4)},
                {"type": "motivation_profile", "field": need_id, "weight": round(weight, 4)},
            )
            if bias:
                sources = (*sources, {"type": "director_bias", "field": need_id, "value": round(bias, 4)})
            scores.append(NeedScore(need_id=need_id, current=current, weight=weight, urgency=urgency, sources=sources))
        return scores

    def _director_bias(self, world: dict[str, Any], npc_id: str) -> dict[str, float]:
        active_focus = world.get("activeFocus") if isinstance(world.get("activeFocus"), dict) else {}
        target_agents = {str(agent_id) for agent_id in active_focus.get("targetAgents", [])}
        if npc_id and npc_id in target_agents:
            return {"affiliation": 0.3, "recognition": 0.2}
        return {}
