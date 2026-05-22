from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.content.codex_loader import load_all_npc_deep_cards, to_runtime_dict
from app.runtime.schema_registry import require_schema_version
from app.simulation import build_life_action_plan_snapshot

from .seed_data import (
    AGENTS,
    ANCHORS,
    DAY1_EVENT_ID,
    DAY1_EVENTS,
    DAY1_LOCATION_IDS,
    DAY1_NPC_IDS,
    FARM_PLOTS,
    INITIAL_RELATIONS,
    INTERACTABLES,
    LOCATIONS,
    NPC_PRESENCE_SOURCES,
    NPC_SOFT_PRESENCE,
)


PHASES = ("morning", "noon", "afternoon", "evening", "night")
PHASE_START_HOURS = {"morning": 8, "noon": 12, "afternoon": 14, "evening": 18, "night": 21}
PHASE_ACTION_BUDGET = {"morning": 3, "noon": 2, "afternoon": 3, "evening": 2, "night": 1}


def clamp(value: int | float, min_value: int = 0, max_value: int = 100) -> int:
    """限制状态数值范围，避免行动执行后出现非法状态。"""
    return int(max(min_value, min(max_value, value)))


def relation_key(a: str, b: str) -> str:
    """关系图使用无向 key，方便任意方向读取。"""
    return "::".join(sorted([a, b]))


def create_initial_world() -> dict[str, Any]:
    """创建首版小镇世界状态。"""
    agents = {agent["id"]: create_agent(agent) for agent in AGENTS}
    deep_cards = load_all_npc_deep_cards()
    for npc_id, card in deep_cards.items():
        if npc_id in agents:
            agents[npc_id]["deepCard"] = to_runtime_dict(card)
    relations: dict[str, dict[str, Any]] = {}
    for a, b, affection, trust, conflict, kind in INITIAL_RELATIONS:
        relations[relation_key(a, b)] = {"affection": affection, "trust": trust, "conflict": conflict, "kind": kind}
    world = {
        "clock": {"day": 1, "hour": 8, "tick": 0, "phase": "morning", "actionBudget": PHASE_ACTION_BUDGET["morning"], "paused": False},
        "player": create_player(),
        "locations": {location["id"]: deepcopy(location) for location in LOCATIONS},
        "anchors": {anchor["id"]: deepcopy(anchor) for anchor in ANCHORS},
        "interactables": {interactable["id"]: deepcopy(interactable) for interactable in INTERACTABLES},
        "farmPlots": {plot["id"]: deepcopy(plot) for plot in FARM_PLOTS},
        "agents": agents,
        "relations": relations,
        "npcPresence": [],
        "population": {"births": 0, "deaths": 0, "migrationsIn": 1, "migrationsOut": 0, "growthEvents": 0},
        "townStats": {"funds": 500, "harmony": 63, "economy": 58, "health": 72, "curiosity": 80},
        "activeEvents": deepcopy(DAY1_EVENTS),
        "completedEvents": [],
        "nightReflections": [],
        "activeFocus": None,
    }
    sync_farm_interactables(world)
    world["npcPresence"] = build_npc_presence(world)
    sync_agents_from_presence(world, world["npcPresence"])
    return world


def create_player() -> dict[str, Any]:
    """创建首版玩家状态，后续存档系统会直接围绕这些字段扩展。"""
    return {
        "id": "player",
        "name": "新来的农场主",
        "locationId": "farm",
        "anchorId": "farm_house_door",
        "inventory": [
            {"id": "starlight_turnip_seed", "name": "星灯芜菁种子", "quantity": 2, "tags": ["seed", "farm"]},
            {"id": "fresh_turnip", "name": "新鲜芜菁", "quantity": 1, "tags": ["crop", "gift"]},
            {"id": "farm_flower", "name": "农场小花", "quantity": 1, "tags": ["flower", "gift"]},
        ],
        "knownNpcs": [],
        "questFlags": {"day1_intro": "started"},
        "actionHistory": [],
        "profile": {
            "styleSummary": "刚搬来晨露农场，正在通过聊天、送礼和事件选择形成小镇印象。",
            "signals": {"talk": 0, "gift": 0, "festivalChoice": 0, "help": 0, "mediate": 0, "observe": 0, "support": 0},
            "evidence": [],
        },
        "memories": [{"tick": 0, "importance": 0.6, "tags": ["arrival"], "text": "我搬进了晨露农场，准备认识这座小镇。"}],
    }


