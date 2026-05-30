"""展示层（presentation-showcase）纯函数测试骨架。

设计依据：`.kiro/specs/presentation-showcase/design.md` Testing Strategy。

本文件集中承载展示层的 Property-Based Testing（Hypothesis）与 example/unit
测试（pytest）。当前为骨架，仅确保依赖可导入且可被
``python -m pytest scripts/tests`` 正确收集；具体测试随后续任务填充：

- Property 1 Trace 裁剪与排序（R4.4）            —— 任务 7.2
- Property 2 Prev/Next 导航索引 clamp（R4.5）     —— 任务 8.2
- Property 3 Figure/Table 覆盖率与 pending（R6）  —— 任务 3.2
- Property 4 口径一致性扫描（R10）                —— 任务 4.2
- Property 5 manifest 验证态枚举合法性（R11.2）   —— 任务 2.3
- Property 6 manifest readiness 自洽（R11.4）     —— 任务 2.5
- Property 7 manual gate 不变量（R11.3）          —— 任务 2.6
- Property 8 phase2 摘要非空（R4.2）              —— 任务 8.7
- example：capture plan 判据存在性（R1/R2）       —— 任务 10.2

每条 property 测试对应设计文档一条 correctness property，注释格式：
``# Feature: presentation-showcase, Property {number}: {property_text}``，
Hypothesis ``max_examples >= 100``。
"""

# 骨架阶段：确认测试依赖可用（后续任务将基于这两个库填充实际测试）。
import json
import sys
from pathlib import Path

import hypothesis  # noqa: F401  pytest 收集时校验 Hypothesis 可导入
import pytest  # noqa: F401  pytest 收集时校验 pytest 可导入

from . import showcase_refs  # noqa: F401  参考实现落点（后续任务填充）

ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


# =============================================================================
# Property 1：Trace 裁剪与排序（R4.4 / 任务 7.2）
# 被测：scripts/tests/showcase_refs.py 的 clip_and_sort_trace(events, category, limit=50)
# =============================================================================

from hypothesis import example, given, settings
from hypothesis import strategies as st

# ---- 独立 oracle：与 showcase_refs 的匹配/取值规则等价但分开实现，做交叉验证 ----
# 各类别对应的精确 eventType 集合（对齐 _trace_filter_matches）。
_ORACLE_DECISION_TYPES = frozenset({"motivation.decision_made"})
_ORACLE_TOOL_TYPES = frozenset({"tool.execution_completed", "tool.execution_failed"})
_ORACLE_INTERRUPT_TYPES = frozenset({"tool.execution_interrupted"})
_ORACLE_MEMORY_TYPES = frozenset({"memory.result_observed"})


def _oracle_event_type(entry: dict) -> str:
    """独立实现 eventType 提取：eventType → type → 字面量 "trace"。

    交叉验证 showcase_refs._event_type_of，刻意不复用其实现。
    """
    return str(entry.get("eventType", entry.get("type", "trace")))


def _oracle_matches(event_type: str, category: str) -> bool:
    """独立实现类别匹配：all 及任何未知类别匹配全部，其余按精确集合匹配。

    交叉验证 showcase_refs._trace_filter_matches，刻意不复用其实现。
    """
    if category == "decision":
        return event_type in _ORACLE_DECISION_TYPES
    if category == "tool":
        return event_type in _ORACLE_TOOL_TYPES
    if category == "interrupt":
        return event_type in _ORACLE_INTERRUPT_TYPES
    if category == "memory":
        return event_type in _ORACLE_MEMORY_TYPES
    # "all" 及任何未知 category → 全部匹配。
    return True


# ---- Hypothesis 策略：生成多样的 recentTraceEvents 列表 ----
# 能匹配某个具体类别的精确 eventType。
_MATCHING_EVENT_TYPES = (
    "motivation.decision_made",
    "tool.execution_completed",
    "tool.execution_failed",
    "tool.execution_interrupted",
    "memory.result_observed",
)
# 不匹配 decision/tool/interrupt/memory（只会在 all/未知类别下入选）的 eventType。
_NONMATCHING_EVENT_TYPES = (
    "trace",
    "world.tick",
    "agent.spawned",
    "tool.execution_started",
    "unknown.event",
    "",
)
_EVENT_TYPE_POOL = st.sampled_from(_MATCHING_EVENT_TYPES + _NONMATCHING_EVENT_TYPES)

# dict 携带 eventType 字段（主路径）。
_dict_with_event_type = st.builds(
    lambda et, payload: {"eventType": et, "payload": payload},
    _EVENT_TYPE_POOL,
    st.integers(min_value=-5, max_value=5),
)
# dict 缺失 eventType、携带 type 字段（fallback 到 type）。
_dict_with_type_only = st.builds(lambda et: {"type": et}, _EVENT_TYPE_POOL)
# dict 既无 eventType 又无 type（fallback 到字面量 "trace"）。
_dict_without_type = st.builds(lambda n: {"note": n}, st.integers(min_value=0, max_value=9))
# 非 dict 噪声项（应被裁剪逻辑跳过）。
_non_dict_item = st.one_of(
    st.none(),
    st.integers(),
    st.text(max_size=6),
    st.floats(allow_nan=False, allow_infinity=False),
    st.lists(st.integers(), max_size=3),
)
_event_item = st.one_of(
    _dict_with_event_type,
    _dict_with_event_type,  # 加权：让带 eventType 的项更常见，便于探索匹配/裁剪
    _dict_with_type_only,
    _dict_without_type,
    _non_dict_item,
)
# max_size=130 保证能产生 >50（裁剪上限）的样例；min_size 默认 0 覆盖空列表。
_events_strategy = st.lists(_event_item, max_size=130)
_category_strategy = st.sampled_from(showcase_refs.TRACE_CATEGORIES)

_PBT_SEQ_KEY = "__pbt_seq__"


def _inject_sequence(events: list) -> list:
    """给每个原始项按出现顺序注入单调递增序号，便于验证 newest→oldest 顺序。

    dict 项做浅拷贝并写入 _PBT_SEQ_KEY（不影响 eventType/type 字段）；非 dict 项原样
    保留（裁剪逻辑会跳过它们）。序号在整个列表内唯一且随原始位置递增。
    """
    seq_events: list = []
    for idx, item in enumerate(events):
        if isinstance(item, dict):
            tagged = dict(item)
            tagged[_PBT_SEQ_KEY] = idx
            seq_events.append(tagged)
        else:
            seq_events.append(item)
    return seq_events


# Feature: presentation-showcase, Property 1: For any phase2 recentTraceEvents 列表与任一 trace 过滤类别（all/decision/tool/interrupt/memory），裁剪后输出 SHALL 满足：(a) 长度至多 50 条；(b) 每一项的 eventType 都匹配所选类别；(c) 顺序为 newest→oldest。
@settings(max_examples=200, deadline=None)
@given(events=_events_strategy, category=_category_strategy)
# 关键边界 example：空列表、>50 条同类、全非 dict 噪声、混入 type/无类型 dict。
@example(events=[], category="all")
@example(
    events=[{"eventType": "motivation.decision_made"} for _ in range(53)],
    category="decision",
)
@example(events=[1, "x", None, [1, 2], 3.5], category="all")
@example(
    events=[{"type": "tool.execution_completed"}, {"note": 1}, {"eventType": "memory.result_observed"}],
    category="tool",
)
def test_property_1_clip_and_sort_trace(events: list, category: str) -> None:
    """Property 1：trace 裁剪 + 类别过滤 + newest→oldest 排序。

    **Validates: Requirements 4.4**

    对任意 events 列表与任一合法 category，断言 clip_and_sort_trace 输出满足：
    (a) 长度至多 50；(b) 每项 eventType 匹配 category（独立 oracle 交叉验证）；
    (c) 顺序为 newest→oldest（注入序号严格递减），且恰为「过滤后原序尾段 50 条的
    reverse」（强校验裁剪正确性与完整性）。
    """
    seq_events = _inject_sequence(events)
    clipped = showcase_refs.clip_and_sort_trace(seq_events, category)

    # 输出恒为 dict 列表（非 dict 噪声已被跳过）。
    assert all(isinstance(entry, dict) for entry in clipped)

    # (a) 长度至多 50 条（默认 limit=TRACE_RECENT_LIMIT）。
    assert len(clipped) <= showcase_refs.TRACE_RECENT_LIMIT

    # (b) 每一项的 eventType 都匹配所选类别（独立 oracle 判定，交叉验证参考实现）。
    for entry in clipped:
        assert _oracle_matches(_oracle_event_type(entry), category)

    # 用独立 oracle 复算期望：过滤（保序）→ 取尾段 50 条 → reverse。
    matched = [
        entry
        for entry in seq_events
        if isinstance(entry, dict) and _oracle_matches(_oracle_event_type(entry), category)
    ]
    start_index = max(0, len(matched) - showcase_refs.TRACE_RECENT_LIMIT)
    expected = list(reversed(matched[start_index:]))
    expected_seqs = [entry[_PBT_SEQ_KEY] for entry in expected]
    output_seqs = [entry[_PBT_SEQ_KEY] for entry in clipped]

    # (c) 顺序为 newest→oldest：注入序号严格递减。
    assert all(
        earlier > later for earlier, later in zip(output_seqs, output_seqs[1:])
    ), "trace 输出顺序应为 newest→oldest（序号严格递减）"

    # 强校验：输出恰等于「过滤后原序尾段 50 条的 reverse」（裁剪 + 排序 + 完整性）。
    assert output_seqs == expected_seqs


