from __future__ import annotations

from app.skills.event_skill_schema import (
    EventAssetHint,
    EventChoiceOutcome,
    EventConsequence,
    EventDialogueFallback,
    EventMemoryTemplate,
    EventParticipantDelta,
    EventPlayerOption,
    EventReflectionSeed,
    EventSkillSchema,
    EventSkillDebugField,
    EventTriggerCondition,
)

STARLIGHT_FESTIVAL_SHORTAGE_SKILL_ID = "event.starlight_festival_shortage"

_STARLIGHT_COMMON_MEMORY_TEMPLATES = (
    EventMemoryTemplate(
        agent_id="kai",
        text_template="星灯祭前夜差点因为食材短缺冷场，玩家的选择让我重新看见节日还能继续发光。结局：{summary}",
        tags=("starlight_shortage", "event_memory"),
    ),
    EventMemoryTemplate(
        agent_id="bram",
        text_template="酒馆欠账和供货压力被摆到台面上，玩家的处理方式让我重新评估这个新农场主。结局：{summary}",
        tags=("starlight_shortage", "event_memory"),
    ),
    EventMemoryTemplate(
        agent_id="mira",
        text_template="今晚的供应短缺让我担心小镇账目，但玩家让局面没有继续恶化。结局：{summary}",
        tags=("starlight_shortage", "event_memory"),
    ),
    EventMemoryTemplate(
        agent_id="lena",
        text_template="争执让大家都紧绷，玩家的介入至少让晚上的情绪风险降了下来。结局：{summary}",
        tags=("starlight_shortage", "event_memory"),
    ),
    EventMemoryTemplate(
        agent_id="orren",
        text_template="星灯祭的传统需要年轻人接住，玩家今晚给这段传统留下了新的注脚。结局：{summary}",
        tags=("starlight_shortage", "event_memory"),
    ),
    EventMemoryTemplate(
        agent_id="tomas",
        text_template="我在旁边修灯架时看见玩家处理争执，这个人也许愿意认真守护小镇。结局：{summary}",
        tags=("starlight_shortage", "event_memory"),
    ),
)

_STARLIGHT_COMMON_REFLECTION_SEEDS = (
    EventReflectionSeed(
        agent_id="kai",
        text_template="如果玩家没有选择“{choiceLabel}”，我可能会把节日压力全推给别人。明天要认真面对欠账。",
        tags=("night_reflection", "starlight_shortage"),
    ),
    EventReflectionSeed(
        agent_id="bram",
        text_template="这个新来的农场主没有把供应当成理所当然。无论是否站在我这边，至少看见了农场人的压力。",
        tags=("night_reflection", "starlight_shortage"),
    ),
    EventReflectionSeed(
        agent_id="lena",
        text_template="今晚的冲突证明节日压力会影响健康和关系。玩家的选择值得继续观察。",
        tags=("night_reflection", "starlight_shortage"),
    ),
)

_STARLIGHT_COMMON_FALLBACK_DIALOGUE = (
    EventDialogueFallback(
        agent_id="mira",
        speech_template="今晚账本上的数字终于没有继续失控。玩家选了“{choiceLabel}”，至少让大家能坐下来把话说完。",
    ),
    EventDialogueFallback(
        agent_id="lena",
        speech_template="冲突还没完全结束，但玩家用“{choiceLabel}”把最危险的情绪先降了下来。",
    ),
    EventDialogueFallback(
        agent_id="orren",
        speech_template="节日从来要靠人一起守住。玩家今晚的“{choiceLabel}”给了小镇一点信心。",
    ),
    EventDialogueFallback(
        agent_id="tomas",
        speech_template="我在旁边修灯架都看见了，玩家这次“{choiceLabel}”确实稳住了场面。",
    ),
)

_STARLIGHT_SKILL_DEBUG_FIELDS = (
    EventSkillDebugField(field_id="skillId", label="事件 Skill", value_template="{skillId}"),
    EventSkillDebugField(field_id="eventId", label="事件 ID", value_template="{eventId}"),
    EventSkillDebugField(field_id="choiceId", label="玩家选项", value_template="{choice}"),
    EventSkillDebugField(field_id="outcomeSource", label="结算来源", value_template="event_skill_registry"),
)

