"""NPC 深度卡（npc codex）数据契约。

字段语义详见 docs/npc_deep_card_spec.md。schema 只描述结构，
校验逻辑统一放在 codex_loader.py，便于产生友好的中文错误信息。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

CURRENT_SCHEMA_VERSION = 1

GiftTier = Literal["loved", "liked", "neutral", "disliked"]
SecretVisibility = Literal["hidden", "town_known"]


@dataclass(frozen=True, slots=True)
class Identity:
    """NPC 身份与语气锚点。"""

    age: int
    gender: str
    job: str
    archetype: str
    voice_style: str
    speech_register: str


@dataclass(frozen=True, slots=True)
class Personality:
    """NPC 内在性格与口癖。"""

    core_traits: tuple[str, ...]
    inner_contradiction: str
    speech_quirks: tuple[str, ...]
    stress_triggers: tuple[str, ...]
    comforts: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Goals:
    """NPC 目标与恐惧。"""

    long_term: tuple[str, ...]
    today: tuple[str, ...]
    fears: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MotivationProfile:
    """Phase 2 动机系统占位；实际权重在内容期填充。"""

    needs: dict[str, Any] = field(default_factory=dict)
    personality_modifiers: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class HeuristicSeed:
    """设计师注入的启发式种子，Phase 2 先允许为空。"""

    heuristic_id: str
    trigger_pattern: dict[str, Any]
    adjustment: dict[str, Any]
    confidence: float
    narrative: str


@dataclass(frozen=True, slots=True)
class Secret:
    """NPC 秘密，按关系阶段或可见性解锁。"""

    secret_id: str
    visibility: str
    summary: str
    unlock_after: str
    tags: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Preference:
    """喜好或厌恶条目，标签 + 物品双通道。"""

    tag: str
    weight: int
    items: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class StageThreshold:
    """阶段门槛，仅在数值达到要求且冲突未超限时进入。"""

    affection: int = 0
    trust: int = 0
    conflict_max: int | None = None


@dataclass(frozen=True, slots=True)
class RelationshipStage:
    """关系阶段定义。"""

    stage: str
    label: str
    threshold: StageThreshold
    unlocks: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class MonologueSeed:
    """NPC 内心独白种子，提供 prompt 锚与夜间反思 fallback。"""

    monologue_id: str
    context_tags: tuple[str, ...]
    text: str


@dataclass(frozen=True, slots=True)
class GiftReactionTier:
    """送礼分级反应：标签命中 + 修正值 + fallback 台词。"""

    tier: str
    tag_any: tuple[str, ...] = ()
    item_any: tuple[str, ...] = ()
    delta_modifier: dict[str, int] = field(default_factory=dict)
    fallback_speech_pool: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class GiftReactions:
    """送礼四档反应容器。"""

    loved: GiftReactionTier
    liked: GiftReactionTier
    neutral: GiftReactionTier
    disliked: GiftReactionTier


@dataclass(frozen=True, slots=True)
class GossipHook:
    """谣言钩子，首版仅入库为后续传播玩法奠基。"""

    hook_id: str
    summary: str
    visibility: str
    spread_affinity: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class LifeActionSeed:
    """Day 1 日常行动素材种子，用于低风险驱动日程行为。"""

    action_id: str
    time_window: str
    summary: str
    intent_tags: tuple[str, ...]
    location_hints: tuple[str, ...] = ()
    related_npc_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class DailyRumorBeat:
    """Day 1 谣言节拍素材，供后续传播玩法消费。"""

    beat_id: str
    visibility: str
    cue: str
    spread_targets: tuple[str, ...]
    tags: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RelationshipBeatSeed:
    """Day 1 关系节拍素材，供关系变化反馈与表达锚点消费。"""

    beat_id: str
    stage_hint: str
    trigger: str
    direction: str
    summary: str
    tags: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class AssetRefs:
    """关联美术资产 id，校验时与 asset_manifest.json 交叉引用。"""

    portrait: str
    expressions: dict[str, str] = field(default_factory=dict)
    map_sprite: str = ""


@dataclass(frozen=True, slots=True)
class NpcDeepCard:
    """NPC 深度卡顶层结构。"""

    schema_version: int
    npc_id: str
    display_name: str
    short_name: str
    identity: Identity
    personality: Personality
    goals: Goals
    motivation_profile: MotivationProfile
    capability_preferences: dict[str, dict[str, Any]]
    heuristic_seeds: tuple[HeuristicSeed, ...]
    secrets: tuple[Secret, ...]
    likes: tuple[Preference, ...]
    dislikes: tuple[Preference, ...]
    relationship_stages: tuple[RelationshipStage, ...]
    monologue_seeds: tuple[MonologueSeed, ...]
    gift_reactions: GiftReactions
    gossip_hooks: tuple[GossipHook, ...]
    asset_refs: AssetRefs
    life_action_seeds: tuple[LifeActionSeed, ...] = ()
    daily_rumor_beats: tuple[DailyRumorBeat, ...] = ()
    relationship_beat_seeds: tuple[RelationshipBeatSeed, ...] = ()
