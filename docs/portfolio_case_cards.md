---
status: active
owner_lane: portfolio-showcase
last_verified: 2026-06-07
startup_load: on-demand
source_of_truth: true
scope: Loomstead 对外求职展示三张 case card：读者问题、展示路径、30 秒讲法与诚实边界
---

# Loomstead Portfolio Case Cards

> 自管理层文档，软上限 250 行。用途：作为 README 第一跳，让外部读者先看三个可讲清的工程案例，再进入长文、trace walkthrough 或原始 artifact。

## 0. 展示总线

一句话：

> Loomstead is a full-stack agent behavior observatory: a playable multi-agent runtime with structured traces, evidence-linked decisions, eval exports, and audit artifacts for debugging complex agent behavior.

讲法顺序：

1. 小镇提供行为场景。
2. Python runtime 持有权威状态并运行 agent loop。
3. 每次关键决策写入 trace 与 evidence links。
4. Eval / audit pipeline 把 trace 变成可复查 artifact。
5. 结论限定在 engineering showcase / explainability / failure analysis 层。

## Card A — Why did this NPC choose that action?

### 读者问题

> 一个 NPC 为什么选择这个动作，并放弃其他候选动作？

### 首选展示路径

1. Godot ShowcasePanel 或 Observer Dock：显示 Goal / Director Beat / Event Skill / NPC Decision / Trace Evidence。
2. `GET /api/debug.phase2`：查看 motivation、subjective memory、relationship edges、heuristics。
3. Appendix：`paper/trace_walkthroughs/figure3_trace_walkthrough_pf_branna_seed01.md`。

### 30 秒讲法

> Loomstead 不只记录最终动作。NPC 的动机、记忆、关系、候选工具分数和结果观察都会进入 `phase2.trace.v1`。调试时可以从 selected action 反向跳到 `sourceEventIds` 与 `traceRefs`，定位哪些证据影响了行为。

### 关键证据

| 证据 | 用法 |
|---|---|
| `MotivationEngine -> ToolExecutor -> ResultObserver` | 说明 agent loop 边界 |
| `candidateScores` | 展示候选工具如何被比较 |
| `scoreComponentSourceRefs` | 展示分数来源 |
| `sourceEventIds` / `traceRefs` | 展示证据可追溯性 |
| Godot Observer Dock / Web Debug | 展示可视化调试面 |

### 诚实边界

- 该案例展示 behavior provenance 与 debug 可见性。
- 不主张玩家一定会认为行为 believable。
- `process_believability_score` 等旧指标只作为历史 artifact 字段与复查索引使用。

## Card B — What changed when evidence was removed?

### 读者问题

> 如果移除某条记忆、关系或 evidence link，系统会显示什么差异？

### 首选展示路径

1. `.run/eval-promoted/run_2026-05-29T13-57-50Z`：读取 promoted process artifact。
2. `counterfactual_replay.jsonl`：对比 Full 与 evidence-removed 条件。
3. `summary.json` / `manifest.json`：确认 machine-level 状态与 `promoted with caveat` 口径。

### 30 秒讲法

> Loomstead 的 eval 层把复杂行为转成 before/after 对照。Full 条件下保留完整 evidence；移除 memory、relationship 或 evidence link 后，artifact 会记录 score、selected tool 或 verdict 是否变化。指标用于索引复查，case comparison 承担第一屏解释。

### 关键证据

| 证据 | 用法 |
|---|---|
| `counterfactual_replay.jsonl` | 展示移除 evidence 后的差异 |
| `ablation_comparison.json` | 展示 baseline 对照 |
| `manifest.json` | 固定 run、seed、provider、promotion 状态 |
| `llm_evidence.json` | 固定真实 provider evidence |
| `PROMOTION.md` | 记录 owner-approved `promoted with caveat` 口径 |

### 诚实边界

- 该案例支持 explainability / evidence-completeness 级展示。
- 不主张 Full 条件生成了人类盲评验证过的更可信行为。
- `promotionStatus=needs_manual_review` 与 `promoted with caveat` 同时保留：前者是机器层 caveat，后者是主人确认的展示口径。

## Card C — Why was this high-risk tool call blocked?

### 读者问题

> 当 agent 要执行高风险工具时，缺少 policy evidence 会发生什么？

### 首选展示路径

1. `.run/eval-reviewer-packets/audit_llm_supplement_2026-06-06T10-59-22Z/README.md`：先看 Go / No-Go。
2. `.run/eval-reviewer-packets/audit_llm_supplement_2026-06-06T10-59-22Z/LLM_CASE_COMPARISONS.md`：看 Full vs No Policy Evidence。
3. `.run/eval-reviewer-packets/audit_reviewer_packet_2026-06-06T08-58-33Z/README_REVIEWERS.md`：看 deterministic packet 与 reviewer rubric。

### 30 秒讲法

> Audit harness 把高风险工具调用拆成 required evidence、policy verdict 和 counterfactual evidence removal。Full 条件下证据齐全，高风险工具可以被允许；No Policy Evidence 条件下，系统转向 safe review tool。真实 `CloudApiProvider` smoke 覆盖 5 个场景 x 2 evidence 条件，10/10 cases pass。

### 关键证据

| 证据 | 用法 |
|---|---|
| `audit.go_no_go.v1` | 展示机器门禁结论 |
| `audit.report.v1` | 展示每个场景的证据地图 |
| `evidenceInfluenceMap` | 展示 required evidence 如何影响 verdict |
| `audit.counterfactual_replay.v1` | 展示移除证据后的动作变化 |
| LLM supplement | 展示真实 provider contract-following smoke |

### 诚实边界

- 该案例支持 toy workflow 中的 trace-grounded auditability 与 failure-analysis 展示。
- 不主张企业级生产安全、完整因果证明或跨域有效性。
- prompt 显式给出 required evidence 与 decision rules，因此结果只支持 contract-following / evidence-linking 可行性。

## 对外展示最短脚本

1. **10 秒定位**：这是 agent behavior observatory，Godot 小镇是 live surface。
2. **20 秒 Card A**：解释一个 NPC 行为如何从动机、记忆、关系追到 selected action。
3. **20 秒 Card B**：解释 evidence removal 如何改变 score / selected tool / verdict。
4. **20 秒 Card C**：解释高风险工具在 missing policy evidence 下如何转向 safe review tool。
5. **10 秒边界**：这是工程展示项目，claim 限定在 observability / eval artifact / failure analysis。

## 跳过项

- 最终视频、GIF、截图依赖人工窗口采集，当前可以跳过。
- 不为截图继续扩 Godot UI。
- 不继续扩 human rating、跨模型统计、新指标或新 audit scenario。
