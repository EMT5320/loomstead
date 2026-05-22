from __future__ import annotations

from dataclasses import dataclass
from typing import Any

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


class NeedAccumulator:
    """Phase 2 需求累积器：把状态、NPC 深度卡和 Director 偏置合成为需求分数。"""

    def score(self, world: dict[str, Any], agent: dict[str, Any], delta_minutes: float) -> list[NeedScore]:
        status = agent.get("status", {}) if isinstance(agent.get("status"), dict) else {}
        profile = agent.get("deepCard", {}).get("motivationProfile", {}) if isinstance(agent.get("deepCard"), dict) else {}
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
            weight = self._need_weight(profile, need_id)
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

    def debug_snapshot(self, world: dict[str, Any], npc_ids: list[str], delta_minutes: float = 20.0) -> dict[str, Any]:
        """输出独立需求快照，方便 Debug Console 解释 MotivationEngine 之前的来源。"""
        items: list[dict[str, Any]] = []
        for npc_id in npc_ids:
            agent = world.get("agents", {}).get(npc_id)
            if not isinstance(agent, dict):
                continue
            scores = sorted(self.score(world, agent, delta_minutes), key=lambda item: item.urgency, reverse=True)
            items.append({"npcId": npc_id, "npcName": agent.get("name", npc_id), "needs": [score.to_dict() for score in scores]})
        return {"version": "need_accumulator.v0", "items": items}

    def _need_weight(self, profile: Any, need_id: str) -> float:
        """读取深度卡 motivationProfile.needs.<need>.weight；兼容早期 weights 占位。"""
        if not isinstance(profile, dict):
            return 1.0
        needs = profile.get("needs", {}) if isinstance(profile.get("needs"), dict) else {}
        need_config = needs.get(need_id)
        if isinstance(need_config, dict) and need_config.get("weight") is not None:
            return self._safe_weight(need_config.get("weight"))
        legacy_weights = profile.get("weights", {}) if isinstance(profile.get("weights"), dict) else {}
        if legacy_weights.get(need_id) is not None:
            return self._safe_weight(legacy_weights.get(need_id))
        return 1.0

    def _safe_weight(self, value: Any) -> float:
        try:
            return max(0.0, float(value))
        except (TypeError, ValueError):
            return 1.0

    def _director_bias(self, world: dict[str, Any], npc_id: str) -> dict[str, float]:
        active_focus = world.get("activeFocus") if isinstance(world.get("activeFocus"), dict) else {}
        target_agents = {str(agent_id) for agent_id in active_focus.get("targetAgents", [])}
        if npc_id and npc_id in target_agents:
            return {"affiliation": 0.3, "recognition": 0.2}
        return {}
