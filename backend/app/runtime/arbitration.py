from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.tools import ToolDefinition


@dataclass(frozen=True)
class ArbitrationInput:
    npc_id: str
    need_id: str
    urgency: float
    candidates: tuple[ToolDefinition, ...]
    contributing_sources: tuple[dict[str, Any], ...]
    relationship_edges: tuple[dict[str, Any], ...] = ()


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
        }


class ArbitrationLayer:
    def decide(self, arbitration_input: ArbitrationInput) -> ArbitrationDecision:
        candidates = list(arbitration_input.candidates)
        scored = self._score_candidates(
            candidates,
            arbitration_input.relationship_edges,
            arbitration_input.npc_id,
        )
        selected_score = scored[0] if scored else None
        selected = selected_score["tool"] if selected_score else None
        relationship_refs = (
            self._relationship_refs(arbitration_input.relationship_edges, arbitration_input.npc_id)
            if selected and str(selected.tool_id).startswith("social.")
            else []
        )
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
        return ArbitrationDecision(
            npc_id=arbitration_input.npc_id,
            need_id=arbitration_input.need_id,
            selected_tool_id=selected.tool_id if selected else None,
            urgency=arbitration_input.urgency,
            candidate_tool_ids=tuple(tool.tool_id for tool in candidates),
            reason=(
                "relationship_memory_weighted_fit"
                if relationship_refs
                else ("highest_rule_tier_fit" if selected else "no_capability_available")
            ),
            contributing_sources=contributing_sources,
            candidate_scores=tuple(self._score_to_debug(item) for item in scored),
            relationship_edge_refs=tuple(relationship_refs),
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
        npc_id: str,
    ) -> list[dict[str, Any]]:
        """对候选工具打分；关系边只影响社交工具内部排序，避免越权改需求。"""
        tier_rank = {"physiological": 0, "vocational": 1, "social_strategic": 2}
        relationship_strength = self._relationship_strength(relationship_edges, npc_id)
        scored: list[dict[str, Any]] = []
        for tool in candidates:
            tier_score = 1.0 - float(tier_rank.get(tool.tier, 99)) * 0.1
            duration_score = max(0.0, 1.0 - float(tool.duration_seconds) / 3600.0) * 0.05
            relationship_bonus = 0.0
            if relationship_strength > 0.0 and tool.tool_id == "social.chat_with":
                relationship_bonus = 0.12 * relationship_strength
            elif relationship_strength > 0.0 and tool.tool_id == "social.give_gift":
                relationship_bonus = 0.03 * relationship_strength
            score = tier_score + duration_score + relationship_bonus
            scored.append(
                {
                    "tool": tool,
                    "score": score,
                    "tierScore": tier_score,
                    "durationScore": duration_score,
                    "relationshipBonus": relationship_bonus,
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

    def _score_to_debug(self, item: dict[str, Any]) -> dict[str, Any]:
        tool = item["tool"]
        return {
            "toolId": tool.tool_id,
            "score": round(float(item["score"]), 6),
            "tierScore": round(float(item["tierScore"]), 6),
            "durationScore": round(float(item["durationScore"]), 6),
            "relationshipBonus": round(float(item["relationshipBonus"]), 6),
        }
