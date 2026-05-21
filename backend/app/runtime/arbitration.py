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


@dataclass(frozen=True)
class ArbitrationDecision:
    npc_id: str
    need_id: str
    selected_tool_id: str | None
    urgency: float
    candidate_tool_ids: tuple[str, ...]
    reason: str
    contributing_sources: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "npcId": self.npc_id,
            "needId": self.need_id,
            "selectedToolId": self.selected_tool_id,
            "urgency": round(self.urgency, 4),
            "candidateToolIds": list(self.candidate_tool_ids),
            "reason": self.reason,
            "contributingSources": [dict(item) for item in self.contributing_sources],
        }


class ArbitrationLayer:
    def decide(self, arbitration_input: ArbitrationInput) -> ArbitrationDecision:
        candidates = list(arbitration_input.candidates)
        selected = self._select_tool(candidates)
        return ArbitrationDecision(
            npc_id=arbitration_input.npc_id,
            need_id=arbitration_input.need_id,
            selected_tool_id=selected.tool_id if selected else None,
            urgency=arbitration_input.urgency,
            candidate_tool_ids=tuple(tool.tool_id for tool in candidates),
            reason="highest_rule_tier_fit" if selected else "no_capability_available",
            contributing_sources=arbitration_input.contributing_sources,
        )

    def _select_tool(self, candidates: list[ToolDefinition]) -> ToolDefinition | None:
        if not candidates:
            return None
        tier_rank = {"physiological": 0, "vocational": 1, "social_strategic": 2}
        return sorted(candidates, key=lambda tool: (tier_rank.get(tool.tier, 99), tool.duration_seconds, tool.tool_id))[0]
