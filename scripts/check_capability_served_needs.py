"""校验 CapabilityRegistry 的 served_needs 过滤行为。"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.runtime.capability_registry import CapabilityRegistry  # noqa: E402


def _build_world() -> dict[str, Any]:
    return {
        "clock": {"day": 3, "phase": "morning"},
        "agents": {
            "kai": {
                "id": "kai",
                "name": "凯娅",
                "locationId": "tavern",
                "anchorId": "tavern.table",
                "inventory": [{"itemId": "tea"}],
                "deepCard": {"gossipHooks": ["missing_supply"]},
            },
            "mira": {
                "id": "mira",
                "name": "米拉",
                "locationId": "tavern",
                "anchorId": "tavern.bar",
                "inventory": [],
                "deepCard": {},
            },
        },
        "relations": {"kai::mira": {"trust": 35}},
        "farmPlots": {},
    }


def _layer_decisions(resolution: dict[str, Any], layer_name: str) -> dict[str, Any]:
    layers = resolution.get("layers", [])
    for layer in layers:
        if isinstance(layer, dict) and layer.get("layer") == layer_name:
            return layer
    return {}


def main() -> None:
    world = _build_world()
    registry = CapabilityRegistry()

    affiliation = registry.resolve_with_debug(world, "kai", "affiliation").to_debug_dict()
    recognition = registry.resolve_with_debug(world, "kai", "recognition").to_debug_dict()
    goal_progress = registry.resolve_with_debug(world, "kai", "goal_progress").to_debug_dict()

    affiliation_tools = set(affiliation.get("allowedToolIds", []))
    recognition_tools = set(recognition.get("allowedToolIds", []))
    goal_progress_tools = set(goal_progress.get("allowedToolIds", []))

    assert "strategic.spread_rumor" not in affiliation_tools, "affiliation 不应放行 strategic.spread_rumor"
    assert "strategic.spread_rumor" in recognition_tools, "recognition 应允许 strategic.spread_rumor"
    assert "social.chat_with" in goal_progress_tools, "goal_progress 应匹配 goal_progress.relationship_building"

    affiliation_need_layer = _layer_decisions(affiliation, "need_relevance")
    recognition_need_layer = _layer_decisions(recognition, "need_relevance")

    affiliation_rumor = next(
        (
            decision
            for decision in affiliation_need_layer.get("decisions", [])
            if isinstance(decision, dict) and decision.get("toolId") == "strategic.spread_rumor"
        ),
        {},
    )
    recognition_rumor = next(
        (
            decision
            for decision in recognition_need_layer.get("decisions", [])
            if isinstance(decision, dict) and decision.get("toolId") == "strategic.spread_rumor"
        ),
        {},
    )
    assert affiliation_rumor.get("reason") == "served_need_mismatch", "affiliation 过滤原因应为 served_need_mismatch"
    assert recognition_rumor.get("reason") == "matches_served_need", "recognition 命中原因应为 matches_served_need"

    print(
        json.dumps(
            {
                "ok": True,
                "affiliationAllowedTools": sorted(affiliation_tools),
                "recognitionAllowedTools": sorted(recognition_tools),
                "goalProgressAllowedTools": sorted(goal_progress_tools),
                "affiliationRumorDecision": affiliation_rumor,
                "recognitionRumorDecision": recognition_rumor,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
