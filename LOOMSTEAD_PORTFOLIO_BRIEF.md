# Loomstead Portfolio Brief

> Internal memo — the author's job-search prep notebook (resume bullets, interview talking tracks, development recall). Not the public project entry point; see [README.md](README.md) for the project overview.

> 用途：这份文档是 Loomstead 冻结后的最终求职展示备忘。它同时服务三件事：简历 bullet、面试口述、未来重新回忆项目开发过程。

## 0. 最终一句话

**Loomstead 是一个 Agent Behavior Observatory：用 Godot 小镇承载多 Agent 行为，用 Python runtime、结构化 trace、eval/export pipeline、counterfactual replay 与 audit packet 展示复杂 agent 行为的调试、追踪和审计能力。**

英文版：

> Loomstead is a full-stack agent behavior observatory: a playable multi-agent runtime with structured traces, evidence-linked decisions, eval exports, counterfactual replay, and audit artifacts for debugging complex autonomous behavior.

## 1. 简历可直接使用版本

### 中文简历 bullet

- 设计并实现一个可解释多 Agent 运行时：Godot 小镇作为 live surface，Python Agent Server 持有权威世界状态，Agent loop 覆盖动机、工具执行、结果观察、主观记忆与关系演化。
- 构建行为可观测性链路：关键决策写入 `phase2.trace.v1`，并记录 `sourceEventIds`、`traceRefs`、`candidateScores`、`scoreComponentSourceRefs`，支持从最终动作回溯到动机、记忆、关系、heuristic 与工具证据。
- 搭建 eval/export/replay pipeline：Process Fidelity artifact 覆盖 4 个场景 × 5 seeds，Full aggregate `causal_trace_coverage=1.0`、`required_process_coverage=1.0`、`counterfactual_tool_selection_change_rate=0.375`，并保留 100 条 cloud-backed LLM evidence。
- 实现高风险工具 audit harness：覆盖 5 个非叙事高风险场景、5 类 baseline、逐条 evidence removal、`audit.report.v1`、`audit.counterfactual_replay.v1` 与 reviewer packet；真实 CloudApiProvider smoke 覆盖 5 场景 × 2 evidence 条件，10/10 cases passed。
- 将项目从研究探索收束为求职展示工程：用 case-card-first 叙事、evidence snippets、trace walkthrough 与 showcase readiness gate，把复杂系统包装为可复查的 Agent observability portfolio。

### English resume bullets

- Built a full-stack agent behavior observatory using a Godot town client and an authoritative Python Agent Server for multi-agent decisions, tools, memories, relationships, and world-state updates.
- Designed a structured observability layer (`phase2.trace.v1`) with `sourceEventIds`, `traceRefs`, candidate tool scores, and score-component evidence links for debugging why agents selected specific actions.
- Implemented an eval/export pipeline with counterfactual replay, promoted artifacts, archive checks, and cloud-backed LLM evidence; the process suite covers 4 scenarios × 5 seeds with full trace/process coverage.
- Built a trace-grounded audit harness for high-risk tool calls across 5 scenarios and 5 baselines, including evidence-removal counterfactuals, reviewer packets, and a real provider smoke test with 10/10 passing cases.
- Re-scoped the project into a portfolio-ready engineering showcase focused on agent orchestration, observability, eval infrastructure, and failure analysis.

### 简历项目标题备选

- Loomstead — Agent Behavior Observatory for Multi-Agent Runtime Debugging
- Loomstead — Trace-Grounded Multi-Agent Runtime and Audit Harness
- Loomstead — 可解释多 Agent 运行时与行为观测平台

## 2. 面试 30 秒讲法

> Loomstead 是我做的一个多 Agent 行为可观测性项目。表层是一个 Godot 小镇，真正的工程重点是后端 Python runtime：NPC 的动机、主观记忆、关系边、候选工具分数和工具执行都会被结构化记录。系统可以回答三个问题：NPC 为什么做这个动作；移除某条 evidence 后行为会怎样变；高风险工具缺少 policy evidence 时为什么被阻断。最终我把它收束成 Agent Behavior Observatory，主张限定在 agent orchestration、observability、eval infra 和 failure analysis。

## 3. 面试 2 分钟讲法

