"""NPC 深度卡加载器：JSON → 结构化校验 → 运行时字典。

仅依赖标准库。校验失败统一抛出 CodexValidationError，附带文件路径与字段路径，
便于 scripts/check_npc_codex.py 与 runtime 集成共享同一份错误信息。
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Iterable

from app.content.codex_schema import (
    AssetRefs,
    CURRENT_SCHEMA_VERSION,
    DailyRumorBeat,
    GiftReactionTier,
    GiftReactions,
    Goals,
    GossipHook,
    Identity,
    LifeActionSeed,
    MonologueSeed,
    HeuristicSeed,
    MotivationProfile,
    NpcDeepCard,
    Personality,
    Preference,
    RelationshipBeatSeed,
    RelationshipStage,
    Secret,
    StageThreshold,
)

NPC_CODEX_DIR = Path(__file__).resolve().parent / "data" / "npc"

_VALID_GIFT_TIERS = ("loved", "liked", "neutral", "disliked")
_REQUIRED_TOP_LEVEL_KEYS = (
    "schemaVersion",
    "id",
    "displayName",
    "shortName",
    "identity",
    "personality",
    "goals",
    "motivationProfile",
    "capabilityPreferences",
    "heuristicSeeds",
    "secrets",
    "likes",
    "dislikes",
    "relationshipStages",
    "monologueSeeds",
    "giftReactions",
    "gossipHooks",
    "assetRefs",
)
_MIN_MONOLOGUE_SEEDS = 8
_MIN_SECRETS = 2
_MIN_STAGES = 4
_MAX_STAGES = 6
_MIN_FALLBACK_PER_TIER = 2
_VALID_GOSSIP_VISIBILITY = {"hidden", "town_known"}
_VALID_TIME_WINDOWS = {"morning", "afternoon", "evening", "night"}
_VALID_RELATIONSHIP_DIRECTIONS = {"up", "steady", "down"}


class CodexValidationError(ValueError):
    """NPC 深度卡校验失败。"""


def _require(condition: bool, message: str) -> None:
    """断言失败时抛出 CodexValidationError，统一错误信号。"""
    if not condition:
        raise CodexValidationError(message)


def _ensure_keys(data: dict[str, Any], required: Iterable[str], context: str) -> None:
    """确保必需字段全部存在，缺失时抛出包含上下文的错误。"""
    missing = [key for key in required if key not in data]
    _require(not missing, f"{context} 缺少字段：{', '.join(missing)}")


def _as_str_tuple(values: Any, context: str) -> tuple[str, ...]:
    """把 JSON 数组转为字符串元组，非字符串成员立刻报错。"""
    _require(isinstance(values, list), f"{context} 必须是数组")
    out: list[str] = []
    for index, item in enumerate(values):
        _require(isinstance(item, str), f"{context}[{index}] 必须是字符串")
        out.append(item)
    return tuple(out)


def _build_identity(raw: Any, context: str) -> Identity:
    """构造 Identity，并校验必填字段。"""
    _require(isinstance(raw, dict), f"{context} 必须是对象")
    _ensure_keys(raw, ("age", "gender", "job", "archetype", "voiceStyle", "speechRegister"), context)
    _require(isinstance(raw["age"], int) and raw["age"] > 0, f"{context}.age 必须是正整数")
    return Identity(
        age=int(raw["age"]),
        gender=str(raw["gender"]),
        job=str(raw["job"]),
        archetype=str(raw["archetype"]),
        voice_style=str(raw["voiceStyle"]),
        speech_register=str(raw["speechRegister"]),
    )


def _build_personality(raw: Any, context: str) -> Personality:
    """构造 Personality 并校验最少条数。"""
    _require(isinstance(raw, dict), f"{context} 必须是对象")
    _ensure_keys(
        raw,
        ("coreTraits", "innerContradiction", "speechQuirks", "stressTriggers", "comforts"),
        context,
    )
    quirks = _as_str_tuple(raw["speechQuirks"], f"{context}.speechQuirks")
    _require(len(quirks) >= 2, f"{context}.speechQuirks 至少 2 条")
    _require(str(raw["innerContradiction"]).strip() != "", f"{context}.innerContradiction 不能为空")
    return Personality(
        core_traits=_as_str_tuple(raw["coreTraits"], f"{context}.coreTraits"),
        inner_contradiction=str(raw["innerContradiction"]),
        speech_quirks=quirks,
        stress_triggers=_as_str_tuple(raw["stressTriggers"], f"{context}.stressTriggers"),
        comforts=_as_str_tuple(raw["comforts"], f"{context}.comforts"),
    )


def _build_goals(raw: Any, context: str) -> Goals:
    """构造 Goals。"""
    _require(isinstance(raw, dict), f"{context} 必须是对象")
    _ensure_keys(raw, ("longTerm", "today", "fears"), context)
    return Goals(
        long_term=_as_str_tuple(raw["longTerm"], f"{context}.longTerm"),
        today=_as_str_tuple(raw["today"], f"{context}.today"),
        fears=_as_str_tuple(raw["fears"], f"{context}.fears"),
    )


def _build_motivation_profile(raw: Any, context: str) -> MotivationProfile:
    """构造 Phase 2 动机系统占位，允许内容期再填实际权重。"""
    _require(isinstance(raw, dict), f"{context} 必须是对象")
    needs = raw.get("needs", {})
    personality_modifiers = raw.get("personalityModifiers", {})
    _require(isinstance(needs, dict), f"{context}.needs 必须是对象")
    _require(isinstance(personality_modifiers, dict), f"{context}.personalityModifiers 必须是对象")
    for need_id, config in needs.items():
        _require(isinstance(need_id, str) and need_id.strip(), f"{context}.needs 存在空需求 id")
        _require(isinstance(config, dict), f"{context}.needs.{need_id} 必须是对象")
    return MotivationProfile(
        needs={str(key): dict(value) for key, value in needs.items()},
        personality_modifiers=dict(personality_modifiers),
    )


def _build_capability_preferences(raw: Any, context: str) -> dict[str, dict[str, Any]]:
    """构造工具偏好占位，键为 tool_id，值为权重修正对象。"""
    _require(isinstance(raw, dict), f"{context} 必须是对象")
    preferences: dict[str, dict[str, Any]] = {}
    for tool_id, config in raw.items():
        _require(isinstance(tool_id, str) and tool_id.strip(), f"{context} 存在空 tool_id")
        _require(isinstance(config, dict), f"{context}.{tool_id} 必须是对象")
        preferences[str(tool_id)] = dict(config)
    return preferences


def _build_heuristic_seed(raw: Any, context: str) -> HeuristicSeed:
    """构造设计师启发式种子；空数组是 Phase 2 启动占位。"""
    _require(isinstance(raw, dict), f"{context} 必须是对象")
    _ensure_keys(raw, ("heuristic_id", "trigger_pattern", "adjustment", "confidence", "narrative"), context)
    heuristic_id = str(raw["heuristic_id"]).strip()
    trigger_pattern = raw["trigger_pattern"]
    adjustment = raw["adjustment"]
    confidence = raw["confidence"]
    narrative = str(raw["narrative"]).strip()
    _require(heuristic_id != "", f"{context}.heuristic_id 不能为空")
    _require(isinstance(trigger_pattern, dict), f"{context}.trigger_pattern 必须是对象")
    _require(isinstance(adjustment, dict), f"{context}.adjustment 必须是对象")
    _require(isinstance(confidence, (int, float)), f"{context}.confidence 必须是数字")
    _require(0 <= float(confidence) <= 1, f"{context}.confidence 必须在 0-1 区间")
    _require(narrative != "", f"{context}.narrative 不能为空")
    return HeuristicSeed(
        heuristic_id=heuristic_id,
        trigger_pattern=dict(trigger_pattern),
        adjustment=dict(adjustment),
        confidence=float(confidence),
        narrative=narrative,
    )


def _build_secret(raw: Any, context: str) -> Secret:
    """构造单条秘密。"""
    _require(isinstance(raw, dict), f"{context} 必须是对象")
    _ensure_keys(raw, ("id", "visibility", "summary", "unlockAfter"), context)
    return Secret(
        secret_id=str(raw["id"]),
        visibility=str(raw["visibility"]),
        summary=str(raw["summary"]),
        unlock_after=str(raw["unlockAfter"]),
        tags=_as_str_tuple(raw.get("tags", []), f"{context}.tags"),
    )


def _build_preference(raw: Any, context: str) -> Preference:
    """构造 likes / dislikes 单条目。"""
    _require(isinstance(raw, dict), f"{context} 必须是对象")
    _ensure_keys(raw, ("tag", "weight"), context)
    weight = raw["weight"]
    _require(isinstance(weight, int) and 1 <= weight <= 3, f"{context}.weight 必须是 1-3 之间的整数")
    items = _as_str_tuple(raw.get("items", []), f"{context}.items")
    return Preference(tag=str(raw["tag"]), weight=int(weight), items=items)


def _build_threshold(raw: Any, context: str) -> StageThreshold:
    """构造阶段门槛，conflictMax 为可选。"""
    _require(isinstance(raw, dict), f"{context} 必须是对象")
    affection = int(raw.get("affection", 0))
    trust = int(raw.get("trust", 0))
    _require(0 <= affection <= 100, f"{context}.affection 必须在 0-100 区间")
    _require(0 <= trust <= 100, f"{context}.trust 必须在 0-100 区间")
    conflict_max: int | None = None
    if "conflictMax" in raw:
        conflict_max = int(raw["conflictMax"])
        _require(0 <= conflict_max <= 100, f"{context}.conflictMax 必须在 0-100 区间")
    return StageThreshold(affection=affection, trust=trust, conflict_max=conflict_max)


def _build_stage(raw: Any, context: str) -> RelationshipStage:
    """构造单个关系阶段。"""
    _require(isinstance(raw, dict), f"{context} 必须是对象")
    _ensure_keys(raw, ("stage", "label", "threshold"), context)
    return RelationshipStage(
        stage=str(raw["stage"]),
        label=str(raw["label"]),
        threshold=_build_threshold(raw["threshold"], f"{context}.threshold"),
        unlocks=_as_str_tuple(raw.get("unlocks", []), f"{context}.unlocks"),
    )


def _build_monologue(raw: Any, context: str) -> MonologueSeed:
    """构造独白种子。"""
    _require(isinstance(raw, dict), f"{context} 必须是对象")
    _ensure_keys(raw, ("id", "contextTags", "text"), context)
    text = str(raw["text"])
    _require(text.strip() != "", f"{context}.text 不能为空")
    return MonologueSeed(
        monologue_id=str(raw["id"]),
        context_tags=_as_str_tuple(raw["contextTags"], f"{context}.contextTags"),
        text=text,
    )


def _build_gift_tier(raw: Any, tier_name: str, context: str) -> GiftReactionTier:
    """构造单档礼物反应。"""
    _require(isinstance(raw, dict), f"{context} 必须是对象")
    fallback_pool = _as_str_tuple(raw.get("fallbackSpeechPool", []), f"{context}.fallbackSpeechPool")
    _require(
        len(fallback_pool) >= _MIN_FALLBACK_PER_TIER,
        f"{context}.fallbackSpeechPool 至少 {_MIN_FALLBACK_PER_TIER} 条",
    )
    delta_raw = raw.get("deltaModifier", {})
    _require(isinstance(delta_raw, dict), f"{context}.deltaModifier 必须是对象")
    delta: dict[str, int] = {}
    for key, value in delta_raw.items():
        _require(isinstance(value, int), f"{context}.deltaModifier.{key} 必须是整数")
        delta[str(key)] = int(value)
    return GiftReactionTier(
        tier=tier_name,
        tag_any=_as_str_tuple(raw.get("tagAny", []), f"{context}.tagAny"),
        item_any=_as_str_tuple(raw.get("itemAny", []), f"{context}.itemAny"),
        delta_modifier=delta,
        fallback_speech_pool=fallback_pool,
    )


def _build_gift_reactions(raw: Any, context: str) -> GiftReactions:
    """构造完整四档反应。"""
    _require(isinstance(raw, dict), f"{context} 必须是对象")
    missing = [tier for tier in _VALID_GIFT_TIERS if tier not in raw]
    _require(not missing, f"{context} 缺少反应档：{', '.join(missing)}")
    return GiftReactions(
        loved=_build_gift_tier(raw["loved"], "loved", f"{context}.loved"),
        liked=_build_gift_tier(raw["liked"], "liked", f"{context}.liked"),
        neutral=_build_gift_tier(raw["neutral"], "neutral", f"{context}.neutral"),
        disliked=_build_gift_tier(raw["disliked"], "disliked", f"{context}.disliked"),
    )


def _build_gossip_hook(raw: Any, context: str) -> GossipHook:
    """构造单条谣言钩子。"""
    _require(isinstance(raw, dict), f"{context} 必须是对象")
    _ensure_keys(raw, ("id", "summary", "visibility"), context)
    hook_id = str(raw["id"]).strip()
    summary = str(raw["summary"]).strip()
    visibility = str(raw["visibility"]).strip()
    _require(hook_id != "", f"{context}.id 不能为空")
    _require(summary != "", f"{context}.summary 不能为空")
    _require(
        visibility in _VALID_GOSSIP_VISIBILITY,
        f"{context}.visibility 必须是 hidden 或 town_known，当前为 {visibility}",
    )
    spread_affinity = _as_str_tuple(raw.get("spreadAffinity", []), f"{context}.spreadAffinity")
    _require(spread_affinity, f"{context}.spreadAffinity 至少 1 项")
    return GossipHook(
        hook_id=hook_id,
        summary=summary,
        visibility=visibility,
        spread_affinity=spread_affinity,
    )


def _build_asset_refs(raw: Any, context: str) -> AssetRefs:
    """构造资产引用集合。"""
    _require(isinstance(raw, dict), f"{context} 必须是对象")
    expressions_raw = raw.get("expressions", {})
    _require(isinstance(expressions_raw, dict), f"{context}.expressions 必须是对象")
    expressions = {str(k): str(v) for k, v in expressions_raw.items()}
    return AssetRefs(
        portrait=str(raw.get("portrait", "")),
        expressions=expressions,
        map_sprite=str(raw.get("mapSprite", "")),
    )


def _build_life_action_seed(raw: Any, context: str) -> LifeActionSeed:
    """构造 Day 1 日常行动素材。"""
    _require(isinstance(raw, dict), f"{context} 必须是对象")
    _ensure_keys(raw, ("id", "timeWindow", "summary", "intentTags"), context)
    action_id = str(raw["id"]).strip()
    time_window = str(raw["timeWindow"]).strip()
    summary = str(raw["summary"]).strip()
    _require(action_id != "", f"{context}.id 不能为空")
    _require(time_window in _VALID_TIME_WINDOWS, f"{context}.timeWindow 非法：{time_window}")
    _require(summary != "", f"{context}.summary 不能为空")
    return LifeActionSeed(
        action_id=action_id,
        time_window=time_window,
        summary=summary,
        intent_tags=_as_str_tuple(raw["intentTags"], f"{context}.intentTags"),
        location_hints=_as_str_tuple(raw.get("locationHints", []), f"{context}.locationHints"),
        related_npc_ids=_as_str_tuple(raw.get("relatedNpcIds", []), f"{context}.relatedNpcIds"),
    )


def _build_daily_rumor_beat(raw: Any, context: str) -> DailyRumorBeat:
    """构造 Day 1 谣言节拍素材。"""
    _require(isinstance(raw, dict), f"{context} 必须是对象")
    _ensure_keys(raw, ("id", "visibility", "cue", "spreadTargets"), context)
    beat_id = str(raw["id"]).strip()
    visibility = str(raw["visibility"]).strip()
    cue = str(raw["cue"]).strip()
    _require(beat_id != "", f"{context}.id 不能为空")
    _require(visibility in _VALID_GOSSIP_VISIBILITY, f"{context}.visibility 非法：{visibility}")
    _require(cue != "", f"{context}.cue 不能为空")
    spread_targets = _as_str_tuple(raw["spreadTargets"], f"{context}.spreadTargets")
    _require(len(spread_targets) >= 1, f"{context}.spreadTargets 至少 1 项")
    return DailyRumorBeat(
        beat_id=beat_id,
        visibility=visibility,
        cue=cue,
        spread_targets=spread_targets,
        tags=_as_str_tuple(raw.get("tags", []), f"{context}.tags"),
    )


def _build_relationship_beat_seed(raw: Any, context: str) -> RelationshipBeatSeed:
    """构造 Day 1 关系节拍素材。"""
    _require(isinstance(raw, dict), f"{context} 必须是对象")
    _ensure_keys(raw, ("id", "stageHint", "trigger", "direction", "summary"), context)
    beat_id = str(raw["id"]).strip()
    stage_hint = str(raw["stageHint"]).strip()
    trigger = str(raw["trigger"]).strip()
    direction = str(raw["direction"]).strip()
    summary = str(raw["summary"]).strip()
    _require(beat_id != "", f"{context}.id 不能为空")
    _require(stage_hint != "", f"{context}.stageHint 不能为空")
    _require(trigger != "", f"{context}.trigger 不能为空")
    _require(direction in _VALID_RELATIONSHIP_DIRECTIONS, f"{context}.direction 非法：{direction}")
    _require(summary != "", f"{context}.summary 不能为空")
    return RelationshipBeatSeed(
        beat_id=beat_id,
        stage_hint=stage_hint,
        trigger=trigger,
        direction=direction,
        summary=summary,
        tags=_as_str_tuple(raw.get("tags", []), f"{context}.tags"),
    )


def _validate_stages(stages: tuple[RelationshipStage, ...], context: str) -> None:
    """关系阶段必须按 affection 升序，stage_0 阈值为 0。"""
    _require(
        _MIN_STAGES <= len(stages) <= _MAX_STAGES,
        f"{context} 必须有 {_MIN_STAGES}-{_MAX_STAGES} 个阶段，当前 {len(stages)}",
    )
    _require(stages[0].stage == "stage_0", f"{context}[0].stage 必须为 stage_0")
    _require(
        stages[0].threshold.affection == 0 and stages[0].threshold.trust == 0,
        f"{context}[0] 阈值必须全部为 0",
    )
    for index in range(1, len(stages)):
        prev = stages[index - 1]
        curr = stages[index]
        _require(
            curr.threshold.affection >= prev.threshold.affection,
            f"{context}[{index}] affection 阈值必须 ≥ 前一阶段",
        )
        _require(
            curr.threshold.trust >= prev.threshold.trust,
            f"{context}[{index}] trust 阈值必须 ≥ 前一阶段",
        )


def _validate_secret_unlocks(
    secrets: tuple[Secret, ...],
    stages: tuple[RelationshipStage, ...],
    context: str,
) -> None:
    """secrets.unlockAfter 必须引用合法 stage id；至少 1 条 stage_3+ 解锁。"""
    valid_stage_ids = {stage.stage for stage in stages}
    advanced_stage_ids = {stage.stage for stage in stages if stage.stage >= "stage_3"}
    has_advanced = False
    for index, secret in enumerate(secrets):
        _require(
            secret.unlock_after in valid_stage_ids,
            f"{context}[{index}].unlockAfter 必须是当前 NPC 的合法 stage id：{secret.unlock_after}",
        )
        if secret.unlock_after in advanced_stage_ids:
            has_advanced = True
    _require(has_advanced, f"{context} 至少 1 条 secret 应在 stage_3 及以后解锁")


def _validate_unlocks_references(
    stages: tuple[RelationshipStage, ...],
    secrets: tuple[Secret, ...],
    monologues: tuple[MonologueSeed, ...],
    context: str,
) -> None:
    """阶段 unlocks 中的 secret_* / monologue_* 必须存在，topic_/romance_seed_ 不强制存在。"""
    secret_ids = {item.secret_id for item in secrets}
    monologue_ids = {item.monologue_id for item in monologues}
    for stage in stages:
        for unlock_id in stage.unlocks:
            if unlock_id.startswith("secret_"):
                _require(
                    unlock_id in secret_ids,
                    f"{context} 阶段 {stage.stage} unlocks 引用了未定义的 secret：{unlock_id}",
                )
            elif unlock_id.startswith("monologue_"):
                _require(
                    unlock_id in monologue_ids,
                    f"{context} 阶段 {stage.stage} unlocks 引用了未定义的 monologue：{unlock_id}",
                )


def parse_npc_deep_card(data: dict[str, Any], *, source: str = "<inline>") -> NpcDeepCard:
    """把 JSON 字典解析为 NpcDeepCard，并执行结构 + 一致性校验。"""
    context = f"npc-codex[{source}]"
    _require(isinstance(data, dict), f"{context} 顶层必须是对象")
    _ensure_keys(data, _REQUIRED_TOP_LEVEL_KEYS, context)

    schema_version = data["schemaVersion"]
    _require(
        isinstance(schema_version, int) and schema_version == CURRENT_SCHEMA_VERSION,
        f"{context}.schemaVersion 必须为 {CURRENT_SCHEMA_VERSION}",
    )

    npc_id = str(data["id"]).strip()
    _require(npc_id != "", f"{context}.id 不能为空")

    identity = _build_identity(data["identity"], f"{context}.identity")
    personality = _build_personality(data["personality"], f"{context}.personality")
    goals = _build_goals(data["goals"], f"{context}.goals")
    motivation_profile = _build_motivation_profile(data["motivationProfile"], f"{context}.motivationProfile")
    capability_preferences = _build_capability_preferences(
        data["capabilityPreferences"], f"{context}.capabilityPreferences"
    )
    raw_heuristic_seeds = data["heuristicSeeds"]
    _require(isinstance(raw_heuristic_seeds, list), f"{context}.heuristicSeeds 必须是数组")
    heuristic_seeds = tuple(
        _build_heuristic_seed(item, f"{context}.heuristicSeeds[{i}]")
        for i, item in enumerate(raw_heuristic_seeds)
    )

    raw_secrets = data["secrets"]
    _require(isinstance(raw_secrets, list), f"{context}.secrets 必须是数组")
    _require(len(raw_secrets) >= _MIN_SECRETS, f"{context}.secrets 至少 {_MIN_SECRETS} 条")
    secrets = tuple(_build_secret(item, f"{context}.secrets[{i}]") for i, item in enumerate(raw_secrets))

    raw_likes = data["likes"]
    raw_dislikes = data["dislikes"]
    _require(isinstance(raw_likes, list), f"{context}.likes 必须是数组")
    _require(isinstance(raw_dislikes, list), f"{context}.dislikes 必须是数组")
    likes = tuple(_build_preference(item, f"{context}.likes[{i}]") for i, item in enumerate(raw_likes))
    dislikes = tuple(
        _build_preference(item, f"{context}.dislikes[{i}]") for i, item in enumerate(raw_dislikes)
    )

    raw_stages = data["relationshipStages"]
    _require(isinstance(raw_stages, list), f"{context}.relationshipStages 必须是数组")
    stages = tuple(
        _build_stage(item, f"{context}.relationshipStages[{i}]") for i, item in enumerate(raw_stages)
    )
    _validate_stages(stages, f"{context}.relationshipStages")

    raw_monologues = data["monologueSeeds"]
    _require(isinstance(raw_monologues, list), f"{context}.monologueSeeds 必须是数组")
    _require(
        len(raw_monologues) >= _MIN_MONOLOGUE_SEEDS,
        f"{context}.monologueSeeds 至少 {_MIN_MONOLOGUE_SEEDS} 条",
    )
    monologues = tuple(
        _build_monologue(item, f"{context}.monologueSeeds[{i}]") for i, item in enumerate(raw_monologues)
    )

    gift_reactions = _build_gift_reactions(data["giftReactions"], f"{context}.giftReactions")

    raw_hooks = data["gossipHooks"]
    _require(isinstance(raw_hooks, list), f"{context}.gossipHooks 必须是数组")
    _require(len(raw_hooks) >= 1, f"{context}.gossipHooks 至少 1 条")
    gossip_hooks = tuple(
        _build_gossip_hook(item, f"{context}.gossipHooks[{i}]") for i, item in enumerate(raw_hooks)
    )

    raw_life_action_seeds = data.get("lifeActionSeeds", [])
    _require(isinstance(raw_life_action_seeds, list), f"{context}.lifeActionSeeds 必须是数组")
    life_action_seeds = tuple(
        _build_life_action_seed(item, f"{context}.lifeActionSeeds[{i}]")
        for i, item in enumerate(raw_life_action_seeds)
    )

    raw_daily_rumor_beats = data.get("dailyRumorBeats", [])
    _require(isinstance(raw_daily_rumor_beats, list), f"{context}.dailyRumorBeats 必须是数组")
    daily_rumor_beats = tuple(
        _build_daily_rumor_beat(item, f"{context}.dailyRumorBeats[{i}]")
        for i, item in enumerate(raw_daily_rumor_beats)
    )

    raw_relationship_beat_seeds = data.get("relationshipBeatSeeds", [])
    _require(isinstance(raw_relationship_beat_seeds, list), f"{context}.relationshipBeatSeeds 必须是数组")
    relationship_beat_seeds = tuple(
        _build_relationship_beat_seed(item, f"{context}.relationshipBeatSeeds[{i}]")
        for i, item in enumerate(raw_relationship_beat_seeds)
    )

    asset_refs = _build_asset_refs(data["assetRefs"], f"{context}.assetRefs")

    _validate_secret_unlocks(secrets, stages, f"{context}.secrets")
    _validate_unlocks_references(stages, secrets, monologues, context)

    return NpcDeepCard(
        schema_version=int(schema_version),
        npc_id=npc_id,
        display_name=str(data["displayName"]),
        short_name=str(data["shortName"]),
        identity=identity,
        personality=personality,
        goals=goals,
        motivation_profile=motivation_profile,
        capability_preferences=capability_preferences,
        heuristic_seeds=heuristic_seeds,
        secrets=secrets,
        likes=likes,
        dislikes=dislikes,
        relationship_stages=stages,
        monologue_seeds=monologues,
        gift_reactions=gift_reactions,
        gossip_hooks=gossip_hooks,
        asset_refs=asset_refs,
        life_action_seeds=life_action_seeds,
        daily_rumor_beats=daily_rumor_beats,
        relationship_beat_seeds=relationship_beat_seeds,
    )


def load_npc_deep_card(npc_id: str, *, base_dir: Path | None = None) -> NpcDeepCard:
    """按 NPC id 读取深度卡 JSON 文件并执行校验。"""
    directory = base_dir or NPC_CODEX_DIR
    path = directory / f"{npc_id}.json"
    _require(path.exists(), f"NPC 深度卡文件不存在：{path}")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise CodexValidationError(f"NPC 深度卡 JSON 解析失败：{path}：{error}") from error
    card = parse_npc_deep_card(raw, source=path.name)
    _require(card.npc_id == npc_id, f"NPC 深度卡 id 与文件名不一致：{path.name} vs {card.npc_id}")
    return card


def load_all_npc_deep_cards(*, base_dir: Path | None = None) -> dict[str, NpcDeepCard]:
    """批量加载 data/npc/*.json，文件名作为 NPC id。"""
    directory = base_dir or NPC_CODEX_DIR
    if not directory.exists():
        return {}
    cards: dict[str, NpcDeepCard] = {}
    for path in sorted(directory.glob("*.json")):
        npc_id = path.stem
        cards[npc_id] = load_npc_deep_card(npc_id, base_dir=directory)
    return cards


def to_runtime_dict(card: NpcDeepCard) -> dict[str, Any]:
    """转换为 runtime agent 使用的驼峰字典，挂在 agent['deepCard']。"""
    raw = asdict(card)
    return {
        "schemaVersion": raw["schema_version"],
        "id": raw["npc_id"],
        "displayName": raw["display_name"],
        "shortName": raw["short_name"],
        "identity": {
            "age": raw["identity"]["age"],
            "gender": raw["identity"]["gender"],
            "job": raw["identity"]["job"],
            "archetype": raw["identity"]["archetype"],
            "voiceStyle": raw["identity"]["voice_style"],
            "speechRegister": raw["identity"]["speech_register"],
        },
        "personality": {
            "coreTraits": list(raw["personality"]["core_traits"]),
            "innerContradiction": raw["personality"]["inner_contradiction"],
            "speechQuirks": list(raw["personality"]["speech_quirks"]),
            "stressTriggers": list(raw["personality"]["stress_triggers"]),
            "comforts": list(raw["personality"]["comforts"]),
        },
        "goals": {
            "longTerm": list(raw["goals"]["long_term"]),
            "today": list(raw["goals"]["today"]),
            "fears": list(raw["goals"]["fears"]),
        },
        "motivationProfile": {
            "needs": dict(raw["motivation_profile"]["needs"]),
            "personalityModifiers": dict(raw["motivation_profile"]["personality_modifiers"]),
        },
        "capabilityPreferences": {
            tool_id: dict(config) for tool_id, config in raw["capability_preferences"].items()
        },
        "heuristicSeeds": [
            {
                "heuristic_id": item["heuristic_id"],
                "trigger_pattern": dict(item["trigger_pattern"]),
                "adjustment": dict(item["adjustment"]),
                "confidence": item["confidence"],
                "narrative": item["narrative"],
            }
            for item in raw["heuristic_seeds"]
        ],
        "secrets": [
            {
                "id": secret["secret_id"],
                "visibility": secret["visibility"],
                "summary": secret["summary"],
                "unlockAfter": secret["unlock_after"],
                "tags": list(secret["tags"]),
            }
            for secret in raw["secrets"]
        ],
        "likes": [
            {"tag": item["tag"], "weight": item["weight"], "items": list(item["items"])}
            for item in raw["likes"]
        ],
        "dislikes": [
            {"tag": item["tag"], "weight": item["weight"], "items": list(item["items"])}
            for item in raw["dislikes"]
        ],
        "relationshipStages": [
            {
                "stage": stage["stage"],
                "label": stage["label"],
                "threshold": {
                    "affection": stage["threshold"]["affection"],
                    "trust": stage["threshold"]["trust"],
                    **(
                        {"conflictMax": stage["threshold"]["conflict_max"]}
                        if stage["threshold"]["conflict_max"] is not None
                        else {}
                    ),
                },
                "unlocks": list(stage["unlocks"]),
            }
            for stage in raw["relationship_stages"]
        ],
        "monologueSeeds": [
            {
                "id": item["monologue_id"],
                "contextTags": list(item["context_tags"]),
                "text": item["text"],
            }
            for item in raw["monologue_seeds"]
        ],
        "giftReactions": {
            tier: {
                "tier": raw["gift_reactions"][tier]["tier"],
                "tagAny": list(raw["gift_reactions"][tier]["tag_any"]),
                "itemAny": list(raw["gift_reactions"][tier]["item_any"]),
                "deltaModifier": dict(raw["gift_reactions"][tier]["delta_modifier"]),
                "fallbackSpeechPool": list(raw["gift_reactions"][tier]["fallback_speech_pool"]),
            }
            for tier in ("loved", "liked", "neutral", "disliked")
        },
        "gossipHooks": [
            {
                "id": hook["hook_id"],
                "summary": hook["summary"],
                "visibility": hook["visibility"],
                "spreadAffinity": list(hook["spread_affinity"]),
            }
            for hook in raw["gossip_hooks"]
        ],
        "lifeActionSeeds": [
            {
                "id": item["action_id"],
                "timeWindow": item["time_window"],
                "summary": item["summary"],
                "intentTags": list(item["intent_tags"]),
                "locationHints": list(item["location_hints"]),
                "relatedNpcIds": list(item["related_npc_ids"]),
            }
            for item in raw["life_action_seeds"]
        ],
        "dailyRumorBeats": [
            {
                "id": item["beat_id"],
                "visibility": item["visibility"],
                "cue": item["cue"],
                "spreadTargets": list(item["spread_targets"]),
                "tags": list(item["tags"]),
            }
            for item in raw["daily_rumor_beats"]
        ],
        "relationshipBeatSeeds": [
            {
                "id": item["beat_id"],
                "stageHint": item["stage_hint"],
                "trigger": item["trigger"],
                "direction": item["direction"],
                "summary": item["summary"],
                "tags": list(item["tags"]),
            }
            for item in raw["relationship_beat_seeds"]
        ],
        "assetRefs": {
            "portrait": raw["asset_refs"]["portrait"],
            "expressions": dict(raw["asset_refs"]["expressions"]),
            "mapSprite": raw["asset_refs"]["map_sprite"],
        },
    }


def match_gift_reaction_tier(
    card: NpcDeepCard,
    item: dict[str, Any] | None,
) -> tuple[str, GiftReactionTier]:
    """根据物品 id 和 tags 匹配 NPC 的礼物反应档位。

    优先级：disliked > loved > liked > neutral。
    item.id 命中 itemAny 比 tag 命中 tagAny 更强；首个命中即返回。
    """
    item = item or {}
    item_id = str(item.get("id", ""))
    item_tags = {str(tag) for tag in (item.get("tags") or [])}
    reactions = card.gift_reactions
    ordered: tuple[tuple[str, GiftReactionTier], ...] = (
        ("disliked", reactions.disliked),
        ("loved", reactions.loved),
        ("liked", reactions.liked),
    )
    for tier_name, tier in ordered:
        if item_id and item_id in tier.item_any:
            return tier_name, tier
        if tier.tag_any and item_tags.intersection(tier.tag_any):
            return tier_name, tier
    return "neutral", reactions.neutral


def compute_relationship_stage(
    card: NpcDeepCard, relation: dict[str, Any]
) -> dict[str, Any]:
    """根据当前关系数值计算阶段，返回阶段 id、label 与已解锁条目。"""
    affection = int(relation.get("affection", 0))
    trust = int(relation.get("trust", 0))
    conflict = int(relation.get("conflict", 0))
    matched = card.relationship_stages[0]
    for stage in card.relationship_stages:
        threshold = stage.threshold
        if affection < threshold.affection:
            continue
        if trust < threshold.trust:
            continue
        if threshold.conflict_max is not None and conflict > threshold.conflict_max:
            continue
        matched = stage
    return {
        "stage": matched.stage,
        "label": matched.label,
        "unlocks": list(matched.unlocks),
    }
