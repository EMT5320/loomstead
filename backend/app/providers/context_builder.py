from __future__ import annotations

import json
import re
from typing import Any

from app.memory.memory_store import memory_summary
from app.providers.provider_support import FEATURE_DIALOGUE, FEATURE_EVENT_REACTION, FEATURE_NIGHT_REFLECTION
from app.world.world_state import get_relation, living_agents


_PHASE_TO_MONOLOGUE_TAGS: dict[str, tuple[str, ...]] = {
    "morning": ("morning",),
    "noon": ("afternoon",),
    "afternoon": ("afternoon",),
    "evening": ("evening",),
    "night": ("evening",),
}
_GOSSIP_VISIBILITY_SCORES: dict[str, int] = {"town_known": 3, "hidden": 1}
_GOSSIP_PROPAGATION_TRUST_GATE = 55
_GOSSIP_PROPAGATION_MAX_TARGETS = 3
_GOSSIP_PROPAGATION_REASON_MAX_LEN = 120
_GOSSIP_MAX_DEBUG_CANDIDATES = 6
_GOSSIP_SELECTION_RULE_ID = "score_v2"
_GOSSIP_FORBIDDEN_STATE_FIELDS: tuple[str, ...] = (
    "worldStatePatch",
    "townStatsDelta",
    "relationshipDelta",
    "questFlagsDelta",
    "clockDelta",
    "memoryWrites",
)


def build_agent_context(world: dict[str, Any], agent: dict[str, Any], event_store: Any) -> dict[str, Any]:
    """构建单个 Agent 本轮决策所需上下文。"""
    nearby = [
        {"id": other["id"], "name": other["name"], "job": other["job"], "mood": other["status"]["mood"]}
        for other in living_agents(world)
        if other["id"] != agent["id"] and other["locationId"] == agent["locationId"]
    ]
    return {
        "agent": {
            "id": agent["id"],
            "name": agent["name"],
            "genderIdentity": agent.get("genderIdentity"),
            "age": agent["age"],
            "job": agent["job"],
            "personality": agent["personality"],
            "goals": agent["todayGoals"],
            "status": agent["status"],
            "intent": agent["currentIntent"],
        },
        "clock": world["clock"],
        "location": world["locations"][agent["locationId"]],
        "nearby": nearby,
        "memory": memory_summary(agent),
        "townStats": world["townStats"],
        "recentEvents": event_store.list()[-8:],
        "actions": ["moveTo", "talkTo", "work", "buy", "rest", "careFor", "attendEvent", "remember", "planDay"],
    }


def build_prompt_messages(context: dict[str, Any]) -> list[dict[str, str]]:
    """云端 Provider 使用 OpenAI-compatible messages，同时用于完整 debug。"""
    return [
        {"role": "system", "content": "你是 Loomstead 叙事小镇中的居民。请根据角色、关系、记忆和当前地点，自然地选择一个行动或说一句话。输出可为 JSON，也可为自然语言。"},
        {"role": "user", "content": json.dumps(context, ensure_ascii=False, indent=2)},
    ]


def build_player_dialogue_context(world: dict[str, Any], npc: dict[str, Any], player_action: dict[str, Any], event_store: Any) -> dict[str, Any]:
    """构建玩家主动对话时 NPC 回复所需上下文。"""
    player = world["player"]
    location_id = player_action.get("locationId") or player.get("locationId") or npc.get("locationId")
    location = world["locations"].get(location_id) or world["locations"][npc["locationId"]]
    deep_card = npc.get("deepCard") if isinstance(npc.get("deepCard"), dict) else None
    deep_identity = (deep_card or {}).get("identity") or {}
    deep_personality = (deep_card or {}).get("personality") or {}
    return {
        "feature": "player_dialogue",
        "npc": {
            "id": npc["id"],
            "name": npc["name"],
            "genderIdentity": npc.get("genderIdentity"),
            "age": npc["age"],
            "job": npc["job"],
            "personality": npc["personality"],
            "goals": npc["todayGoals"],
            "status": npc["status"],
            "memory": memory_summary(npc),
            "voiceStyle": deep_identity.get("voiceStyle", ""),
            "archetype": deep_identity.get("archetype", ""),
            "speechQuirks": list(deep_personality.get("speechQuirks", [])),
            "innerContradiction": deep_personality.get("innerContradiction", ""),
        },
        "player": {
            "id": player["id"],
            "name": player["name"],
            "locationId": player["locationId"],
            "knownNpcs": player.get("knownNpcs", []),
            "questFlags": player.get("questFlags", {}),
        },
        "playerAction": {
            "type": player_action.get("type", "talk"),
            "topic": player_action.get("topic") or "free_talk",
            "message": player_action.get("message") or "你好，我刚搬到小镇。",
        },
        "clock": world["clock"],
        "location": location,
        "relationshipWithPlayer": get_relation(world, "player", npc["id"]),
        "gossipEvidence": _select_gossip_evidence(world, npc, player_action),
        "recentEvents": event_store.list()[-8:],
        "expectedOutput": {
            "speech": "NPC 对玩家说的话",
            "memory_to_save": "NPC 应写入的一句话主观记忆",
            "memory_evidence_used": "可选；如果引用了 memoryEvidence，请返回被引用的来源、文本摘要和标签",
            "gossip_propagation": "可选；如果引用了 gossipEvidence，请返回 {\"hookId\":\"谣言 id\",\"targetNpcIds\":[\"mira\"],\"direction\":\"seed|amplify|contain\",\"reason\":\"一句话理由\"}",
        },
    }


