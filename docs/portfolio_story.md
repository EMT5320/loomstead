---
status: active
owner_lane: portfolio-showcase
last_verified: 2026-06-06
startup_load: on-demand
source_of_truth: true
scope: Loomstead 最终展示叙事：Agent Behavior Observatory 与 3 张 case card
---

# Loomstead Portfolio Story

> 自管理层文档，软上限 250 行。用途：冻结 Loomstead 的最终展示叙事，避免继续掉进“指标难展示 -> 前端继续调 -> 需要人工 review”的循环。

## 1. 最终定位

**Loomstead: Agent Behavior Observatory**

一句话：

> 一个以可观测性为核心的多 Agent 运行时：从 NPC 决策、记忆、关系，到工具调用、LLM 输出和审计报告，都能端到端追踪。

英文组合：

> An observability-first multi-agent runtime for debugging, tracing, and evaluating autonomous behavior in a simulated town.

展示重点：小镇是行为场景，真正资产是 agent runtime + trace schema + eval/export + audit/failure-analysis pipeline。

## 2. 主动放弃的讲法

- Loomstead 不再作为 human-believability 论文项目推进。
- Process Fidelity 指标只保留 evidence / explainability 层含义。
- Audit spike 只保留为 failure-analysis 展示资产。
- Godot 前端不再为解释指标继续大改。
- 不再推进 reviewer 大规模评分。

保留讲法：

- Agent orchestration：复杂 agent loop 如何组织。
- Observability：行为证据如何被记录、链接、检索。
- Eval infrastructure：如何把复杂行为转成可复查 artifact。
- Failure analysis：缺证据、断链接、shortcut 行为如何被暴露。

## 3. 3 张展示卡

### Card A — Why did this NPC choose that action?

素材来源：Godot Observer Dock / `/api/debug.phase2` / Figure 3 trace walkthrough。

展示结构：

1. NPC 当前动机、记忆、关系。
2. 候选工具和分数。
3. `sourceEventIds` / `traceRefs` 指向影响决策的证据。
4. 选中动作和结果观察。

一句话 takeaway：

> Loomstead exposes why an agent acted, beyond the final action itself.

### Card B — What changed when evidence was removed?

素材来源：Process Fidelity / domain adapter / counterfactual replay artifact。

展示结构：

1. Full 条件下的选中动作。
2. 移除 memory / relationship / evidence link。
3. 候选分数、selected tool 或 verdict 变化。
4. 指标只作为复查索引，不作为主展示。

一句话 takeaway：

> Counterfactual replay turns opaque agent behavior into a debuggable evidence-difference story.

### Card C — Why was this high-risk tool call blocked?

素材来源：

- `.run/eval-reviewer-packets/audit_reviewer_packet_2026-06-06T08-58-33Z`
- `.run/eval-reviewer-packets/audit_llm_supplement_2026-06-06T10-59-22Z`

展示结构：

1. 高风险工具调用需要哪些 evidence。
2. Full 条件：证据齐全，允许高风险工具。
3. No Policy Evidence 条件：缺 policy evidence，转向 safe review tool。
4. raw JSON 放在附录，主展示只看 case comparison。

一句话 takeaway：

> The audit harness shows how missing evidence changes tool decisions before risky execution.

## 4. 当前可引用资产

| 展示面 | 首选材料 | 用法 |
|---|---|---|
| Runtime | `backend/app/runtime/`、`docs/agent_loop_architecture.md` | 讲系统架构 |
| Trace | `phase2.trace.v1`、`GET /api/debug.phase2`、Godot Observer Dock | 讲可观测性 |
| Eval | `.run/eval-promoted/run_2026-05-29T13-57-50Z`、`scripts/run_agent_eval.py` | 讲可复查 artifact pipeline |
| Audit | audit v2 packet + LLM supplement | 讲 failure analysis |
| Visual | `paper/generated/figures/*.png`、Godot ShowcasePanel | 讲架构与截图 |

## 5. 面试讲法

30 秒版：

> Loomstead started as a narrative multi-agent town. I reframed it as an agent behavior observatory. The strongest part is the infrastructure around the agents: structured traces, source evidence links, debug surfaces, eval exports, counterfactual replay, and audit packets. It demonstrates how I design and debug complex LLM-agent systems with observable behavior, backed by case cards and trace artifacts.

2 分钟版：

> The backend owns the world state and runs a MotivationEngine -> ToolExecutor -> ResultObserver loop. NPCs have subjective memories, relationship edges, heuristics, and legal tool choices. Every meaningful decision emits trace events with sourceEventIds and traceRefs, so the system can answer why an action happened. On top of that I built eval and audit harnesses: process-fidelity checks, robustness runs, archive manifests, and high-risk tool audit scenarios. The final claim is an engineering one: this is a working observability stack for complex agent behavior.

## 6. 冻结规则

- 只做包装层和小修复。
- 不扩研究实验。
- 不扩指标。
- 不扩 Godot UI。
- 不再投入 human rating / large reviewer study。
- 需要展示时优先用 case card、架构图、trace 摘要。

## 7. 下一步边界

如果后续要投入新工作，只允许两类：

1. 求职材料级别：README、portfolio story、1-2 张图、少量 case card 文案。
2. 维护级别：修复坏命令、坏链接、坏 artifact。

其余研究推进转到 `AlgoCoach-Flywheel` 或新的更清晰研究项目。
