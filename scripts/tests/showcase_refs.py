"""展示层 GDScript 逻辑的 Python 参考实现集中落点。

设计依据：`.kiro/specs/presentation-showcase/design.md` Testing Strategy。

GDScript 中难以脱离 Godot 引擎的纯逻辑（trace 裁剪/排序、Prev/Next clamp、
phase2 摘要非空）以等价 Python 参考实现双写，由 Property-Based Testing
（Hypothesis）对参考实现验证，GDScript 侧用 example 测试对齐。

承载（随任务逐步填充）：

- ``clip_and_sort_trace(events, category, limit=50)``  —— Property 1（R4.4）：
  对 recentTraceEvents 按类别过滤、裁剪至多 ``limit`` 条、reverse 为 newest→oldest。
  对齐 ``clients/godot/scripts/world/town_map.gd`` 的 ``_clip_and_sort_trace_entries``。
- ``apply_prev_next(total, ops)``                       —— Property 2（R4.5/R4.6）：
  对 Prev/Next 操作序列计算最终索引并 clamp 到 ``[0, max(0, total-1)]``，
  同帧 Prev+Next 同时触发时 Next 优先。对齐 ``observer_panel.gd`` 的
  ``_apply_trace_navigation``。（任务 8.1）
- ``summarize_section(section, payload)``               —— Property 8（R4.2）：
  对非空 phase2 section payload 返回非空摘要，且不等于空态占位文案。（任务 8.6）
"""

from __future__ import annotations

import copy
from typing import Any

# Observer Dock trace 裁剪上限，对齐 town_map.gd 常量 TRACE_RECENT_LIMIT。
TRACE_RECENT_LIMIT = 50

# trace 过滤类别合法取值，对齐 GDScript 的 5 个过滤器。
TRACE_CATEGORIES = ("all", "decision", "tool", "interrupt", "memory")


def _event_type_of(entry: dict) -> str:
    """提取 trace entry 的 eventType。

    对齐 GDScript：``str(entry.get("eventType", entry.get("type", "trace")))``
    —— 先取 ``eventType``，缺失时回退 ``type``，再缺失时回退字面量 ``"trace"``。
    """
    return str(entry.get("eventType", entry.get("type", "trace")))


def _trace_filter_matches(event_type: str, category: str) -> bool:
    """判断 eventType 是否匹配所选过滤类别。

    匹配规则与 town_map.gd 的 ``_phase2_trace_filter_matches`` 完全一致：
    ``all`` 及任何未知类别匹配全部；其余类别按 eventType 精确匹配。
    """
    if category == "decision":
        return event_type == "motivation.decision_made"
    if category == "tool":
        return event_type in ("tool.execution_completed", "tool.execution_failed")
    if category == "interrupt":
        return event_type == "tool.execution_interrupted"
    if category == "memory":
        return event_type == "memory.result_observed"
    # "all" 及任何未知 category → 全部匹配（对齐 GDScript match 的 `_` 兜底分支）。
    return True


def clip_and_sort_trace(
    events: list[Any], category: str, limit: int = TRACE_RECENT_LIMIT
) -> list[dict]:
    """对 recentTraceEvents 过滤 + 裁剪 + 排序的纯逻辑参考实现。

    等价于 ``town_map.gd`` 的 ``_clip_and_sort_trace_entries``：

    1. 跳过非 dict 项（对齐 GDScript ``item is Dictionary`` 守卫）。
    2. 按 ``category`` 过滤（all/decision/tool/interrupt/memory）。
    3. 保留最近 ``limit`` 条（``start_index = max(0, n - limit)`` 后取尾段）。
    4. ``reverse`` 为 newest→oldest。

    入参为原始 events（oldest→newest，与后端 recentTraceEvents 顺序一致）。
    返回深拷贝后的 entry 列表，避免调用方/测试改动输入（对齐 GDScript
    ``entry.duplicate(true)``）。空列表或无匹配时返回空列表。

    Args:
        events: recentTraceEvents 原始列表（元素期望为 dict，非 dict 会被跳过）。
        category: 过滤类别，取值 all/decision/tool/interrupt/memory；未知值等同 all。
        limit: 裁剪上限，默认 ``TRACE_RECENT_LIMIT``（50）。

    Returns:
        过滤、裁剪、reverse 为 newest→oldest 后的 entry 深拷贝列表。
    """
    filtered: list[dict] = []
    for item in events:
        if not isinstance(item, dict):
            continue
        if _trace_filter_matches(_event_type_of(item), category):
            filtered.append(item)
    start_index = max(0, len(filtered) - limit)
    clipped = filtered[start_index:]
    clipped.reverse()
    return [copy.deepcopy(entry) for entry in clipped]