def build_player_dialogue_messages(context: dict[str, Any]) -> list[dict[str, str]]:
    """玩家对话专用 Prompt，要求模型优先返回可解析 JSON。"""
    system_prompt = build_structured_system_prompt(
        feature=FEATURE_DIALOGUE,
        required_fields=("speech", "memory_to_save"),
        extra_rules=[
            "speech 需像 NPC 当下直接说的话，长度控制在 1-3 句。",
            "memory_to_save 需是 NPC 第一人称主观记忆，长度控制在 1 句。",
            "如果使用了 memoryEvidence，请额外返回 memory_evidence_used，便于客户端展示 NPC 记忆影响。",
            "如果使用了 gossipEvidence，请额外返回 gossip_propagation，字段按 expectedOutput 约定，且 hookId 与 targetNpcIds 只能取自 gossipEvidence。",
        ],
    )
    return [{"role": "system", "content": system_prompt}, {"role": "user", "content": json.dumps(context, ensure_ascii=False, indent=2)}]


def _extract_gossip_keywords(topic: str, message: str) -> set[str]:
    """从对话 topic / message 中提取轻量关键词，用于匹配 gossipHooks。"""
    raw = f"{topic} {message}".lower()
    parts = re.split(r"[^\w\u4e00-\u9fff]+", raw)
    return {part for part in parts if len(part.strip()) >= 2}


def _build_gossip_selection_reasons(
    *,
    visibility: str,
    trust: int,
    matched_known_npcs: list[str],
    keyword_hits: list[str],
) -> list[str]:
    """生成稳定可读的选中理由，便于 debug 与后续传播记录解释。"""
    reasons: list[str] = []
    if visibility == "town_known":
        reasons.append("town_known_public_signal")
    elif visibility == "hidden" and trust >= _GOSSIP_PROPAGATION_TRUST_GATE:
        reasons.append("hidden_but_trust_unlocked")
    elif visibility == "hidden":
        reasons.append("hidden_low_trust_risk")
    if matched_known_npcs:
        reasons.append(f"known_npc_overlap:{','.join(matched_known_npcs)}")
    if keyword_hits:
        reasons.append(f"keyword_hits:{','.join(keyword_hits)}")
    if not reasons:
        reasons.append("fallback_rank_by_visibility")
    return reasons


def _build_gossip_propagation_draft(
    *,
    npc_id: str,
    hook_id: str,
    visibility: str,
    spread_affinity: list[str],
    matched_known_npcs: list[str],
    keyword_hits: list[str],
    trust: int,
) -> dict[str, Any]:
    """生成谣言传播最小闭环的记录草案，供模型按后端约束填写。"""
    primary_targets = matched_known_npcs or spread_affinity
    target_npc_ids = primary_targets[:_GOSSIP_PROPAGATION_MAX_TARGETS]
    direction = "seed"
    if visibility == "town_known":
        direction = "amplify"
    elif trust < _GOSSIP_PROPAGATION_TRUST_GATE:
        direction = "contain"
    return {
        "recordVersion": "gossip-spread-v0",
        "hookId": hook_id,
        "sourceNpcId": npc_id,
        "targetNpcIds": target_npc_ids,
        "direction": direction,
        "trustSnapshot": trust,
        "triggerKeywords": keyword_hits,
        "allowedDirections": ["seed", "amplify", "contain"],
    }