def create_agent(seed: dict[str, Any]) -> dict[str, Any]:
    """把种子数据扩展为运行期 Agent 状态。"""
    status = {
        "energy": 56 if seed["lifeStage"] == "elder" else 78,
        "mood": 82 if seed["lifeStage"] == "child" else 64,
        "stress": 38 if "轻微焦虑" in seed.get("personality", []) else 22,
        "social": 50,
        "money": seed["money"],
        "health": seed["health"],
    }
    agent = deepcopy(seed)
    agent.update(
        {
            "status": status,
            "currentIntent": "观察小镇今日变化",
            "todayGoals": seed["longTermGoals"][:2],
            "memories": [{"tick": 0, "importance": 0.6, "text": f"{seed['name']} 开始了小镇实验的第一天。"}],
            "decisionHistory": [],
            "alive": True,
        }
    )
    return agent


def living_agents(world: dict[str, Any]) -> list[dict[str, Any]]:
    """返回仍在小镇活动的居民。"""
    return [agent for agent in world["agents"].values() if agent.get("alive", True)]


def get_relation(world: dict[str, Any], a: str, b: str) -> dict[str, Any]:
    """读取两个 Agent 的关系，缺省为普通熟人。"""
    return world["relations"].get(relation_key(a, b), {"affection": 45, "trust": 45, "conflict": 0, "kind": "acquaintance"})


def adjust_relation(world: dict[str, Any], a: str, b: str, delta: dict[str, int | str]) -> None:
    """按行动结果调整关系。"""
    current = get_relation(world, a, b)
    world["relations"][relation_key(a, b)] = {
        "affection": clamp(current["affection"] + int(delta.get("affection", 0))),
        "trust": clamp(current["trust"] + int(delta.get("trust", 0))),
        "conflict": clamp(current["conflict"] + int(delta.get("conflict", 0))),
        "kind": str(delta.get("kind", current["kind"])),
    }


def phase_for_hour(hour: int) -> str:
    """把小时映射到首版时段，保持和玩法文档中的五段制一致。"""
    if hour < 12:
        return "morning"
    if hour < 14:
        return "noon"
    if hour < 18:
        return "afternoon"
    if hour < 21:
        return "evening"
    return "night"


def action_budget_for_phase(phase: str) -> int:
    """读取指定时段的玩家行动预算。"""
    return PHASE_ACTION_BUDGET.get(phase, PHASE_ACTION_BUDGET["morning"])


def default_anchor_for_location(world: dict[str, Any], location_id: str) -> str | None:
    """读取地点默认入口锚点，缺省时回退到该地点的第一个锚点。"""
    location = world.get("locations", {}).get(location_id)
    if isinstance(location, dict) and location.get("defaultEntryAnchorId") in world.get("anchors", {}):
        return str(location["defaultEntryAnchorId"])
    for anchor in world.get("anchors", {}).values():
        if anchor.get("locationId") == location_id:
            return str(anchor["id"])
    return None


def sync_farm_interactables(world: dict[str, Any]) -> None:
    """把 farmPlots 的权威阶段同步到同名 interactable，避免客户端读到旧状态。"""
    interactables = world.setdefault("interactables", {})
    for plot_id, plot in world.get("farmPlots", {}).items():
        interactable = interactables.get(plot_id)
        if not isinstance(interactable, dict):
            continue
        interactable["state"] = {
            "farmPlotId": plot_id,
            "cropId": plot.get("cropId"),
            "stage": plot.get("stage", "empty"),
            "seedItemId": plot.get("seedItemId"),
            "outputItemId": (plot.get("outputItem") or {}).get("id") if isinstance(plot.get("outputItem"), dict) else None,
        }