# =============================================================================
# Property 2：Prev/Next 导航索引 clamp 与指示自洽（R4.5 / 任务 8.2）
# 被测：scripts/tests/showcase_refs.py 的 apply_prev_next(total, ops)
# =============================================================================

_nav_token_strategy = st.sampled_from(("prev", "next"))
_nav_frame_strategy = st.one_of(
    _nav_token_strategy,
    st.lists(_nav_token_strategy, max_size=4).map(tuple),
)
_nav_ops_strategy = st.lists(_nav_frame_strategy, max_size=120)


def _position_indicator(index: int, total: int) -> str:
    """根据最终索引生成 UI 位置指示文案；对齐 ObserverPanel 的 0/0 与 current/total。"""
    if total <= 0:
        return "0/0"
    return "%d/%d" % (index + 1, total)


# Feature: presentation-showcase, Property 2: For any total（>=0）与任意 Prev/Next 操作序列，最终索引 SHALL clamp 到 [0, max(0,total-1)]，且 position indicator 的 current/total 与索引一致（current=index+1；total<=0 时为 0/0）。
@settings(max_examples=200, deadline=None)
@given(total=st.integers(min_value=0, max_value=200), ops=_nav_ops_strategy)
@example(total=0, ops=["prev", "next"])
@example(total=1, ops=["next", "prev", ("prev", "next")])
@example(total=3, ops=["next", "next", "next", "prev"])
@example(total=3, ops=[("prev", "next"), ("next", "prev")])
def test_property_2_prev_next_clamp_and_indicator(total: int, ops: list) -> None:
    """Property 2：Prev/Next 导航索引 clamp 与 position indicator 自洽。

    **Validates: Requirements 4.5**

    对任意 total 与任意操作帧序列，断言 apply_prev_next 输出：
    (a) total<=0 时恒为 0，指示为 0/0；
    (b) total>0 时 index 落在 [0,total-1]；
    (c) 指示文案中的 current 始终等于 index+1，total 文本等于输入 total。
    同帧 Prev+Next 的 Next 优先语义由 reference 实现承载，并通过 example 覆盖关键边界。
    """
    index = showcase_refs.apply_prev_next(total, ops)
    indicator = _position_indicator(index, total)

    if total <= 0:
        assert index == 0
        assert indicator == "0/0"
        return

    assert 0 <= index <= total - 1
    current_text, total_text = indicator.split("/")
    assert int(current_text) == index + 1
    assert int(total_text) == total


# =============================================================================
# Property 8：Phase2 摘要非空（R4.2 / 任务 8.7）
# 被测：scripts/tests/showcase_refs.py 的 summarize_section(section, payload)
# =============================================================================

_phase2_item_strategy = st.one_of(
    st.dictionaries(
        keys=st.sampled_from(
            (
                "primaryNeed",
                "decision",
                "text",
                "emotionalValence",
                "sourceNpcId",
                "targetNpcId",
                "strength",
                "relationshipStage",
                "triggerPattern",
                "heuristicId",
                "effectiveConfidence",
                "confidence",
            )
        ),
        values=st.one_of(
            st.text(max_size=24),
            st.integers(min_value=-10, max_value=10),
            st.floats(allow_nan=False, allow_infinity=False, min_value=-10.0, max_value=10.0),
            st.dictionaries(
                keys=st.text(min_size=1, max_size=12),
                values=st.one_of(st.text(max_size=16), st.integers(min_value=-5, max_value=5)),
                max_size=3,
            ),
        ),
        max_size=6,
    ),
    st.integers(min_value=-5, max_value=5),
    st.text(max_size=16),
)
_non_empty_phase2_items_strategy = st.lists(_phase2_item_strategy, min_size=1, max_size=12)
_non_empty_phase2_payload_strategy = st.one_of(
    _non_empty_phase2_items_strategy,
    st.builds(lambda items: {"items": items}, _non_empty_phase2_items_strategy),
)


# Feature: presentation-showcase, Property 8: For any non-empty phase2 section payload, summarize_section SHALL return a non-empty summary string and SHALL NOT equal that section's empty placeholder text.
@settings(max_examples=200, deadline=None)
@given(
    section=st.sampled_from(showcase_refs.PHASE2_SUMMARY_SECTIONS),
    payload=_non_empty_phase2_payload_strategy,
)
@example(section="motivation", payload={"items": [{"primaryNeed": {"needId": "rest", "urgency": 0.7}, "decision": {"selectedToolId": "life.move_to"}}]})
@example(section="subjectiveMemory", payload={"items": [{"text": "Saw Kai repair trust.", "emotionalValence": 0.4}]})
@example(section="relationshipEdges", payload={"items": [{"sourceNpcId": "kai", "targetNpcId": "mira", "strength": 0.8, "relationshipStage": "trust"}]})
@example(section="heuristics", payload={"items": [{"triggerPattern": "repair talk", "effectiveConfidence": 0.6}]})
def test_property_8_phase2_summary_non_empty(section: str, payload) -> None:
    """Property 8：非空 phase2 payload 的摘要必须非空，且不能退回空态占位。

    **Validates: Requirements 4.2**

    该测试覆盖 list 非空与 {"items": [...]} 两类 GDScript 等价输入形态；即使条目
    不是 dict，也必须返回“数据不可读”等非空诊断摘要，避免展示层把有数据误渲为空态。
    """
    summary = showcase_refs.summarize_section(section, payload)
    assert summary.strip() != ""
    assert summary != showcase_refs.SECTION_EMPTY_SUMMARY[section]


# =============================================================================
# Property 5：Showcase_Manifest 验证态枚举合法性（R11.2 / 任务 2.3）
# 被测：scripts/check_showcase.py 的 _validate_deliverables（verification_state
#       枚举校验维度）、Deliverable dataclass、VERIFICATION_STATES 常量。
# pytest prepend 导入模式下 scripts/ 位于 sys.path（tests/ 之上首个无 __init__
# 的目录），故可直接顶层 import check_showcase。
# =============================================================================

import check_showcase  # noqa: E402  顶层脚本（scripts/ 在 sys.path）

# 合法验证态枚举（5 值，design Data Models 验证态枚举 / R11.2）。
_LEGAL_VERIFICATION_STATES = tuple(sorted(check_showcase.VERIFICATION_STATES))

# 精选「形近但非法」的验证态边界，全部不属于 VERIFICATION_STATES：大小写变体、
# 连字符变体、前后空格（枚举要求精确匹配）、部分匹配、取自 exit status 枚举的值、
# 空串/纯空白、通用噪声——稳定覆盖「非法取值使校验失败并指出该行」的关键边界。
_KNOWN_ILLEGAL_STATES = (
    "",                    # 空串
    " ",                   # 纯空白
    "code-integrated",     # 连字符变体（枚举用空格分隔）
    "Code Integrated",     # 大小写变体（枚举为全小写）
    " code integrated ",   # 前后空格（枚举要求精确匹配、无包裹空白）
    "verified",            # 部分匹配（manual verified 的尾词）
    "manual",              # 部分匹配（前缀）
    "integrated",          # 部分匹配
    "done",                # exit status 取值，非 verification_state
    "pending",             # exit status 取值
    "satisfied",           # 近义噪声
    "unknown",             # 通用噪声
)

# 非法验证态策略：精选边界 + 任意文本（过滤掉恰好命中合法枚举的取值）。
_illegal_verification_state_strategy = st.one_of(
    st.sampled_from(_KNOWN_ILLEGAL_STATES),
    st.text(max_size=24).filter(
        lambda s: s not in check_showcase.VERIFICATION_STATES
    ),
)

# 合法验证态策略。
_legal_verification_state_strategy = st.sampled_from(_LEGAL_VERIFICATION_STATES)