> 项目最开始是一个叙事多 Agent 小镇。后来我发现最有价值的部分在 agent runtime 与观测基础设施，于是把它收束为 Agent Behavior Observatory。  
> 
> 系统架构上，Godot 只负责表现和合法玩家输入，Python Agent Server 持有权威世界状态。NPC 决策走 `MotivationEngine -> ToolExecutor -> ResultObserver`，并结合 subjective memory、relationship edges、heuristics 和 capability-aware tool arbitration。每个关键动作都会写 trace，包含 `sourceEventIds`、`traceRefs`、候选工具分数和分数来源。  
> 
> 展示时我用三张 case card：第一，解释 NPC 为什么选中某个动作；第二，展示移除 memory / relationship / evidence link 后 score 或 selected tool 如何变化；第三，展示高风险工具调用在缺少 policy evidence 时如何转向 safe review tool。  
> 
> 这个项目也经历了研究 claim 收束：human-validated believability 已退出主张范围，证据限定在 explainability、metric-level guardrail 和 failure-analysis。最终成果是一个能展示复杂 agent 系统设计、trace 设计、eval artifact 管理和诚实 scope 控制的求职工程项目。

## 4. 面试 5 分钟深讲结构

1. **背景问题**：复杂 agent 的行为通常只看到最终动作，很难知道动机、记忆、关系和工具约束如何共同影响结果。
2. **系统设计**：Godot 是 live surface；Python backend 是权威运行时；Web Debug / Observer Dock / artifact docs 是观测面。
3. **Agent loop**：`MotivationEngine -> ToolExecutor -> ResultObserver`，外加 Director / Event Skill、CapabilityRegistry、ArbitrationLayer、SubjectiveMemoryStore、relationship edges。
4. **可观测性契约**：`phase2.trace.v1` 统一承载 decision、tool、interrupt、memory observation、budget events；`sourceEventIds` 与 `traceRefs` 让读者从结果回到原因。
5. **Eval 与 artifact**：process suite、stability、domain adapter、robustness、archive/promote；用 promoted artifact 作为稳定证据源。
6. **Audit spike**：高风险工具场景、required evidence、policy verdict、counterfactual evidence removal、LLM contract-following smoke。
7. **收束决策**：human-believability pilot 前提不足，研究强 claim 关闭；项目转为工程展示，保留能复查的 trace/eval/audit 资产。

## 4.1 Agent 面试深挖故事

### 4.1.1 Trace schema 为什么这样设计

面试问题：为什么不只记录最终动作和日志文本？

推荐回答：复杂 Agent 的调试需要同时看到动作、候选项、证据来源和可跳转位置。`sourceEventIds` 说明当前决策受哪些历史事件或证据影响；`traceRefs` 让读者从结论跳回 decision / memory / heuristic / budget span；`candidateScores` 暴露被放弃的候选工具；`scoreComponentSourceRefs` 把分数拆到关系、记忆、工具定义和 heuristic 证据。这样设计后，面试时可以从 selected action 反向解释“为什么是这个动作”和“哪些证据改变了排序”。

### 4.1.2 Evidence-removal replay 证明了什么

面试问题：counterfactual replay 如何支持可观测性？

推荐回答：它把复杂行为变成同一 scenario / seed 下的 before-after 对照。Full 条件保留完整 evidence；移除 memory、relationship 或 evidence link 后，artifact 记录 score、selected tool 或 verdict 的变化，也记录没有变化的情况。Branna 单例提供可读故事，aggregate `counterfactual_tool_selection_change_rate=0.375` 用来约束外推范围。这个证据支持的是“行为依赖关系可复查”，不升级成完整因果证明。

### 4.1.3 High-risk audit 与 ContextGuard 的共同抽象

面试问题：Loomstead audit 和 ContextGuard evidence-gated execution 有什么共同点？

推荐回答：两者都把 Agent 动作执行前的信任判断拆成四件事：required evidence 是否齐全、policy verdict 如何产生、缺证据时进入哪个 safe fallback、移除关键 evidence 后动作或 verdict 是否变化。ContextGuard 面向 RAG / tool execution 的引用与护栏策略，Loomstead 面向 runtime trace / audit artifact；共同卖点是 evidence-gated execution 和可复查 failure analysis。

### 4.1.4 哪些 claim 主动降级

面试问题：项目为什么最终冻结为 portfolio engineering showcase？

推荐回答：复查 evidence 后，human-validated believability、完整 causal proof、enterprise-ready safety 都缺少对应验证，因此全部保留为边界。保留的强项是可复查工程事实：agent runtime、trace schema、eval/export、counterfactual replay、audit packet 和 claim discipline。这个决策展示的是我会判断 Agent 系统在什么证据下可信，在什么证据下需要降级。

