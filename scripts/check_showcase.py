"""Showcase 层三合一校验脚本（`P_demo.exit` 展示线）。

设计依据：`.kiro/specs/presentation-showcase/design.md`
  - C2.3 Showcase_Manifest 结构校验
  - Data Models / 验证态枚举
  - Error Handling / Showcase_Manifest 状态错误

报告结构沿用 `scripts/check_research_evidence.py` 的 `{ok, check, errors, warnings, ...}`
JSON 模式与防御性解析风格。

本模块按任务拆分增量落地，当前已实现：

- Showcase_Manifest（`docs/showcase_manifest.md`）的 `## Exit Criteria Status` 与
  `## Deliverables` 区块**防御性解析**为结构化记录（任务 2.2）。
- `validate_manifest_structure(records)` 结构校验（任务 2.2）。
- `compute_readiness(...)` readiness 自洽（R11.4/R11.5，Property 6）、
  `validate_manual_gate(...)` manual gate 不变量（R11.3，Property 7）、
  `validate_readiness_consistency(...)` readiness 与 exit status 自洽校验（任务 2.4）。
- Figure/Table 覆盖率子检查（R6.1–R6.5，Property 3，任务 3.1）：
  `parse_claim_matrix_targets(...)` / `tokenize_target_cell(...)` 解析 claim matrix
  「Figure / table target」列并归一为离散 target；`compute_coverage(...)` 纯函数
  覆盖率计算；`scan_rendered_targets(...)` 扫描 `paper/generated/` 判定已渲染；
  `evaluate_figure_table_coverage(...)` 端到端（含 R6.5 promoted manifest 缺失防御）。
- 口径一致性子检查（R7.4 / R8.4 / R10.1–R10.4，Property 4，任务 4.1）：
  `scan_consistency(text, source_name)` 纯函数逐行扫描 showcase material 文本，
  判定每个提及 C2/C3/C4 的语句行是否带 promoted-with-caveat 措辞、是否使用了高于
  owner-confirmed 级别的禁用短语（overclaim）、是否声明状态却缺 caveat；
  `scan_consistency_sources(...)` / `scan_consistency_files(...)` 对多源/默认
  showcase material 集合聚合扫描。

- CLI 主入口 `main()`（任务 5.1）：聚合 manifest 结构 + readiness 自洽 +
  manual gate / coverage / consistency 三子检查，输出 `{ok, check, errors,
  warnings, ...}` JSON 报告；缺失文件记 `errors[]`；任一子检查 errors 非空 →
  退出码 1，仅 warnings → 退出码 0；并把 coverage pending / consistency 结论 /
  readiness 结论幂等回填进 `docs/showcase_manifest.md` 的 `## Figure/Table
  Coverage` / `## Consistency` / `## Readiness` 区块（只动这三块）。

后续任务接续：

- npm `showcase:check` 接线        —— 任务 5.2
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST_PATH = ROOT / "docs" / "showcase_manifest.md"

# Exit criteria status 枚举（design Data Models / showcase_manifest 字段约定）。
EXIT_STATUS_VALUES = {"pending", "done", "not-accepted"}

# 验证态枚举（R11.2，5 值，复用 AGENTS.md §6 口径）。
VERIFICATION_STATES = {
    "code integrated",
    "command checked",
    "artifact backed",
    "manual verified",
    "manual unverified",
}

# 5 条 `P_demo.exit` exit criteria 的稳定 id（必须齐全）。
REQUIRED_EXIT_IDS = (
    "demo_recording",
    "blog_main",
    "readme_entry",
    "shareable_assets",
    "figure_coverage",
)

# Readiness 结论文案（R11.4 / R11.5，design C1 `## Readiness` 单行结论）。
READINESS_READY = "ready for owner review"
READINESS_NOT_READY = "not ready for owner review"

# 「依赖人工」判定关键词（design Property 7「命中人工依赖标记」）。
#
# 判定规则（确定性、可测）：扫描 deliverable 的 `requirement` + `notes` 文本，
# 大小写不敏感地匹配下列任一关键词即视为「依赖真实 LLM / 人工 reviewer /
# 真实 Godot 窗口」的人工依赖项。
#
# 关键词刻意选用**强信号短语**（如完整的「真实 godot 窗口」、动作性的「人工
# 录制 / 人工捕获」），避免命中半自动 deliverable 中「指向另一个 manual gate
# 项」的旁注/交叉引用。反例：`backend_unreachable_indicator` 是半自动代码交付
# 项（design 分类表「代码可交付，表现人工复验」），其 notes 含「真实窗口表现
# 另需人工复验（见 godot_window_recheck）」是把真实窗口复验**拆给**独立的
# `godot_window_recheck`（manual_gate=yes）承载，自身代码部分并不依赖人工。
# 故刻意不收录过宽的「真实窗口」（无 godot 限定）与「人工复验」（常见于旁注）。
MANUAL_DEPENDENCY_KEYWORDS = (
    "真实 llm",
    "真实llm",
    "real llm",
    "人工 reviewer",
    "人工reviewer",
    "human reviewer",
    "人工录制",
    "人工捕获",
    "真实 godot 窗口",
    "真实 godot窗口",
    "真实godot 窗口",
    "真实godot窗口",
    "real godot window",
    "玩家手感",
)

# 已知人工 deliverable id 集合（design C4 / 分类表 Manual_Verification_Gate 项）。
# 作为关键词判定的兜底：即便文案改写未命中关键词，这些 id 仍判定为依赖人工。
KNOWN_MANUAL_DELIVERABLE_IDS = (
    "final_demo_video",
    "godot_window_recheck",
    "shareable_gif_screenshots",
)

# 离线门禁不得为人工依赖项标记的验证态（R11.3：不得由离线门禁标记为
# satisfied / manual verified）。`manual verified` 表示人工已验收，离线门禁
# 无权代为标记；其余四态中只有 `manual unverified` 是人工 gate 的合法待办态，
# 其它三态（code/command/artifact）意味着被离线门禁当作「已满足」。
OFFLINE_SATISFIED_STATES = {
    "code integrated",
    "command checked",
    "artifact backed",
    "manual verified",
}

EXIT_SECTION_HEADING = "## Exit Criteria Status"
DELIVERABLES_SECTION_HEADING = "## Deliverables"

# 表格分隔行（`| --- | :---: |` 等）单元格形态。
_SEPARATOR_CELL = re.compile(r"^:?-+:?$")

# --------------------------------------------------------------------------- #
# Figure/Table 覆盖率（R6，design C2.2 / Property 3）常量
# --------------------------------------------------------------------------- #

# claim matrix 默认路径与「Figure / table target」列表头（design C2.2 解析目标）。
DEFAULT_CLAIM_MATRIX_PATH = ROOT / "paper" / "claim_evidence_matrix.md"
CLAIM_MATRIX_TARGET_COLUMN = "Figure / table target"

# `paper/generated/` 渲染产物根目录与 figures 子目录（design C2.2「已渲染」判定）。
GENERATED_DIR = ROOT / "paper" / "generated"
GENERATED_FIGURES_DIR = GENERATED_DIR / "figures"

# claim matrix 引用的 promoted manifest（R6.3 数据源认知 / R6.5 缺失防御）。
DEFAULT_PROMOTED_MANIFEST_PATH = (
    ROOT / ".run" / "eval-promoted" / "run_2026-05-29T13-57-50Z" / "manifest.json"
)

# 覆盖率门槛（R6.2：≥ 70%）。
COVERAGE_THRESHOLD = 0.70

# Figure N ↔ `paper/generated/figures/` 文件名词干映射（design C2.2 内联映射表）。
#
# 探查实证（`paper/figures.md` + `paper/generated/figures/` 实际文件）：
#   Figure 1 → system_overview.{svg,png,pdf}              （已渲染）
#   Figure 2 → motivational_delegation_loop.{svg,png,pdf} （已渲染）
#   Figure 3 → trace_evidence_chain_figure3.{svg,png,pdf} （已渲染）
#   Figure 4 → relationship_evidence_figure4.{svg,png,pdf} （已渲染）
# 映射词干以真实文件名为准（与设计文案一致），供 coverage 子检查判定
# `paper/generated/figures/` 下是否存在非空资产。
FIGURE_FILENAME_STEMS: dict[int, str | None] = {
    1: "system_overview",
    2: "motivational_delegation_loop",
    3: "trace_evidence_chain_figure3",
    4: "relationship_evidence_figure4",
}

# Figure 渲染资产可接受的扩展名（svg/png/pdf 任一即视为已渲染，design C2.2）。
FIGURE_ASSET_SUFFIXES = (".svg", ".png", ".pdf")

# `paper/generated/` 下承载 Table 的生成文件（design C2.2：eval_tables.tex /
# eval_summary_tables.md / ablation_table.csv）。某 Table N 视为「已渲染」当且仅当
# 至少一个生成文件存在、非空，且其文本声明了该表（按编号匹配，见
# `_table_rendered_in_generated`）。
TABLE_SOURCE_FILENAMES = (
    "eval_tables.tex",
    "eval_summary_tables.md",
    "ablation_table.csv",
)

# 探查实证：`paper/generated/eval_tables.tex` 实际含 3 个 `\label{tab:...}` 发布表，
# 与 `paper/figures.md` 声明的「generated ... included by experiments」状态一致：
#   tab:process-ablation → Table 2（Process Fidelity ablation summary）
#   tab:stability-24h    → Table 4（24h stability）
#   tab:domain-adapter   → Table 5（cross-domain adapter）
# 这是文件内容驱动的确定性映射（直接读真实渲染产物的 label），避免解析 figures.md
# 散文。Table 1（仅 drafted in paper/latex）、Table 3（baseline pending）、Table 6
# （related-work prose only）在 `paper/generated/` 下无承载发布表，故判 pending。
TABLE_LABEL_TO_NUMBER: dict[str, int] = {
    "tab:process-ablation": 2,
    "tab:stability-24h": 4,
    "tab:domain-adapter": 5,
}

# `ablation_table.csv` 直接承载 Table 2 的 ablation 数据（非空即视为 Table 2 已渲染）。
ABLATION_CSV_TABLE_NUMBER = 2

# `\label{tab:...}` 抽取（eval_tables.tex 表标签）。
_LATEX_TABLE_LABEL = re.compile(r"\\label\{(tab:[^}]+)\}")

# Target token 形态：`Figure N` / `Table N`（大小写不敏感，单复数皆可）。
_FIGURE_TABLE_TOKEN = re.compile(r"(figure|table)s?\s+(\d+)", re.IGNORECASE)

# 把 `Figures 1/2`、`Tables 2/4/5` 这类「复数 + 斜杠列表」展开为多个编号。
_PLURAL_LIST_TOKEN = re.compile(
    r"(figure|table)s?\s+((?:\d+\s*/\s*)+\d+)", re.IGNORECASE
)

# --------------------------------------------------------------------------- #
# 口径一致性（R10 / R7.4 / R8.4，design C2.1 / Property 4）常量
# --------------------------------------------------------------------------- #

# 受 R10 一致性约束的 claim id（design C2.1：扫描 C2/C3/C4）。
CONSISTENCY_CLAIM_IDS = ("C2", "C3", "C4")

# 一致性扫描的默认 showcase material（design C2.1 输入集合 / R10.1 限定范围：
# Demo_Recording / Shareable_Asset_Set / README_Portfolio_Entry / Blog_Main /
# Trace_Walkthrough 承载的文本）。caption 文本内嵌于 capture plan / manifest。
CONSISTENCY_SOURCE_FILENAMES = (
    "README.md",
    "paper/blog_main.md",
    "paper/trace_walkthroughs/figure3_trace_walkthrough_pf_branna_seed01.md",
    "docs/demo_capture_plan.md",
    "docs/showcase_manifest.md",
)

# 行内出现的 claim id token（`C2` / `C3` / `C4`，词边界，允许反引号包裹如 `C2`）。
# 反引号不是 `\b` 词边界，故显式允许两侧反引号/常见标点。大小写敏感（claim id
# 是大写约定，避免误命中小写 `c2` 之类非 claim 文本）。
_CLAIM_ID_TOKEN = re.compile(r"(?<![A-Za-z0-9])C[234](?![A-Za-z0-9])")

# promoted-with-caveat 措辞匹配（design C2.1：`promoted with caveat` /
# `promoted-with-caveat`，大小写不敏感、连字符与空格等价）。`[-\s]+` 让连字符
# 与一个或多个空白互换，覆盖 `promoted   with  caveat` / `promoted-with-caveat`。
CAVEAT_WORDING_PATTERN = re.compile(r"promoted[-\s]+with[-\s]+caveat", re.IGNORECASE)

# 高于 owner-confirmed（promoted-with-caveat）级别的**禁用短语**（R10.2 / R10.3）。
# 内联为脚本常量便于主人调整。命中任一即视为 overclaim（前提：同一行声明了
# C2/C3/C4 的状态且未带 caveat 措辞——带 caveat 的行优先判 compliant，见
# `scan_consistency` 判定顺序，从而不误伤「不要用 proven/fully validated」这类
# 明确带 caveat 基线的元讨论行）。短语用「单词边界 + 连字符/空格等价」匹配。
FORBIDDEN_OVERCLAIM_PHRASES = (
    "proven",
    "fully validated",
    "fully established",
    "confirmed empirically",
    "empirically confirmed",
    "conclusively demonstrated",
    "definitively proven",
)

# 状态性词汇（design 任务说明：行内同时出现 claim id 与状态性词汇才算「声明
# claim 状态」，使判定确定可测、避免误伤纯引用如「see C2 below」）。这些词刻画
# 一条 claim 的 validation / support level。`validated` / `proven` 等同时也是
# overclaim 短语的一部分，此处用于「声明了状态」的判定，overclaim 判定另由
# `FORBIDDEN_OVERCLAIM_PHRASES` 负责。
CLAIM_STATUS_TERMS = (
    "promoted",
    "validated",
    "proven",
    "confirmed",
    "established",
    "verified",
    "demonstrated",
    "substantiated",
    "claim status",
    "support level",
    "validation level",
    "evidence level",
)

# 把状态短语编译为「单词边界 + 连字符/空格等价」的正则，供逐行匹配复用。
def _phrase_to_pattern(phrase: str) -> "re.Pattern[str]":
    """把禁用/状态短语编译为大小写不敏感、连字符与空格等价、带词边界的正则。"""

    tokens = re.split(r"[-\s]+", phrase.strip())
    escaped = r"[-\s]+".join(re.escape(tok) for tok in tokens if tok)
    return re.compile(rf"(?<![A-Za-z]){escaped}(?![A-Za-z])", re.IGNORECASE)


_FORBIDDEN_PATTERNS = tuple(
    (phrase, _phrase_to_pattern(phrase)) for phrase in FORBIDDEN_OVERCLAIM_PHRASES
)
_STATUS_TERM_PATTERNS = tuple(
    (term, _phrase_to_pattern(term)) for term in CLAIM_STATUS_TERMS
)


__all__ = [
    "ExitCriterion",
    "Deliverable",
    "ManifestRecords",
    "ReadinessResult",
    "FigureTableTarget",
    "CoverageResult",
    "parse_manifest",
    "parse_manifest_text",
    "validate_manifest_structure",
    "compute_readiness",
    "validate_manual_gate",
    "validate_readiness_consistency",
    "deliverable_depends_on_manual",
    "tokenize_target_cell",
    "parse_claim_matrix_targets",
    "parse_claim_matrix_targets_text",
    "scan_rendered_targets",
    "compute_coverage",
    "evaluate_figure_table_coverage",
    "ConsistencyViolation",
    "ConsistencyResult",
    "scan_consistency",
    "scan_consistency_sources",
    "scan_consistency_files",
    "EXIT_STATUS_VALUES",
    "VERIFICATION_STATES",
    "REQUIRED_EXIT_IDS",
    "READINESS_READY",
    "READINESS_NOT_READY",
    "MANUAL_DEPENDENCY_KEYWORDS",
    "KNOWN_MANUAL_DELIVERABLE_IDS",
    "CLAIM_MATRIX_TARGET_COLUMN",
    "COVERAGE_THRESHOLD",
    "FIGURE_FILENAME_STEMS",
    "TABLE_SOURCE_FILENAMES",
    "CONSISTENCY_CLAIM_IDS",
    "CAVEAT_WORDING_PATTERN",
    "FORBIDDEN_OVERCLAIM_PHRASES",
    "CLAIM_STATUS_TERMS",
    "CONSISTENCY_SOURCE_FILENAMES",
]


@dataclass
class ExitCriterion:
    """`## Exit Criteria Status` 表的一行。"""

    exit_id: str
    title: str
    status: str
    verification_state: str
    blocking_reason: str
    line_number: int


@dataclass
class Deliverable:
    """`## Deliverables` 表的一行。"""

    deliverable_id: str
    requirement: str
    verification_state: str
    manual_gate: str
    notes: str
    line_number: int


@dataclass
class ManifestRecords:
    """Showcase_Manifest 解析后的结构化记录。"""

    exit_criteria: list[ExitCriterion] = field(default_factory=list)
    deliverables: list[Deliverable] = field(default_factory=list)


@dataclass
class ReadinessResult:
    """`compute_readiness` 的结构化结论（design C1 `## Readiness` 区块）。

    - `ready`：当且仅当 5 条 exit criteria 全部非 pending（R11.4）。
    - `readiness`：人类可读结论文案（`READINESS_READY` / `READINESS_NOT_READY`）。
    - `pending_exit_ids`：仍为 pending 的 exit criterion id 列表（R11.5）。
    - `blocking_manual_gates`：阻塞 pending exit criteria 的 Manual_Verification_Gate
      deliverable id 列表（R11.5）。
    """

    ready: bool
    readiness: str
    pending_exit_ids: list[str] = field(default_factory=list)
    blocking_manual_gates: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class FigureTableTarget:
    """claim matrix「Figure / table target」列归一后的一个离散 target。

    - `kind`：`"figure"` / `"table"` / `"non-renderable"`。
    - `number`：Figure N / Table N 的编号（non-renderable 为 None）。
    - `key`：稳定标识（renderable 用 `"Figure 4"` / `"Table 2"`；non-renderable
      用原始短语，如 `"Limitations box"`）。
    - `renderable`：是否纳入覆盖率分母（仅 figure / table 为 True）。
    - `raw`：来源原文（便于诊断 / blocking_reason）。
    """

    kind: str
    number: int | None
    key: str
    renderable: bool
    raw: str


@dataclass
class CoverageResult:
    """`compute_coverage` 的结构化结论（design C2.2 输出字段 / Property 3）。

    字段对应 design「输出 `coverage.percent` / `coverage.rendered` /
    `coverage.total` / `coverage.pending[]` / `coverage.pass`」：

    - `percent`：`|rendered ∩ renderable| / |renderable|`，落在 `[0,1]`。
    - `rendered`：已渲染的 renderable target 数（`|rendered ∩ renderable|`）。
    - `total`：renderable target 总数（分母，排除 non-renderable）。
    - `pending`：未渲染的 renderable target，每项 `{target, blocking_reason}`（R6.4）。
    - `passed`：当且仅当 `percent >= COVERAGE_THRESHOLD`（R6.2）。
    """

    percent: float
    rendered: int
    total: int
    pending: list[dict[str, str]] = field(default_factory=list)
    passed: bool = False


# --------------------------------------------------------------------------- #
# 解析（防御性、逐行容错，不抛未捕获异常）
# --------------------------------------------------------------------------- #


def parse_manifest(path: Path | str | None = None) -> ManifestRecords:
    """读取并解析 Showcase_Manifest（默认 `docs/showcase_manifest.md`）。

    文件不可读时返回空记录而非抛异常；文件缺失的报错由 CLI 主入口（任务 5.1）
    另行检测，本函数只负责防御性解析。
    """

    manifest_path = Path(path) if path is not None else DEFAULT_MANIFEST_PATH
    try:
        text = manifest_path.read_text(encoding="utf-8")
    except OSError:
        return ManifestRecords()
    return parse_manifest_text(text)


def parse_manifest_text(text: str) -> ManifestRecords:
    """把 Showcase_Manifest 文本解析为结构化记录（纯函数，便于测试）。"""

    lines = text.splitlines()
    records = ManifestRecords()
    for cells, line_number in _extract_section_rows(lines, EXIT_SECTION_HEADING):
        records.exit_criteria.append(_build_exit_criterion(cells, line_number))
    for cells, line_number in _extract_section_rows(lines, DELIVERABLES_SECTION_HEADING):
        records.deliverables.append(_build_deliverable(cells, line_number))
    return records


def _extract_section_rows(
    lines: list[str], heading: str
) -> list[tuple[list[str], int]]:
    """提取指定 `## ` 区块内某张 Markdown 表格的数据行（含 1-based 行号）。

    跳过表头行与分隔行；遇到下一个 `## ` 级标题即视为区块结束。
    """

    rows: list[tuple[list[str], int]] = []
    in_section = False
    seen_separator = False
    for idx, raw in enumerate(lines):
        stripped = raw.strip()
        if stripped.startswith("## "):
            if in_section:
                break  # 抵达下一个区块，结束。
            if stripped == heading:
                in_section = True
                seen_separator = False
            continue
        if not in_section:
            continue
        if not stripped.startswith("|"):
            continue
        if _is_separator_row(stripped):
            seen_separator = True
            continue
        if not seen_separator:
            continue  # 分隔行之前的是表头，跳过。
        rows.append((_split_row(stripped), idx + 1))
    return rows


def _is_separator_row(line: str) -> bool:
    cells = _split_row(line)
    return bool(cells) and all(_SEPARATOR_CELL.match(cell) for cell in cells)


def _split_row(line: str) -> list[str]:
    inner = line.strip()
    if inner.startswith("|"):
        inner = inner[1:]
    if inner.endswith("|"):
        inner = inner[:-1]
    return [cell.strip() for cell in inner.split("|")]


def _normalize_cells(cells: list[str], size: int) -> list[str]:
    """把单元格数归一到 size：不足补空，超出则把溢出合并回最后一列。

    防御性处理 notes/blocking_reason 中可能出现的 `|`，避免内容被截断。
    """

    if len(cells) < size:
        return cells + [""] * (size - len(cells))
    if len(cells) > size:
        head = cells[: size - 1]
        tail = " | ".join(cells[size - 1 :]).strip()
        return head + [tail]
    return list(cells)


def _build_exit_criterion(cells: list[str], line_number: int) -> ExitCriterion:
    exit_id, title, status, verification_state, blocking_reason = _normalize_cells(cells, 5)
    return ExitCriterion(
        exit_id=exit_id,
        title=title,
        status=status,
        verification_state=verification_state,
        blocking_reason=blocking_reason,
        line_number=line_number,
    )


def _build_deliverable(cells: list[str], line_number: int) -> Deliverable:
    deliverable_id, requirement, verification_state, manual_gate, notes = _normalize_cells(cells, 5)
    return Deliverable(
        deliverable_id=deliverable_id,
        requirement=requirement,
        verification_state=verification_state,
        manual_gate=manual_gate,
        notes=notes,
        line_number=line_number,
    )


# --------------------------------------------------------------------------- #
# 结构校验（R11.1 / R11.2 + not-accepted 必填 blocking_reason）
# --------------------------------------------------------------------------- #


def validate_manifest_structure(records: ManifestRecords) -> list[str]:
    """校验 Showcase_Manifest 结构，返回 `manifest.errors[]`（每项含定位信息）。

    校验内容（任务 2.2，对应 design C2.3）：

    - 5 条 exit criteria 行齐全（`REQUIRED_EXIT_IDS`），无重复 / 无未知 exit_id；
    - 每条 exit criterion 的 `status` 取值合法（`EXIT_STATUS_VALUES`）；
    - 每条 exit criterion 的 `verification_state` 取值合法（`VERIFICATION_STATES`）；
    - `not-accepted` 行必填 `blocking_reason`（R1.7 / design Error Handling）；
    - 每个 deliverable 的 `verification_state` 取值合法（R11.2），无重复 deliverable_id。

    readiness 自洽与 manual gate 不变量校验不在本函数范围（任务 2.4）。
    """

    errors: list[str] = []
    _validate_exit_criteria(records.exit_criteria, errors)
    _validate_deliverables(records.deliverables, errors)
    return errors


def _validate_exit_criteria(
    exit_criteria: list[ExitCriterion], errors: list[str]
) -> None:
    seen: dict[str, int] = {}
    for crit in exit_criteria:
        if not crit.exit_id:
            errors.append(f"exit criterion row at line {crit.line_number} has empty exit_id")
            continue
        if crit.exit_id in seen:
            errors.append(
                f"exit_id '{crit.exit_id}' duplicated at line {crit.line_number} "
                f"(first seen at line {seen[crit.exit_id]})"
            )
        else:
            seen[crit.exit_id] = crit.line_number

    for required_id in REQUIRED_EXIT_IDS:
        if required_id not in seen:
            errors.append(
                f"exit criterion '{required_id}' missing from '{EXIT_SECTION_HEADING}'"
            )

    for crit in exit_criteria:
        loc = f"exit_id '{crit.exit_id}' (line {crit.line_number})"
        if crit.exit_id and crit.exit_id not in REQUIRED_EXIT_IDS:
            errors.append(
                f"unexpected exit_id '{crit.exit_id}' at line {crit.line_number}, "
                f"expected one of {sorted(REQUIRED_EXIT_IDS)}"
            )
        if crit.status not in EXIT_STATUS_VALUES:
            errors.append(
                f"{loc} has invalid status '{crit.status}', "
                f"expected one of {sorted(EXIT_STATUS_VALUES)}"
            )
        if crit.verification_state not in VERIFICATION_STATES:
            errors.append(
                f"{loc} has invalid verification_state '{crit.verification_state}', "
                f"expected one of {sorted(VERIFICATION_STATES)}"
            )
        if crit.status == "not-accepted" and not crit.blocking_reason:
            errors.append(
                f"{loc} has status 'not-accepted' but blocking_reason is empty"
            )


def _validate_deliverables(
    deliverables: list[Deliverable], errors: list[str]
) -> None:
    seen: dict[str, int] = {}
    for deliv in deliverables:
        loc = f"deliverable_id '{deliv.deliverable_id}' (line {deliv.line_number})"
        if not deliv.deliverable_id:
            errors.append(f"deliverable row at line {deliv.line_number} has empty deliverable_id")
        elif deliv.deliverable_id in seen:
            errors.append(
                f"deliverable_id '{deliv.deliverable_id}' duplicated at line {deliv.line_number} "
                f"(first seen at line {seen[deliv.deliverable_id]})"
            )
        else:
            seen[deliv.deliverable_id] = deliv.line_number
        if deliv.verification_state not in VERIFICATION_STATES:
            errors.append(
                f"{loc} has invalid verification_state '{deliv.verification_state}', "
                f"expected one of {sorted(VERIFICATION_STATES)}"
            )


# --------------------------------------------------------------------------- #
# Readiness 自洽（R11.4 / R11.5，Property 6）与 manual gate 不变量（R11.3，Property 7）
#
# 本节为任务 2.4 增量，与任务 2.2 的 `validate_manifest_structure` 职责分离：
#   - 结构枚举 / 齐全性 / not-accepted 必填 blocking_reason  → 2.2
#   - readiness 自洽 / manual gate 不变量 / readiness 与状态一致  → 本节
# 所有函数写成纯函数，便于任务 2.5（Property 6 PBT）/ 2.6（Property 7 PBT）复用。
# --------------------------------------------------------------------------- #


def _coerce_exit_items(exit_criteria) -> list[tuple[str, str]]:
    """把多种输入形态归一为 `(exit_id, status)` 列表（防御性、纯函数）。

    支持的输入（便于 PBT 直接喂状态组合）：

    - `ManifestRecords` —— 取其 `exit_criteria`；
    - `ExitCriterion` 序列 —— 取 `(exit_id, status)`；
    - `str` 序列 —— 视为 status，id 用 1-based 占位（`#1`..）；
    - `(id, status)` 二元组序列。
    """

    if isinstance(exit_criteria, ManifestRecords):
        exit_criteria = exit_criteria.exit_criteria

    items: list[tuple[str, str]] = []
    for idx, item in enumerate(exit_criteria, start=1):
        if isinstance(item, ExitCriterion):
            items.append((item.exit_id or f"#{idx}", item.status))
        elif isinstance(item, str):
            items.append((f"#{idx}", item))
        elif isinstance(item, (tuple, list)) and len(item) == 2:
            items.append((str(item[0]), str(item[1])))
        else:  # 未知形态，防御性兜底（不抛异常）。
            items.append((f"#{idx}", str(item)))
    return items


def deliverable_depends_on_manual(deliverable: Deliverable) -> bool:
    """判定一个 deliverable 是否「依赖人工」（design Property 7「命中人工依赖标记」）。

    判定规则（确定性、可测，两条任一命中即为依赖人工）：

    1. **已知人工项兜底**：`deliverable_id` 命中 `KNOWN_MANUAL_DELIVERABLE_IDS`
       （`final_demo_video` / `godot_window_recheck` / `shareable_gif_screenshots`）。
    2. **关键词扫描**：把 `requirement` + `notes` 拼接后小写化，命中
       `MANUAL_DEPENDENCY_KEYWORDS` 中任一关键词（真实 LLM / 人工 reviewer /
       真实 Godot 窗口 / 真实窗口 / 人工录制 / 人工捕获 / 人工复验 / 玩家手感 等）。

    任一命中即返回 True；否则 False。
    """

    if deliverable.deliverable_id in KNOWN_MANUAL_DELIVERABLE_IDS:
        return True
    haystack = f"{deliverable.requirement} {deliverable.notes}".lower()
    return any(keyword in haystack for keyword in MANUAL_DEPENDENCY_KEYWORDS)


def compute_readiness(exit_criteria, deliverables=None) -> ReadinessResult:
    """计算展示线 readiness 结论（R11.4 / R11.5，Property 6）。

    规则：当且仅当 5 条 `P_demo.exit` exit criteria 的 status 全部非 `pending` 时
    报告 `ready for owner review`（R11.4）；否则报告 `not ready for owner review`
    并列出每个仍为 pending 的 exit criterion，以及阻塞展示线的
    Manual_Verification_Gate deliverable（R11.5）。

    参数：
      - `exit_criteria`：`ManifestRecords` / `ExitCriterion` 序列 /
        status 字符串序列 / `(id, status)` 序列（见 `_coerce_exit_items`）。
      - `deliverables`：可选 `Deliverable` 序列；提供时用于列出阻塞的
        Manual_Verification_Gate 项。传入 `ManifestRecords` 作为首参时，
        缺省自动取其 deliverables。

    返回 `ReadinessResult`。空 exit criteria 视为 **not ready**（避免对空集做
    「全部非 pending」的真空真判定误报 ready；齐全性由结构校验 2.2 负责）。
    """

    if isinstance(exit_criteria, ManifestRecords) and deliverables is None:
        deliverables = exit_criteria.deliverables

    items = _coerce_exit_items(exit_criteria)
    pending_exit_ids = [exit_id for exit_id, status in items if status == "pending"]
    ready = bool(items) and not pending_exit_ids

    blocking_manual_gates: list[str] = []
    if not ready and deliverables:
        for deliv in deliverables:
            is_manual = (
                deliverable_depends_on_manual(deliv)
                or deliv.manual_gate.strip().lower() == "yes"
            )
            if is_manual and deliv.verification_state != "manual verified":
                blocking_manual_gates.append(deliv.deliverable_id)

    return ReadinessResult(
        ready=ready,
        readiness=READINESS_READY if ready else READINESS_NOT_READY,
        pending_exit_ids=pending_exit_ids,
        blocking_manual_gates=blocking_manual_gates,
    )


def validate_manual_gate(deliverables: list[Deliverable]) -> list[str]:
    """校验 Manual_Verification_Gate 不变量（R11.3，Property 7）。

    对每个**依赖人工**（`deliverable_depends_on_manual` 命中）的 deliverable：

    1. 其 `manual_gate` SHALL 为 `yes`；「依赖人工但 manual_gate=no」→ 报错。
    2. 其验证态 SHALL NOT 被离线门禁标记为 satisfied / manual verified，
       即对人工 gate 项，只有 `manual unverified` 是合法的离线可记态；
       命中 `OFFLINE_SATISFIED_STATES`（code integrated / command checked /
       artifact backed / manual verified）→ 报错（离线门禁不得代为「满足」人工项）。

    同时，对**显式声明** `manual_gate = yes` 的 deliverable（无论关键词是否命中）
    也应用第 2 条状态约束，防止「声明为人工 gate 却被离线门禁标满足」。

    返回 `manual.errors[]`（每项含 deliverable_id 与行号定位）。
    """

    errors: list[str] = []
    for deliv in deliverables:
        loc = f"deliverable_id '{deliv.deliverable_id}' (line {deliv.line_number})"
        depends_manual = deliverable_depends_on_manual(deliv)
        declared_manual = deliv.manual_gate.strip().lower() == "yes"

        if depends_manual and not declared_manual:
            errors.append(
                f"{loc} depends on manual verification "
                f"(real LLM / human reviewer / real Godot window) "
                f"but manual_gate is '{deliv.manual_gate}', expected 'yes'"
            )

        if (depends_manual or declared_manual) and (
            deliv.verification_state in OFFLINE_SATISFIED_STATES
        ):
            errors.append(
                f"{loc} is a Manual_Verification_Gate item but its "
                f"verification_state '{deliv.verification_state}' marks it as "
                f"satisfied by an offline gate; expected 'manual unverified' "
                f"(offline gates must not satisfy manual-dependent deliverables)"
            )

    return errors


def validate_readiness_consistency(
    records: ManifestRecords, claimed_ready: bool | None
) -> list[str]:
    """校验 manifest 声明的 readiness 与 exit status 自洽（任务 2.4 第 4 点）。

    `claimed_ready` 为 manifest `## Readiness` 区块声明的结论（True = 报告
    `ready for owner review`，False = 报告 not ready，None = 未声明则跳过）。

    不自洽情形（均报错）：

    - 声明 ready 但仍有 pending exit criteria（**over-claim**，R11.4，对应
      design Error Handling「readiness 与 exit status 不自洽」）；
    - 声明 not ready 但 5 条 exit criteria 全部非 pending（**under-claim**，
      自洽性反向校验）。
    """

    errors: list[str] = []
    if claimed_ready is None:
        return errors

    result = compute_readiness(records.exit_criteria, records.deliverables)
    if claimed_ready and not result.ready:
        errors.append(
            "readiness claims 'ready for owner review' but exit criteria still "
            f"pending: {result.pending_exit_ids}"
        )
    elif not claimed_ready and result.ready:
        errors.append(
            "readiness claims 'not ready for owner review' but all exit criteria "
            "are non-pending; expected 'ready for owner review'"
        )
    return errors


# --------------------------------------------------------------------------- #
# Figure/Table 覆盖率子检查（R6.1–R6.5，design C2.2，Property 3）
#
# 本节为任务 3.1 增量，与上方 manifest/readiness 校验职责分离：
#   - 解析 claim matrix「Figure / table target」列 → 离散 target；
#   - 把 non-renderable 目标（Workflow / Limitations box / Regression guardrail
#     note 等非 Figure N / Table N）排除出分母；
#   - 扫描 `paper/generated/` 判定「已渲染」（Figure → figures/ 命名资产；
#     Table → 生成表格文件按编号承载）；
#   - `compute_coverage(...)` 纯函数计算覆盖率（便于任务 3.2 PBT）。
#
# 本任务聚焦「覆盖率判定」，不重造表格生成器（design 注：paper:tables 工具链已
# 覆盖 table 生成；R6.3 在此理解为「判定 table 已渲染时数据源取 promoted manifest」
# 的认知，promoted manifest 缺失/不可读时按 R6.5 走 pending 防御，不重渲染）。
# --------------------------------------------------------------------------- #


# 非 Figure N / Table N 的目标（design C2.2 示例：Workflow / Limitations box /
# Regression guardrail note）天然不命中 `Figure N` / `Table N` token 形态，
# 由 `tokenize_target_cell` 统一归为 `non-renderable`，无需单独白名单。


def tokenize_target_cell(cell: str) -> list[FigureTableTarget]:
    """把 claim matrix「Figure / table target」单元格拆为离散 target（纯函数）。

    处理三类形态（探查 `paper/claim_evidence_matrix.md` 实证）：

    - 单数：`Figure 1` / `Table 2` / `Figure 4` → renderable target；
    - 复数 + 斜杠列表：`Figures 1/2` / `Tables 2/4/5` → 展开为多个 renderable；
    - 非图表短语：`Limitations box` / `Workflow` /
      `Limitations / Regression guardrail note` → 单个 `non-renderable` target
      （排除出覆盖率分母，R6.2）。

    去重保序：同一单元格内重复编号只保留一个；renderable token 用
    `Figure N` / `Table N` 作 `key`，便于跨 claim 行聚合去重。
    """

    text = (cell or "").strip()
    if not text:
        return []

    targets: list[FigureTableTarget] = []
    seen_keys: set[str] = set()
    matched_any = False

    # 1) 先展开复数 + 斜杠列表（`Tables 2/4/5`、`Figures 1/2`）。
    consumed_spans: list[tuple[int, int]] = []
    for m in _PLURAL_LIST_TOKEN.finditer(text):
        matched_any = True
        consumed_spans.append(m.span())
        kind = m.group(1).lower()
        numbers = [int(n) for n in re.split(r"\s*/\s*", m.group(2)) if n.strip()]
        for number in numbers:
            key = f"{kind.capitalize()} {number}"
            if key in seen_keys:
                continue
            seen_keys.add(key)
            targets.append(
                FigureTableTarget(
                    kind=kind, number=number, key=key, renderable=True, raw=text
                )
            )

    # 2) 再匹配单数 token（`Figure 1` / `Table 2`），跳过已被复数列表消费的区间。
    for m in _FIGURE_TABLE_TOKEN.finditer(text):
        if any(start <= m.start() < end for start, end in consumed_spans):
            continue
        matched_any = True
        kind = m.group(1).lower()
        number = int(m.group(2))
        key = f"{kind.capitalize()} {number}"
        if key in seen_keys:
            continue
        seen_keys.add(key)
        targets.append(
            FigureTableTarget(
                kind=kind, number=number, key=key, renderable=True, raw=text
            )
        )

    # 3) 未命中任何 Figure/Table 编号 → 整格视为单个 non-renderable target。
    if not matched_any:
        targets.append(
            FigureTableTarget(
                kind="non-renderable",
                number=None,
                key=text,
                renderable=False,
                raw=text,
            )
        )

    return targets


def parse_claim_matrix_targets_text(text: str) -> list[FigureTableTarget]:
    """解析 claim matrix 文本的「Figure / table target」列，返回去重后的 target。

    防御性逐行解析（沿用 manifest 解析风格）：定位含 `CLAIM_MATRIX_TARGET_COLUMN`
    的表头行确定目标列索引，跳过分隔行，对每个数据行的该列调用
    `tokenize_target_cell`。跨行去重：renderable target 按 `key` 去重（多条 claim
    可共用同一 Figure/Table，如 Table 2 被 C2/C3 共同引用，只计一次）；
    non-renderable target 按 `key`（原始短语）去重。
    """

    lines = text.splitlines()
    target_col_index: int | None = None
    seen_separator = False

    collected: list[FigureTableTarget] = []
    seen_keys: set[str] = set()

    for raw in lines:
        stripped = raw.strip()
        if not stripped.startswith("|"):
            continue
        cells = _split_row(stripped)

        if target_col_index is None:
            # 仍在找表头：当前行若含目标列名，记录列索引。
            for idx, cell in enumerate(cells):
                if cell.strip() == CLAIM_MATRIX_TARGET_COLUMN:
                    target_col_index = idx
                    seen_separator = False
                    break
            continue

        if _is_separator_row(stripped):
            seen_separator = True
            continue
        if not seen_separator:
            continue  # 表头与分隔行之间无数据。

        if target_col_index >= len(cells):
            continue  # 防御：列错位，跳过该行而非抛异常。
        cell = cells[target_col_index]
        for target in tokenize_target_cell(cell):
            if target.key in seen_keys:
                continue
            seen_keys.add(target.key)
            collected.append(target)

    return collected


def parse_claim_matrix_targets(
    path: Path | str | None = None,
) -> list[FigureTableTarget]:
    """读取并解析 claim matrix（默认 `paper/claim_evidence_matrix.md`）。

    文件不可读时返回空列表而非抛异常（缺失报错由 CLI 主入口任务 5.1 另行检测）。
    """

    matrix_path = Path(path) if path is not None else DEFAULT_CLAIM_MATRIX_PATH
    try:
        text = matrix_path.read_text(encoding="utf-8")
    except OSError:
        return []
    return parse_claim_matrix_targets_text(text)


def _figure_rendered(number: int, figures_dir: Path) -> bool:
    """判定 Figure N 是否已渲染：figures/ 下存在对应词干的非空 svg/png/pdf 资产。"""

    stem = FIGURE_FILENAME_STEMS.get(number)
    if not stem:
        return False  # 无映射词干（如 Figure 4 待渲染）→ 未渲染。
    for suffix in FIGURE_ASSET_SUFFIXES:
        asset = figures_dir / f"{stem}{suffix}"
        try:
            if asset.is_file() and asset.stat().st_size > 0:
                return True
        except OSError:
            continue
    return False


def _rendered_table_numbers(generated_dir: Path) -> set[int]:
    """扫描 `paper/generated/` 下生成文件，返回「已渲染」的 Table 编号集合。

    判定（design C2.2，内容驱动、确定性）：
      - `eval_tables.tex`：抽取 `\\label{tab:...}`，按 `TABLE_LABEL_TO_NUMBER`
        映射为 Table 编号（仅当文件非空）。
      - `ablation_table.csv`：非空即承载 Table 2（`ABLATION_CSV_TABLE_NUMBER`）。
    `eval_summary_tables.md` 是 metric dump，不单独声明发布表编号，不参与编号判定
    （其覆盖的表数据已由上述两文件承载）。
    """

    rendered: set[int] = set()

    tex_path = generated_dir / "eval_tables.tex"
    try:
        if tex_path.is_file() and tex_path.stat().st_size > 0:
            tex_text = tex_path.read_text(encoding="utf-8")
            for label in _LATEX_TABLE_LABEL.findall(tex_text):
                number = TABLE_LABEL_TO_NUMBER.get(label.strip())
                if number is not None:
                    rendered.add(number)
    except OSError:
        pass

    csv_path = generated_dir / "ablation_table.csv"
    try:
        if csv_path.is_file() and csv_path.stat().st_size > 0:
            rendered.add(ABLATION_CSV_TABLE_NUMBER)
    except OSError:
        pass

    return rendered


def scan_rendered_targets(
    targets: list[FigureTableTarget],
    figures_dir: Path | str | None = None,
    generated_dir: Path | str | None = None,
) -> set[str]:
    """扫描 `paper/generated/`，返回已渲染的 renderable target `key` 集合。

    Figure N → `paper/generated/figures/` 下存在对应命名非空资产（svg/png/pdf 任一）。
    Table N  → `paper/generated/` 下生成表格文件按编号承载（见 `_rendered_table_numbers`）。
    non-renderable target 不参与（不会出现在返回集合中）。
    """

    fig_dir = Path(figures_dir) if figures_dir is not None else GENERATED_FIGURES_DIR
    gen_dir = Path(generated_dir) if generated_dir is not None else GENERATED_DIR

    rendered_keys: set[str] = set()
    rendered_tables = _rendered_table_numbers(gen_dir)

    for target in targets:
        if not target.renderable or target.number is None:
            continue
        if target.kind == "figure":
            if _figure_rendered(target.number, fig_dir):
                rendered_keys.add(target.key)
        elif target.kind == "table":
            if target.number in rendered_tables:
                rendered_keys.add(target.key)

    return rendered_keys


def _blocking_reason_for(target: FigureTableTarget) -> str:
    """为未渲染的 renderable target 生成 blocking reason（R6.4）。"""

    if target.kind == "figure":
        if not FIGURE_FILENAME_STEMS.get(target.number):
            return (
                f"{target.key}: no committed figure asset under "
                f"paper/generated/figures/ (figure not yet drawn)"
            )
        return (
            f"{target.key}: committed asset missing or empty under "
            f"paper/generated/figures/"
        )
    if target.kind == "table":
        return (
            f"{target.key}: no committed table under paper/generated/ "
            f"({', '.join(TABLE_SOURCE_FILENAMES)})"
        )
    return f"{target.key}: not rendered"


def compute_coverage(
    renderable_targets: list[FigureTableTarget],
    rendered_set: set[str],
) -> CoverageResult:
    """计算 Figure/Table 覆盖率（纯函数，design C2.2 / Property 3）。

    `coverage_percent = |rendered ∩ renderable| / |renderable|`，落在 `[0,1]`；
    `passed` 当且仅当 `percent >= COVERAGE_THRESHOLD`（R6.2，0.70）；
    `pending` 恰为未渲染的 renderable target，每项携带 `blocking_reason`（R6.4）。

    安全默认（避免除零）：当 `renderable_targets` 为空时（分母为 0），定义
    `percent = 0.0`、`rendered = total = 0`、`pending = []`、`passed = False`。
    选择 0.0 而非 1.0 是保守口径——「没有任何可渲染目标」不应被误判为达标 70%，
    且这是退化输入（claim matrix 至少声明若干 Figure/Table），由 CLI 主入口
    （任务 5.1）对空矩阵另行报错；本纯函数只保证不抛异常、返回自洽结构。

    入参 `renderable_targets` 应只含 `renderable=True` 的 target；防御性地仍按
    `renderable` 过滤，并按 `key` 去重以保证分母为离散 target 个数。
    """

    # 去重 + 仅保留 renderable（防御调用方传入混合/重复集合）。
    unique: dict[str, FigureTableTarget] = {}
    for target in renderable_targets:
        if target.renderable and target.key not in unique:
            unique[target.key] = target

    total = len(unique)
    if total == 0:
        return CoverageResult(
            percent=0.0, rendered=0, total=0, pending=[], passed=False
        )

    rendered_keys = {key for key in unique if key in rendered_set}
    rendered_count = len(rendered_keys)
    percent = rendered_count / total

    pending = [
        {"target": target.key, "blocking_reason": _blocking_reason_for(target)}
        for key, target in unique.items()
        if key not in rendered_keys
    ]

    return CoverageResult(
        percent=percent,
        rendered=rendered_count,
        total=total,
        pending=pending,
        passed=percent >= COVERAGE_THRESHOLD,
    )


def evaluate_figure_table_coverage(
    matrix_path: Path | str | None = None,
    figures_dir: Path | str | None = None,
    generated_dir: Path | str | None = None,
    promoted_manifest_path: Path | str | None = None,
) -> CoverageResult:
    """端到端覆盖率评估：解析 matrix → 扫描渲染产物 → 计算覆盖率（含 R6.5 防御）。

    R6.5（promoted manifest 缺失/不可读防御）：claim matrix 引用的 promoted
    manifest（默认 `run_2026-05-29T13-57-50Z/manifest.json`）是 table 再生成的
    数据源认知（R6.3）。当该 manifest 缺失或不可读时，**不重渲染任何表格、保留
    既有 `paper/generated/` 资产不变**；并把依赖该 promoted manifest 的 Table
    target（Table 2/3/4/5——其 evidence source 指向 promoted eval run）记为
    pending 并写入 blocking reason，而不是误判为已渲染。

    注意：本任务聚焦覆盖率判定，不实现表格再生成（design 注 paper:tables 已覆盖）。
    因此 R6.5 防御的语义是「数据源缺失时，覆盖率扫描对 promoted-manifest 依赖的
    Table 保守判 pending」，保护既有资产不被本脚本动到（本脚本本就只读扫描）。
    """

    targets = parse_claim_matrix_targets(matrix_path)
    renderable = [t for t in targets if t.renderable]
    rendered_set = scan_rendered_targets(renderable, figures_dir, generated_dir)

    manifest_path = (
        Path(promoted_manifest_path)
        if promoted_manifest_path is not None
        else DEFAULT_PROMOTED_MANIFEST_PATH
    )
    manifest_ok = False
    try:
        manifest_ok = manifest_path.is_file() and manifest_path.stat().st_size > 0
    except OSError:
        manifest_ok = False

    if not manifest_ok:
        # R6.5：promoted manifest 不可用 → 依赖它的 Table target 保守判 pending，
        # 既有资产保持不变（只读扫描，本就不写）。从 rendered_set 移除 Table 项，
        # 使其落入 pending；Figure 资产不依赖 promoted manifest，保留判定。
        table_keys = {t.key for t in renderable if t.kind == "table"}
        rendered_set = rendered_set - table_keys

    result = compute_coverage(renderable, rendered_set)

    if not manifest_ok:
        # 给因 manifest 缺失而 pending 的 Table 写明 R6.5 blocking reason。
        manifest_reason_suffix = (
            f" (promoted manifest unavailable: {manifest_path}; "
            f"table not regenerated, existing assets left unchanged per R6.5)"
        )
        for item in result.pending:
            if item["target"].lower().startswith("table"):
                item["blocking_reason"] = item["blocking_reason"] + manifest_reason_suffix

    return result


# --------------------------------------------------------------------------- #
# 口径一致性扫描子检查（R7.4 / R8.4 / R10.1–R10.4，design C2.1，Property 4）
#
# 本节为任务 4.1 增量，与上方 manifest/readiness/coverage 校验职责分离，全部写成
# 纯函数（`scan_consistency` 不读文件，只吃文本 + source_name），便于任务 4.2
# （Property 4 PBT）用 Hypothesis 测试。实际文件读取的 CLI 编排在任务 5.1。
#
# 判定规则（确定性、可测，逐行扫描，大小写不敏感、连字符与空格等价）：
#
#   对每一行：
#   1. 若该行**未出现** claim id（C2/C3/C4）→ 跳过（不是 claim 相关行）。
#   2. 若该行出现 claim id 但**未声明状态**（不含 `CLAIM_STATUS_TERMS` 任一状态
#      性词汇，也不含 caveat 措辞）→ 跳过（纯引用行，如「see C2 below」/ claim
#      内容描述行「**C2**: Motivational Delegation satisfies...」，避免误伤）。
#   3. 若该行含 promoted-with-caveat 措辞（`CAVEAT_WORDING_PATTERN`）→ 判
#      **compliant**（带 caveat 基线的行即使提到 `proven`/`fully validated`，
#      如 capture plan「Do not use stronger wording such as proven ... for
#      C2/C3/C4」这类元讨论行，也不误伤——caveat 措辞优先）。
#   4. 否则该行声明了 claim 状态却缺 caveat 措辞：
#      a. 若命中 `FORBIDDEN_OVERCLAIM_PHRASES` 任一短语 → **overclaim**
#         （R10.2 / R10.3：高于 owner-confirmed 级别），记 violation。
#      b. 否则 → **missing caveat**（R10.4：声明状态却未用 caveat 措辞），
#         记 violation。
#
# 判定顺序对应 Property 4 的陈述：含 caveat → compliant；声明状态缺 caveat 或
# 用 overclaim 措辞 → non-compliant 并定位到 source + 行号。
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class ConsistencyViolation:
    """一条口径一致性违规（design C2.1 输出 `consistency.violations[]`）。

    - `source`：违规所在 showcase material 名称（如 `README.md`）。
    - `line_number`：1-based 行号（定位用，R10.3 / R10.4 要求定位到材料与行）。
    - `claim_ids`：该行命中的 claim id 列表（C2/C3/C4 子集）。
    - `kind`：`"overclaim"`（R10.2/R10.3，高于 owner-confirmed 级别）或
      `"missing-caveat"`（R10.4，声明状态却缺 caveat 措辞）。
    - `reason`：人类可读原因（含命中的禁用短语 / 缺失 caveat 说明）。
    - `line`：违规行原文（截断便于诊断）。
    """

    source: str
    line_number: int
    claim_ids: tuple[str, ...]
    kind: str
    reason: str
    line: str


@dataclass
class ConsistencyResult:
    """`scan_consistency` / 聚合扫描的结构化结论（design C2.1 输出字段）。

    - `compliant`：当且仅当 `violations` 为空（bool）。
    - `violations`：`ConsistencyViolation` 列表（按 source、行号有序）。
    """

    compliant: bool
    violations: list[ConsistencyViolation] = field(default_factory=list)


# 违规行原文在 reason/记录中的最大保留字符数（防御超长行，便于诊断）。
_CONSISTENCY_LINE_MAX_CHARS = 240


def _claim_ids_in_line(line: str) -> tuple[str, ...]:
    """返回该行出现的 claim id（C2/C3/C4），保序去重；无则空元组。"""

    found: list[str] = []
    for m in _CLAIM_ID_TOKEN.finditer(line):
        token = m.group(0)
        if token not in found:
            found.append(token)
    return tuple(found)


def _matched_status_terms(line: str) -> list[str]:
    """返回该行命中的状态性词汇（`CLAIM_STATUS_TERMS` 子集，保序去重）。"""

    matched: list[str] = []
    for term, pattern in _STATUS_TERM_PATTERNS:
        if pattern.search(line) and term not in matched:
            matched.append(term)
    return matched


def _matched_forbidden_phrases(line: str) -> list[str]:
    """返回该行命中的禁用 overclaim 短语（`FORBIDDEN_OVERCLAIM_PHRASES` 子集）。"""

    matched: list[str] = []
    for phrase, pattern in _FORBIDDEN_PATTERNS:
        if pattern.search(line) and phrase not in matched:
            matched.append(phrase)
    return matched


def _truncate_line(line: str) -> str:
    stripped = line.strip()
    if len(stripped) <= _CONSISTENCY_LINE_MAX_CHARS:
        return stripped
    return stripped[: _CONSISTENCY_LINE_MAX_CHARS - 1] + "…"


def scan_consistency(text: str, source_name: str) -> ConsistencyResult:
    """逐行扫描单个 showcase material 文本的 C2/C3/C4 口径一致性（纯函数）。

    参数：
      - `text`：showcase material 全文（不读文件，便于 PBT）。
      - `source_name`：材料名称（用于违规定位，如 `README.md`）。

    返回 `ConsistencyResult`：`compliant` 当且仅当无违规；`violations` 每项含
    `source` + `line_number` + `claim_ids` + `kind` + `reason`（design C2.1 输出）。

    判定规则见本节顶部模块注释。要点：
      - 只对**同时出现 claim id 且声明了状态**的行做合规判定，纯引用 / claim
        内容描述行（无状态词）跳过，避免误伤（design 任务说明的可判定语义）。
      - 含 promoted-with-caveat 措辞的行优先判 compliant（连字符与空格等价、
        大小写不敏感），从而不误伤明确以 caveat 为基线的元讨论行。
    """

    violations: list[ConsistencyViolation] = []

    for idx, line in enumerate(text.splitlines(), start=1):
        claim_ids = _claim_ids_in_line(line)
        if not claim_ids:
            continue  # 规则 1：非 claim 相关行。

        has_caveat = bool(CAVEAT_WORDING_PATTERN.search(line))
        status_terms = _matched_status_terms(line)

        # 规则 2：出现 claim id 但既未声明状态也无 caveat 措辞 → 纯引用，跳过。
        if not status_terms and not has_caveat:
            continue

        # 规则 3：含 caveat 措辞 → compliant（含 caveat 基线的元讨论行不误伤）。
        if has_caveat:
            continue

        # 规则 4：声明了状态却缺 caveat 措辞 → non-compliant。
        forbidden = _matched_forbidden_phrases(line)
        claim_label = "/".join(claim_ids)
        if forbidden:
            reason = (
                f"{claim_label} described with wording above the owner-confirmed "
                f"promoted-with-caveat level (forbidden phrase(s): "
                f"{', '.join(forbidden)}); missing promoted-with-caveat wording"
            )
            kind = "overclaim"
        else:
            reason = (
                f"{claim_label} status asserted (term(s): {', '.join(status_terms)}) "
                f"without the required promoted-with-caveat wording"
            )
            kind = "missing-caveat"

        violations.append(
            ConsistencyViolation(
                source=source_name,
                line_number=idx,
                claim_ids=claim_ids,
                kind=kind,
                reason=reason,
                line=_truncate_line(line),
            )
        )

    return ConsistencyResult(compliant=not violations, violations=violations)


def scan_consistency_sources(
    sources: list[tuple[str, str]] | dict[str, str],
) -> ConsistencyResult:
    """对多个 (source_name, text) 聚合扫描口径一致性（纯函数）。

    参数 `sources`：`(source_name, text)` 序列或 `{source_name: text}` 映射。
    返回聚合 `ConsistencyResult`：`compliant` 当且仅当所有源均无违规；
    `violations` 为各源违规按输入顺序拼接（每项已带 source 定位）。

    本函数是 design C2.1「按文本列表聚合的纯函数」入口（不读文件），实际文件
    读取的 CLI 编排在任务 5.1。
    """

    items: list[tuple[str, str]]
    if isinstance(sources, dict):
        items = list(sources.items())
    else:
        items = list(sources)

    all_violations: list[ConsistencyViolation] = []
    for source_name, text in items:
        result = scan_consistency(text, source_name)
        all_violations.extend(result.violations)

    return ConsistencyResult(
        compliant=not all_violations, violations=all_violations
    )


def scan_consistency_files(
    paths: list[Path | str] | None = None,
    root: Path | str | None = None,
) -> ConsistencyResult:
    """读取并聚合扫描 showcase material 文件集合的口径一致性。

    薄 I/O 包装（任务 5.1 CLI 可直接复用）：默认扫描
    `CONSISTENCY_SOURCE_FILENAMES`（README.md / paper/blog_main.md /
    trace walkthrough / docs/demo_capture_plan.md / docs/showcase_manifest.md），相对 `root`
    （默认仓库根 `ROOT`）解析。source_name 使用相对路径（POSIX 风格，稳定可读）。

    防御性：文件不可读时记为一条 `missing-source` 违规（compliant=False），
    不抛异常；缺失文件的硬报错由 CLI 主入口（任务 5.1）按 `errors[]` 另行汇总。
    """

    base = Path(root) if root is not None else ROOT
    rel_paths = (
        [Path(p) for p in paths]
        if paths is not None
        else [Path(name) for name in CONSISTENCY_SOURCE_FILENAMES]
    )

    sources: list[tuple[str, str]] = []
    missing: list[ConsistencyViolation] = []
    for rel in rel_paths:
        full = rel if rel.is_absolute() else base / rel
        source_name = rel.as_posix()
        try:
            text = full.read_text(encoding="utf-8")
        except OSError:
            missing.append(
                ConsistencyViolation(
                    source=source_name,
                    line_number=0,
                    claim_ids=(),
                    kind="missing-source",
                    reason=f"showcase material not readable: {full}",
                    line="",
                )
            )
            continue
        sources.append((source_name, text))

    result = scan_consistency_sources(sources)
    if missing:
        result.violations = missing + result.violations
        result.compliant = False
    return result


# --------------------------------------------------------------------------- #
# CLI 主入口、JSON 报告、退出码契约与 manifest 回填（任务 5.1）
#
# 本节聚合上方三组纯函数子检查（manifest 结构 + readiness 自洽 + manual gate /
# coverage / consistency），沿用 `scripts/check_research_evidence.py` 的
# `{ok, check, errors, warnings, ...}` JSON 报告结构与退出码风格：
#   - 任一子检查 errors 非空 → 退出码 1；仅 warnings → 退出码 0。
#
# 覆盖率口径（主人确认 B 方案）：当前真实 Figure/Table 覆盖率 = 0.60（6/10），
# 低于 R6.2 的 0.70 阈值。脚本如实报告 0.60 / pass=false / pending 列表，并按
# design「Error Handling / 校验脚本」让 coverage fail 进入 errors[]——整体退出码
# 1 是如实反映「覆盖率尚未达标」的正确行为，不放宽阈值、不虚报、不降级为 warning。
#
# 回填（R6.4 / R10.4 / R11.5）：把 coverage pending 列表、consistency 结论、
# readiness 结论幂等回填进 `docs/showcase_manifest.md` 的 `## Figure/Table
# Coverage` / `## Consistency` / `## Readiness` 三个区块；只动这三块，绝不触碰
# `## Exit Criteria Status` / `## Deliverables` 表。回填保留文件原有行尾（CRLF/LF），
# 多次运行结果稳定（幂等）。
# --------------------------------------------------------------------------- #

# 缺失即记 errors[] 的 showcase 输入文件（design Error Handling「缺失文件」）。
REQUIRED_INPUT_FILES = (
    "paper/claim_evidence_matrix.md",
    "README.md",
    "paper/blog_main.md",
    "paper/trace_walkthroughs/figure3_trace_walkthrough_pf_branna_seed01.md",
    "docs/demo_capture_plan.md",
    "docs/showcase_manifest.md",
)

# manifest 软上限（AGENTS.md §2 自管理层软上限 250 行）→ 超出记 warning（非 error）。
MANIFEST_SOFT_LINE_LIMIT = 250

# 回填目标区块标题（只动这三块）。
COVERAGE_SECTION_HEADING = "## Figure/Table Coverage"
CONSISTENCY_SECTION_HEADING = "## Consistency"
READINESS_SECTION_HEADING = "## Readiness"

CHECK_NAME = "showcase.exit_criteria"


def _repo_relative(path: Path | None) -> str | None:
    """把绝对路径转为相对仓库根的 POSIX 路径（沿用 check_research_evidence 风格）。"""

    if path is None:
        return None
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def _read_text_and_newline(path: Path) -> tuple[str, str]:
    """读取文本并探测主导行尾，返回 `(text_lf, newline)`。

    text_lf 把所有 `\\r\\n` 归一为 `\\n`（便于纯文本处理）；newline 为探测到的
    主导行尾（`\\r\\n` 或 `\\n`），写回时复用以保留文件原有风格、保证幂等不污染 diff。
    """

    raw = path.read_bytes().decode("utf-8")
    newline = "\r\n" if "\r\n" in raw else "\n"
    return raw.replace("\r\n", "\n"), newline


def _write_text_preserving(path: Path, text_lf: str, newline: str) -> None:
    """以指定行尾写回文本（不经平台换行翻译，保证幂等）。"""

    data = text_lf.replace("\n", newline) if newline != "\n" else text_lf
    path.write_bytes(data.encode("utf-8"))


def _replace_section(text_lf: str, heading: str, content_lines: list[str]) -> str:
    """替换 `## heading` 区块的正文（标题行之后至下一个 `## ` 标题或 EOF）。

    `content_lines` 为正文内容行（不含标题行、不含包裹空行）。本函数统一在正文
    前后各补一个空行，复现「标题行 → 空行 → 正文 → 空行 → 下一标题/EOF」的既有
    文档风格，从而幂等可重复运行。区块标题未找到时原样返回（防御性 no-op）。
    """

    lines = text_lf.split("\n")
    start: int | None = None
    for idx, line in enumerate(lines):
        if line.strip() == heading:
            start = idx
            break
    if start is None:
        return text_lf

    end = len(lines)
    for j in range(start + 1, len(lines)):
        if lines[j].strip().startswith("## "):
            end = j
            break

    body = [""] + content_lines + [""]
    new_lines = lines[: start + 1] + body + lines[end:]
    return "\n".join(new_lines)


def _format_coverage_block(coverage: CoverageResult) -> list[str]:
    """生成 `## Figure/Table Coverage` 区块正文（R6.4，如实记录已知缺口）。"""

    pass_text = "true" if coverage.passed else "false"
    lines = [
        "> 由 `showcase:check`（任务 5.1）回填——如实记录覆盖率与待渲染缺口；"
        "不放宽阈值、不虚报（已知缺口口径）。",
        "",
        f"- `coverage_percent`: {coverage.percent:.2f}",
        f"- `rendered_count`: {coverage.rendered}",
        f"- `renderable_total`: {coverage.total}",
        f"- `pass`: {pass_text}（门槛 `>= {COVERAGE_THRESHOLD:.2f}`）",
    ]
    if coverage.pending:
        lines.append("- `pending[]`:")
        for item in sorted(coverage.pending, key=lambda p: p["target"]):
            lines.append(f"  - `{item['target']}`: {item['blocking_reason']}")
    else:
        lines.append("- `pending[]`: 无")

    if not coverage.passed:
        pending_targets = ", ".join(
            sorted(item["target"] for item in coverage.pending)
        )
        lines.extend(
            [
                "",
                f"`figure_coverage` 维持 pending：覆盖率 {coverage.percent:.2f} < "
                f"{COVERAGE_THRESHOLD:.2f}；待渲染 {pending_targets}。这是如实反映"
                "覆盖率尚未达标，不放宽阈值、不虚报。",
            ]
        )
    return lines


def _format_consistency_block(consistency: ConsistencyResult) -> list[str]:
    """生成 `## Consistency` 区块正文（R10.4 口径一致性最近一次扫描结论）。"""

    compliant_text = "true" if consistency.compliant else "false"
    lines = [
        "> 由 `showcase:check`（任务 5.1）回填 C2/C3/C4 口径一致性最近一次扫描结论。",
        "",
        f"- `compliant`: {compliant_text}",
    ]
    if consistency.violations:
        lines.append("- `violations[]`:")
        for v in consistency.violations:
            locator = f"{v.source}:L{v.line_number}" if v.line_number else v.source
            lines.append(f"  - {locator} [{v.kind}] {v.reason}")
    else:
        lines.append("- `violations[]`: 无")

    lines.extend(
        [
            "",
            "口径基线：C2 / C3 / C4 为主人确认的 `promoted with caveat`，2026-06-02 "
            "复盘后限定在 metric / explainability 级"
            "（human-believability pilot 评估为前提不成立、不执行）；"
            "所有 showcase material 提及其状态时必须使用 `promoted with caveat` 措辞。",
        ]
    )
    return lines


def _format_readiness_block(readiness: ReadinessResult) -> list[str]:
    """生成 `## Readiness` 区块正文（R11.4 / R11.5 readiness 自洽结论）。"""

    pending_text = ", ".join(readiness.pending_exit_ids) if readiness.pending_exit_ids else "无"
    gates_text = (
        ", ".join(readiness.blocking_manual_gates)
        if readiness.blocking_manual_gates
        else "无"
    )
    lines = [
        "> 由 `showcase:check`（任务 5.1）回填，规则见 R11.4 / R11.5。",
        "",
        f"- `readiness`: {readiness.readiness}",
        f"- `pending_exit_ids`: {pending_text}",
        f"- `blocking_manual_gates`: {gates_text}",
        "",
    ]
    if readiness.ready:
        lines.append(
            "5 条 exit criteria 全部非 pending，展示线 ready for owner review。"
        )
    else:
        lines.append(
            "当且仅当 5 条 exit criteria 全部非 pending 时报 ready for owner review；"
            f"当前仍有 pending exit criteria（{pending_text}），故 not ready。"
        )
    return lines


def _parse_claimed_readiness(text_lf: str) -> bool | None:
    """从现有 `## Readiness` 区块解析人工/上轮声明的 readiness 结论。

    返回 True（声明 ready）/ False（声明 not ready）/ None（占位未声明 → 跳过校验）。
    仅当结构化行 `- `readiness`: <value>` 的取值以明确结论短语开头时才判定，
    占位文案（如「待回填（…报 `ready for owner review`）」）返回 None，避免误判。
    """

    in_block = False
    pattern = re.compile(r"^-\s*`readiness`\s*:\s*(.+)$")
    for line in text_lf.split("\n"):
        stripped = line.strip()
        if stripped.startswith("## "):
            in_block = stripped == READINESS_SECTION_HEADING
            continue
        if not in_block:
            continue
        m = pattern.match(stripped)
        if m:
            val = m.group(1).strip().lower()
            if val.startswith("not ready for owner review"):
                return False
            if val.startswith("ready for owner review"):
                return True
            return None
    return None


def _backfill_manifest(
    manifest_path: Path,
    coverage: CoverageResult,
    consistency: ConsistencyResult,
    readiness: ReadinessResult,
) -> bool:
    """把 coverage / consistency / readiness 结论幂等回填进 manifest 三个区块。

    只替换 `## Figure/Table Coverage` / `## Consistency` / `## Readiness` 区块正文，
    保留文件原有行尾。返回是否发生了内容变更（幂等：内容不变则不写盘）。
    """

    try:
        text_lf, newline = _read_text_and_newline(manifest_path)
    except OSError:
        return False

    updated = text_lf
    updated = _replace_section(
        updated, COVERAGE_SECTION_HEADING, _format_coverage_block(coverage)
    )
    updated = _replace_section(
        updated, CONSISTENCY_SECTION_HEADING, _format_consistency_block(consistency)
    )
    updated = _replace_section(
        updated, READINESS_SECTION_HEADING, _format_readiness_block(readiness)
    )

    if updated == text_lf:
        return False  # 幂等：无变更不写盘。
    _write_text_preserving(manifest_path, updated, newline)
    return True


def _print_result(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Showcase 层三合一校验（manifest 结构 / 覆盖率 / 口径一致性）。"
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST_PATH)
    parser.add_argument("--claim-matrix", type=Path, default=DEFAULT_CLAIM_MATRIX_PATH)
    parser.add_argument(
        "--no-backfill",
        action="store_true",
        help="只校验、不回填 manifest（dry-run / 测试用）。",
    )
    args = parser.parse_args()

    manifest_path = (
        args.manifest if args.manifest.is_absolute() else ROOT / args.manifest
    )
    matrix_path = (
        args.claim_matrix
        if args.claim_matrix.is_absolute()
        else ROOT / args.claim_matrix
    )

    errors: list[str] = []
    warnings: list[str] = []

    # 1) 缺失文件检测（design Error Handling「缺失文件」）。
    missing_inputs: list[str] = []
    for rel in REQUIRED_INPUT_FILES:
        full = ROOT / rel
        if not full.is_file():
            missing_inputs.append(rel)
            errors.append(f"missing showcase input: {rel}")

    # 2) manifest 解析 + 结构校验 + manual gate + readiness 自洽。
    records = parse_manifest(manifest_path)
    structure_errors = validate_manifest_structure(records)
    manual_gate_errors = validate_manual_gate(records.deliverables)
    readiness = compute_readiness(records.exit_criteria, records.deliverables)

    claimed_ready: bool | None = None
    manifest_exists = manifest_path.is_file()
    if manifest_exists:
        try:
            existing_text, _ = _read_text_and_newline(manifest_path)
            claimed_ready = _parse_claimed_readiness(existing_text)
        except OSError:
            claimed_ready = None
    readiness_consistency_errors = validate_readiness_consistency(
        records, claimed_ready
    )

    errors.extend(structure_errors)
    errors.extend(manual_gate_errors)
    errors.extend(readiness_consistency_errors)

    # 3) Figure/Table 覆盖率（R6）——如实报告，coverage fail 进 errors[]（不降级）。
    coverage = evaluate_figure_table_coverage(matrix_path)
    if not coverage.passed:
        pending_targets = sorted(item["target"] for item in coverage.pending)
        errors.append(
            f"figure/table coverage {coverage.percent:.2f} below threshold "
            f"{COVERAGE_THRESHOLD:.2f}: {coverage.rendered}/{coverage.total} "
            f"rendered; pending {pending_targets}"
        )

    # 4) 口径一致性（R10）——只扫描存在的源，避免与缺失文件错误重复。
    existing_sources = [
        rel for rel in CONSISTENCY_SOURCE_FILENAMES if (ROOT / rel).is_file()
    ]
    consistency = scan_consistency_files(existing_sources)
    for v in consistency.violations:
        locator = f"{v.source}:L{v.line_number}" if v.line_number else v.source
        errors.append(f"consistency {locator} [{v.kind}]: {v.reason}")

    # 5) manifest 软上限 warning（非 error）。
    if manifest_exists:
        try:
            line_count = len(manifest_path.read_text(encoding="utf-8").splitlines())
            if line_count > MANIFEST_SOFT_LINE_LIMIT:
                warnings.append(
                    f"manifest exceeds soft line limit: {line_count} > "
                    f"{MANIFEST_SOFT_LINE_LIMIT}"
                )
        except OSError:
            pass

    # 6) 回填 manifest（缺失则跳过；回填本身不改变退出码契约）。
    backfilled = False
    if manifest_exists and not args.no_backfill:
        backfilled = _backfill_manifest(
            manifest_path, coverage, consistency, readiness
        )

    payload: dict[str, Any] = {
        "ok": not errors,
        "check": CHECK_NAME,
        "errors": errors,
        "warnings": warnings,
        "manifest": {
            "path": _repo_relative(manifest_path),
            "exists": manifest_exists,
            "missingInputs": missing_inputs,
            "exitCriteriaCount": len(records.exit_criteria),
            "deliverableCount": len(records.deliverables),
            "structureErrors": structure_errors,
            "manualGateErrors": manual_gate_errors,
            "readinessConsistencyErrors": readiness_consistency_errors,
            "backfilled": backfilled,
        },
        "readiness": {
            "ready": readiness.ready,
            "readiness": readiness.readiness,
            "pendingExitIds": readiness.pending_exit_ids,
            "blockingManualGates": readiness.blocking_manual_gates,
        },
        "coverage": {
            "percent": round(coverage.percent, 4),
            "rendered": coverage.rendered,
            "total": coverage.total,
            "threshold": COVERAGE_THRESHOLD,
            "pass": coverage.passed,
            "pending": coverage.pending,
        },
        "consistency": {
            "compliant": consistency.compliant,
            "violations": [
                {
                    "source": v.source,
                    "lineNumber": v.line_number,
                    "kind": v.kind,
                    "claimIds": list(v.claim_ids),
                    "reason": v.reason,
                }
                for v in consistency.violations
            ],
        },
    }

    _print_result(payload)
    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
