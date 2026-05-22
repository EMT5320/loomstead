from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.tools import ToolDefinition

HEURISTIC_DECAY_PER_TICK = 0.01
HEURISTIC_MIN_DECAY_FACTOR = 0.25


@dataclass(frozen=True)
class ArbitrationInput:
    npc_id: str
    need_id: str
    urgency: float
    candidates: tuple[ToolDefinition, ...]
    contributing_sources: tuple[dict[str, Any], ...]
    relationship_edges: tuple[dict[str, Any], ...] = ()
    subjective_memories: tuple[dict[str, Any], ...] = ()
    heuristics: tuple[dict[str, Any], ...] = ()
    decision_budgets: tuple[dict[str, Any], ...] = ()
    world_tick: int = 0


@dataclass(frozen=True)
class ArbitrationDecision:
    npc_id: str
    need_id: str
    selected_tool_id: str | None
    urgency: float
    candidate_tool_ids: tuple[str, ...]
    reason: str
    contributing_sources: tuple[dict[str, Any], ...]
    candidate_scores: tuple[dict[str, Any], ...] = ()
    relationship_edge_refs: tuple[dict[str, Any], ...] = ()
    subjective_memory_refs: tuple[dict[str, Any], ...] = ()
    heuristic_refs: tuple[dict[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "npcId": self.npc_id,
            "needId": self.need_id,
            "selectedToolId": self.selected_tool_id,
            "urgency": round(self.urgency, 4),
            "candidateToolIds": list(self.candidate_tool_ids),
            "reason": self.reason,
            "contributingSources": [dict(item) for item in self.contributing_sources],
            "candidateScores": [dict(item) for item in self.candidate_scores],
            "relationshipEdgeRefs": [dict(item) for item in self.relationship_edge_refs],
            "subjectiveMemoryRefs": [dict(item) for item in self.subjective_memory_refs],
            "heuristicRefs": [dict(item) for item in self.heuristic_refs],
        }


class ArbitrationLayer:
    def decide(self, arbitration_input: ArbitrationInput) -> ArbitrationDecision:
        candidates = list(arbitration_input.candidates)
        scored = self._score_candidates(
            candidates,
            arbitration_input.relationship_edges,
            arbitration_input.subjective_memories,
            arbitration_input.heuristics,
            arbitration_input.decision_budgets,
            arbitration_input.npc_id,
            arbitration_input.need_id,
            arbitration_input.world_tick,
        )
        selected_score = scored[0] if scored else None
        selected = selected_score["tool"] if selected_score else None
        relationship_refs = (
            self._relationship_refs(arbitration_input.relationship_edges, arbitration_input.npc_id)
            if selected and str(selected.tool_id).startswith("social.")
            else []
        )
        subjective_memory_refs = selected_score.get("subjectiveMemoryRefs", []) if selected_score else []
        heuristic_refs = selected_score.get("heuristicRefs", []) if selected_score else []
        contributing_sources = arbitration_input.contributing_sources
        if relationship_refs:
            contributing_sources = (
                *contributing_sources,
                {
                    "type": "relationship_edge_refs",
                    "count": len(relationship_refs),
                    "edgeIds": [ref["edgeId"] for ref in relationship_refs],
                },
            )
        if subjective_memory_refs:
            contributing_sources = (
                *contributing_sources,
                {
                    "type": "subjective_memory_refs",
                    "count": len(subjective_memory_refs),
                    "recordIds": [ref["recordId"] for ref in subjective_memory_refs],
                    "sourceEventIds": [ref["sourceEventId"] for ref in subjective_memory_refs if ref.get("sourceEventId")],
                },
            )
        if heuristic_refs:
            contributing_sources = (
                *contributing_sources,
                {
                    "type": "heuristic_refs",
                    "count": len(heuristic_refs),
                    "heuristicIds": [ref["heuristicId"] for ref in heuristic_refs],
                    "sourceEventIds": [ref["sourceEventId"] for ref in heuristic_refs if ref.get("sourceEventId")],
                },
            )
        reason = "highest_rule_tier_fit" if selected else "no_capability_available"
        if heuristic_refs and (relationship_refs or subjective_memory_refs):
            reason = "memory_and_heuristic_weighted_fit"
        elif relationship_refs and subjective_memory_refs:
            reason = "relationship_and_subjective_memory_weighted_fit"
        elif heuristic_refs:
            reason = "heuristic_weighted_fit"
        elif subjective_memory_refs:
            reason = "subjective_memory_weighted_fit"
        elif relationship_refs:
            reason = "relationship_memory_weighted_fit"
        return ArbitrationDecision(
            npc_id=arbitration_input.npc_id,
            need_id=arbitration_input.need_id,
            selected_tool_id=selected.tool_id if selected else None,
            urgency=arbitration_input.urgency,
            candidate_tool_ids=tuple(tool.tool_id for tool in candidates),
            reason=reason,
            contributing_sources=contributing_sources,
            candidate_scores=tuple(self._score_to_debug(item) for item in scored),
            relationship_edge_refs=tuple(relationship_refs),
            subjective_memory_refs=tuple(subjective_memory_refs),
            heuristic_refs=tuple(heuristic_refs),
        )

    def _select_tool(self, candidates: list[ToolDefinition]) -> ToolDefinition | None:
        if not candidates:
            return None
        tier_rank = {"physiological": 0, "vocational": 1, "social_strategic": 2}
        return sorted(candidates, key=lambda tool: (tier_rank.get(tool.tier, 99), tool.duration_seconds, tool.tool_id))[0]

    def _score_candidates(
        self,
        candidates: list[ToolDefinition],
        relationship_edges: tuple[dict[str, Any], ...],
        subjective_memories: tuple[dict[str, Any], ...],
        heuristics: tuple[dict[str, Any], ...],
        decision_budgets: tuple[dict[str, Any], ...],
        npc_id: str,
        need_id: str,
        world_tick: int,
    ) -> list[dict[str, Any]]:
        """对候选工具打分；记忆证据只影响同一需求候选内部排序，避免越权改需求。"""
        tier_rank = {"physiological": 0, "vocational": 1, "social_strategic": 2}
        relationship_strength = self._relationship_strength(relationship_edges, npc_id)
        decision_budget_by_tool = {
            str(item.get("toolId") or ""): dict(item)
            for item in decision_budgets
            if isinstance(item, dict) and item.get("toolId")
        }
        scored: list[dict[str, Any]] = []
        for tool in candidates:
            tier_score = 1.0 - float(tier_rank.get(tool.tier, 99)) * 0.1
            duration_score = max(0.0, 1.0 - float(tool.duration_seconds) / 3600.0) * 0.05
            relationship_bonus = 0.0
            if relationship_strength > 0.0 and tool.tool_id == "social.chat_with":
                relationship_bonus = 0.12 * relationship_strength
            elif relationship_strength > 0.0 and tool.tool_id == "social.give_gift":
                relationship_bonus = 0.03 * relationship_strength
            subjective_memory_refs = self._subjective_memory_refs(subjective_memories, tool.tool_id, npc_id)
            subjective_memory_bonus = self._subjective_memory_bonus(subjective_memory_refs)
            heuristic_refs = self._heuristic_refs(heuristics, tool.tool_id, need_id, npc_id, world_tick)
            heuristic_bonus = self._heuristic_bonus(heuristic_refs)
            decision_budget = decision_budget_by_tool.get(tool.tool_id, {})
            score = tier_score + duration_score + relationship_bonus + subjective_memory_bonus + heuristic_bonus
            scored.append(
                {
                    "tool": tool,
                    "score": score,
                    "tierScore": tier_score,
                    "durationScore": duration_score,
                    "relationshipBonus": relationship_bonus,
                    "subjectiveMemoryBonus": subjective_memory_bonus,
                    "subjectiveMemoryRefs": subjective_memory_refs,
                    "heuristicBonus": heuristic_bonus,
                    "heuristicRefs": heuristic_refs,
                    "decisionBudget": decision_budget,
                }
            )
        return sorted(
            scored,
            key=lambda item: (
                -float(item["score"]),
                float(item["tool"].duration_seconds),
                str(item["tool"].tool_id),
            ),
        )

    def _relationship_strength(self, relationship_edges: tuple[dict[str, Any], ...], npc_id: str) -> float:
        if not relationship_edges:
            return 0.0
        positive_edges = [
            edge
            for edge in relationship_edges
            if str(edge.get("edgeType") or "") in {"affection", "trust", "respect"} and edge.get("sourceEventIds")
            and self._edge_mentions_agent(edge, npc_id)
        ]
        if not positive_edges:
            return 0.0
        return min(1.0, sum(float(edge.get("strength", 0.0)) for edge in positive_edges) / float(len(positive_edges)))

    def _relationship_refs(self, relationship_edges: tuple[dict[str, Any], ...], npc_id: str) -> list[dict[str, Any]]:
        refs: list[dict[str, Any]] = []
        for edge in relationship_edges:
            if not self._edge_mentions_agent(edge, npc_id):
                continue
            if str(edge.get("edgeType") or "") not in {"affection", "trust", "respect"}:
                continue
            source_event_ids = [str(event_id) for event_id in edge.get("sourceEventIds", []) if str(event_id)]
            if not source_event_ids:
                continue
            refs.append(
                {
                    "edgeId": edge.get("edgeId"),
                    "sourceAgentId": edge.get("sourceAgentId"),
                    "targetAgentId": edge.get("targetAgentId"),
                    "edgeType": edge.get("edgeType"),
                    "strength": edge.get("strength"),
                    "sourceEventIds": source_event_ids[-3:],
                }
            )
        return refs[:4]

    def _edge_mentions_agent(self, edge: dict[str, Any], npc_id: str) -> bool:
        """避免错把其他 NPC 的记忆边计入当前 NPC 的仲裁。"""
        return npc_id in {str(edge.get("sourceAgentId") or ""), str(edge.get("targetAgentId") or "")}

    def _subjective_memory_refs(self, subjective_memories: tuple[dict[str, Any], ...], tool_id: str, npc_id: str) -> list[dict[str, Any]]:
        refs: list[dict[str, Any]] = []
        for memory in subjective_memories:
            if str(memory.get("agentId") or "") != npc_id:
                continue
            relevance = self._memory_tool_relevance(memory, tool_id)
            if relevance <= 0.0:
                continue
            refs.append(
                {
                    "recordId": memory.get("recordId"),
                    "sourceEventId": memory.get("sourceEventId"),
                    "emotionalValence": memory.get("emotionalValence", 0.0),
                    "confidence": memory.get("confidence", 1.0),
                    "relevance": round(relevance, 4),
                    "tags": [str(tag) for tag in memory.get("tags", [])[:4] if str(tag)] if isinstance(memory.get("tags"), list) else [],
                }
            )
        refs.sort(key=lambda ref: (float(ref.get("relevance") or 0.0), float(ref.get("confidence") or 0.0), str(ref.get("recordId") or "")), reverse=True)
        return refs[:4]

    def _memory_tool_relevance(self, memory: dict[str, Any], tool_id: str) -> float:
        tags = [str(tag).lower() for tag in memory.get("tags", []) if str(tag)] if isinstance(memory.get("tags"), list) else []
        text = str(memory.get("text") or "").lower()
        normalized_tool = tool_id.lower()
        namespace = f"{normalized_tool.split('.', 1)[0]}." if "." in normalized_tool else ""
        if normalized_tool in tags or normalized_tool in text:
            return 1.0
        if namespace and any(tag.startswith(namespace) for tag in tags):
            return 0.35
        return 0.0

    def _subjective_memory_bonus(self, refs: list[dict[str, Any]]) -> float:
        total = 0.0
        for ref in refs:
            valence = float(ref.get("emotionalValence") or 0.0)
            confidence = max(0.0, min(1.0, float(ref.get("confidence") or 0.0)))
            relevance = max(0.0, min(1.0, float(ref.get("relevance") or 0.0)))
            if valence < -0.1:
                total -= 0.05 * abs(valence) * confidence * relevance
            else:
                total += 0.08 * (1.0 + max(0.0, valence)) * confidence * relevance
        return max(-0.1, min(0.12, total))

    def _heuristic_refs(self, heuristics: tuple[dict[str, Any], ...], tool_id: str, need_id: str, npc_id: str, world_tick: int) -> list[dict[str, Any]]:
        refs: list[dict[str, Any]] = []
        for heuristic in heuristics:
            if str(heuristic.get("agentId") or "") != npc_id:
                continue
            if str(heuristic.get("status") or "active") != "active":
                continue
            adjustment = heuristic.get("adjustment") if isinstance(heuristic.get("adjustment"), dict) else {}
            target_kind = ""
            target_id = ""
            relevance = 0.0
            if str(adjustment.get("toolId") or "") == tool_id:
                target_kind = "tool"
                target_id = tool_id
                relevance = 1.0
            elif str(adjustment.get("needId") or "") == need_id:
                target_kind = "need"
                target_id = need_id
                relevance = 1.0
            if not target_kind:
                continue
            weight_delta = self._safe_float(adjustment.get("weightDelta"), 0.0)
            if weight_delta == 0.0:
                continue
            effective_confidence = self._heuristic_effective_confidence(heuristic, world_tick)
            applied_delta = weight_delta * effective_confidence * relevance
            refs.append(
                {
                    "heuristicId": heuristic.get("heuristicId"),
                    "triggerPattern": heuristic.get("triggerPattern"),
                    "sourceEventId": heuristic.get("sourceEventId"),
                    "targetKind": target_kind,
                    "targetId": target_id,
                    "weightDelta": round(weight_delta, 4),
                    "confidence": heuristic.get("confidence", 0.0),
                    "effectiveConfidence": round(effective_confidence, 4),
                    "appliedDelta": round(applied_delta, 6),
                    "conflictResolution": "none",
                }
            )
        return self._resolve_heuristic_conflicts(refs)[:4]

    def _resolve_heuristic_conflicts(self, refs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for ref in refs:
            grouped.setdefault((str(ref.get("targetKind") or ""), str(ref.get("targetId") or "")), []).append(ref)
        resolved: list[dict[str, Any]] = []
        for group in grouped.values():
            has_positive = any(float(ref.get("appliedDelta") or 0.0) > 0.0 for ref in group)
            has_negative = any(float(ref.get("appliedDelta") or 0.0) < 0.0 for ref in group)
            if has_positive and has_negative:
                winner_ref = max(group, key=lambda ref: (abs(float(ref.get("appliedDelta") or 0.0)), float(ref.get("effectiveConfidence") or 0.0), str(ref.get("heuristicId") or "")))
                winner = dict(winner_ref)
                winner["conflictResolution"] = "highest_effective_delta_wins"
                winner["conflictingHeuristicIds"] = [str(ref.get("heuristicId") or "") for ref in group if ref is not winner_ref]
                resolved.append(winner)
                continue
            resolved.extend(dict(ref) for ref in group)
        resolved.sort(key=lambda ref: (abs(float(ref.get("appliedDelta") or 0.0)), float(ref.get("effectiveConfidence") or 0.0), str(ref.get("heuristicId") or "")), reverse=True)
        return resolved

    def _heuristic_bonus(self, refs: list[dict[str, Any]]) -> float:
        total = sum(float(ref.get("appliedDelta") or 0.0) for ref in refs)
        return max(-0.12, min(0.12, total))

    def _heuristic_effective_confidence(self, heuristic: dict[str, Any], world_tick: int) -> float:
        if heuristic.get("effectiveConfidence") is not None:
            return max(0.0, min(1.0, self._safe_float(heuristic.get("effectiveConfidence"), 0.0)))
        confidence = max(0.0, min(1.0, self._safe_float(heuristic.get("confidence"), 0.0)))
        updated_tick = heuristic.get("updatedTick")
        if updated_tick is None:
            return confidence
        try:
            age_ticks = max(0, int(world_tick) - int(updated_tick))
        except (TypeError, ValueError):
            return confidence
        decay_factor = max(HEURISTIC_MIN_DECAY_FACTOR, 1.0 - float(age_ticks) * HEURISTIC_DECAY_PER_TICK)
        return max(0.0, min(1.0, confidence * decay_factor))

    def _safe_float(self, value: Any, fallback: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return fallback

    def _score_to_debug(self, item: dict[str, Any]) -> dict[str, Any]:
        tool = item["tool"]
        return {
            "toolId": tool.tool_id,
            "score": round(float(item["score"]), 6),
            "tierScore": round(float(item["tierScore"]), 6),
            "durationScore": round(float(item["durationScore"]), 6),
            "relationshipBonus": round(float(item["relationshipBonus"]), 6),
            "subjectiveMemoryBonus": round(float(item["subjectiveMemoryBonus"]), 6),
            "subjectiveMemoryRefCount": len(item.get("subjectiveMemoryRefs", [])),
            "heuristicBonus": round(float(item["heuristicBonus"]), 6),
            "heuristicRefCount": len(item.get("heuristicRefs", [])),
            "heuristicConflictCount": sum(1 for ref in item.get("heuristicRefs", []) if isinstance(ref, dict) and ref.get("conflictResolution") != "none"),
            "decisionBudgetRoute": item.get("decisionBudget", {}).get("route"),
            "decisionBudgetChannel": item.get("decisionBudget", {}).get("channel"),
            "decisionBudgetRemaining": item.get("decisionBudget", {}).get("remaining"),
        }