def advance_phase(world: dict[str, Any]) -> dict[str, Any]:
    """结束当前时段并进入下一时段，同时重置行动预算和推进作物成熟。"""
    clock = world["clock"]
    previous_phase = str(clock.get("phase") or phase_for_hour(int(clock.get("hour", 8))))
    previous_day = int(clock.get("day", 1))
    current_index = PHASES.index(previous_phase) if previous_phase in PHASES else 0
    matured_plots = mature_farm_plots(world)
    if previous_phase == "night":
        clock["day"] = previous_day + 1
        next_phase = "morning"
    else:
        next_phase = PHASES[current_index + 1]
    clock["phase"] = next_phase
    clock["hour"] = PHASE_START_HOURS[next_phase]
    clock["tick"] = int(clock.get("tick", 0)) + 1
    clock["actionBudget"] = action_budget_for_phase(next_phase)
    return {
        "fromDay": previous_day,
        "toDay": clock["day"],
        "fromPhase": previous_phase,
        "toPhase": next_phase,
        "actionBudget": clock["actionBudget"],
        "maturedFarmPlotIds": matured_plots,
    }


def mature_farm_plots(world: dict[str, Any]) -> list[str]:
    """首版作物成熟规则：已浇水田块在时段结束时进入可收获阶段。"""
    matured: list[str] = []
    for plot_id, plot in world.get("farmPlots", {}).items():
        if plot.get("stage") == "watered":
            plot["stage"] = "harvestable"
            matured.append(str(plot_id))
    if matured:
        sync_farm_interactables(world)
    return matured


def advance_clock(world: dict[str, Any]) -> None:
    """推进世界时钟，每天从 08:00 到 21:00。"""
    clock = world["clock"]
    previous_phase = str(clock.get("phase") or phase_for_hour(int(clock.get("hour", 8))))
    clock["tick"] += 1
    clock["hour"] += 1
    if clock["hour"] >= 22:
        clock["day"] += 1
        clock["hour"] = 8
    next_phase = phase_for_hour(int(clock["hour"]))
    clock["phase"] = next_phase
    if next_phase != previous_phase:
        clock["actionBudget"] = action_budget_for_phase(next_phase)
        mature_farm_plots(world)


def build_npc_presence(world: dict[str, Any]) -> list[dict[str, Any]]:
    """按软日程、导演焦点、事件和关系牵引生成首版 NPC Presence。"""
    presence: list[dict[str, Any]] = []
    clock = world.get("clock", {})
    phase = str(clock.get("phase") or "morning")
    active_focus = world.get("activeFocus") if isinstance(world.get("activeFocus"), dict) else {}
    spotlight_ids = [str(agent_id) for agent_id in active_focus.get("targetAgents", []) if str(agent_id) in DAY1_NPC_IDS]
    spotlight_anchor_id = anchor_for_location_kind(world, str(active_focus.get("eventLocationId") or "tavern"), "event_spot") or "tavern_stage"
    event_skill_ids = event_skill_presence_ids(world)
    relationship_pull_ids = relationship_pull_presence_ids(world)

    for npc_id in DAY1_NPC_IDS:
        agent = world.get("agents", {}).get(npc_id)
        if not agent or not agent.get("alive", True):
            continue
        source, anchor_id, intent = npc_presence_rule(
            world,
            npc_id,
            phase=phase,
            spotlight_ids=spotlight_ids,
            spotlight_anchor_id=spotlight_anchor_id,
            event_skill_ids=event_skill_ids,
            relationship_pull_ids=relationship_pull_ids,
            active_focus=active_focus,
        )
        anchor = world.get("anchors", {}).get(anchor_id)
        if not anchor:
            continue
        presence.append(
            {
                "agentId": npc_id,
                "locationId": anchor["locationId"],
                "anchorId": anchor_id,
                "visibility": "visible",
                "intent": intent,
                "source": source,
                "expiresAtPhase": phase,
            }
        )
    return presence