## 5. 技术架构回忆

### 5.1 顶层组件

| 层 | 内容 | 面试信号 |
|---|---|---|
| Godot client | `clients/godot/`，默认 `world_main.tscn`，展示 ShowcasePanel、Observer Dock、NPC 小镇表面 | full-stack integration / UX surface |
| Python Agent Server | `/api/world/state`、`/api/player/action`、`/api/world/tick`、`/api/debug.phase2`、`/api/showcase/starlight` | backend systems / runtime authority |
| Agent runtime | MotivationEngine、ToolExecutor、ResultObserver、CapabilityRegistry、ArbitrationLayer | agent orchestration |
| Memory / relationship | subjective memory、relationship edges、heuristic seeds | stateful agent behavior |
| Observability | `phase2.trace.v1`、source links、candidate scores、Observer Dock、Web Debug | debugging tools |
| Eval / archive | process/stability/domain/robustness suites、manifest、promote、drift notes | eval infra / reproducibility |
| Audit | audit harness、reviewer packets、LLM supplement | reliability / failure analysis |

### 5.2 Agent loop

核心运行路径：

```text
Director / Event Skill
    -> NeedAccumulator / MotivationEngine
    -> CapabilityRegistry
    -> ArbitrationLayer
    -> ToolExecutor
    -> ResultObserver
    -> SubjectiveMemoryStore + relationship edges
    -> phase2.trace.v1 + eval artifacts
```

可以这样解释：

- Director / Event Skill 给世界施加节奏和压力。
- MotivationEngine 计算 NPC 当前需求与动机。
- CapabilityRegistry 过滤合法工具。
- ArbitrationLayer 对候选工具打分，输出候选列表、分数、分数来源和解释引用。
- ToolExecutor 执行世界状态变更，带事务回滚和中断处理。
- ResultObserver 生成观察、记忆和关系变化。
- Trace / Eval 层把运行过程固化为可复查证据。

### 5.3 关键 trace 字段

| 字段 | 用途 |
|---|---|
| `phase2.trace.v1` | 统一 trace envelope |
| `sourceEventIds` | 当前事件受哪些历史事件或证据影响 |
| `traceRefs` | 从结果跳回 decision / memory / heuristic / budget span |
| `candidateScores` | 候选工具排序 |
| `scoreComponentSourceRefs` | 分数来源，含 tool definition、relationship edges、subjective memory、heuristics、decision budget |
| `memory.result_observed` | 工具结果如何被观察并写成主观记忆 / 关系变化 |
| `decision_budget_trace` | 真实 LLM / fallback / budget 路由证据 |

## 6. 三个展示 case

### Case A — NPC 为什么选择这个动作

入口：

- `docs/portfolio_case_cards.md`
- `docs/portfolio_evidence_snippets.md`
- `paper/trace_walkthroughs/figure3_trace_walkthrough_pf_branna_seed01.md`
- Godot ShowcasePanel / Observer Dock

讲法：

> Bram 案例里，Full evidence 下 `social.chat_with` 以 `0.956874` 领先 `social.give_gift` 的 `0.902323`。移除 relationship edges 后，选择仍是 `social.chat_with`，分数变成 `0.893874` vs `0.886573`。单条 replay 显示移除 harm memory 不改变选择，移除 interaction memory 会把 replay 翻到 `social.give_gift`。这个案例展示系统能把“为什么是这个动作”拆到分数、记忆、关系和 trace 证据层。

面试重点：

- 可解释 agent decision。
- near-tie 排序和证据敏感性。
- trace walkthrough 能对上当前 promoted artifact。

### Case B — 移除证据后发生什么

入口：

- `.run/eval-promoted/run_2026-05-29T13-57-50Z`
- `summary.json`
- `ablation_comparison.json`
- `counterfactual_replay.jsonl`

关键数字：

- Full aggregate `causal_trace_coverage=1.0`
- Full aggregate `required_process_coverage=1.0`
- Full aggregate `counterfactual_tool_selection_change_rate=0.375`
- `no_relationship_edge` change rate `0.25`
- `no_subjective_memory` change rate `0.0`
- `llmEvidence.recordCount=100`

讲法：

> eval 层把复杂 agent 行为转成 before/after 对照。Full 条件保留完整 evidence，移除 memory、relationship 或 evidence link 后，artifact 会记录候选分数、selected tool 或 verdict 的变化。指标只作为复查索引，第一屏展示用具体 case comparison。