_STARLIGHT_OUTCOME_DEBUG_FIELDS = (
    EventSkillDebugField(field_id="styleSignal", label="风格信号", value_template="{styleSignal}"),
    EventSkillDebugField(field_id="choiceLabel", label="结算选项文案", value_template="{choiceLabel}"),
    EventSkillDebugField(field_id="consequenceTypes", label="后果类型", value_template="{consequenceTypes}"),
    EventSkillDebugField(field_id="memoryTemplateCount", label="记忆模板数量", value_template="{memoryTemplateCount}"),
    EventSkillDebugField(field_id="reflectionSeedCount", label="反思种子数量", value_template="{reflectionSeedCount}"),
    EventSkillDebugField(field_id="profileEvidence", label="玩家画像记忆模板", value_template="{profileEvidence}"),
    EventSkillDebugField(field_id="fallbackMemory", label="事件反应记忆模板", value_template="{fallbackMemory}"),
)

_STARLIGHT_PROFILE_EVIDENCE_TEMPLATE = "在星灯祭供应短缺中选择“{choiceLabel}”，小镇会把玩家记为{styleLabel}。"
_STARLIGHT_REACTION_MEMORY_TEMPLATE = "事件结算：{summary}"

STARLIGHT_FESTIVAL_SHORTAGE_SKILL = EventSkillSchema(
    skill_id=STARLIGHT_FESTIVAL_SHORTAGE_SKILL_ID,
    event_id="starlight_festival_shortage",
    title="星灯祭供应短缺",
    brief="月猫酒馆准备星灯祭前夜小聚时，食材紧缺引发凯娅与布兰娜的欠账争执。",
    trigger=EventTriggerCondition(
        phase="evening",
        location_id="tavern",
        required_status="available",
        required_active_event_id="starlight_festival_shortage",
    ),
    participants=("player", "kai", "bram", "mira", "lena", "orren", "tomas"),
    player_options=(
        EventPlayerOption(
            option_id="donate_crop",
            label="拿出新鲜芜菁帮酒馆渡过今晚",
            brief="玩家直接补齐食材，立刻缓解供应压力。",
            requires_player_item_id="fresh_turnip",
            consequences=(
                EventConsequence(
                    consequence_type="supply",
                    brief="食材短缺被立刻补上，庆典流程可以继续推进。",
                ),
                EventConsequence(
                    consequence_type="help",
                    brief="玩家同时安抚凯娅与布兰娜，冲突强度快速下降。",
                    deltas=(
                        EventParticipantDelta(participant_id="kai", affection=5, trust=4, conflict=-5),
                        EventParticipantDelta(participant_id="bram", affection=2, trust=3, conflict=-4),
                    ),
                ),
            ),
        ),
        EventPlayerOption(
            option_id="mediate",
            label="调解凯娅和布兰娜的欠账冲突",
            brief="玩家主持对话，优先稳定关系与后续供货秩序。",
            consequences=(
                EventConsequence(
                    consequence_type="help",
                    brief="双方接受先还款再供货的临时安排。",
                ),
                EventConsequence(
                    consequence_type="mediate",
                    brief="关系摩擦下降，镇民对玩家调解能力建立信任。",
                    deltas=(
                        EventParticipantDelta(participant_id="kai", affection=3, trust=4, conflict=-4),
                        EventParticipantDelta(participant_id="bram", affection=3, trust=4, conflict=-5),
                    ),
                ),
            ),
        ),
        EventPlayerOption(
            option_id="support_kai",
            label="优先支持凯娅维持节日气氛",
            brief="玩家偏向酒馆侧，让庆典氛围先保持热闹。",
            consequences=(
                EventConsequence(
                    consequence_type="atmosphere",
                    brief="节日现场情绪回暖，凯娅获得即时支持。",
                    deltas=(EventParticipantDelta(participant_id="kai", affection=5, trust=2, conflict=-2),),
                ),
                EventConsequence(
                    consequence_type="support",
                    brief="布兰娜对欠账问题更不满，后续供货关系更紧张。",
                    deltas=(EventParticipantDelta(participant_id="bram", affection=-1, trust=-1, conflict=4),),
                ),
            ),
        ),
        EventPlayerOption(
            option_id="support_bram",
            label="优先支持布兰娜守住供货底线",
            brief="玩家偏向农场侧，优先明确欠账与供货纪律。",
            consequences=(
                EventConsequence(
                    consequence_type="supply",
                    brief="供货底线被确认，后续补货风险下降。",
                    deltas=(EventParticipantDelta(participant_id="bram", affection=5, trust=3, conflict=-2),),
                ),
                EventConsequence(
                    consequence_type="stability",
                    brief="酒馆气氛短时降温，凯娅情绪出现反弹。",
                    deltas=(EventParticipantDelta(participant_id="kai", affection=-1, trust=0, conflict=3),),
                ),
            ),
        ),
        EventPlayerOption(
            option_id="observe",
            label="先旁观并记录大家的反应",
            brief="玩家收集现场信息，等待后续介入窗口。",
            consequences=(
                EventConsequence(
                    consequence_type="observe",
                    brief="玩家获得冲突全貌，核心矛盾被记录用于后续决策。",
                ),
                EventConsequence(
                    consequence_type="relationship",
                    brief="奥蕾娅和莉娜认可玩家保持克制，建立基础信任。",
                    deltas=(
                        EventParticipantDelta(participant_id="orren", trust=1),
                        EventParticipantDelta(participant_id="lena", trust=1),
                    ),
                ),
            ),
        ),
    ),
    asset_hints=(
        EventAssetHint(
            hint_id="starlight_shortage_scene",
            asset_type="event_scene",
            brief="月猫酒馆夜景，祭灯、空食材箱、争执中的凯娅与布兰娜。",
            tags=("festival", "night", "supply_shortage", "tavern"),
        ),
        EventAssetHint(
            hint_id="starlight_shortage_ui_card",
            asset_type="ui_event_card",
            brief="事件卡面包含供应告急标识、酒馆与农场对立信息。",
            tags=("event_card", "supply", "decision"),
        ),
        EventAssetHint(
            hint_id="starlight_shortage_choice_icons",
            asset_type="icon_set",
            brief="为捐赠、调解、站队、观察四类选项准备视觉图标。",
            tags=("choice", "donate", "mediate", "observe"),
        ),
    ),
    fallback_dialogue_templates=_STARLIGHT_COMMON_FALLBACK_DIALOGUE,
    choice_outcomes=(
        EventChoiceOutcome(
            option_id="donate_crop",
            choice_label_template="拿出{itemName}帮酒馆渡过今晚",
            summary_template="玩家拿出{itemName}补上节日食材，凯娅松了一口气，布兰娜也承认这份帮忙很实在。",
            player_style_signal="help",
            player_style_label="愿意拿出资源帮忙的人",
            profile_evidence_template=_STARLIGHT_PROFILE_EVIDENCE_TEMPLATE,
            reaction_memory_template=_STARLIGHT_REACTION_MEMORY_TEMPLATE,
            relation_deltas=(
                EventParticipantDelta(participant_id="kai", affection=5, trust=4, conflict=-5),
                EventParticipantDelta(participant_id="bram", affection=2, trust=3, conflict=-4),
                EventParticipantDelta(participant_id="mira", affection=1, trust=2, conflict=-1),
                EventParticipantDelta(participant_id="lena", affection=1, trust=1, conflict=-1),
                EventParticipantDelta(participant_id="orren", affection=1, trust=2, conflict=-1),
                EventParticipantDelta(participant_id="tomas", affection=1, trust=1, conflict=-1),
            ),
            memory_templates=_STARLIGHT_COMMON_MEMORY_TEMPLATES,
            fallback_dialogue=(
                EventDialogueFallback(agent_id="kai", speech_template="你真的把{itemName}拿来了？今晚的星灯不会暗下去了，谢谢你！"),
                EventDialogueFallback(agent_id="bram", speech_template="哼，至少你知道作物都要靠人种出来。这份人情我记下。"),
            ),
            reflection_seeds=_STARLIGHT_COMMON_REFLECTION_SEEDS,
            debug_fields=_STARLIGHT_OUTCOME_DEBUG_FIELDS,
        ),
        EventChoiceOutcome(
            option_id="mediate",
            choice_label_template="调解凯娅和布兰娜的欠账冲突",
            summary_template="玩家请凯娅先确认还款安排，也帮布兰娜保住供货底线，争执被暂时压了下来。",
            player_style_signal="mediate",
            player_style_label="愿意调解冲突的人",
            profile_evidence_template=_STARLIGHT_PROFILE_EVIDENCE_TEMPLATE,
            reaction_memory_template=_STARLIGHT_REACTION_MEMORY_TEMPLATE,
            relation_deltas=(
                EventParticipantDelta(participant_id="kai", affection=3, trust=4, conflict=-4),
                EventParticipantDelta(participant_id="bram", affection=3, trust=4, conflict=-5),
                EventParticipantDelta(participant_id="mira", affection=1, trust=2, conflict=-1),
                EventParticipantDelta(participant_id="lena", affection=1, trust=2, conflict=-1),
                EventParticipantDelta(participant_id="orren", affection=1, trust=2, conflict=-1),
            ),
            memory_templates=_STARLIGHT_COMMON_MEMORY_TEMPLATES,
            fallback_dialogue=(
                EventDialogueFallback(agent_id="kai", speech_template="好啦好啦，我会把账单写清楚。谢谢你没有让今晚变成吵架大会。"),
                EventDialogueFallback(agent_id="bram", speech_template="能把话说到点子上，比单纯站队强。新来的，你有点分寸。"),
            ),
            reflection_seeds=_STARLIGHT_COMMON_REFLECTION_SEEDS,
            debug_fields=_STARLIGHT_OUTCOME_DEBUG_FIELDS,
        ),
        EventChoiceOutcome(
            option_id="support_kai",
            choice_label_template="优先支持凯娅维持节日气氛",
            summary_template="玩家站在凯娅这边让星灯祭继续热闹，但布兰娜对酒馆旧账更加不满。",
            player_style_signal="support",
            player_style_label="重视节日气氛的人",
            profile_evidence_template=_STARLIGHT_PROFILE_EVIDENCE_TEMPLATE,
            reaction_memory_template=_STARLIGHT_REACTION_MEMORY_TEMPLATE,
            relation_deltas=(
                EventParticipantDelta(participant_id="kai", affection=5, trust=2, conflict=-2),
                EventParticipantDelta(participant_id="bram", affection=-1, trust=-1, conflict=4),
                EventParticipantDelta(participant_id="mira", trust=1),
                EventParticipantDelta(participant_id="orren", trust=1),
            ),
            memory_templates=_STARLIGHT_COMMON_MEMORY_TEMPLATES,
            fallback_dialogue=(
                EventDialogueFallback(agent_id="kai", speech_template="我就知道有人懂星灯祭的重要！今晚先让大家笑起来吧。"),
                EventDialogueFallback(agent_id="bram", speech_template="热闹不能抵账。你今天的选择我看见了。"),
            ),
            reflection_seeds=_STARLIGHT_COMMON_REFLECTION_SEEDS,
            debug_fields=_STARLIGHT_OUTCOME_DEBUG_FIELDS,
        ),
        EventChoiceOutcome(
            option_id="support_bram",
            choice_label_template="优先支持布兰娜守住供货底线",
            summary_template="玩家支持布兰娜先把欠账说清，酒馆气氛短暂降温，但供货压力被认真看见了。",
            player_style_signal="support",
            player_style_label="尊重供货底线的人",
            profile_evidence_template=_STARLIGHT_PROFILE_EVIDENCE_TEMPLATE,
            reaction_memory_template=_STARLIGHT_REACTION_MEMORY_TEMPLATE,
            relation_deltas=(
                EventParticipantDelta(participant_id="kai", affection=-1, trust=0, conflict=3),
                EventParticipantDelta(participant_id="bram", affection=5, trust=3, conflict=-2),
                EventParticipantDelta(participant_id="mira", trust=1),
                EventParticipantDelta(participant_id="lena", trust=1),
            ),
            memory_templates=_STARLIGHT_COMMON_MEMORY_TEMPLATES,
            fallback_dialogue=(
                EventDialogueFallback(agent_id="bram", speech_template="总算有人听见供货人的难处。节日也得先把账算明白。"),
                EventDialogueFallback(agent_id="kai", speech_template="我知道她辛苦，可今晚的灯要是灭了，大家都会难过的。"),
            ),
            reflection_seeds=_STARLIGHT_COMMON_REFLECTION_SEEDS,
            debug_fields=_STARLIGHT_OUTCOME_DEBUG_FIELDS,
        ),
        EventChoiceOutcome(
            option_id="observe",
            choice_label_template="先旁观并记录大家的反应",
            summary_template="玩家没有立刻介入，只观察到凯娅的焦虑、布兰娜的压力，以及旁观居民的担心。",
            player_style_signal="observe",
            player_style_label="先观察局势的人",
            profile_evidence_template=_STARLIGHT_PROFILE_EVIDENCE_TEMPLATE,
            reaction_memory_template=_STARLIGHT_REACTION_MEMORY_TEMPLATE,
            relation_deltas=(
                EventParticipantDelta(participant_id="orren", trust=1),
                EventParticipantDelta(participant_id="lena", trust=1),
            ),
            memory_templates=_STARLIGHT_COMMON_MEMORY_TEMPLATES,
            fallback_dialogue=(
                EventDialogueFallback(agent_id="orren", speech_template="观察也是选择。你至少看见了节日背后的裂缝。"),
                EventDialogueFallback(agent_id="lena", speech_template="先不急着介入也可以，但今晚需要有人继续照看大家的情绪。"),
            ),
            reflection_seeds=_STARLIGHT_COMMON_REFLECTION_SEEDS,
            debug_fields=_STARLIGHT_OUTCOME_DEBUG_FIELDS,
        ),
    ),
    debug_fields=_STARLIGHT_SKILL_DEBUG_FIELDS,
)