def _build_gossip_candidate_debug_summary(
    scored: list[tuple[int, dict[str, Any]]],
    *,
    picked_ids: set[str],
) -> list[dict[str, Any]]:
    """把候选谣言压成轻量调试摘要，便于前后端直接消费。"""
    summary: list[dict[str, Any]] = []
    for score, item in scored[:_GOSSIP_MAX_DEBUG_CANDIDATES]:
        hook_id = str(item.get("id") or "")
        propagation = item.get("propagationDraft") if isinstance(item.get("propagationDraft"), dict) else {}
        targets = propagation.get("targetNpcIds") if isinstance(propagation.get("targetNpcIds"), list) else []
        reasons = item.get("selectionReasons") if isinstance(item.get("selectionReasons"), list) else []
        summary.append(
            {
                "id": hook_id,
                "picked": hook_id in picked_ids,
                "score": int(score),
                "visibility": str(item.get("visibility") or ""),
                "direction": str(propagation.get("direction") or ""),
                "targetCount": len(targets),
                "reasonHead": str(reasons[0]) if reasons else "",
            }
        )
    return summary


def validate_gossip_propagation_payload(
    payload: Any,
    gossip_evidence: dict[str, Any],
) -> dict[str, Any]:
    """校验 gossip_propagation 回包，保证后端权威约束不被覆盖。"""
    violations: list[str] = []
    normalized: dict[str, Any] = {}
    if not isinstance(payload, dict):
        return {"accepted": False, "violations": ["payload_not_object"], "normalized": normalized}

    item_map: dict[str, dict[str, Any]] = {}
    items = gossip_evidence.get("items")
    if isinstance(items, list):
        for item in items:
            if isinstance(item, dict):
                hook_id = str(item.get("id") or "").strip()
                if hook_id:
                    item_map[hook_id] = item

    hook_id = str(payload.get("hookId") or "").strip()
    if not hook_id:
        violations.append("hookId_missing")
    elif hook_id not in item_map:
        violations.append("hookId_not_in_gossip_evidence")
    normalized["hookId"] = hook_id

    contract = gossip_evidence.get("propagationRecordContract")
    allowed_directions = ["seed", "amplify", "contain"]
    if isinstance(contract, dict):
        direction_enum = contract.get("directionEnum")
        if isinstance(direction_enum, list) and direction_enum:
            allowed_directions = [str(item).strip() for item in direction_enum if str(item).strip()]

    direction = str(payload.get("direction") or "").strip()
    if not direction:
        violations.append("direction_missing")
    elif direction not in allowed_directions:
        violations.append("direction_not_allowed")
    normalized["direction"] = direction

    reason = str(payload.get("reason") or "").strip()
    if not reason:
        violations.append("reason_missing")
    elif len(reason) > _GOSSIP_PROPAGATION_REASON_MAX_LEN:
        violations.append("reason_too_long")
    normalized["reason"] = reason

    raw_targets = payload.get("targetNpcIds")
    targets: list[str] = []
    if not isinstance(raw_targets, list):
        violations.append("targetNpcIds_not_array")
    else:
        seen_targets: set[str] = set()
        for target in raw_targets:
            target_id = str(target).strip()
            if not target_id or target_id in seen_targets:
                continue
            seen_targets.add(target_id)
            targets.append(target_id)
    if not targets:
        violations.append("targetNpcIds_empty")
    normalized["targetNpcIds"] = targets

    if hook_id in item_map:
        hook = item_map[hook_id]
        draft = hook.get("propagationDraft") if isinstance(hook.get("propagationDraft"), dict) else {}
        allowed_targets = draft.get("targetNpcIds")
        if isinstance(allowed_targets, list):
            allowed_set = {str(item).strip() for item in allowed_targets if str(item).strip()}
            invalid_targets = [item for item in targets if item not in allowed_set]
            if invalid_targets:
                violations.append(f"targetNpcIds_out_of_allowed_scope:{','.join(invalid_targets)}")

    forbidden_hits = [field for field in _GOSSIP_FORBIDDEN_STATE_FIELDS if field in payload]
    if forbidden_hits:
        violations.append(f"forbidden_state_fields:{','.join(forbidden_hits)}")

    return {
        "accepted": not violations,
        "violations": violations,
        "normalized": normalized,
    }


