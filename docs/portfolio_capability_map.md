---
status: active
owner_lane: portfolio-showcase
last_verified: 2026-06-06
startup_load: on-demand
source_of_truth: true
scope: Loomstead 求职展示 capability map：Agent Behavior Observatory、能力栈、面试讲法、诚实边界
---

# Loomstead Portfolio Capability Map

> 自管理层文档，软上限 250 行。用途：把 Loomstead 现有资产串联成展示入口，主张收束为 Agent Behavior Observatory。

## 1. 一句话定位

- 中文：一个**面向复杂 Agent 行为调试与审计的可观测叙事运行时**，用 Godot 小镇承载 NPC 行为，用 Python runtime 记录动机、记忆、关系、工具调用、LLM 输出和 eval artifact。
- EN：*An observability-first multi-agent runtime for debugging, tracing, and evaluating autonomous behavior in a simulated town.*

最终展示主张：

> Loomstead 展示 agent behavior observability；believability 只作为历史背景和明确边界。

## 2. 能力栈 -> 证据 -> 岗位信号

| 能力栈 | 具体资产 | 岗位信号 |
|---|---|---|
| **Agent runtime architecture** | `MotivationEngine -> ToolExecutor -> ResultObserver` tick 主路径；Director v0 + Event Skill；ToolDefinition / CapabilityRegistry / ArbitrationLayer；subjective memory、relationship edge、heuristics。 | Agent infra / LLM application engineer |
| **Behavior observability** | `phase2.trace.v1`、`sourceEventIds`、`traceRefs`、`candidateScores`、`scoreComponentSourceRefs`、Godot Observer Dock、Web Debug。 | Observability / debugging tools / platform engineer |
| **Eval infrastructure** | `scripts/run_agent_eval.py` 覆盖 process / stability / determinism / domain / robustness；manifest-backed exports；promoted artifacts；drift notes。 | Eval infra / ML systems / research engineer |
| **Failure analysis / audit artifacts** | `backend/app/eval/audit.py`、`audit.go_no_go.v1`、counterfactual evidence removal、v2 reviewer packet、real LLM smoke supplement。 | Agent reliability / safety tooling / backend systems |
| **Full-stack integration** | Python Agent Server + Godot 4 client + Web Debug + OpenAI-compatible provider + schema registry。 | Full-stack / backend / systems engineer |

## 3. 三个展示案例

### A. NPC 行为为什么发生

- 入口：Godot Observer Dock、`/api/debug.phase2`、Figure 3 trace walkthrough。
- 讲法：从动机、记忆、关系、候选工具分数追到 selected action。
- 边界：不要把它讲成玩家一定会觉得 believable。

### B. 移除证据后发生什么

- 入口：Process Fidelity / counterfactual replay / domain adapter artifacts。
- 讲法：展示证据移除如何改变候选分数、工具选择或 verdict。
- 边界：指标作为复查索引，case card 承担第一屏解释。

### C. 高风险工具调用如何被阻断

- 入口：`.run/eval-reviewer-packets/audit_llm_supplement_2026-06-06T10-59-22Z`。
- 讲法：Full evidence 允许执行；No Policy Evidence 进入 safe review tool。
- 边界：不要宣称企业级安全或跨域有效性。

## 4. 面试 talking points

- **系统设计**：后端持有权威世界状态，Godot 做表现层，agent loop 与工具执行在 Python runtime 内有清晰边界。
- **可观测性设计**：决策时写 trace，trace 带 `sourceEventIds` 和 `traceRefs`，后续 Debug / Eval / Audit 共用同一套证据语言。
- **评测工程**：每条 evidence、baseline、export 都有 manifest 和 archive 检查，支持复查。
- **研究素养**：主动降级 claim，保留能证明的工程事实，停止扩张难以验证的 believability / safety 论断。
- **项目复盘**：最终把复杂系统从“论文证明型”收束为“agent behavior observability 展示型”，让资产更适合面试和工程讨论。

## 5. 诚实边界

- 当前结果支持工程展示，不支持 human-validated believability。
- Process Fidelity 只作为 evidence / explainability 层指标，无法承载强因果证明。
- Audit spike 只作为 failure-analysis artifact，无法承载完整 AI Safety 方法。
- Godot 视觉展示作为 live surface，核心讲法依赖 case card 和 trace 摘要。
- 项目冻结后不再扩研究实验、指标和 UI。

## 6. 与 AlgoCoach 的分工

- **AlgoCoach-Flywheel**：求职 + 论文主力，偏 post-training / verifier-backed eval / model improvement loop。
- **Loomstead**：第二展示项目，偏 agent runtime / observability / eval artifact / full-stack integration。

简历叙事：

> AlgoCoach demonstrates model-training and verifier-backed improvement. Loomstead demonstrates agent-system architecture and observability engineering.

## 7. 当前收束状态

- 保留：runtime、trace、eval、audit harness、v2 packet、LLM supplement、portfolio story。
- 丢弃：冗余旧 packet、继续扩实验、人工大规模 review 计划。
- 冻结：只允许包装层、小修复和坏链接维护。