# Prev/Next 导航合法 token，对齐 observer_panel.gd 的两个方向。
_PREV_NEXT_TOKENS = ("prev", "next")


def _normalize_nav_token(token: Any) -> str:
    """把单个导航 token 归一化为 ``"prev"`` / ``"next"``。

    大小写不敏感（对齐测试生成器的宽松取值）；非法 token 抛 ``ValueError``，
    便于及早发现 PBT 生成器越界，而非静默吞掉。
    """
    text = str(token).strip().lower()
    if text not in _PREV_NEXT_TOKENS:
        raise ValueError(
            "invalid prev/next op token: %r (expected one of %r)"
            % (token, _PREV_NEXT_TOKENS)
        )
    return text


def apply_prev_next(total: int, ops: list[Any]) -> int:
    """Prev/Next 导航最终选中索引的纯逻辑参考实现。

    等价于 ``observer_panel.gd`` 的 ``_apply_trace_navigation``：

    1. 索引始终 **clamp** 到 ``[0, max(0, total - 1)]``，**不 wrap**——
       Prev 在 index=0 时保持 0，Next 在 index=total-1 时保持 total-1。
    2. ``total <= 0`` 时索引恒为 0（对应 position indicator 显示 ``0/0``）。
    3. 起始索引为 0，对齐 GDScript ``_current_trace_detail_index`` 初值。

    **ops 序列语义（与 GDScript 帧模型对齐）**：``ops`` 中每个元素表示「一个输入帧」
    内触发的导航。元素可以是：

    - 单个字符串 ``"prev"`` / ``"next"``：该帧只触发一个方向（最常见情形，
      每次按键各占一帧）。
    - 一个字符串集合 / 列表 / 元组（如 ``("prev", "next")``）：该帧内**同时**触发了
      多个方向。此时遵循 GDScript 的帧守卫与 **Next 优先**（R4.6）：
        * 帧内只要含 ``"next"`` → 从「该帧前的基线索引」应用一次 Next（``baseline + 1`` 后 clamp），
          覆盖同帧 Prev 的结果；
        * 帧内只含 ``"prev"`` → 应用一次 Prev（``baseline - 1`` 后 clamp）；
        * 空帧 → 索引不变。

    这与 ``_apply_trace_navigation`` 的实现一致：同一 ``Engine.get_process_frames()``
    内，首个导航前记录 ``_trace_nav_baseline_index``；Next 始终从基线 +1 并置
    ``_trace_nav_next_applied``；同帧 Next 应用后忽略后续 Prev。因此无论同帧内
    Prev / Next 到达顺序如何，最终结果都等于「从基线应用一次 Next」。

    **position indicator 对齐**：调用方可据返回索引 ``index`` 推导指示文案——
    ``total > 0`` 时显示 ``f"{index + 1}/{total}"``（current = index + 1）；
    ``total <= 0`` 时显示 ``"0/0"``。对齐 ``_update_trace_index_label``。

    Args:
        total: 当前过滤下可用 trace detail 总数（``>= 0``）。
        ops: 帧序列；每个元素是单个 ``"prev"``/``"next"`` 或同帧导航集合。

    Returns:
        应用全部 ops 后的最终选中索引，恒落在 ``[0, max(0, total - 1)]``。

    Raises:
        ValueError: 当某个导航 token 不是 ``"prev"`` / ``"next"`` 时。
    """
    max_index = max(0, total - 1)
    index = 0
    for frame_op in ops:
        # 单字符串 → 单方向帧；可迭代集合 → 同帧多方向。
        if isinstance(frame_op, str):
            frame_tokens = (frame_op,)
        else:
            frame_tokens = tuple(frame_op)
        baseline = index
        has_next = False
        has_prev = False
        for token in frame_tokens:
            direction = _normalize_nav_token(token)
            if direction == "next":
                has_next = True
            else:
                has_prev = True
        # R4.6：同帧 Next 优先，覆盖同帧 Prev。
        if has_next:
            index = min(max_index, baseline + 1)
        elif has_prev:
            index = max(0, baseline - 1)
        # 空帧不改变索引。
        # 收尾再 clamp 一次，保证不变量（防御 total 变化等情形）。
        index = max(0, min(index, max_index))
    return index