# 单个 deliverable 的验证态：合法 + 非法混合采样（加权合法，便于探索「全合法 →
# 无 error」分支，同时保证非法分支也常见）。
_verification_state_strategy = st.one_of(
    _legal_verification_state_strategy,
    _legal_verification_state_strategy,
    _illegal_verification_state_strategy,
)

# 一组 deliverable 的验证态列表（max_size=12 足以覆盖多行混合；min_size 默认 0
# 覆盖空 deliverable 集合）。
_verification_states_strategy = st.lists(_verification_state_strategy, max_size=12)


def _build_deliverables_from_states(states: list) -> list:
    """把 verification_state 列表构造为 Deliverable 列表（每行唯一 id+行号）。

    给每个 deliverable 唯一 deliverable_id（`deliv_{i}`）与唯一 line_number，
    避免空 id / 重复 id 维度的 error 干扰 verification_state 维度断言（任务约束）。
    requirement / notes 留空、manual_gate 置 'no'——`_validate_deliverables` 只校验
    deliverable_id 与 verification_state，不涉及 manual gate，故不影响本属性。
    """
    deliverables = []
    for idx, state in enumerate(states):
        deliverables.append(
            check_showcase.Deliverable(
                deliverable_id="deliv_%d" % idx,
                requirement="",
                verification_state=state,
                manual_gate="no",
                notes="",
                line_number=100 + idx,
            )
        )
    return deliverables


# Feature: presentation-showcase, Property 5: For any Showcase_Manifest deliverable 行集合，结构校验 SHALL 通过当且仅当每一个 deliverable 的 verification_state 属于枚举集合 {code integrated, command checked, artifact backed, manual verified, manual unverified}；任一非法取值 SHALL 使校验失败并指出该行。
@settings(max_examples=200, deadline=None)
@given(states=_verification_states_strategy)
# 关键边界 example：空集、全部 5 个合法枚举、合法+非法混合、全非法形近边界。
@example(states=[])
@example(states=list(_LEGAL_VERIFICATION_STATES))
@example(states=["code integrated", "bogus"])
@example(states=["", " code integrated ", "Code Integrated"])
def test_property_5_verification_state_enum_validity(states: list) -> None:
    """Property 5：Showcase_Manifest deliverable 验证态枚举合法性。

    **Validates: Requirements 11.2**

    对任意 deliverable 行集合（每行唯一 deliverable_id，避免 id 维度 error 干扰），
    断言 check_showcase._validate_deliverables 在 verification_state 维度满足：
    (a) 当所有 verification_state 合法时，该维度不产生任何 error；
    (b) 存在非法取值时，校验对**每个**非法行恰好产生一条 verification_state error，
        且该 error 定位到该行（含 deliverable_id 与行号）。
    """
    deliverables = _build_deliverables_from_states(states)
    errors = []
    check_showcase._validate_deliverables(deliverables, errors)

    # 仅取 verification_state 维度 error（避免其它维度 error 干扰本属性断言）。
    vstate_errors = [err for err in errors if "invalid verification_state" in err]

    # 独立 oracle：以实际是否落在枚举集合判定非法（不依赖生成器的合法/非法标签）。
    illegal = [
        deliv
        for deliv in deliverables
        if deliv.verification_state not in check_showcase.VERIFICATION_STATES
    ]

    # 当且仅当性：verification_state error 数恰等于非法行数。
    assert len(vstate_errors) == len(illegal)

    if not illegal:
        # (a) 全部合法（含空集）→ 该维度无 error。
        assert vstate_errors == []
    else:
        # (b) 每个非法行都被定位到（error 含 deliverable_id 与行号）。
        for deliv in illegal:
            loc = "deliverable_id '%s' (line %d)" % (
                deliv.deliverable_id,
                deliv.line_number,
            )
            assert any(loc in err for err in vstate_errors), (
                "非法 verification_state 行未被定位：%s" % loc
            )


# =============================================================================
# Property 6：Showcase_Manifest readiness 自洽（R11.4 / 任务 2.5）
# 被测：scripts/check_showcase.py 的 compute_readiness(...)（返回 ReadinessResult）、
#       READINESS_READY / READINESS_NOT_READY 文案常量、EXIT_STATUS_VALUES 枚举。
# compute_readiness 接受 status 字符串序列（id 占位 #1..）或 (id, status) 序列，
# 本属性同时覆盖这两种输入形态。
# =============================================================================

# 合法 exit status 枚举（design Data Models：pending / done / not-accepted）。
_EXIT_STATUS_POOL = tuple(sorted(check_showcase.EXIT_STATUS_VALUES))

# 「形近但非 pending」噪声：compute_readiness 以精确 `status == "pending"` 判定，
# 故大小写变体（Pending / PENDING）、带空白包裹（" pending" / "pending "）、枚举外
# 取值（accepted / blocked / n/a）与空串/纯空白都属于**非 pending**。这些噪声用于
# 探索「非 pending 但非合法枚举」的鲁棒性，断言端用同一精确规则交叉验证。
_STATUS_NOISE = (
    "",                # 空串（非 pending）
    " ",               # 纯空白（非 pending）
    "Pending",         # 大小写变体（精确匹配下非 pending）
    "PENDING",         # 大小写变体
    " pending",        # 前导空白（精确匹配下非 pending）
    "pending ",        # 尾随空白
    "Done",            # 大小写变体
    "accepted",        # 枚举外噪声
    "blocked",         # 枚举外噪声
    "n/a",             # 枚举外噪声
)

# 单个 exit status 策略：加权让合法枚举更常见（便于探索「全非 pending → ready」
# 分支），同时让 pending 与噪声足量出现（探索 not-ready 分支与精确匹配边界）。
_exit_status_strategy = st.one_of(
    st.sampled_from(_EXIT_STATUS_POOL),
    st.sampled_from(_EXIT_STATUS_POOL),
    st.sampled_from(_STATUS_NOISE),
)

# 一组 exit criteria 状态组合（max_size=8 足以覆盖多条混合；min_size 默认 0 覆盖
# 空集边界——真空真规避：空集 SHALL 判 not ready）。
_exit_statuses_strategy = st.lists(_exit_status_strategy, max_size=8)


# Feature: presentation-showcase, Property 6: For any 5 条 P_demo.exit exit criteria 状态组合，Showcase_Manifest SHALL 报告 ready for owner review 当且仅当全部 5 条状态均为非 pending。
@settings(max_examples=200, deadline=None)
@given(statuses=_exit_statuses_strategy)
# 关键边界 example：空集（→ not ready，真空真规避）、恰 5 条全 done（→ ready）、
# 恰 5 条含一个 pending（→ not ready）、全 pending、合法+噪声混合（含大小写/空白变体）。
@example(statuses=[])
@example(statuses=["done", "done", "not-accepted", "done", "done"])
@example(statuses=["done", "done", "pending", "not-accepted", "done"])
@example(statuses=["pending", "pending", "pending", "pending", "pending"])
@example(statuses=["done", "PENDING", " pending", "not-accepted", "Done"])
def test_property_6_readiness_self_consistency(statuses: list) -> None:
    """Property 6：Showcase_Manifest readiness 自洽。

    **Validates: Requirements 11.4**

    对任意 exit criteria 状态组合（含空集、合法枚举与形近噪声的混合），断言
    compute_readiness 满足「当且仅当」自洽性，且对 str 序列与 (id, status) 序列
    两种输入形态结论一致：
    (a) result.ready 为 True ⟺ 序列非空且无任何 status == "pending"（空集 → not ready，
        规避「全部非 pending」对空集的真空真误报）；
    (b) result.readiness 文案与 ready bool 自洽（ready → READINESS_READY，否则
        READINESS_NOT_READY）；
    (c) result.pending_exit_ids 恰为 status == "pending" 的项（(id,status) 形态为原
        id，str 形态为 1-based 占位 id #1..）；
    (d) 未提供 deliverables 时 blocking_manual_gates 恒为空（无阻塞项可列出）。
    """
    # 独立 oracle：以精确 `status == "pending"` 判定（与 compute_readiness 等价但
    # 分开实现），不依赖生成器对「合法/噪声」的标签。
    expected_ready = bool(statuses) and all(status != "pending" for status in statuses)
    expected_readiness = (
        check_showcase.READINESS_READY
        if expected_ready
        else check_showcase.READINESS_NOT_READY
    )

    # ---- 形态一：(id, status) 序列（每条唯一 id，断言 pending_exit_ids 为原 id）----
    pairs = [("exit_%d" % idx, status) for idx, status in enumerate(statuses)]
    expected_pending_pair_ids = [
        exit_id for exit_id, status in pairs if status == "pending"
    ]
    result_pairs = check_showcase.compute_readiness(pairs)

    # (a) 当且仅当性：ready ⟺ 非空且无任何 pending。
    assert result_pairs.ready is expected_ready
    # (b) readiness 文案与 ready bool 自洽。
    assert result_pairs.readiness == expected_readiness
    # (c) pending_exit_ids 恰为 pending 项（原 id，保持原序）。
    assert result_pairs.pending_exit_ids == expected_pending_pair_ids
    # (d) 未传 deliverables → 无可列出的阻塞 manual gate。
    assert result_pairs.blocking_manual_gates == []

    # ---- 形态二：纯 status 字符串序列（id 用 1-based 占位 #1..）----
    expected_pending_placeholder_ids = [
        "#%d" % idx
        for idx, status in enumerate(statuses, start=1)
        if status == "pending"
    ]
    result_str = check_showcase.compute_readiness(statuses)

    # 两种输入形态的 ready / readiness 结论一致（自洽性不依赖 id 形态）。
    assert result_str.ready is expected_ready
    assert result_str.readiness == expected_readiness
    # pending_exit_ids 恰为 pending 项（占位 id #1..，与位置一一对应）。
    assert result_str.pending_exit_ids == expected_pending_placeholder_ids
    assert result_str.blocking_manual_gates == []


