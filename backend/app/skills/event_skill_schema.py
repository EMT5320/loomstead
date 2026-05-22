from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.runtime.schema_registry import require_schema_version

ConsequenceType = Literal[
    "supply",
    "help",
    "mediate",
    "support",
    "observe",
    "relationship",
    "atmosphere",
    "stability",
]


@dataclass(frozen=True, slots=True)
class EventTriggerCondition:
    """事件可触发条件，供 Runtime 或调试面板读取。"""

    phase: str
    location_id: str
    required_status: str = "available"
    required_active_event_id: str | None = None


@dataclass(frozen=True, slots=True)
class EventParticipantDelta:
    """选项对参与者关系产生的增减预览。"""

    participant_id: str
    affection: int = 0
    trust: int = 0
    conflict: int = 0


@dataclass(frozen=True, slots=True)
class EventConsequence:
    """事件选项可视化后果结构，可映射 supply/help 等语义。"""

    consequence_type: ConsequenceType
    brief: str
    deltas: tuple[EventParticipantDelta, ...] = ()


@dataclass(frozen=True, slots=True)
class EventPlayerOption:
    """玩家可见选项定义，保留和 attend_event 结算可映射的 id。"""

    option_id: str
    label: str
    brief: str
    consequences: tuple[EventConsequence, ...]
    requires_player_item_id: str | None = None


@dataclass(frozen=True, slots=True)
class EventAssetHint:
    """客户端或工具链可用的资源提示。"""

    hint_id: str
    asset_type: str
    brief: str
    tags: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class EventSkillDebugField:
    """事件技能希望 Debug 面板展示的字段。"""

    field_id: str
    label: str
    value_template: str


@dataclass(frozen=True, slots=True)
class EventMemoryTemplate:
    """事件结算后写入 NPC 记忆的模板。"""

    agent_id: str
    text_template: str
    importance: float = 0.8
    tags: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class EventDialogueFallback:
    """离线规则 Provider 使用的 NPC 反应台词。"""

    agent_id: str
    speech_template: str


@dataclass(frozen=True, slots=True)
class EventReflectionSeed:
    """夜间反思的规则种子，LLM 跳过时可直接落地。"""

    agent_id: str
    text_template: str
    tags: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class EventChoiceOutcome:
    """单个玩家选项对应的 Skill 结算数据。"""

    option_id: str
    choice_label_template: str
    summary_template: str
    player_style_signal: str = ""
    player_style_label: str = ""
    profile_evidence_template: str = ""
    reaction_memory_template: str = "事件结算：{summary}"
    relation_deltas: tuple[EventParticipantDelta, ...] = ()
    memory_templates: tuple[EventMemoryTemplate, ...] = ()
    fallback_dialogue: tuple[EventDialogueFallback, ...] = ()
    reflection_seeds: tuple[EventReflectionSeed, ...] = ()
    debug_fields: tuple[EventSkillDebugField, ...] = ()


@dataclass(frozen=True, slots=True)
class EventSkillSchema:
    """事件技能定义。"""

    skill_id: str
    event_id: str
    title: str
    brief: str
    trigger: EventTriggerCondition
    participants: tuple[str, ...]
    player_options: tuple[EventPlayerOption, ...]
    asset_hints: tuple[EventAssetHint, ...]
    fallback_dialogue_templates: tuple[EventDialogueFallback, ...] = ()
    choice_outcomes: tuple[EventChoiceOutcome, ...] = ()
    debug_fields: tuple[EventSkillDebugField, ...] = ()
    outcome_record_version: str = require_schema_version("event_skill_outcome")