# phase2 Inspector 四个可摘要 section，对齐 town_map.gd 的 _summarize_phase2_* 系列。
PHASE2_SUMMARY_SECTIONS = (
    "motivation",
    "subjectiveMemory",
    "relationshipEdges",
    "heuristics",
)

# 各 section 在「items 为空」时返回的空态占位文案，逐字对齐 town_map.gd 的
# 四个 _summarize_phase2_* 函数在 `items.is_empty()` 分支的 return 文本。
# Property 8（R4.2）针对的"空态占位文案"即此处文本：非空 payload 的摘要
# SHALL NOT 等于对应 section 的这一条。
SECTION_EMPTY_SUMMARY = {
    "motivation": "暂无 motivation：后端没有返回该 NPC 的决策记录，等待下一次世界 tick。",
    "subjectiveMemory": "暂无 subjectiveMemory：该 NPC 尚未写入主观记忆。",
    "relationshipEdges": "暂无 relationshipEdges：该 NPC 暂无可解释关系边。",
    "heuristics": "暂无 heuristics：该 NPC 暂无启发式学习记录。",
}


def _phase2_items(payload: Any) -> list:
    """从 section payload 提取条目列表，等价 town_map.gd 的 ``_phase2_items``。

    对齐规则（逐分支）：

    - payload 是 ``list`` → 直接作为条目列表返回；
    - payload 是 ``dict`` → 取其 ``items`` 字段，且仅当该字段是 ``list`` 时返回，
      否则视为空（对齐 GDScript ``items is Array`` 守卫）；
    - 其它一切类型（含无 ``items`` 字段的 dict、``None``、标量）→ 返回空列表。

    **关键语义**：无 ``items`` 字段的 dict（如 ``{"topNeed": "rest"}``）按 GDScript
    判为**空态**——dict 形态的非空 payload 必须形如 ``{"items": [ ... ]}``。
    """
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        items = payload.get("items", [])
        if isinstance(items, list):
            return items
    return []


def _safe_float(value: Any) -> float:
    """把任意值安全转 float，对齐 GDScript ``float(...)`` 对非数字返回 ``0.0`` 的宽容行为。

    GDScript 的 ``float("abc")`` / ``float(null)`` 取 ``0.0``；Python ``float()`` 会抛
    异常，故此处捕获 ``TypeError`` / ``ValueError`` 回退 ``0.0`` 以保持等价。
    """
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _truncate_text(value: str, max_chars: int) -> str:
    """等价 town_map.gd 的 ``_truncate_text``：超 ``max_chars`` 截断并补省略号。

    ``len(value) <= max_chars`` 原样返回；否则取前 ``max(0, max_chars - 1)`` 个字符再
    追加 ``…``（与 GDScript ``value.substr(0, max(0, max_chars - 1))`` 对齐，按
    Unicode code point 计数，BMP 内中文与 GDScript ``String.length()`` 一致）。
    """
    if len(value) <= max_chars:
        return value
    return "%s…" % value[: max(0, max_chars - 1)]


def _summarize_motivation(payload: Any) -> str:
    """对齐 town_map.gd 的 ``_summarize_phase2_motivation``。"""
    items = _phase2_items(payload)
    if not items:
        return SECTION_EMPTY_SUMMARY["motivation"]
    focus = items[0]
    if not isinstance(focus, dict):
        return "motivation 数据不可读"
    primary_need = focus.get("primaryNeed", {})
    if isinstance(primary_need, dict):
        need_id = str(primary_need.get("needId", "unknown"))
        urgency = _safe_float(primary_need.get("urgency", 0.0))
    else:
        need_id = "unknown"
        urgency = 0.0
    decision = focus.get("decision", {})
    if isinstance(decision, dict):
        tool_id = str(decision.get("selectedToolId", decision.get("toolId", "")))
    else:
        tool_id = ""
    if tool_id == "":
        if isinstance(decision, dict):
            tool_id = str(decision.get("reason", "pending"))
        else:
            tool_id = "pending"
    return "need=%s(%.2f) / decision=%s" % (need_id, urgency, tool_id)


def _summarize_subjective_memory(payload: Any) -> str:
    """对齐 town_map.gd 的 ``_summarize_phase2_subjective_memory``。"""
    items = _phase2_items(payload)
    if not items:
        return SECTION_EMPTY_SUMMARY["subjectiveMemory"]
    latest = items[-1]
    if not isinstance(latest, dict):
        return "subjective memory 数据不可读"
    text = str(latest.get("text", ""))
    valence = _safe_float(latest.get("emotionalValence", 0.0))
    return "%d 条，最新 valence=%.2f：%s" % (len(items), valence, _truncate_text(text, 44))


