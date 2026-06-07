---
status: active
owner_lane: portfolio-showcase
last_verified: 2026-06-07
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
| B promotion | `.run/eval-promoted/run_2026-05-29T13-57-50Z/PROMOTION.md` |
| C deterministic | `.run/eval-reviewer-packets/audit_reviewer_packet_2026-06-06T08-58-33Z/reviewer_packet.json` |
| C LLM smoke | `.run/eval-reviewer-packets/audit_llm_supplement_2026-06-06T10-59-22Z/packet_summary.json` |

## Card A — NPC decision provenance

| Field | Evidence |
|---|---|
| scenarioId | `pf.branna_forgiveness_requires_memory` |
| npcId / target | `bram` -> `player` |
| selectedToolId | `social.chat_with` |
| sourceEventIds | `1` direct source event(s) |
| traceRefs | `director_bias=1, heuristic_refs=1, motivation_decision_trace=1, motivation_profile=1, status=1, subjective_memory_refs=1` |
| memory result bridge | `1` memory trace link(s) |
| relationship sources | `2` source id(s) |

30 秒讲法：NPC 的 selected action 可反向追到 motivation decision trace、subjective memory refs、heuristic refs 与 relationship sources。

## Card B — Evidence removal delta

| Field | Evidence |
|---|---|
| selected with relationship memory | `social.chat_with` |
| selected without relationship memory | `social.give_gift` |
| toolSelectionChanged | `true` |
| top score with memory | `social.chat_with` score `0.956874` |
| top score without memory | `social.give_gift` score `0.845833` |
| aggregate causal_trace_coverage | mean `1.0` over n=`20` |
| aggregate required_process_coverage | mean `1.0` over n=`20` |
| aggregate counterfactual_tool_selection_change_rate | mean `0.375` over n=`20` |
| llmEvidence.recordCount | `100` |

30 秒讲法：Full 条件保留 evidence links；移除 relationship memory 后，工具选择从 `social.chat_with` 变为 `social.give_gift`。

## Card C — High-risk tool audit

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
- Human-validated believability、enterprise-ready AI safety、完整因果证明均为 out of scope。
- 需要更新 snippets 时先确认 source artifact，再运行 `npm.cmd run portfolio:snippets` 与 `npm.cmd run portfolio:check`。