def _select_gossip_evidence(
    world: dict[str, Any],
    npc: dict[str, Any],
    player_action: dict[str, Any],
    *,
    limit: int = 3,
) -> dict[str, Any]:
    """从 NPC 深度卡 gossipHooks 中挑选本轮对话可用的谣言证据。"""
    deep_card = npc.get("deepCard") if isinstance(npc.get("deepCard"), dict) else {}
    hooks = deep_card.get("gossipHooks") if isinstance(deep_card.get("gossipHooks"), list) else []
    topic = str(player_action.get("topic") or "")
    message = str(player_action.get("message") or "")
    keywords = _extract_gossip_keywords(topic, message)
    known_npcs = {
        str(item)
        for item in world.get("player", {}).get("knownNpcs", [])
        if isinstance(item, str)
    }
    relation = get_relation(world, "player", str(npc.get("id") or ""))
    trust = int(relation.get("trust", 0))

    scored: list[tuple[int, dict[str, Any]]] = []
    npc_id = str(npc.get("id") or "")
    for hook in hooks:
        if not isinstance(hook, dict):
            continue
        hook_id = str(hook.get("id") or "").strip()
        summary = str(hook.get("summary") or "").strip()
        visibility = str(hook.get("visibility") or "").strip()
        spread_affinity = {
            str(agent_id).strip()
            for agent_id in hook.get("spreadAffinity", [])
            if str(agent_id).strip()
        }
        if not hook_id or not summary:
            continue

        score = _GOSSIP_VISIBILITY_SCORES.get(visibility, 0)
        matched_known_npcs = sorted(spread_affinity.intersection(known_npcs))
        score += min(len(matched_known_npcs), 2)
        if visibility == "hidden" and trust >= _GOSSIP_PROPAGATION_TRUST_GATE:
            score += 1

        haystack = f"{hook_id} {summary}".lower()
        keyword_hits = sorted(keyword for keyword in keywords if keyword in haystack)
        score += min(len(keyword_hits), 3)

        selection_reasons = _build_gossip_selection_reasons(
            visibility=visibility,
            trust=trust,
            matched_known_npcs=matched_known_npcs,
            keyword_hits=keyword_hits,
        )
        spread_affinity_sorted = sorted(spread_affinity)
        propagation_draft = _build_gossip_propagation_draft(
            npc_id=npc_id,
            hook_id=hook_id,
            visibility=visibility,
            spread_affinity=spread_affinity_sorted,
            matched_known_npcs=matched_known_npcs,
            keyword_hits=keyword_hits,
            trust=trust,
        )
        scored.append(
            (
                score,
                {
                    "id": hook_id,
                    "summary": summary,
                    "visibility": visibility,
                    "spreadAffinity": spread_affinity_sorted,
                    "matchedKnownNpcs": matched_known_npcs,
                    "keywordHits": keyword_hits,
                    "selectionReasons": selection_reasons,
                    "propagationDraft": propagation_draft,
                    "score": score,
                },
            )
        )

    query = " ".join(part for part in (topic, message) if part).strip()
    contract = {
        "recordVersion": "gossip-spread-v0",
        "requiredFields": ["hookId", "targetNpcIds", "direction", "reason"],
        "directionEnum": ["seed", "amplify", "contain"],
        "forbiddenWorldStateFields": list(_GOSSIP_FORBIDDEN_STATE_FIELDS),
        "validator": "validate_gossip_propagation_payload",
        "notes": [
            "hookId 只能使用 gossipEvidence.items 中提供的 id",
            "targetNpcIds 只能从对应条目的 propagationDraft.targetNpcIds 中选择",
            "gossip_propagation 只用于传播记录，不允许携带世界状态修改字段",
        ],
    }
    selection_meta = {
        "trustWithPlayer": trust,
        "knownNpcCount": len(known_npcs),
        "keywordCount": len(keywords),
        "contractVersion": contract["recordVersion"],
        "selectionRule": _GOSSIP_SELECTION_RULE_ID,
        "candidateCount": len(scored),
    }

    if not scored:
        return {
            "query": query,
            "keywords": sorted(keywords),
            "selectionMeta": selection_meta,
            "propagationRecordContract": contract,
            "candidateDebugSummary": [],
            "items": [],
        }

    scored.sort(
        key=lambda item: (
            -int(item[0]),
            -_GOSSIP_VISIBILITY_SCORES.get(str(item[1].get("visibility") or ""), 0),
            str(item[1].get("id") or ""),
        )
    )
    picked = [item for score, item in scored if score > 0][:limit]
    if not picked:
        picked = [item for _, item in scored[:limit]]
    picked_ids = {str(item.get("id") or "") for item in picked}
    selection_meta["pickedCount"] = len(picked)
    return {
        "query": query,
        "keywords": sorted(keywords),
        "selectionMeta": selection_meta,
        "propagationRecordContract": contract,
        "candidateDebugSummary": _build_gossip_candidate_debug_summary(scored, picked_ids=picked_ids),
        "items": picked,
    }