def _summarize_relationship_edges(payload: Any) -> str:
    """对齐 town_map.gd 的 ``_summarize_phase2_relationship_edges``。"""
    items = _phase2_items(payload)
    if not items:
        return SECTION_EMPTY_SUMMARY["relationshipEdges"]
    strongest: dict = {}
    strongest_strength = -1.0
    for item in items:
        if not isinstance(item, dict):
            continue
        strength = abs(_safe_float(item.get("strength", 0.0)))
        if strength > strongest_strength:
            strongest_strength = strength
            strongest = item
    if not strongest:
        return "%d 条，暂无可读 edge" % len(items)
    return "%d 条，最强 %s %.2f (%s→%s)" % (
        len(items),
        str(strongest.get("edgeType", "edge")),
        _safe_float(strongest.get("strength", 0.0)),
        str(strongest.get("sourceAgentId", "?")),
        str(strongest.get("targetAgentId", "?")),
    )


def _summarize_heuristics(payload: Any) -> str:
    """对齐 town_map.gd 的 ``_summarize_phase2_heuristics``。"""
    items = _phase2_items(payload)
    if not items:
        return SECTION_EMPTY_SUMMARY["heuristics"]
    top = items[0]
    if not isinstance(top, dict):
        return "heuristic 数据不可读"
    return "%d 条，top=%s (%.2f)" % (
        len(items),
        str(top.get("triggerPattern", top.get("heuristicId", "unknown"))),
        _safe_float(top.get("effectiveConfidence", top.get("confidence", 0.0))),
    )


_SECTION_SUMMARIZERS = {
    "motivation": _summarize_motivation,
    "subjectiveMemory": _summarize_subjective_memory,
    "relationshipEdges": _summarize_relationship_edges,
    "heuristics": _summarize_heuristics,
}


def summarize_section(section: str, payload: Any) -> str:
    """phase2 Inspector section 摘要的纯逻辑参考实现（Property 8 / R4.2）。

    等价于 ``clients/godot/scripts/world/town_map.gd`` 的 ``_summarize_phase2_*``
    系列（``_build_phase2_observer_summary`` 中按 section 分派），把该 section 的原始
    payload 摘要成一行人类可读文本。

    **空态 vs 非空（两类情况须清晰区分）**：

    - **空 payload**——空 ``list``、空 ``dict``、无 ``items`` 字段的 dict、``{"items": []}``、
      ``None`` 或标量——经 :func:`_phase2_items` 提取后条目为空，返回该 section 的
      **空态占位文案**（见 :data:`SECTION_EMPTY_SUMMARY`）。这是正常返回，**不**违反
      Property 8。
    - **非空 payload**——``list`` 非空或 ``{"items": [ ... ]}`` 的 items 非空——返回
      非空摘要文本，且该文本 SHALL NOT 等于该 section 的空态占位文案。即使首/末条目
      不是 dict（如 ``[42]``），也返回 ``"... 数据不可读"`` / ``"N 条，暂无可读 edge"``
      这类非空且 ≠ 空态占位的文本，仍满足 Property 8。

    **对齐方式**：

    - 条目提取走 :func:`_phase2_items`（list 直用 / dict 取 ``items`` 列表字段 / 否则空），
      与 GDScript ``_phase2_items`` 完全一致；
    - float 字段用 :func:`_safe_float` 容错（对齐 GDScript ``float(...)`` 对非数字取 ``0.0``）；
    - subjectiveMemory 文本用 :func:`_truncate_text` 截断（max_chars=44，对齐 GDScript）；
    - 摘要格式串逐字对齐四个 ``_summarize_phase2_*`` 的 ``return`` 文本。

    Args:
        section: section 名，取值 ``motivation`` / ``subjectiveMemory`` /
            ``relationshipEdges`` / ``heuristics``。
        payload: 该 section 的原始 payload（list、含 ``items`` 的 dict，或空态形态）。

    Returns:
        该 section 的一行摘要文本；空态时为 :data:`SECTION_EMPTY_SUMMARY` 中对应文案。

    Raises:
        ValueError: 当 ``section`` 不属于四个合法 section 名时（便于及早发现 PBT
            生成器越界，而非静默返回错误摘要）。
    """
    summarizer = _SECTION_SUMMARIZERS.get(section)
    if summarizer is None:
        raise ValueError(
            "invalid phase2 section: %r (expected one of %r)"
            % (section, PHASE2_SUMMARY_SECTIONS)
        )
    return summarizer(payload)