### Case C — 高风险工具为什么被阻断

入口：

- `.run/eval-reviewer-packets/audit_reviewer_packet_2026-06-06T08-58-33Z`
- `.run/eval-reviewer-packets/audit_llm_supplement_2026-06-06T10-59-22Z`

关键数字：

- deterministic audit：5 个高风险场景 × 5 个 baseline。
- Real provider smoke：5 场景 × 2 evidence 条件。
- 10/10 cases passed。
- provider usage：18,348 tokens / 0.00351806 USD。
- Full 条件：`coding.apply_patch` 可被允许，source evidence 完整。
- No-policy 条件：转向 `audit.request_policy_review`，verdict 为 `blocked_missing_policy_evidence`。

讲法：

> 高风险工具调用需要执行前 evidence contract。Full evidence 条件下，系统允许具体工具；缺 policy evidence 时，系统转向 safe review tool，并记录阻断原因。这个 case 展示 trace/evidence 语言也能服务 failure analysis。

## 7. 开发流程回忆

### Phase 1：小镇活起来

目标：先做出可运行的 Godot 小镇。

结果：

- `world_main.tscn` 成为默认主场景。
- 玩家移动、NPC 行动、基础交互、地点背景、立绘、小人资源进入 Godot。
- 2026-05-21 通过 Phase 1 手工收口。

简历价值：

- 说明项目有真实运行 surface。
- 说明项目具备真实运行 surface。

### Phase 2：Agent runtime 骨架

目标：让 NPC 决策有动机、工具、观察和状态演化。

结果：

- 后端成为权威世界状态。
- `MotivationEngine -> ToolExecutor -> ResultObserver` 路径落地。
- CapabilityRegistry、ArbitrationLayer、SubjectiveMemoryStore、relationship edges、heuristic seeds 接入。
- `schema_registry.v1` 管理主要 schema。

简历价值：

- 展示 agent runtime architecture。
- 展示复杂状态变更和工具执行边界。

### Phase 2 debug / trace 增量

目标：让行为可解释、可追踪、可复查。

结果：

- `phase2.trace.v1` 覆盖 decision、tool、interrupt、memory、budget events。
- Godot Observer Dock 和 Web Debug 能读 motivation、memory、relationship、heuristics、trace timeline。
- `memory.result_observed`、来源跳转、Copy trace JSON、Prev/Next navigation 等调试功能落地。

简历价值：

- 展示 observability engineering。
- 展示调试复杂 agent 行为的工具思维。

### Eval / artifact pipeline

目标：把复杂行为转成可复查 artifact。

结果：

- `scripts/run_agent_eval.py` 覆盖 process、stability、domain、robustness。
- `.run/eval-promoted/run_2026-05-29T13-57-50Z` 成为 Process Fidelity 主证据。
- 100 条 cloud-backed LLM evidence 进入 promoted artifact。
- archive / promote / drift / manifest / snippets / portfolio verify 形成可维护证据链。

简历价值：

- 展示 eval infra。
- 展示 reproducibility、artifact governance、claim discipline。

### Human Rating pilot gate

目标：判断是否能做人工盲评来支持 believability。

结果：

- 评估发现前提不成立：`hard_delegation` 是 metric stub；memory / relationship ablation 虽进入决策路径，promoted scenarios 中未形成足够强的 `goalToolEvents` 行为分化。
- blind pilot 关闭。
- Process Fidelity 收缩为 evidence / explainability / debug guardrail。

面试讲法：

> 我主动停止了难以支撑的强 claim，把项目保留在可以证明的工程范围内。这展示了工程判断和研究诚实性。

### Audit rescue spike

目标：保留一个可讲清的 failure-analysis case。

结果：

- `backend/app/eval/audit.py` 与 audit export/packet 生成器落地。
- 覆盖 coding patch、destructive file change、data export、model switch、staged rollout 等高风险场景。
- 真实 LLM smoke 通过全 5 场景。

简历价值：

- 展示 high-risk agent tooling。
- 展示 evidence contract、policy verdict、counterfactual evidence removal。

### Portfolio freeze

目标：停止继续扩研究线，把现有资产包装成完整工程展示。

结果：

- README / case cards / snippets / portfolio story / capability map / blog / trace walkthrough 统一成 Agent Behavior Observatory。
- `demo_recording` / `shareable_assets` 标为 `not-accepted`，最终视频/GIF/截图成为可选人工资产。
- `showcase:check` readiness 为 `ready for owner review`。
- 后续只允许包装层、小修复、坏链接维护或主人手工补截图/GIF。