_EVENT_SKILL_REGISTRY: dict[str, EventSkillSchema] = {
    STARLIGHT_FESTIVAL_SHORTAGE_SKILL.skill_id: STARLIGHT_FESTIVAL_SHORTAGE_SKILL,
}


def list_event_skills() -> tuple[EventSkillSchema, ...]:
    """返回已注册事件技能列表。"""
    return tuple(_EVENT_SKILL_REGISTRY.values())


def get_event_skill(skill_id: str) -> EventSkillSchema:
    """按 skill id 获取事件技能定义。"""
    try:
        return _EVENT_SKILL_REGISTRY[skill_id]
    except KeyError as error:
        raise KeyError(f"未知事件技能：{skill_id}") from error


def find_event_option(skill_id: str, option_id: str) -> EventPlayerOption:
    """按选项 id 读取玩家选项，供 attend_event 参数校验与 UI 使用。"""
    skill = get_event_skill(skill_id)
    for option in skill.player_options:
        if option.option_id == option_id:
            return option
    raise KeyError(f"事件技能 {skill_id} 中不存在选项：{option_id}")


def find_event_choice_outcome(skill_id: str, option_id: str) -> EventChoiceOutcome:
    """按选项 id 读取 Skill 结算定义。"""
    skill = get_event_skill(skill_id)
    for outcome in skill.choice_outcomes:
        if outcome.option_id == option_id:
            return outcome
    raise KeyError(f"事件技能 {skill_id} 中不存在结算定义：{option_id}")