# =============================================================================
# Property 7：Manual gate 不变量（R11.3 / 任务 2.6）
# 被测：scripts/check_showcase.py 的 validate_manual_gate(deliverables)、
#       deliverable_depends_on_manual(deliverable)、KNOWN_MANUAL_DELIVERABLE_IDS /
#       MANUAL_DEPENDENCY_KEYWORDS / OFFLINE_SATISFIED_STATES 常量、Deliverable。
# validate_manual_gate 只产两类 error，本属性精确对应其两条规则：
#   规则1：依赖人工 且 未声明 manual_gate=yes      → "depends on manual verification ... expected 'yes'"
#   规则2：(依赖人工 或 声明 manual_gate=yes) 且 验证态∈OFFLINE_SATISFIED_STATES
#                                                  → "is a Manual_Verification_Gate item ... satisfied by an offline gate"
# =============================================================================

# ---- 独立 oracle：与 check_showcase 的判定等价但分开实现，做交叉验证 ----
def _oracle_depends_on_manual(deliverable_id: str, requirement: str, notes: str) -> bool:
    """独立复算「是否依赖人工」：命中已知人工 id 或 requirement+notes 命中关键词。

    交叉验证 check_showcase.deliverable_depends_on_manual，刻意不复用其实现
    （此处用显式 for 循环 + 字符串拼接，对齐其「id 兜底 + 关键词小写扫描」语义）。
    """
    if deliverable_id in check_showcase.KNOWN_MANUAL_DELIVERABLE_IDS:
        return True
    haystack = (requirement + " " + notes).lower()
    for keyword in check_showcase.MANUAL_DEPENDENCY_KEYWORDS:
        if keyword in haystack:
            return True
    return False


def _oracle_declared_manual(manual_gate: str) -> bool:
    """独立复算「是否声明 manual_gate=yes」：strip + 小写后精确等于 'yes'。"""
    return manual_gate.strip().lower() == "yes"


# ---- Hypothesis 策略：生成多样的 deliverable「配方」，测试函数据此构造 Deliverable ----
# 普通 id 占位：测试函数把它替换为唯一 deliv_NN（避免与已知人工 id 混淆）。
_NORMAL_ID_SENTINEL = "__normal__"

# deliverable_id：混合「命中 KNOWN_MANUAL_DELIVERABLE_IDS 的人工 id」与普通 id
# （加权普通 id，便于探索「靠关键词/无依赖」的分支）。
_deliverable_id_choice = st.one_of(
    st.sampled_from(check_showcase.KNOWN_MANUAL_DELIVERABLE_IDS),
    st.just(_NORMAL_ID_SENTINEL),
    st.just(_NORMAL_ID_SENTINEL),
)

# 命中人工依赖关键词的文本片段：原样关键词 + 大写变体（验 .lower() 归一）+
# 嵌入句子（前后缀刻意不含任何关键词，确保只靠 kw 命中）。
_keyword_fragment = st.one_of(
    st.sampled_from(check_showcase.MANUAL_DEPENDENCY_KEYWORDS),
    st.sampled_from(tuple(kw.upper() for kw in check_showcase.MANUAL_DEPENDENCY_KEYWORDS)),
    st.builds(
        lambda pre, kw, post: "%s%s%s" % (pre, kw, post),
        st.sampled_from(("", "依赖 ", "需要")),
        st.sampled_from(check_showcase.MANUAL_DEPENDENCY_KEYWORDS),
        st.sampled_from(("", " 输出", " 完成")),
    ),
)
# 中性文本：手选确保不含任一 MANUAL_DEPENDENCY_KEYWORDS（不触发关键词命中）。
_NEUTRAL_TEXT = (
    "",
    "自动离线校验",
    "command checked via script",
    "命令行核对产物",
    "see C2 below",
    "纯脚本生成",
)
# 单个 requirement / notes 文本：关键词片段 + 中性文本混合（加权中性以平衡分布）。
_text_fragment = st.one_of(
    _keyword_fragment,
    st.sampled_from(_NEUTRAL_TEXT),
    st.sampled_from(_NEUTRAL_TEXT),
)

# manual_gate：yes/no 及其大小写/空白变体与无关取值（验 strip+lower 精确匹配 'yes'）。
_manual_gate_choice = st.sampled_from(("yes", "no", "Yes", " yes ", "YES", "", "n/a"))

# verification_state：5 个合法枚举混合（枚举合法性由 Property 5 负责，本属性只关心
# 验证态是否落在 OFFLINE_SATISFIED_STATES）。
_verification_state_choice = st.sampled_from(tuple(sorted(check_showcase.VERIFICATION_STATES)))

# 单个 deliverable 配方。
_deliverable_recipe = st.fixed_dictionaries(
    {
        "id_choice": _deliverable_id_choice,
        "requirement": _text_fragment,
        "notes": _text_fragment,
        "manual_gate": _manual_gate_choice,
        "verification_state": _verification_state_choice,
    }
)
# 一组 deliverable 配方（max_size=10 足以覆盖多行混合；min_size 默认 0 覆盖空集）。
_deliverable_recipes_strategy = st.lists(_deliverable_recipe, max_size=10)


def _build_deliverables_from_recipes(recipes: list) -> list:
    """把配方列表构造为 Deliverable 列表（普通 id 唯一化、line_number 唯一等长）。

    - 普通 id 占位 `_NORMAL_ID_SENTINEL` → `deliv_NN`（唯一）；已知人工 id 原样保留
      （可重复，靠 line_number 区分定位）。
    - line_number 用 1000+idx（4 位等长，避免 loc 子串前缀互相包含）。
    """
    deliverables = []
    for idx, rec in enumerate(recipes):
        raw_id = rec["id_choice"]
        deliverable_id = ("deliv_%02d" % idx) if raw_id == _NORMAL_ID_SENTINEL else raw_id
        deliverables.append(
            check_showcase.Deliverable(
                deliverable_id=deliverable_id,
                requirement=rec["requirement"],
                verification_state=rec["verification_state"],
                manual_gate=rec["manual_gate"],
                notes=rec["notes"],
                line_number=1000 + idx,
            )
        )
    return deliverables


