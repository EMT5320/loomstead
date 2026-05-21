"""校验 Day 1 MotivationPlan 目标，避免 NPC 再次退化为全员同点迁徙。"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.runtime.agent_runtime import AgentRuntime  # noqa: E402
from app.world.seed_data import DAY1_LOCATION_IDS  # noqa: E402
from app.world.world_state import build_npc_presence, sync_agents_from_presence  # noqa: E402

CHECK_PHASES = ("morning", "afternoon", "evening")


def _selected_targets_for_phase(phase: str) -> tuple[dict[str, object], list[dict[str, object]]]:
    """按指定时段构造目标，用初始 presence 捕获工具目标容量问题。"""
    runtime = AgentRuntime(provider_mode="rule")
    world = runtime.world
    world["clock"]["phase"] = phase
    world["npcPresence"] = build_npc_presence(world)
    sync_agents_from_presence(world, world["npcPresence"])

    _, plan = runtime._phase2_motivation_plan_snapshot()
    return world, plan.get("selectedActions", [])


def main() -> None:
    """构造初始世界并检查 tick 目标分布与当前客户端切片一致。"""
    for phase in CHECK_PHASES:
        world, selected_actions = _selected_targets_for_phase(phase)
        if not selected_actions:
            raise SystemExit(f"[motivation-target-check] {phase} selectedActions 为空")

        visible_anchor_ids = {
            str(anchor_id)
            for anchor_id, anchor in world.get("anchors", {}).items()
            if isinstance(anchor, dict) and str(anchor.get("locationId") or "") in DAY1_LOCATION_IDS
        }
        target_counts = Counter(str(item.get("anchorId") or item.get("targetAnchorId") or "") for item in selected_actions)
        outside_slice = sorted(anchor_id for anchor_id in target_counts if anchor_id not in visible_anchor_ids)
        if outside_slice:
            raise SystemExit(f"[motivation-target-check] {phase} 存在客户端切片外目标：{', '.join(outside_slice)}")

        over_capacity: list[str] = []
        for anchor_id, count in sorted(target_counts.items()):
            anchor = world.get("anchors", {}).get(anchor_id, {})
            capacity = max(1, int(anchor.get("capacity") or 1)) if isinstance(anchor, dict) else 1
            if count > capacity:
                over_capacity.append(f"{anchor_id}={count}/{capacity}")
        if over_capacity:
            raise SystemExit(f"[motivation-target-check] {phase} 目标锚点超容量：{', '.join(over_capacity)}")

    print("[motivation-target-check] ok")


if __name__ == "__main__":
    main()
