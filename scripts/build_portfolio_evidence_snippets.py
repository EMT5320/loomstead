"""从既有 artifact 生成 portfolio case cards 的轻量 evidence snippets。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = ROOT / "docs" / "portfolio_evidence_snippets.md"

PROCESS_RUN_DIR = ROOT / ".run" / "eval-promoted" / "run_2026-05-29T13-57-50Z"
CARD_A_SCENARIO_PATH = (
    PROCESS_RUN_DIR
    / "per_scenario"
    / "pf.branna_forgiveness_requires_memory_full_motivational_delegation_seed01.json"
)
AUDIT_PACKET_DIR = ROOT / ".run" / "eval-reviewer-packets" / "audit_reviewer_packet_2026-06-06T08-58-33Z"
AUDIT_LLM_DIR = ROOT / ".run" / "eval-reviewer-packets" / "audit_llm_supplement_2026-06-06T10-59-22Z"
AUDIT_FULL_CASE = (
    AUDIT_LLM_DIR
    / "raw"
    / "per_case"
    / "audit.coding_policy_before_patch.full_runtime.seed01.json"
)
AUDIT_NO_POLICY_CASE = (
    AUDIT_LLM_DIR
    / "raw"
    / "per_case"
    / "audit.coding_policy_before_patch.no_policy_evidence.seed01.json"
)


def load_json(path: Path) -> Any:
    """读取 JSON artifact；缺失或格式错误直接让命令失败。"""

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def metric(
    summary: dict[str, Any],
    metric_name: str,
    baseline: str = "full_motivational_delegation",
) -> dict[str, Any]:
    """按 baseline 与 metric 名称提取 aggregate 指标。"""

    for row in summary.get("metrics", []):
        if (
            row.get("metric") == metric_name
            and row.get("baseline") == baseline
            and row.get("scenarioId") == "aggregate"
        ):
            return row
    raise KeyError(f"missing aggregate metric: {baseline}.{metric_name}")


def first_candidate(score_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """取候选工具分数列表中的第一名。"""

    if not score_rows:
        raise ValueError("candidate score rows are empty")
    return score_rows[0]


def count_trace_ref_types(trace_refs: list[dict[str, Any]]) -> str:
    """把 traceRefs 压缩成可读类型摘要。"""

    counts: dict[str, int] = {}
    for ref in trace_refs:
        ref_type = str(ref.get("type", "unknown"))
        counts[ref_type] = counts.get(ref_type, 0) + 1
    return ", ".join(f"{key}={value}" for key, value in sorted(counts.items()))


def bool_word(value: Any) -> str:
    """将布尔值格式化为 Markdown 友好的字符串。"""

    return "true" if bool(value) else "false"


def score_delta(left: dict[str, Any], right: dict[str, Any]) -> str:
    """格式化两个候选工具分数差，突出 near-tie 场景。"""

    return f"`{left['toolId']}` `{left['score']}` vs `{right['toolId']}` `{right['score']}`"


def first_replay_comparison(
    replay: dict[str, Any],
    record_id_suffix: str,
) -> dict[str, Any]:
    """从单条记忆移除 replay 中提取指定 record 的首个 comparison。"""

    comparisons = replay.get("toolSelectionReplay", {}).get("comparisons", [])
    for comparison in comparisons:
        record_id = str(comparison.get("removedSubjectiveMemoryRecordId", ""))
        if record_id.endswith(record_id_suffix):
            return comparison
    raise KeyError(f"missing replay comparison for suffix: {record_id_suffix}")


def build_markdown() -> str:
    """构造稳定 Markdown 输出。"""

    scenario = load_json(CARD_A_SCENARIO_PATH)
    summary = load_json(PROCESS_RUN_DIR / "summary.json")
    manifest = load_json(PROCESS_RUN_DIR / "manifest.json")
    audit_packet = load_json(AUDIT_PACKET_DIR / "reviewer_packet.json")
    audit_summary = load_json(AUDIT_LLM_DIR / "packet_summary.json")
    audit_full = load_json(AUDIT_FULL_CASE)
    audit_no_policy = load_json(AUDIT_NO_POLICY_CASE)

    scenario_meta = scenario["scenario"]
    evidence = scenario["evidence"]
    goal_event = evidence["goalToolEvents"][0]
    goal_details = goal_event["details"]
    trace_refs = goal_details.get("traceRefs", [])
    replay = evidence["counterfactualReplay"]
    with_memory = first_candidate(replay["candidateScoresWithRelationshipMemory"])
    with_memory_runner_up = replay["candidateScoresWithRelationshipMemory"][1]
    without_edges = first_candidate(replay["candidateScoresWithoutRelationshipEdges"])
    without_edges_runner_up = replay["candidateScoresWithoutRelationshipEdges"][1]
    without_memory = first_candidate(replay["candidateScoresWithoutRelationshipMemory"])
    without_memory_runner_up = replay["candidateScoresWithoutRelationshipMemory"][1]
    harm_memory = next(
        ref
        for ref in replay.get("subjectiveMemoryRefs", [])
        if str(ref.get("recordId", "")).endswith(":bram:harm")
    )
    interaction_memory = next(
        ref
        for ref in replay.get("subjectiveMemoryRefs", [])
        if not str(ref.get("recordId", "")).endswith(":bram:harm")
    )
    harm_replay = first_replay_comparison(replay, ":bram:harm")
    interaction_replay = first_replay_comparison(replay, ":bram")

    causal_trace = metric(summary, "causal_trace_coverage")
    counterfactual_change = metric(summary, "counterfactual_tool_selection_change_rate")
    required_process = metric(summary, "required_process_coverage")
    no_relationship_change = metric(
        summary,
        "counterfactual_tool_selection_change_rate",
        baseline="no_relationship_edge",
    )
    no_subjective_change = metric(
        summary,
        "counterfactual_tool_selection_change_rate",
        baseline="no_subjective_memory",
    )

    go_no_go = audit_packet["goNoGo"]
    sensitive_check = next(
        check
        for check in go_no_go["checks"]
        if check.get("checkId") == "counterfactual_changes_at_least_two_scenarios"
    )
    full_decision = audit_full["parsed"]
    no_policy_decision = audit_no_policy["parsed"]

    lines = [
        "---",
        "status: active",
        "owner_lane: portfolio-showcase",
        "last_verified: 2026-06-07",
        "startup_load: on-demand",
        "source_of_truth: true",
        "scope: Loomstead 三张 portfolio case card 的轻量 evidence snippets",
        "---",
        "",
        "# Loomstead Portfolio Evidence Snippets",
        "",
        "> 自管理层文档，由 `npm.cmd run portfolio:snippets` 生成。用途：给面试或作品集阅读者提供三张 case card 的最短证据片段，避免第一屏打开大 JSON。",
        "",
        "## Source files",
        "",
        "| Case | Source |",
        "|---|---|",
        f"| A / B | `{CARD_A_SCENARIO_PATH.relative_to(ROOT).as_posix()}` |",
        f"| B aggregate | `{(PROCESS_RUN_DIR / 'summary.json').relative_to(ROOT).as_posix()}` |",
        f"| B baselines | `{(PROCESS_RUN_DIR / 'ablation_comparison.json').relative_to(ROOT).as_posix()}` |",
        f"| B promotion | `{(PROCESS_RUN_DIR / 'PROMOTION.md').relative_to(ROOT).as_posix()}` |",
        f"| C deterministic | `{(AUDIT_PACKET_DIR / 'reviewer_packet.json').relative_to(ROOT).as_posix()}` |",
        f"| C LLM smoke | `{(AUDIT_LLM_DIR / 'packet_summary.json').relative_to(ROOT).as_posix()}` |",
        "",
        "## Card A — NPC decision provenance",
        "",
        "Why it matters：复杂 agent 的最终动作需要能追到候选排序、证据来源和 near-tie 翻转点。",
        "",
        "| Field | Evidence |",
        "|---|---|",
        f"| scenarioId | `{scenario_meta['scenarioId']}` |",
        f"| npcId / target | `{scenario_meta['npcId']}` -> `{scenario_meta['targetNpcId']}` |",
        f"| selectedToolId | `{goal_details['toolId']}` |",
        f"| sourceEventIds | `{len(goal_details.get('sourceEventIds', []))}` direct source event(s) |",
        f"| traceRefs | `{count_trace_ref_types(trace_refs)}` |",
        f"| memory result bridge | `{len(evidence.get('memoryTraceLinks', []))}` memory trace link(s) |",
        f"| relationship sources | `{len(evidence.get('relationshipSourceIds', []))}` source id(s) |",
        f"| full ranking | {score_delta(with_memory, with_memory_runner_up)} |",
        f"| relationship-edge-only removal | selected `{replay['selectedWithoutRelationshipEdges']}`; {score_delta(without_edges, without_edges_runner_up)} |",
        f"| harm memory valence | `{harm_memory['emotionalValence']}`; single-record removal changed=`{bool_word(harm_replay['changed'])}` |",
        f"| interaction memory valence | `{interaction_memory['emotionalValence']}`; single-record removal changed=`{bool_word(interaction_replay['changed'])}` |",
        "",
        "30 秒讲法：NPC 的 selected action 可反向追到 motivation decision trace、subjective memory refs、heuristic refs 与 relationship sources。Bram 案例中，relationship-edge-only removal 只缩小分差；interaction memory removal 才把 replay 翻到 `social.give_gift`。",
        "",
        "## Card B — Evidence removal delta",
        "",
        "Why it matters：反事实 replay 把“证据缺失后发生什么”变成可复查的分数、工具选择和 verdict 差异。",
        "",
        "| Field | Evidence |",
        "|---|---|",
        f"| selected with relationship memory | `{replay['selectedWithRelationshipMemory']}` |",
        f"| selected without relationship memory | `{replay['selectedWithoutRelationshipMemory']}` |",
        f"| toolSelectionChanged | `{bool_word(replay['toolSelectionChanged'])}` |",
        f"| top score with memory | `{with_memory['toolId']}` score `{with_memory['score']}` |",
        f"| top score without memory | `{without_memory['toolId']}` score `{without_memory['score']}` |",
        f"| no-memory ranking | {score_delta(without_memory, without_memory_runner_up)} |",
        f"| aggregate causal_trace_coverage | mean `{causal_trace['mean']}` over n=`{causal_trace['n']}` |",
        f"| aggregate required_process_coverage | mean `{required_process['mean']}` over n=`{required_process['n']}` |",
        f"| aggregate counterfactual_tool_selection_change_rate | mean `{counterfactual_change['mean']}` over n=`{counterfactual_change['n']}` |",
        f"| no_relationship_edge change_rate | mean `{no_relationship_change['mean']}` over n=`{no_relationship_change['n']}` |",
        f"| no_subjective_memory change_rate | mean `{no_subjective_change['mean']}` over n=`{no_subjective_change['n']}` |",
        f"| llmEvidence.recordCount | `{manifest['llmEvidence']['recordCount']}` |",
        "",
        "30 秒讲法：Full 条件保留 evidence links；移除 memory / relationship evidence 后，工具选择、分数或 verdict 会被记录。Branna 单例提供可读故事，aggregate 数字约束外推边界。",
        "",
        "## Card C — High-risk tool audit",
        "",
        "Why it matters：高风险 agent 工具需要执行前 evidence contract；缺 policy evidence 时，系统应给出可追溯阻断理由。",
        "",
        "| Field | Evidence |",
        "|---|---|",
        f"| deterministic go/no-go | `{bool_word(go_no_go['pass'])}` |",
        f"| sensitive scenarios | `{len(sensitive_check['sensitiveScenarioIds'])}` scenario(s) |",
        f"| LLM smoke pass count | `{audit_summary['passed']}/{audit_summary['total']}` |",
        f"| LLM provider mode | `{audit_summary['providerMode']}` |",
        f"| LLM cost | `{audit_summary['costUsd']}` USD |",
        f"| Full selectedToolId | `{full_decision['selectedToolId']}` |",
        f"| Full verdict | `{full_decision['policyVerdict']['verdict']}` |",
        f"| Full sourceEventIds | `{len(full_decision.get('sourceEventIds', []))}` |",
        f"| No-policy selectedToolId | `{no_policy_decision['selectedToolId']}` |",
        f"| No-policy verdict | `{no_policy_decision['policyVerdict']['verdict']}` |",
        f"| No-policy sourceEventIds | `{len(no_policy_decision.get('sourceEventIds', []))}` |",
        "",
        "30 秒讲法：Full evidence 允许 `coding.apply_patch`；缺 policy evidence 时，LLM smoke 选择 `audit.request_policy_review` 并给出 `blocked_missing_policy_evidence`。",
        "",
        "## Boundary",
        "",
        "- 这些 snippets 支持 engineering showcase / explainability / failure analysis 层展示。",
        "- `process_believability_score` 仍存在于历史 JSON artifact；本 snippets 有意不输出该字段，避免把兼容字段当作 believability claim。",
        "- Human-validated believability、enterprise-ready AI safety、完整因果证明均为 out of scope。",
        "- 需要更新 snippets 时先确认 source artifact，再运行 `npm.cmd run portfolio:snippets` 与 `npm.cmd run portfolio:check`。",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    """写入 evidence snippets 文档并打印输出路径。"""

    OUTPUT_PATH.write_text(build_markdown(), encoding="utf-8")
    print(f"[portfolio-snippets] wrote {OUTPUT_PATH.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