# Feature: presentation-showcase, Property 7: For any Showcase_Manifest deliverable，若其依赖真实 LLM、人工 reviewer 或真实 Godot 窗口（命中人工依赖标记），则其 manual_gate SHALL 为 yes，且其验证态 SHALL NOT 被离线门禁标记为 satisfied/manual verified；校验器在"依赖人工但 manual_gate=no"时 SHALL 报错。
@settings(max_examples=200, deadline=None)
@given(recipes=_deliverable_recipes_strategy)
# 关键边界 example：
#   1) 空集 → 无 error。
#   2) 已知人工 id + manual_gate=no + manual unverified → 仅规则1（依赖人工但未标 yes）。
#   3) 已知人工 id + manual_gate=yes + manual verified  → 仅规则2（离线门禁不得代为满足）。
#   4) 关键词命中 + manual_gate=no + code integrated     → 规则1 + 规则2 同时触发。
#   5) 不依赖人工 + manual_gate=no + artifact backed     → 无 error。
#   6) 声明 manual_gate=yes（非依赖）+ command checked    → 仅规则2。
#   7) 声明 manual_gate=yes（非依赖）+ manual unverified   → 无 error（合法待办态）。
#   8) 大写关键词 + manual_gate=no + code integrated      → 规则1 + 规则2（验 .lower() 归一）。
@example(recipes=[])
@example(
    recipes=[
        {"id_choice": "final_demo_video", "requirement": "", "notes": "",
         "manual_gate": "no", "verification_state": "manual unverified"}
    ]
)
@example(
    recipes=[
        {"id_choice": "godot_window_recheck", "requirement": "", "notes": "",
         "manual_gate": "yes", "verification_state": "manual verified"}
    ]
)
@example(
    recipes=[
        {"id_choice": _NORMAL_ID_SENTINEL, "requirement": "", "notes": "依赖真实 llm 输出",
         "manual_gate": "no", "verification_state": "code integrated"}
    ]
)
@example(
    recipes=[
        {"id_choice": _NORMAL_ID_SENTINEL, "requirement": "纯脚本生成", "notes": "命令行核对产物",
         "manual_gate": "no", "verification_state": "artifact backed"}
    ]
)
@example(
    recipes=[
        {"id_choice": _NORMAL_ID_SENTINEL, "requirement": "", "notes": "",
         "manual_gate": "yes", "verification_state": "command checked"}
    ]
)
@example(
    recipes=[
        {"id_choice": _NORMAL_ID_SENTINEL, "requirement": "", "notes": "",
         "manual_gate": "yes", "verification_state": "manual unverified"}
    ]
)
@example(
    recipes=[
        {"id_choice": _NORMAL_ID_SENTINEL, "requirement": "REAL LLM REQUIRED", "notes": "",
         "manual_gate": "no", "verification_state": "code integrated"}
    ]
)
def test_property_7_manual_gate_invariant(recipes: list) -> None:
    """Property 7：Manual_Verification_Gate 不变量。

    **Validates: Requirements 11.3**

    对任意 deliverable 列表（混合已知人工 id / 普通 id、关键词文本 / 中性文本、
    manual_gate 变体、5 个合法验证态），用独立 oracle 复算「是否依赖人工」与
    「是否声明 manual_gate=yes」，断言 check_showcase.validate_manual_gate 精确对应
    其两条规则：
    (规则1) 依赖人工 且 manual_gate≠yes → 恰一条「依赖人工但 manual_gate≠yes」error；
    (规则2) (依赖人工 或 声明 manual_gate=yes) 且 验证态∈OFFLINE_SATISFIED_STATES →
            恰一条「离线门禁不得代为满足人工项」error；
    (反向) 既不触发规则1 也不触发规则2 的行 → 不产生任何 error（涵盖「不依赖人工且
            manual_gate=no」与「声明 manual_gate=yes 且验证态=manual unverified」）。
    所有 error 均含 deliverable_id 与行号定位，且只属于这两类。
    """
    deliverables = _build_deliverables_from_recipes(recipes)
    errors = check_showcase.validate_manual_gate(deliverables)

    # validate_manual_gate 只产两类 error，用稳定子串分类（互不重叠）。
    rule1_errors = [err for err in errors if "depends on manual verification" in err]
    rule2_errors = [err for err in errors if "is a Manual_Verification_Gate item" in err]
    # 完整性：每条 error 恰好归入两类之一（无第三类、无重复计数）。
    assert len(rule1_errors) + len(rule2_errors) == len(errors)

    expected_rule1 = 0
    expected_rule2 = 0
    for deliv in deliverables:
        loc = "deliverable_id '%s' (line %d)" % (deliv.deliverable_id, deliv.line_number)
        depends = _oracle_depends_on_manual(deliv.deliverable_id, deliv.requirement, deliv.notes)
        declared = _oracle_declared_manual(deliv.manual_gate)
        want_rule1 = depends and not declared
        want_rule2 = (depends or declared) and (
            deliv.verification_state in check_showcase.OFFLINE_SATISFIED_STATES
        )

        # 规则1：依赖人工但未声明 manual_gate=yes ⟺ 该行恰被一条规则1 error 定位。
        if want_rule1:
            expected_rule1 += 1
            assert any(loc in err for err in rule1_errors), (
                "依赖人工但 manual_gate≠yes 的行未被规则1 error 定位：%s" % loc
            )
        else:
            assert not any(loc in err for err in rule1_errors), (
                "不应触发规则1 的行被误报：%s" % loc
            )

        # 规则2：人工 gate 项被离线门禁标满足 ⟺ 该行恰被一条规则2 error 定位。
        if want_rule2:
            expected_rule2 += 1
            assert any(loc in err for err in rule2_errors), (
                "人工 gate 项被离线门禁标满足却未被规则2 error 定位：%s" % loc
            )
        else:
            assert not any(loc in err for err in rule2_errors), (
                "不应触发规则2 的行被误报：%s" % loc
            )

        # 反向：两条规则都不触发的行 → 不产生任何 error（含其它维度）。
        if not want_rule1 and not want_rule2:
            assert not any(loc in err for err in errors), (
                "既不依赖人工/未声明 manual gate 又非离线满足的行不应有 error：%s" % loc
            )

    # 当且仅当性：两类 error 计数恰等于 oracle 复算的触发行数。
    assert len(rule1_errors) == expected_rule1
    assert len(rule2_errors) == expected_rule2


# =============================================================================
# Property 3：Figure/Table 覆盖率与 pending 集（R6.2 / R6.4 / 任务 3.2）
# 被测：scripts/check_showcase.py 的 compute_coverage(renderable_targets,
#       rendered_set)（返回 CoverageResult）、FigureTableTarget、CoverageResult、
#       COVERAGE_THRESHOLD（0.70）。
# compute_coverage 防御性地按 renderable 过滤并按 key 去重，故本属性刻意混入
# non-renderable target 与重复 key，交叉验证「过滤 + 去重」语义。
# =============================================================================

# renderable target 的 kind / number：number 取值域小（1..6），便于在 max_size 内
# 制造重复 key（验证 compute_coverage 的按 key 去重）。
_COVERAGE_TARGET_KINDS = ("figure", "table")
_COVERAGE_NUMBER_POOL = st.integers(min_value=1, max_value=6)


def _rt(kind: str, number: int) -> "check_showcase.FigureTableTarget":
    """构造 renderable FigureTableTarget（key 用与 compute_coverage 一致的规范格式）。

    key 复刻 tokenize_target_cell 的 `f"{kind.capitalize()} {number}"`（如 "Figure 4" /
    "Table 2"），确保与被测实现的去重/交集口径对齐。
    """
    key = "%s %d" % (kind.capitalize(), number)
    return check_showcase.FigureTableTarget(
        kind=kind, number=number, key=key, renderable=True, raw=key
    )


def _nrt(phrase: str) -> "check_showcase.FigureTableTarget":
    """构造 non-renderable FigureTableTarget（应被 compute_coverage 过滤出分母）。"""
    return check_showcase.FigureTableTarget(
        kind="non-renderable", number=None, key=phrase, renderable=False, raw=phrase
    )


# renderable target 策略。
_renderable_target_strategy = st.builds(
    _rt, st.sampled_from(_COVERAGE_TARGET_KINDS), _COVERAGE_NUMBER_POOL
)
# non-renderable 噪声短语（手选，确保非空、互异；验证「过滤且不计入分母」）。
_NONRENDERABLE_PHRASES = (
    "Limitations box",
    "Workflow",
    "Regression guardrail note",
    "Limitations / Regression guardrail note",
)
_nonrenderable_target_strategy = st.builds(_nrt, st.sampled_from(_NONRENDERABLE_PHRASES))
# 单个 target：加权 renderable（便于探索覆盖率各分支），混入 non-renderable 与重复 key。
_coverage_target_item = st.one_of(
    _renderable_target_strategy,
    _renderable_target_strategy,
    _nonrenderable_target_strategy,
)
# rendered_set 外来噪声 key：不属于任何生成的 renderable target，验证
# |rendered ∩ renderable| 只计交集（外来 key 不抬高 rendered 计数）。
_RENDERED_NOISE_KEYS = ("Figure 99", "Table 99", "ghost-key", "Limitations box")


@st.composite
def _coverage_inputs(draw):
    """生成 (targets, rendered_set)。

    targets：renderable + non-renderable + 重复 key 混合（max_size=14，min_size 默认 0
    覆盖空集）。rendered_set：取自 targets 的 renderable key 子集（含全选/全不选边界），
    再并入若干不相关噪声 key（探索交集鲁棒性）。
    """
    targets = draw(st.lists(_coverage_target_item, max_size=14))
    renderable_keys = sorted({t.key for t in targets if t.renderable})
    if renderable_keys:
        rendered_subset = draw(
            st.lists(
                st.sampled_from(renderable_keys), max_size=len(renderable_keys) + 2
            )
        )
    else:
        rendered_subset = []
    noise = draw(st.lists(st.sampled_from(_RENDERED_NOISE_KEYS), max_size=3))
    rendered_set = set(rendered_subset) | set(noise)
    return targets, rendered_set