def build_event_reaction_context(
    world: dict[str, Any],
    event: dict[str, Any],
    outcome: dict[str, Any],
    choice: str,
    event_store: Any,
) -> dict[str, Any]:
    """构建事件结算后 NPC 即时反应所需上下文。"""
    participant_ids = [agent_id for agent_id in event.get("participants", []) if agent_id in world["agents"]]
    return {
        "feature": FEATURE_EVENT_REACTION,
        "event": {
            "id": event.get("id"),
            "title": event.get("title"),
            "summary": event.get("summary"),
            "choice": choice,
            "choiceLabel": outcome.get("choiceLabel"),
            "outcomeSummary": outcome.get("summary"),
        },
        "player": {"id": world["player"]["id"], "name": world["player"]["name"], "questFlags": world["player"].get("questFlags", {})},
        "participants": [_agent_brief(world["agents"][agent_id]) for agent_id in participant_ids],
        "relationsWithPlayer": {agent_id: get_relation(world, "player", agent_id) for agent_id in participant_ids},
        "clock": world["clock"],
        "recentEvents": event_store.list()[-10:],
        "expectedOutput": {
            "dialogue": [{"agentId": "参与事件的 NPC id", "speech": "NPC 对玩家或现场说的话"}],
        },
    }


def build_event_reaction_messages(context: dict[str, Any]) -> list[dict[str, str]]:
    """事件反应 Prompt，要求输出可解析的多 NPC 台词 JSON。"""
    system_prompt = build_structured_system_prompt(
        feature=FEATURE_EVENT_REACTION,
        required_fields=("dialogue",),
        extra_rules=[
            "dialogue 必须是数组，长度 1-3。",
            "数组项必须包含 agentId 和 speech。",
            "speech 保持短句风格，贴合角色语气。",
        ],
    )
    return [{"role": "system", "content": system_prompt}, {"role": "user", "content": json.dumps(context, ensure_ascii=False, indent=2)}]


def build_night_reflection_context(
    world: dict[str, Any],
    event: dict[str, Any],
    outcome: dict[str, Any],
    choice: str,
    event_store: Any,
) -> dict[str, Any]:
    """构建夜间反思所需上下文，用于写入长期记忆。"""
    target_ids = [agent_id for agent_id in event.get("participants", []) if agent_id in world["agents"]][:4]
    phase = str(world.get("clock", {}).get("phase", ""))
    event_location_id = str(event.get("locationId") or "")
    agent_briefs = [
        _agent_brief(
            world["agents"][agent_id],
            night_reflection_hints={"phase": phase, "eventLocationId": event_location_id},
        )
        for agent_id in target_ids
    ]
    monologue_evidence = [
        {
            "agentId": brief.get("id"),
            "agentName": brief.get("name"),
            "seeds": brief.get("nightReflectionMonologueSeeds", []),
        }
        for brief in agent_briefs
        if brief.get("nightReflectionMonologueSeeds")
    ]
    return {
        "feature": FEATURE_NIGHT_REFLECTION,
        "event": {
            "id": event.get("id"),
            "title": event.get("title"),
            "choice": choice,
            "choiceLabel": outcome.get("choiceLabel"),
            "outcomeSummary": outcome.get("summary"),
        },
        "agents": agent_briefs,
        "monologueEvidence": monologue_evidence,
        "relationsWithPlayer": {agent_id: get_relation(world, "player", agent_id) for agent_id in target_ids},
        "clock": world["clock"],
        "recentEvents": event_store.list()[-10:],
        "expectedOutput": {
            "reflections": [{"agentId": "需要写入反思的 NPC id", "text": "一段第一人称夜间反思"}],
            "monologue_used": "可选；如果引用了 monologueEvidence，请返回被引用的独白种子 id",
        },
    }