def npc_presence_rule(
    world: dict[str, Any],
    npc_id: str,
    *,
    phase: str,
    spotlight_ids: list[str],
    spotlight_anchor_id: str,
    event_skill_ids: set[str],
    relationship_pull_ids: set[str],
    active_focus: dict[str, Any],
) -> tuple[str, str, str]:
    """为单个 NPC 选择 Presence 来源、锚点和可解释意图。"""
    rule = NPC_SOFT_PRESENCE.get(npc_id, {})
    anchor_id = str(rule.get("anchorId") or default_anchor_for_location(world, world["agents"][npc_id].get("locationId", "plaza")) or "plaza_fountain")
    intent = str(rule.get("intent") or "按照日常习惯在小镇中活动。")
    source = "habit"

    # Director 只把一个角色推到台前，避免首版所有居民因为同一个事件挤到同一锚点。
    if spotlight_ids and npc_id == spotlight_ids[0]:
        return (
            "director_spotlight",
            spotlight_anchor_id,
            str(active_focus.get("brief") or "导演层把该角色推入玩家视野，制造当前时段的舞台焦点。"),
        )

    if npc_id in relationship_pull_ids:
        return (
            "relationship_pull",
            "farm_field",
            "被凯娅与布兰娜之间的供货矛盾牵引，回到农场确认是否还有可支援作物。",
        )

    if npc_id in event_skill_ids:
        return (
            "event_skill",
            "tavern_door",
            f"受到星灯祭供应短缺事件牵引，准备在{phase}收集酒馆现场信息。",
        )

    return source, anchor_id, intent


def event_skill_presence_ids(world: dict[str, Any]) -> set[str]:
    """提取当前事件需要推入玩家视野的轻量参与者集合。"""
    ids: set[str] = set()
    for event in world.get("activeEvents", []):
        if event.get("id") != DAY1_EVENT_ID or event.get("status") == "resolved":
            continue
        participants = [str(agent_id) for agent_id in event.get("participants", []) if str(agent_id) in DAY1_NPC_IDS]
        # 初版只选择米娅补充事件线索，主冲突双方留给 director_spotlight / relationship_pull。
        for candidate in participants:
            if candidate == "mira":
                ids.add(candidate)
    return ids


def relationship_pull_presence_ids(world: dict[str, Any]) -> set[str]:
    """根据高冲突关系生成关系牵引 Presence。"""
    relation = get_relation(world, "kai", "bram")
    if int(relation.get("conflict", 0)) >= 35:
        return {"bram"}
    return set()


def anchor_for_location_kind(world: dict[str, Any], location_id: str, kind: str) -> str | None:
    """按地点和锚点类型查找锚点。"""
    for anchor in world.get("anchors", {}).values():
        if anchor.get("locationId") == location_id and anchor.get("kind") == kind:
            return str(anchor["id"])
    return default_anchor_for_location(world, location_id)


def sync_agents_from_presence(world: dict[str, Any], presence: list[dict[str, Any]]) -> None:
    """把 Presence 同步回 Agent 运行态，减少旧客户端读取 npcs 时的歧义。"""
    for item in presence:
        agent = world.get("agents", {}).get(item.get("agentId"))
        if not isinstance(agent, dict):
            continue
        agent["locationId"] = item["locationId"]
        agent["anchorId"] = item["anchorId"]
        agent["currentIntent"] = item["intent"]