# Feature: presentation-showcase, Property 3: For any 可渲染 Figure_Table_Target 集合与已渲染资产子集，覆盖率计算 SHALL 满足：coverage_percent = |rendered ∩ renderable| / |renderable| 且落在 [0,1]；pass 为真当且仅当 coverage_percent >= 0.70；pending 列表 SHALL 恰为未渲染的 renderable target 集合，且每一项 SHALL 携带 blocking_reason。
@settings(max_examples=200, deadline=None)
@given(data=_coverage_inputs())
# 关键边界 example：
#   1) 空集 → 分母 0：percent=0.0 / passed=False / pending=[]（安全默认，规避除零）。
#   2) 全 non-renderable → 分母仍 0（过滤后 renderable 为空）。
#   3) 全渲染 → percent=1.0 / passed=True / pending=[]。
#   4) 0 渲染 → percent=0.0 / passed=False / pending 为全部 renderable。
#   5) 刚好 0.70 边界：7/10 → passed=True。
#   6) 略低于 0.70：6/10=0.6 → passed=False。
#   7) 重复 key → 按 key 去重（figure 1 出现两次只计一次，total=2）。
#   8) non-renderable 混入 + 外来 rendered 噪声 key → 只计 renderable 交集。
@example(data=([], set()))
@example(data=([_nrt("Limitations box"), _nrt("Workflow")], set()))
@example(data=([_rt("figure", 1), _rt("table", 2)], {"Figure 1", "Table 2"}))
@example(data=([_rt("figure", 1), _rt("table", 2)], set()))
@example(
    data=(
        [_rt("figure", n) for n in range(1, 6)]
        + [_rt("table", n) for n in range(1, 6)],
        {"Figure 1", "Figure 2", "Figure 3", "Figure 4", "Figure 5", "Table 1", "Table 2"},
    )
)
@example(
    data=(
        [_rt("figure", n) for n in range(1, 6)]
        + [_rt("table", n) for n in range(1, 6)],
        {"Figure 1", "Figure 2", "Figure 3", "Figure 4", "Figure 5", "Table 1"},
    )
)
@example(data=([_rt("figure", 1), _rt("figure", 1), _rt("table", 2)], {"Figure 1"}))
@example(data=([_rt("figure", 1), _nrt("Workflow")], {"Figure 1", "Workflow", "Figure 99"}))
def test_property_3_coverage_and_pending(data) -> None:
    """Property 3：Figure/Table 覆盖率与 pending 集。

    **Validates: Requirements 6.2, 6.4**

    对任意 target 集合（混合 renderable / non-renderable / 重复 key）与任意已渲染
    key 集合（含外来噪声 key），用独立 oracle 复算「按 key 去重 + 仅 renderable」后的
    分母与交集，断言 compute_coverage 满足：
    (1) total / rendered 与 oracle 一致（验证过滤 + 去重）；
    (2) percent 恒落在 [0,1]；
    (3) 非空 renderable 时 percent = |rendered∩renderable| / |renderable|；
        空 renderable（分母 0）时取安全默认 percent=0.0 / passed=False / pending=[]；
    (4) passed 为真当且仅当 percent >= COVERAGE_THRESHOLD（0.70）；
    (5) pending 的 target 集合恰为「未渲染的 renderable target」key 集合，无重复；
    (6) 每个 pending 项携带非空 blocking_reason（R6.4）；
    (7) rendered + len(pending) == total（覆盖与 pending 划分完整）。
    """
    targets, rendered_set = data
    result = check_showcase.compute_coverage(targets, rendered_set)

    # 独立 oracle：按 key 去重（保留首次出现）+ 仅保留 renderable（与 compute_coverage
    # 等价但分开实现，刻意不复用其代码，交叉验证过滤 + 去重）。
    unique: dict = {}
    for target in targets:
        if target.renderable and target.key not in unique:
            unique[target.key] = target
    total = len(unique)
    rendered_keys = {key for key in unique if key in rendered_set}
    rendered_count = len(rendered_keys)

    # (1) total / rendered 与 oracle 一致。
    assert result.total == total
    assert result.rendered == rendered_count

    # (2) percent 恒落在 [0,1]。
    assert 0.0 <= result.percent <= 1.0

    if total == 0:
        # (3a) 空 renderable 边界（分母 0）：安全默认，规避除零。
        assert result.percent == 0.0
        assert result.passed is False
        assert result.pending == []
    else:
        # (3b) percent = |rendered∩renderable| / |renderable|。
        assert result.percent == pytest.approx(rendered_count / total)
        # (4) passed ⟺ percent >= COVERAGE_THRESHOLD（0.70）。
        expected_passed = (rendered_count / total) >= check_showcase.COVERAGE_THRESHOLD
        assert result.passed is expected_passed

    # (5) pending 的 target 集合恰为「未渲染的 renderable target」key 集合。
    pending_keys = [item["target"] for item in result.pending]
    expected_pending_keys = {key for key in unique if key not in rendered_set}
    assert set(pending_keys) == expected_pending_keys
    # pending 无重复：每个未渲染 renderable target 恰对应一项。
    assert len(pending_keys) == len(expected_pending_keys)

    # (6) 每个 pending 项都携带非空 blocking_reason（R6.4）。
    for item in result.pending:
        reason = item.get("blocking_reason")
        assert isinstance(reason, str)
        assert reason.strip() != "", "pending 项缺少非空 blocking_reason：%r" % item

    # (7) rendered + len(pending) == total（覆盖与 pending 对 renderable 的划分完整）。
    assert result.rendered + len(result.pending) == result.total


# =============================================================================
# Property 4：口径一致性扫描（R10 / R7.4 / R8.4 / 任务 4.2）
# 被测：scripts/check_showcase.py 的 scan_consistency(text, source_name)（返回
#       ConsistencyResult）及常量 CONSISTENCY_CLAIM_IDS / CAVEAT_WORDING_PATTERN /
#       FORBIDDEN_OVERCLAIM_PHRASES / CLAIM_STATUS_TERMS。
#
# scan_consistency 逐行规则（模块注释规则 1-4，大小写不敏感、连字符与空格等价）：
#   规则1 行内无 claim id（C2/C3/C4，词边界）           → 跳过。
#   规则2 有 claim id 但既无状态词也无 caveat 措辞        → 跳过（纯引用行）。
#   规则3 含 promoted-with-caveat 措辞                   → compliant（caveat 优先，
#         即使同时含 proven 等也判 compliant）。
#   规则4 声明了状态却缺 caveat → non-compliant：
#         命中 FORBIDDEN_OVERCLAIM_PHRASES → kind="overclaim"，否则 "missing-caveat"。
#
# 策略：用「行配方」生成器组合各维度（真 claim id / 词边界陷阱 / 状态词 / caveat
# 变体 / overclaim 短语 / 中性噪声），随机重排拼成一行，多行拼成文本。oracle 用
# **纯 ground-truth**（记录每行实际放入的成分，按规则 1-4 复算期望），刻意不复用
# 被测的任何正则或内部函数（_claim_ids_in_line / _matched_* / scan_consistency），
# 从而能交叉验证：claim id 词边界（C2 不被 C20/C234/c2/AC2/C2x 误匹配）、caveat 的
# 连字符/空格/大小写等价识别、status/overclaim 短语识别与规则判定顺序。
# =============================================================================

# 真 claim id token → 该行**真** claim id（ground truth，保序去重）。涵盖单个、
# 反引号包裹（`C2`，design 注释明确允许）、同行多个（C2 C4 / C3 C4）。
_P4_TRUE_CLAIM_TOKENS = {
    "C2": ("C2",),
    "C3": ("C3",),
    "C4": ("C4",),
    "`C2`": ("C2",),
    "`C4`": ("C4",),
    "C2 C4": ("C2", "C4"),
    "C3 C4": ("C3", "C4"),
}

# 词边界陷阱：均**不应**被 _CLAIM_ID_TOKEN（(?<![A-Za-z0-9])C[234](?![A-Za-z0-9])）
# 匹配——C20/C42（后接数字）、C234（多位）、c2/c3（小写）、C5（非 2/3/4）、AC2（前接
# 字母）、C2x（后接字母）。生成「纯陷阱行」验证不误报（真 claim id = 空 → 规则1跳过）。
_P4_TRAP_TOKENS = ("C20", "C234", "c2", "c3", "C5", "C42", "AC2", "C2x")

