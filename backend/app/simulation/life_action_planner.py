from __future__ import annotations

from collections import defaultdict
from typing import Any

from app.runtime.schema_registry import require_schema_version

LIFE_ACTION_PLAN_VERSION = require_schema_version("legacy_life_action_plan")
PHASE_WINDOWS = ("morning", "afternoon", "evening")


def build_life_action_plan_snapshot(
    world: dict[str, Any],
    npc_presence: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """根据 NPC 深度卡 seeds 生成可消费的日程与行动候选快照。"""
    clock = world.get("clock", {})
    day = int(clock.get("day", 1))
    phase = str(clock.get("phase") or "morning")
    tick = int(clock.get("tick", 0))
    presence_by_npc = {
        str(item.get("agentId")): item
        for item in npc_presence
        if isinstance(item, dict) and item.get("agentId")
    }
    anchor_by_id = {
        str(anchor.get("id")): anchor
        for anchor in world.get("anchors", {}).values()
        if isinstance(anchor, dict) and anchor.get("id")
    }
    interactables_by_anchor: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for interactable in world.get("interactables", {}).values():
        if not isinstance(interactable, dict):
            continue
        anchor_id = str(interactable.get("anchorId") or "")
        if anchor_id:
            interactables_by_anchor[anchor_id].append(interactable)

    schedules: list[dict[str, Any]] = []
    selected_actions: list[dict[str, Any]] = []
    rumor_candidates: list[dict[str, Any]] = []
    relation_candidates: list[dict[str, Any]] = []

    for npc_id, agent in world.get("agents", {}).items():
        if not isinstance(agent, dict):
            continue
        deep_card = agent.get("deepCard")
        if not isinstance(deep_card, dict):
            continue
        presence = presence_by_npc.get(str(npc_id))
        if not isinstance(presence, dict):
            continue
        presence_anchor_id = str(presence.get("anchorId") or "")
        presence_location_id = str(presence.get("locationId") or "")
        nearby_npc_ids = _collect_nearby_npcs(npc_id=str(npc_id), presence=presence, all_presence=presence_by_npc)

        life_action_candidates = _build_life_action_candidates(
            npc_id=str(npc_id),
            deep_card=deep_card,
            phase=phase,
            nearby_npc_ids=nearby_npc_ids,
            presence_anchor_id=presence_anchor_id,
            anchor_by_id=anchor_by_id,
            interactables_by_anchor=interactables_by_anchor,
        )
        active_life_action = life_action_candidates[0] if life_action_candidates else None

        rumor_beats = _build_rumor_candidates(str(npc_id), deep_card, phase)
        relationship_beats = _build_relationship_candidates(str(npc_id), deep_card, world, phase)

        schedule = {
            "npcId": str(npc_id),
            "day": day,
            "phase": phase,
            "generatedAtTick": tick,
            "locationId": presence_location_id,
            "anchorId": presence_anchor_id,
            "presenceSource": str(presence.get("source") or "unknown"),
            "activeLifeAction": active_life_action,
            "lifeActionCandidates": life_action_candidates,
            "rumorBeatCandidates": rumor_beats,
            "relationshipBeatCandidates": relationship_beats,
            "worldMutationPolicy": {
                "llmMayMutateWorld": False,
                "owner": "runtime_rule_planner",
            },
        }
        schedules.append(schedule)

        if active_life_action:
            selected_actions.append(
                {
                    "npcId": str(npc_id),
                    "actionId": str(active_life_action.get("id") or ""),
                    "summary": str(active_life_action.get("summary") or ""),
                    "locationId": presence_location_id,
                    "anchorId": presence_anchor_id,
                }
            )
        rumor_candidates.extend(
            {
                "npcId": str(npc_id),
                "beatId": str(item.get("id") or ""),
                "visibility": str(item.get("visibility") or ""),
                "cue": str(item.get("cue") or ""),
                "spreadTargets": list(item.get("spreadTargets") or []),
                "score": int(item.get("score", 0)),
            }
            for item in rumor_beats
        )
        relation_candidates.extend(
            {
                "npcId": str(npc_id),
                "beatId": str(item.get("id") or ""),
                "direction": str(item.get("direction") or ""),
                "stageHint": str(item.get("stageHint") or ""),
                "summary": str(item.get("summary") or ""),
                "score": int(item.get("score", 0)),
            }
            for item in relationship_beats
        )

    plan = {
        "version": LIFE_ACTION_PLAN_VERSION,
        "day": day,
        "phase": phase,
        "generatedAtTick": tick,
        "selectedActions": selected_actions,
        "locationBuckets": _build_location_buckets(selected_actions),
        "rumorBeatQueue": sorted(rumor_candidates, key=lambda item: item["score"], reverse=True)[:12],
        "relationshipBeatQueue": sorted(relation_candidates, key=lambda item: item["score"], reverse=True)[:12],
        "policy": {
            "llmMayMutateWorld": False,
            "worldMutationPath": "runtime_only",
        },
    }
    return schedules, plan


def _collect_nearby_npcs(
    *,
    npc_id: str,
    presence: dict[str, Any],
    all_presence: dict[str, dict[str, Any]],
) -> set[str]:
    """收集同一地点的 NPC，供 lifeAction score 加权。"""
    location_id = str(presence.get("locationId") or "")
    result: set[str] = set()
    for candidate_id, item in all_presence.items():
        if candidate_id == npc_id:
            continue
        if str(item.get("locationId") or "") == location_id:
            result.add(candidate_id)
    return result


def _build_life_action_candidates(
    *,
    npc_id: str,
    deep_card: dict[str, Any],
    phase: str,
    nearby_npc_ids: set[str],
    presence_anchor_id: str,
    anchor_by_id: dict[str, dict[str, Any]],
    interactables_by_anchor: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """把 lifeActionSeeds 转成排序后的运行时候选。"""
    candidates: list[dict[str, Any]] = []
    for seed in deep_card.get("lifeActionSeeds", []):
        if not isinstance(seed, dict):
            continue
        action_id = str(seed.get("id") or "")
        if not action_id:
            continue
        time_window = str(seed.get("timeWindow") or "")
        location_hints = _normalize_str_list(seed.get("locationHints"))
        related_npc_ids = _normalize_str_list(seed.get("relatedNpcIds"))
        score = 0
        if time_window == phase:
            score += 100
        if time_window in PHASE_WINDOWS:
            score += 10
        if nearby_npc_ids.intersection(related_npc_ids):
            score += 8
        if presence_anchor_id:
            score += 4
        space_candidates = _build_space_action_candidates(
            npc_id=npc_id,
            action_id=action_id,
            summary=str(seed.get("summary") or ""),
            location_hints=location_hints,
            presence_anchor_id=presence_anchor_id,
            anchor_by_id=anchor_by_id,
            interactables_by_anchor=interactables_by_anchor,
        )
        candidates.append(
            {
                "id": action_id,
                "timeWindow": time_window,
                "summary": str(seed.get("summary") or ""),
                "intentTags": _normalize_str_list(seed.get("intentTags")),
                "locationHints": location_hints,
                "relatedNpcIds": related_npc_ids,
                "score": score,
                "spaceActionCandidates": space_candidates,
            }
        )
    candidates.sort(key=lambda item: (int(item.get("score", 0)), str(item.get("id"))), reverse=True)
    if candidates:
        candidates[0]["selected"] = True
    return candidates


def _build_space_action_candidates(
    *,
    npc_id: str,
    action_id: str,
    summary: str,
    location_hints: list[str],
    presence_anchor_id: str,
    anchor_by_id: dict[str, dict[str, Any]],
    interactables_by_anchor: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """把 locationHints 映射为空间行动候选。"""
    anchor_ids: list[str] = []
    if presence_anchor_id and presence_anchor_id in anchor_by_id:
        anchor_ids.append(presence_anchor_id)
    for hint in location_hints:
        anchor_ids.extend(_anchor_ids_for_hint(hint, anchor_by_id))
    dedup_anchor_ids = _dedupe_keep_order(anchor_ids)
    candidates: list[dict[str, Any]] = []
    for anchor_id in dedup_anchor_ids:
        anchor = anchor_by_id.get(anchor_id)
        if not isinstance(anchor, dict):
            continue
        scene_actions = _build_scene_action_candidates(interactables_by_anchor.get(anchor_id, []))
        candidates.append(
            {
                "id": f"space_{npc_id}_{action_id}_{anchor_id}",
                "actionType": "move_to_anchor",
                "anchorId": anchor_id,
                "locationId": str(anchor.get("locationId") or ""),
                "intentSummary": summary,
                "sceneActionCandidates": scene_actions,
            }
        )
    return candidates


def _anchor_ids_for_hint(hint: str, anchor_by_id: dict[str, dict[str, Any]]) -> list[str]:
    """按 location hint 选择锚点候选。"""
    normalized = hint.strip().lower()
    result: list[str] = []
    for anchor_id, anchor in anchor_by_id.items():
        location_id = str(anchor.get("locationId") or "")
        tags = {str(tag).lower() for tag in anchor.get("tags", []) if str(tag).strip()}
        if normalized == str(anchor_id).lower():
            result.append(anchor_id)
        elif normalized == location_id.lower():
            result.append(anchor_id)
        elif normalized == "home" and ("home" in tags or "rest" in tags):
            result.append(anchor_id)
        elif normalized == "work_spot" and (
            "market" in tags or "farm" in tags or "event" in tags or "service" in str(anchor.get("kind") or "")
        ):
            result.append(anchor_id)
        elif normalized == "town_center" and location_id == "plaza":
            result.append(anchor_id)
        elif normalized == "tavern" and location_id == "tavern":
            result.append(anchor_id)
    return result


def _build_scene_action_candidates(interactables: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """把锚点周围 interactables 转成 scene_action 候选。"""
    results: list[dict[str, Any]] = []
    for interactable in interactables:
        if not isinstance(interactable, dict):
            continue
        interactable_id = str(interactable.get("id") or "")
        kind = str(interactable.get("kind") or "")
        for action_name in interactable.get("actions", []):
            action = str(action_name or "").strip()
            if not action:
                continue
            results.append(
                {
                    "interactableId": interactable_id,
                    "kind": kind,
                    "sceneAction": action,
                }
            )
    return results


def _build_rumor_candidates(npc_id: str, deep_card: dict[str, Any], phase: str) -> list[dict[str, Any]]:
    """把 dailyRumorBeats 转成可排序候选。"""
    candidates: list[dict[str, Any]] = []
    for beat in deep_card.get("dailyRumorBeats", []):
        if not isinstance(beat, dict):
            continue
        beat_id = str(beat.get("id") or "")
        visibility = str(beat.get("visibility") or "")
        if not beat_id:
            continue
        score = 60 if visibility == "town_known" else 48
        if phase == "evening" and visibility == "hidden":
            score += 7
        if phase in {"morning", "afternoon"} and visibility == "town_known":
            score += 5
        candidates.append(
            {
                "id": beat_id,
                "visibility": visibility,
                "cue": str(beat.get("cue") or ""),
                "spreadTargets": _normalize_str_list(beat.get("spreadTargets")),
                "tags": _normalize_str_list(beat.get("tags")),
                "score": score,
                "ownerNpcId": npc_id,
            }
        )
    candidates.sort(key=lambda item: (int(item.get("score", 0)), str(item.get("id"))), reverse=True)
    return candidates


def _build_relationship_candidates(
    npc_id: str,
    deep_card: dict[str, Any],
    world: dict[str, Any],
    phase: str,
) -> list[dict[str, Any]]:
    """把 relationshipBeatSeeds 转成可消费候选。"""
    relation = _player_relation(world, npc_id)
    matched_stage = _matched_relationship_stage(deep_card, relation)
    candidates: list[dict[str, Any]] = []
    for beat in deep_card.get("relationshipBeatSeeds", []):
        if not isinstance(beat, dict):
            continue
        beat_id = str(beat.get("id") or "")
        stage_hint = str(beat.get("stageHint") or "")
        direction = str(beat.get("direction") or "")
        if not beat_id:
            continue
        score = 40
        if stage_hint == matched_stage:
            score += 25
        if phase == "evening":
            score += 3
        if direction == "up":
            score += 4
        candidates.append(
            {
                "id": beat_id,
                "stageHint": stage_hint,
                "direction": direction,
                "trigger": str(beat.get("trigger") or ""),
                "summary": str(beat.get("summary") or ""),
                "tags": _normalize_str_list(beat.get("tags")),
                "score": score,
                "matchedStage": matched_stage,
            }
        )
    candidates.sort(key=lambda item: (int(item.get("score", 0)), str(item.get("id"))), reverse=True)
    return candidates


def _player_relation(world: dict[str, Any], npc_id: str) -> dict[str, Any]:
    """读取玩家与 NPC 的关系快照。"""
    key = "::".join(sorted(["player", npc_id]))
    default_relation = {"affection": 45, "trust": 45, "conflict": 0}
    relation = world.get("relations", {}).get(key)
    if not isinstance(relation, dict):
        return default_relation
    return {
        "affection": int(relation.get("affection", 45)),
        "trust": int(relation.get("trust", 45)),
        "conflict": int(relation.get("conflict", 0)),
    }


def _matched_relationship_stage(deep_card: dict[str, Any], relation: dict[str, Any]) -> str:
    """根据当前关系数值匹配深度卡阶段。"""
    stages = [item for item in deep_card.get("relationshipStages", []) if isinstance(item, dict)]
    if not stages:
        return ""
    matched = stages[0]
    affection = int(relation.get("affection", 0))
    trust = int(relation.get("trust", 0))
    conflict = int(relation.get("conflict", 0))
    for stage in stages:
        threshold = stage.get("threshold")
        if not isinstance(threshold, dict):
            continue
        min_affection = int(threshold.get("affection", 0))
        min_trust = int(threshold.get("trust", 0))
        max_conflict = threshold.get("conflictMax")
        if affection < min_affection or trust < min_trust:
            continue
        if max_conflict is not None and conflict > int(max_conflict):
            continue
        matched = stage
    return str(matched.get("stage") or "")


def _build_location_buckets(selected_actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """按地点聚合选中的 life action。"""
    buckets: dict[str, dict[str, Any]] = {}
    for item in selected_actions:
        location_id = str(item.get("locationId") or "")
        if not location_id:
            continue
        bucket = buckets.setdefault(location_id, {"locationId": location_id, "npcIds": [], "actionIds": []})
        npc_id = str(item.get("npcId") or "")
        action_id = str(item.get("actionId") or "")
        if npc_id and npc_id not in bucket["npcIds"]:
            bucket["npcIds"].append(npc_id)
        if action_id and action_id not in bucket["actionIds"]:
            bucket["actionIds"].append(action_id)
    return sorted(buckets.values(), key=lambda item: item["locationId"])


def _normalize_str_list(raw: Any) -> list[str]:
    """把输入统一成字符串数组。"""
    if not isinstance(raw, list):
        return []
    result: list[str] = []
    for item in raw:
        value = str(item or "").strip()
        if value:
            result.append(value)
    return result


def _dedupe_keep_order(items: list[str]) -> list[str]:
    """按原顺序去重。"""
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result