def build_night_reflection_messages(context: dict[str, Any]) -> list[dict[str, str]]:
    """夜间反思 Prompt，要求输出适合记忆系统保存的 JSON。"""
    system_prompt = build_structured_system_prompt(
        feature=FEATURE_NIGHT_REFLECTION,
        required_fields=("reflections",),
        extra_rules=[
            "reflections 必须是数组，长度 2-4。",
            "数组项必须包含 agentId 和 text。",
            "text 需为第一人称主观反思，控制在 1-3 句。",
            "优先参考 monologueEvidence 或 agents[].nightReflectionMonologueSeeds，让反思贴合角色内在独白。",
        ],
    )
    return [{"role": "system", "content": system_prompt}, {"role": "user", "content": json.dumps(context, ensure_ascii=False, indent=2)}]


def build_structured_system_prompt(
    *,
    feature: str,
    required_fields: tuple[str, ...],
    extra_rules: list[str] | None = None,
) -> str:
    """统一生成结构化输出系统提示词，降低多功能 Prompt 维护成本。"""
    field_list = "、".join(required_fields)
    rules = extra_rules or []
    rules_text = "\n".join(f"- {item}" for item in rules)
    base = [
        "你是生活模拟叙事运行时《Loomstead》中的居民智能体。",
        f"当前功能：{feature}。",
        f"请仅输出 JSON 对象，必须包含字段：{field_list}。",
        "禁止输出 Markdown 代码块、解释文本和多余键名。",
    ]
    if rules_text:
        base.append("补充规则：")
        base.append(rules_text)
    return "\n".join(base)


def _agent_brief(agent: dict[str, Any], *, night_reflection_hints: dict[str, Any] | None = None) -> dict[str, Any]:
    """提取 Prompt 所需的 NPC 摘要，避免把完整运行态塞进 messages。"""
    brief: dict[str, Any] = {
        "id": agent["id"],
        "name": agent["name"],
        "job": agent["job"],
        "personality": agent.get("personality", []),
        "status": agent.get("status", {}),
        "goals": agent.get("todayGoals", []),
        "memory": memory_summary(agent),
    }
    deep_card = agent.get("deepCard")
    if isinstance(deep_card, dict):
        identity = deep_card.get("identity") or {}
        personality = deep_card.get("personality") or {}
        brief["voiceStyle"] = identity.get("voiceStyle", "")
        brief["archetype"] = identity.get("archetype", "")
        brief["speechQuirks"] = list(personality.get("speechQuirks", []))
        brief["innerContradiction"] = personality.get("innerContradiction", "")
        if night_reflection_hints is not None:
            brief["nightReflectionMonologueSeeds"] = _select_night_reflection_monologues(
                agent,
                phase=str(night_reflection_hints.get("phase", "")),
                event_location_id=str(night_reflection_hints.get("eventLocationId", "")),
            )
    return brief


def _select_night_reflection_monologues(
    agent: dict[str, Any],
    *,
    phase: str,
    event_location_id: str,
    limit: int = 3,
) -> list[dict[str, Any]]:
    """按时段、地点和情绪筛出夜间反思可用的独白种子。"""
    deep_card = agent.get("deepCard") if isinstance(agent.get("deepCard"), dict) else {}
    seeds = deep_card.get("monologueSeeds") if isinstance(deep_card.get("monologueSeeds"), list) else []
    if not seeds:
        return []

    location_id = str(agent.get("locationId") or event_location_id or "")
    mood = str(agent.get("status", {}).get("mood", "")).lower()
    mood_tag = "high_mood" if mood in {"happy", "excited", "calm"} else "low_mood"
    phase_tags = set(_PHASE_TO_MONOLOGUE_TAGS.get(phase, (phase,)))
    scored: list[tuple[int, dict[str, Any]]] = []
    for item in seeds:
        if not isinstance(item, dict):
            continue
        text = str(item.get("text") or "").strip()
        if not text:
            continue
        tags = {str(tag) for tag in item.get("contextTags", [])}
        score = 0
        if "post_event" in tags:
            score += 3
        if phase_tags.intersection(tags):
            score += 2
        if location_id and location_id in tags:
            score += 2
        if mood_tag in tags:
            score += 1
        if "any" in tags:
            score += 1
        scored.append(
            (
                score,
                {
                    "id": str(item.get("id", "")),
                    "contextTags": sorted(tags),
                    "text": text,
                },
            )
        )

    if not scored:
        return []

    scored.sort(key=lambda item: (item[0], item[1].get("id", "")), reverse=True)
    picked = [item for score, item in scored if score > 0][:limit]
    if picked:
        return picked
    return [item for _, item in scored[:limit]]