# 状态词候选：取自 CLAIM_STATUS_TERMS，但剔除 "proven"（它同时是 overclaim 短语，
# 单独出现会被判 overclaim，破坏 ground-truth 的 has_forbidden 记账；proven 由
# overclaim 短语维度单独覆盖）。其余状态词单独出现都不触发任何 overclaim 短语。
_P4_STATUS_CANDIDATES = tuple(
    term for term in check_showcase.CLAIM_STATUS_TERMS if term != "proven"
)

# caveat 措辞变体：覆盖连字符/空格等价与大小写不敏感（均应被 CAVEAT_WORDING_PATTERN
# 匹配 → 规则3 compliant）。
_P4_CAVEAT_VARIANTS = (
    "promoted with caveat",
    "promoted-with-caveat",
    "Promoted With Caveat",
    "PROMOTED WITH CAVEAT",
    "promoted   with  caveat",
    "promoted-with caveat",
    "promoted with-caveat",
)

# 中性噪声词：手选确保不含任何 claim id、状态词、overclaim 短语组成词或 caveat 措辞，
# 故只增加文本多样性，不改变任何行的判定（ground-truth 不受其影响）。
_P4_NEUTRAL_WORDS = (
    "showcase", "material", "owner", "review", "section",
    "below", "above", "see", "note", "reference", "entry",
    "portfolio", "walkthrough", "blog", "readme", "caption",
    "and", "the", "展示层", "见下方", "参考",
)


@st.composite
def _p4_line_recipe(draw):
    """生成单行配方：组合各维度成分，随机重排拼成一行，并记录 ground-truth 字段。

    返回 dict：
      - line：渲染后的行文本（各成分以空格连接、随机重排）。
      - claim_ids：该行**真** claim id（trap 不计入；ground truth）。
      - has_status_token / has_caveat / has_forbidden：是否放入了状态词 / caveat
        措辞 / overclaim 短语（ground truth，供 oracle 按规则 1-4 复算）。
    """

    claim = draw(st.sampled_from((None,) + tuple(_P4_TRUE_CLAIM_TOKENS)))
    trap = draw(st.sampled_from((None,) + _P4_TRAP_TOKENS))
    status = draw(st.sampled_from((None,) + _P4_STATUS_CANDIDATES))
    caveat = draw(st.sampled_from((None,) + _P4_CAVEAT_VARIANTS))
    forbidden = draw(
        st.sampled_from((None,) + tuple(check_showcase.FORBIDDEN_OVERCLAIM_PHRASES))
    )
    noise = draw(st.lists(st.sampled_from(_P4_NEUTRAL_WORDS), max_size=2))

    parts = [p for p in (claim, trap, status, caveat, forbidden) if p] + list(noise)
    if parts:
        parts = list(draw(st.permutations(parts)))

    return {
        "line": " ".join(parts),
        "claim_ids": _P4_TRUE_CLAIM_TOKENS.get(claim, ()) if claim else (),
        "has_status_token": status is not None,
        "has_caveat": caveat is not None,
        "has_forbidden": forbidden is not None,
    }


_p4_recipes_strategy = st.lists(_p4_line_recipe(), max_size=12)


def _p4_expected_kind(recipe: dict):
    """独立 ground-truth oracle：按 scan_consistency 规则 1-4 复算单行期望。

    返回 None（compliant / 跳过，不记 violation）或 "overclaim" / "missing-caveat"。
    刻意不复用被测正则/内部函数：仅依据该行实际放入的成分（ground truth）判定。
    要点：
      - 「行内是否声明状态」(被测 status_terms 非空) ⟺ 放了状态词 或 放了 caveat
        措辞（含 "promoted"）或 放了 overclaim 短语（每条都含一个状态词）。
      - caveat 优先：含 caveat → compliant（规则3），即使同时含 overclaim 短语。
    """

    if not recipe["claim_ids"]:
        return None  # 规则1：无 claim id。
    has_status = (
        recipe["has_status_token"] or recipe["has_caveat"] or recipe["has_forbidden"]
    )
    if not has_status and not recipe["has_caveat"]:
        return None  # 规则2：纯引用行。
    if recipe["has_caveat"]:
        return None  # 规则3：caveat 优先 → compliant。
    return "overclaim" if recipe["has_forbidden"] else "missing-caveat"  # 规则4。


# Feature: presentation-showcase, Property 4: 对任意 showcase material 文本，对每一行声明 claim C2/C3/C4 状态的语句：若该行包含 promoted-with-caveat 措辞（连字符与空格等价、大小写不敏感）则判为 compliant；若声明了状态但缺少 caveat 措辞，或使用了高于 owner-confirmed 级别的措辞，则判为 non-compliant 并能定位到该文件与行号。
@settings(max_examples=200, deadline=None)
@given(recipes=_p4_recipes_strategy, source=st.sampled_from(check_showcase.CONSISTENCY_SOURCE_FILENAMES))
# 关键边界 example：
#   1) 空文本 → 无 violation（compliant）。
#   2) 纯引用行（有 claim id 无状态词无 caveat）→ 规则2跳过。
#   3) 含 caveat 行即使含 proven → compliant（规则3 caveat 优先）。
#   4) overclaim 行（C3 proven，无 caveat）→ overclaim。
#   5) missing-caveat 行（C4 validated，无 caveat）→ missing-caveat。
#   6) 纯陷阱行 C20 / C234（有状态词/overclaim 但无真 claim id）→ 规则1跳过，不误报。
#   7) 反引号 `C2` + caveat → compliant。
#   8) 同行多 claim id（C2 C4 demonstrated）→ 单条 missing-caveat，claim_ids=(C2,C4)。
#   9) 多行混合（引用 / caveat / overclaim / missing / 陷阱 / 中性）→ 行号定位正确。
@example(recipes=[], source="README.md")
@example(
    recipes=[{"line": "see C2 below for details", "claim_ids": ("C2",),
              "has_status_token": False, "has_caveat": False, "has_forbidden": False}],
    source="README.md",
)
@example(
    recipes=[{"line": "C2 proven promoted with caveat", "claim_ids": ("C2",),
              "has_status_token": False, "has_caveat": True, "has_forbidden": True}],
    source="paper/blog_main.md",
)
@example(
    recipes=[{"line": "C3 proven", "claim_ids": ("C3",),
              "has_status_token": False, "has_caveat": False, "has_forbidden": True}],
    source="docs/showcase_manifest.md",
)
@example(
    recipes=[{"line": "C4 validated", "claim_ids": ("C4",),
              "has_status_token": True, "has_caveat": False, "has_forbidden": False}],
    source="docs/demo_capture_plan.md",
)
@example(
    recipes=[{"line": "C20 validated proven", "claim_ids": (),
              "has_status_token": True, "has_caveat": False, "has_forbidden": True},
             {"line": "C234 promoted", "claim_ids": (),
              "has_status_token": True, "has_caveat": False, "has_forbidden": False}],
    source="README.md",
)
@example(
    recipes=[{"line": "`C2` promoted with caveat", "claim_ids": ("C2",),
              "has_status_token": False, "has_caveat": True, "has_forbidden": False}],
    source="README.md",
)
@example(
    recipes=[{"line": "C2 C4 demonstrated", "claim_ids": ("C2", "C4"),
              "has_status_token": True, "has_caveat": False, "has_forbidden": False}],
    source="paper/blog_main.md",
)
@example(
    recipes=[
        {"line": "see C3 below", "claim_ids": ("C3",),
         "has_status_token": False, "has_caveat": False, "has_forbidden": False},
        {"line": "C2 promoted with caveat owner review", "claim_ids": ("C2",),
         "has_status_token": False, "has_caveat": True, "has_forbidden": False},
        {"line": "C4 fully validated", "claim_ids": ("C4",),
         "has_status_token": False, "has_caveat": False, "has_forbidden": True},
        {"line": "C3 verified", "claim_ids": ("C3",),
         "has_status_token": True, "has_caveat": False, "has_forbidden": False},
        {"line": "C42 proven", "claim_ids": (),
         "has_status_token": False, "has_caveat": False, "has_forbidden": True},
        {"line": "showcase material section", "claim_ids": (),
         "has_status_token": False, "has_caveat": False, "has_forbidden": False},
    ],
    source="docs/showcase_manifest.md",
)
def test_property_4_consistency_scan(recipes: list, source: str) -> None:
    """Property 4：口径一致性扫描（逐行 claim C2/C3/C4 状态合规判定）。

    **Validates: Requirements 7.4, 8.4, 10.1, 10.2, 10.3**

    对任意「行配方」列表（混合真 claim id / 词边界陷阱 / 状态词 / caveat 变体 /
    overclaim 短语 / 中性噪声，随机重排）拼成的 showcase material 文本，用独立
    ground-truth oracle 按规则 1-4 复算每行期望，断言 check_showcase.scan_consistency：
    (a) compliant ⟺ violations 为空（自洽）；
    (b) 每条 violation 都定位到正确的 source + 行号，claim_ids ⊆ {C2,C3,C4} 且非空，
        kind ∈ {overclaim, missing-caveat}；
    (c) violations 的 (行号, claim_ids, kind) 序列与 oracle **完全一致**（含顺序），
        从而交叉验证：claim id 词边界不误匹配（C20/C234/c2/AC2/C2x/C5/C42）、caveat
        的连字符/空格/大小写等价识别（含 proven 时 caveat 仍优先判 compliant）、
        声明状态缺 caveat 的 overclaim / missing-caveat 区分。
    """
    text = "\n".join(recipe["line"] for recipe in recipes)
    result = check_showcase.scan_consistency(text, source)

    # 独立 ground-truth oracle：逐行按规则 1-4 复算期望 (行号, claim_ids, kind)。
    expected = []
    for idx, recipe in enumerate(recipes, start=1):
        kind = _p4_expected_kind(recipe)
        if kind is not None:
            expected.append((idx, tuple(recipe["claim_ids"]), kind))

    # (a) compliant 当且仅当无 violation。
    assert result.compliant == (len(result.violations) == 0)

    # (b) 每条 violation 的定位与字段合法性。
    line_count = len(text.splitlines())
    legal_claim_ids = set(check_showcase.CONSISTENCY_CLAIM_IDS)
    for violation in result.violations:
        assert violation.source == source
        assert violation.kind in ("overclaim", "missing-caveat")
        assert violation.claim_ids, "violation 必须命中至少一个 claim id"
        assert set(violation.claim_ids) <= legal_claim_ids
        assert 1 <= violation.line_number <= line_count

    # (c) 强校验：violations 的 (行号, claim_ids, kind) 序列与 oracle 完全一致。
    actual = [
        (violation.line_number, violation.claim_ids, violation.kind)
        for violation in result.violations
    ]
    assert actual == expected