def public_world(world: dict[str, Any]) -> dict[str, Any]:
    """输出前端需要的公开状态，裁剪长历史。"""
    view = deepcopy(world)
    view["playerAnchor"] = current_player_anchor(world)
    view["locations"] = list(view["locations"].values())
    view["agents"] = list(view["agents"].values())
    view["player"]["actionHistory"] = view["player"].get("actionHistory", [])[-10:]
    view["player"]["memories"] = view["player"].get("memories", [])[-10:]
    for agent in view["agents"]:
        agent["memories"] = agent.get("memories", [])[-5:]
        agent["decisionHistory"] = agent.get("decisionHistory", [])[-3:]
    return view


def public_game_world(world: dict[str, Any], recent_events: list[dict[str, Any]]) -> dict[str, Any]:
    """输出 Godot 游戏客户端使用的状态契约，保留后续扩展字段。"""
    view = public_world(world)
    location_ids = set(DAY1_LOCATION_IDS)
    npc_ids = set(DAY1_NPC_IDS)
    # Tick 执行器会维护运行期 npcPresence；仅在缺失时回退到软日程快照。
    runtime_presence = world.get("npcPresence")
    npc_presence = deepcopy(runtime_presence) if isinstance(runtime_presence, list) and runtime_presence else build_npc_presence(world)
    presence_by_agent = {item["agentId"]: item for item in npc_presence}
    npcs = [agent for agent in view["agents"] if agent["id"] in npc_ids]
    for agent in npcs:
        presence = presence_by_agent.get(agent["id"])
        if presence:
            agent["locationId"] = presence["locationId"]
            agent["anchorId"] = presence["anchorId"]
            agent["currentIntent"] = presence["intent"]
    anchors = [deepcopy(anchor) for anchor in world.get("anchors", {}).values() if anchor.get("locationId") in location_ids]
    interactables = [deepcopy(item) for item in world.get("interactables", {}).values() if item.get("locationId") in location_ids]
    farm_plots = [deepcopy(plot) for plot in world.get("farmPlots", {}).values() if plot.get("locationId") in location_ids]
    npc_schedules, life_action_plan = build_life_action_plan_snapshot(world, npc_presence)
    return {
        "clock": view["clock"],
        "player": view["player"],
        "playerAnchor": view.get("playerAnchor"),
        "locations": [location for location in view["locations"] if location["id"] in location_ids],
        "anchors": anchors,
        "interactables": interactables,
        "npcPresence": npc_presence,
        "farmPlots": farm_plots,
        "npcs": npcs,
        "activeEvents": view.get("activeEvents", []),
        "completedEvents": view.get("completedEvents", []),
        "nightReflections": view.get("nightReflections", [])[-10:],
        "npcSchedules": npc_schedules,
        "lifeActionPlan": life_action_plan,
        "recentEvents": recent_events[-20:],
        "slice": {
            "npcIds": DAY1_NPC_IDS,
            "locationIds": DAY1_LOCATION_IDS,
            "anchorIds": [anchor["id"] for anchor in anchors],
            "supportedNpcPresenceSources": list(NPC_PRESENCE_SOURCES),
            "scheduleSnapshotVersion": require_schema_version("legacy_life_action_plan"),
            "supportedLifeActionWindows": list(PHASES),
        },
        "townStats": view["townStats"],
    }


def current_player_anchor(world: dict[str, Any]) -> dict[str, Any] | None:
    """返回玩家当前锚点快照，给公共状态和客户端状态统一透出。"""
    player = world.get("player", {})
    anchor_id = str(player.get("anchorId") or "")
    anchor = world.get("anchors", {}).get(anchor_id)
    if not isinstance(anchor, dict):
        return None
    return {
        "id": anchor.get("id"),
        "locationId": anchor.get("locationId"),
        "kind": anchor.get("kind"),
        "screenPosition": anchor.get("screenPosition"),
        "tags": list(anchor.get("tags", [])) if isinstance(anchor.get("tags"), list) else [],
    }
