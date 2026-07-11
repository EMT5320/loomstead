---
status: active
owner_lane: portfolio-showcase
last_verified: 2026-07-11
startup_load: on-demand
source_of_truth: true
scope: Loomstead 三张 portfolio case card 的轻量 evidence snippets
---

# Loomstead Portfolio Evidence Snippets

> 自管理层文档，由 `npm.cmd run portfolio:snippets` 生成。用途：给面试或作品集阅读者提供三张 case card 的最短证据片段，避免第一屏打开大 JSON。

## Source files

| Case | Source |
|---|---|
| A / B | `.run/eval-promoted/run_2026-05-29T13-57-50Z/per_scenario/pf.branna_forgiveness_requires_memory_full_motivational_delegation_seed01.json` |
| B aggregate | `.run/eval-promoted/run_2026-05-29T13-57-50Z/summary.json` |
| B baselines | `.run/eval-promoted/run_2026-05-29T13-57-50Z/ablation_comparison.json` |
| B promotion | `.run/eval-promoted/run_2026-05-29T13-57-50Z/PROMOTION.md` |
| C deterministic | `.run/eval-reviewer-packets/audit_reviewer_packet_2026-06-06T08-58-33Z/reviewer_packet.json` |
| C LLM smoke | `.run/eval-reviewer-packets/audit_llm_supplement_2026-06-06T10-59-22Z/packet_summary.json` |

## Card A — NPC decision provenance

Why it matters：复杂 agent 的最终动作需要能追到候选排序、证据来源和 near-tie 翻转点。

| Field | Evidence |
|---|---|
| scenarioId | `pf.branna_forgiveness_requires_memory` |
| npcId / target | `bram` -> `player` |
| selectedToolId | `social.chat_with` |
| sourceEventIds | `1` direct source event(s) |
| traceRefs | `director_bias=1, heuristic_refs=1, motivation_decision_trace=1, motivation_profile=1, status=1, subjective_memory_refs=1` |
| memory result bridge | `1` memory trace link(s) |
| relationship sources | `2` source id(s) |
| full ranking | `social.chat_with` `0.956874` vs `social.give_gift` `0.902323` |
| relationship-edge-only removal | selected `social.chat_with`; `social.chat_with` `0.893874` vs `social.give_gift` `0.886573` |
| harm memory valence | `-0.7976000000000001`; single-record removal changed=`false` |
| interaction memory valence | `0.25`; single-record removal changed=`true` |

30 秒讲法：NPC 的 selected action 可反向追到 motivation decision trace、subjective memory refs、heuristic refs 与 relationship sources。Bram 案例中，relationship-edge-only removal 只缩小分差；interaction memory removal 才把 replay 翻到 `social.give_gift`。

## Card B — Evidence removal delta

Why it matters：反事实 replay 把“证据缺失后发生什么”变成可复查的分数、工具选择和 verdict 差异。

| Field | Evidence |
|---|---|
| selected with relationship memory | `social.chat_with` |
| selected without relationship memory | `social.give_gift` |
| toolSelectionChanged | `true` |
| top score with memory | `social.chat_with` score `0.956874` |
| top score without memory | `social.give_gift` score `0.845833` |
| no-memory ranking | `social.give_gift` `0.845833` vs `social.chat_with` `0.845` |
| aggregate causal_trace_coverage | mean `1.0` over n=`20` |
| aggregate required_process_coverage | mean `1.0` over n=`20` |
| aggregate counterfactual_tool_selection_change_rate | mean `0.375` over n=`20` |
| no_relationship_edge change_rate | mean `0.25` over n=`20` |
| no_subjective_memory change_rate | mean `0.0` over n=`20` |
| llmEvidence.recordCount | `100` |

30 秒讲法：Full 条件保留 evidence links；移除 memory / relationship evidence 后，工具选择、分数或 verdict 会被记录。Branna 单例提供可读故事，aggregate 数字约束外推边界。

## Card C — High-risk tool audit

Why it matters：高风险 agent 工具需要执行前 evidence contract；缺 policy evidence 时，系统应给出可追溯阻断理由。

| Field | Evidence |
|---|---|
| deterministic go/no-go | `true` |
| sensitive scenarios | `5` scenario(s) |
| LLM smoke pass count | `10/10` |
| LLM provider mode | `cloud` |
| LLM cost | `0.00351806` USD |
| Full selectedToolId | `coding.apply_patch` |
| Full verdict | `allow` |
| Full sourceEventIds | `3` |
| No-policy selectedToolId | `audit.request_policy_review` |
| No-policy verdict | `blocked_missing_policy_evidence` |
| No-policy sourceEventIds | `0` |

30 秒讲法：Full evidence 允许 `coding.apply_patch`；缺 policy evidence 时，LLM smoke 选择 `audit.request_policy_review` 并给出 `blocked_missing_policy_evidence`。

## Boundary

- 这些 snippets 支持 engineering showcase / explainability / failure analysis 层展示。
- `process_believability_score` 仍存在于历史 JSON artifact；本 snippets 有意不输出该字段，避免把兼容字段当作 believability claim。
- Human-validated believability、enterprise-ready AI safety、完整因果证明均为 out of scope。
- 需要更新 snippets 时先确认 source artifact，再运行 `npm.cmd run portfolio:snippets` 与 `npm.cmd run portfolio:check`。