# =============================================================================
# example：capture plan 判据存在性（R1.1 / R1.2 / R1.3 / R1.4 / 任务 10.2）
# 被测：docs/demo_capture_plan.md（任务 10.1 写入的可机检判据文本与启动命令段落）。
# 非 PBT：脚本不解码视频，真实录制属 Manual_Verification_Gate；此处仅断言 capture
# plan **文档**已显式承载操作者录制时对照的判据语义与后端 + Godot 启动命令。
# 断言抓稳定关键词组合（数字 + 语义词 + R 标签锚点），避免脆弱的整句精确匹配。
# =============================================================================

from pathlib import Path  # noqa: E402  example 测试定位 capture plan 文档路径

# capture plan 文档相对本测试文件的路径：scripts/tests/ → 仓库根 → docs/。
_CAPTURE_PLAN_PATH = (
    Path(__file__).resolve().parents[2] / "docs" / "demo_capture_plan.md"
)


def _capture_plan_lines() -> list:
    """读取 capture plan，返回逐行 strip + lowercase 的行列表（按行匹配避免跨判据串扰）。"""
    raw = _CAPTURE_PLAN_PATH.read_text(encoding="utf-8")
    return [line.strip().lower() for line in raw.splitlines()]


def _has_line_with(lines: list, *keywords: str) -> bool:
    """存在某一行同时包含全部 keywords（小写）→ True。

    按「单行同时命中」匹配，确保判据数字（20/60/5/3）与其语义词出现在同一条判据行，
    规避「数字落在别处、语义词落在别处」的误判（如 60 中的 6/0 与 5 的串扰）。
    """
    return any(all(kw in line for kw in keywords) for line in lines)


def test_backend_showcase_starlight_contract_no_focus_no_trace() -> None:
    """Showcase Mode v1 后端聚合包：无 active focus / 无 trace 时仍可展示且只读。"""
    from app.main import create_town_app  # noqa: WPS433  测试内导入避免污染纯函数 PBT

    app = create_town_app(provider_mode="rule")
    app.runtime.world["activeFocus"] = None
    before = json.dumps(app.runtime.world, ensure_ascii=False, sort_keys=True, default=str)
    payload = app.showcase_starlight({})
    after = json.dumps(app.runtime.world, ensure_ascii=False, sort_keys=True, default=str)

    required_fields = {
        "schemaVersion",
        "scenario",
        "goalCard",
        "directorCard",
        "eventSkillCard",
        "npcDecisionCard",
        "traceEvidenceCard",
        "traceStrip",
        "deepLinks",
    }
    required_card_fields = {"id", "title", "kicker", "summary", "fields", "evidenceRefs", "status"}
    assert before == after
    assert payload["schemaVersion"] == "showcase.starlight.v1"
    assert required_fields <= set(payload)
    assert payload["directorCard"]["status"] == "fallback"
    assert payload["traceEvidenceCard"]["status"] == "fallback"
    assert [item["stage"] for item in payload["traceStrip"]] == ["goal", "director", "skill", "decision", "trace"]
    for card_key in ("goalCard", "directorCard", "eventSkillCard", "npcDecisionCard", "traceEvidenceCard"):
        assert required_card_fields <= set(payload[card_key])
        assert payload[card_key]["summary"]
    for link_key in ("director", "skills", "phase2", "traceFocus"):
        assert payload["deepLinks"][link_key].startswith("/api/")


def test_example_capture_plan_criteria_present() -> None:
    """example test (R1.1, R1.2, R1.3, R1.4)：capture plan 判据存在性。

    断言 docs/demo_capture_plan.md 已显式承载操作者录制对照所需的可机检判据语义与
    后端 + Godot 启动命令段落（任务 10.1 写入、任务 10.2 守护）：
    (R1.2) duration 20–60s 判据：同一行含 "duration" + "20" + "60" + "r1.2"。
    (R1.3) subject 连续可见 ≥5s 判据：同一行含 "subject" + "continuously visible"
           + "5" + "r1.3"。
    (R1.4) caption ≥3s 判据：同一行含 "caption" + "continuously visible" + "3"
           + "r1.4"。
    (R1.1) 后端 + Godot 启动命令段落：含标注 R1.1 的 backend/godot 启动命令小节，
           且正文含 `npm.cmd run start`（后端运行时）与 `npm.cmd run client:run`
           （Godot 客户端窗口）两条命令。
    匹配抓稳定关键词组合（数字 + 语义词 + R 标签锚点），非整句精确匹配，避免脆弱。
    """
    assert _CAPTURE_PLAN_PATH.is_file(), (
        "capture plan 文档缺失：%s" % _CAPTURE_PLAN_PATH
    )

    lines = _capture_plan_lines()
    text = "\n".join(lines)

    # R1.2：Demo_Recording 总时长 20–60s 判据（数字 20 与 60 同行 + duration 语义 + R 锚）。
    assert _has_line_with(lines, "duration", "20", "60", "r1.2"), (
        "capture plan 缺少 duration 20–60s 判据（R1.2）"
    )

    # R1.3：目标 subject 连续可见 ≥5s 判据。
    assert _has_line_with(lines, "subject", "continuously visible", "5", "r1.3"), (
        "capture plan 缺少 subject 连续可见 ≥5s 判据（R1.3）"
    )

    # R1.4：C2/C3/C4 caveat caption 连续可见 ≥3s 判据。
    assert _has_line_with(lines, "caption", "continuously visible", "3", "r1.4"), (
        "capture plan 缺少 caption 连续可见 ≥3s 判据（R1.4）"
    )

    # R1.1：后端运行时 + Godot 客户端启动命令段落（先验证标注 R1.1 的命令小节存在）。
    assert _has_line_with(lines, "backend", "godot", "launch commands", "r1.1"), (
        "capture plan 缺少标注 R1.1 的后端 + Godot 启动命令小节"
    )
    # R1.1：后端运行时启动命令。
    assert "npm.cmd run start" in text, (
        "capture plan 缺少后端运行时启动命令 `npm.cmd run start`（R1.1）"
    )
    # R1.1：Godot 客户端窗口启动命令。
    assert "npm.cmd run client:run" in text, (
        "capture plan 缺少 Godot 客户端启动命令 `npm.cmd run client:run`（R1.1）"
    )