## 8. 可以强调的岗位能力

| 岗位信号 | Loomstead 证据 |
|---|---|
| Agent infra | Agent loop、CapabilityRegistry、ArbitrationLayer、ToolExecutor |
| Observability | trace schema、source links、debug surfaces、Observer Dock |
| Eval systems | process/stability/domain/robustness suites、promoted artifacts |
| Backend systems | Python Agent Server、authority boundary、schema registry、transaction rollback |
| Full-stack | Godot client + backend API + Web Debug + docs/artifacts |
| Reliability / audit | high-risk tool audit harness、policy evidence、safe fallback |
| Research judgment | claim downgrade、human-rating gate closure、honest boundaries |
| Portfolio communication | case-card-first entry、evidence snippets、readiness gate |

## 9. 需要避免的表述

避免这些强 claim：

- “证明了 NPC 行为具有人类认可的可信度”
- “证明了完整因果性”
- “这是企业级 AI Safety 方案”
- “Process Fidelity 可以直接代表 human believability”
- “audit harness 已跨真实生产环境验证”

推荐这些稳健表述：

- “支持 explainability / evidence-completeness / failure-analysis 展示”
- “展示复杂 agent runtime 的可观测性设计”
- “用 counterfactual replay 索引证据缺失后的行为变化”
- “用真实 provider smoke 验证 contract-following 与 evidence-linking 的可行性”
- “项目已诚实收束为 portfolio engineering showcase”

## 10. 如果面试官问“为什么转型”

推荐回答：

> 项目早期有研究化目标，例如 Motivational Delegation 和 Process Fidelity。后来我复查 evidence 后发现，现有 artifact 更适合支持 explainability 和 eval guardrail，无法支撑 human-validated believability 这类强结论。我选择关闭人工盲评和研究扩展，把项目收束为 Agent Behavior Observatory。这个决策保留了最有价值的工程资产：runtime、trace、debug、eval/export、counterfactual replay 和 audit packet，也让项目在求职展示里更清晰、更诚实。

## 11. 关键文件速查

| 用途 | 文件 |
|---|---|
| 第一屏入口 | `README.md` |
| 三张 case card | `docs/portfolio_case_cards.md` |
| 短证据包 | `docs/portfolio_evidence_snippets.md` |
| 最终叙事 | `docs/portfolio_story.md` |
| 岗位能力映射 | `docs/portfolio_capability_map.md` |
| 技术博客长文 | `paper/blog_main.md` |
| Bram / Tomas trace walkthrough | `paper/trace_walkthroughs/figure3_trace_walkthrough_pf_branna_seed01.md` |
| 当前状态 | `docs/current_status.md` |
| 新会话入口 | `docs/agent_context.md` |
| 展示 readiness | `docs/showcase_manifest.md` |
| 录屏计划，已冻结为可选 | `docs/demo_capture_plan.md` |
| Process artifact | `.run/eval-promoted/run_2026-05-29T13-57-50Z` |
| Audit packet | `.run/eval-reviewer-packets/audit_reviewer_packet_2026-06-06T08-58-33Z` |
| LLM audit supplement | `.run/eval-reviewer-packets/audit_llm_supplement_2026-06-06T10-59-22Z` |

## 12. 常用验证命令

```powershell
npm.cmd run context:resume
npm.cmd run context:check
npm.cmd run portfolio:verify
npm.cmd run check
git diff --check
```

面试前如果只想快速确认展示链路：

```powershell
npm.cmd run portfolio:verify
```

该命令会顺序运行 snippets freshness、portfolio entry check、showcase readiness check。

## 13. 最终冻结状态

- 当前项目主张：Agent Behavior Observatory / engineering showcase。
- 当前展示状态：case-card-first 路径完成，`showcase:check` readiness 为 `ready for owner review`。
- 可选人工资产：最终视频、GIF、截图。
- 已停止方向：human rating、大规模 reviewer、跨模型统计扩展、新 audit scenario、Godot UI 指标展示调优。
- 后续维护范围：包装层、小修复、坏链接维护、必要的截图/GIF 手工补充。

## 14. 一句话自我评价

Loomstead 最适合在简历里展示三种能力：**复杂 agent 系统设计、行为可观测性工程、证据边界清晰的 eval / audit 基础设施**。
