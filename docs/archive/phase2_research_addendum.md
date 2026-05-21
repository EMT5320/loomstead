---
status: archived
owner_lane: planning
last_verified: 2026-05-20
startup_load: never
source_of_truth: false
scope: 一次性 patch notes，2026-05-20 已应用并归档
---

# Phase 2 研究向增补 Patch Notes（已归档）

> **2026-05-20 归档说明**：本文内容已应用到 `docs/project_vision.md`、`docs/production_roadmap.md`、`docs/agent_loop_architecture.md`、`docs/README.md` 与 `AGENTS.md`。研究 framing 长期事实源为 `docs/research_framing_motivational_delegation.md`、`docs/process_fidelity_eval_spec.md` 与 `docs/cross_domain_adapter.md`。本文仅保留作历史溯源，不得作为当前事实源。
>
> 原文：本文不是长期事实源；它是一次性修改指南。应用后，把核心内容并入对应文档，再将本文删除或归档。

## 1. `project_vision.md` 建议修改

### 1.1 一句话定位替换建议

当前：

```text
Agent Valley 是一个可解释的多 Agent 叙事运行时...
```

建议改为：

```text
Agent Valley 是一个 narrative-primary 的可解释多 Agent 叙事运行时与研究环境：通过 Director / Event Skill、主观记忆、关系演化、启发式学习与 Debug Trace，研究 Director 如何以 Motivational Delegation 的方式间接驱动少量深度 NPC 朝过程约束目标演化，并用 Process Fidelity Eval 验证“目标达成过程是否可信”。
```

### 1.2 差异化定位新增段落

```text
2026-05-20 研究 framing 更新：小镇不再被描述为“通用架构的引言”，而是 primary validation domain。Process Fidelity 需要人类能直觉判断过程是否合理的场景；恋爱、和解、节日、信任修复和谣言传播这类叙事目标天然暴露“直接硬改状态”和“可信过程演化”的区别。跨域任务环境保留为 secondary validation，用于证明 GoalSpec / Intervention / Trace / Eval 抽象具备迁移可能，但不反客为主。
```

### 1.3 核心创新点新增两项

放在 Eval Framework 前后均可：

```text
### Motivational Delegation（动机委派）

用户目标不会被 Director 直接执行，也不会被拆成硬性 todo-list 分配给 NPC。Director 只能通过 motivation_bias、event_skill_load、opportunity_schedule、resource_shift、information_exposure、constraint_injection 等间接干预改变 Agent 的行动分布。NPC 是否接受、如何行动、是否失败，由自身动机、记忆、关系和 ArbitrationLayer 决定。

### Process Fidelity Eval（过程保真评估）

Eval 不只判断最终状态是否达成，还判断过程是否可信：是否绕过了中间过程、是否强制 Agent 行动、关键关系变化是否有记忆证据、Director 是否过度干预、Agent 行为是否与其长期记忆和关系一致。该体系用于回答“为什么不直接 task delegation”以及“关系记忆是否真的影响结果”。
```

## 2. `production_roadmap.md` 建议修改

### 2.1 Phase 2 核心目标增补

在 4.1 后新增：

```text
2026-05-20 研究向增补：Phase 2 保持原骨架计划不大改，但必须加入三项研究护栏：

1. 研究文档：明确 narrative-primary / task-secondary、Motivational Delegation、Process Fidelity Eval、核心反论点和 baseline matrix。
2. 跨域 adapter 接口：抽象 GoalSpec / Intervention / Observation / EvalTrace，保证小镇是 primary domain，同时保留 task-secondary 可迁移路径。
3. Hard Delegation baseline：在 Eval 中加入“直接任务委派 / todo-list”对照，严肃回答为什么不用传统 task delegation。
```

### 2.2 Phase 2 骨架清单新增行

加入表格：

```text
| ResearchFraming | Motivational Delegation + Process Fidelity Eval 研究文档 | `docs/research_framing_motivational_delegation.md` |
| DomainAdapter | GoalSpec / Observation / Intervention / EvalTrace 抽象接口 | `backend/app/domain/base.py`, `docs/cross_domain_adapter.md` |
| ProcessFidelityEval | 过程保真指标 + hard delegation baseline + ablation protocol | `backend/app/eval/process_fidelity.py`, `docs/process_fidelity_eval_spec.md` |
```

### 2.3 Phase 2 收口标准增补

当前 4.5 后新增：

```text
研究向硬验收：

- 至少 3 个 process-constrained GoalSpec。
- 至少 1 个 Hard Delegation baseline 可运行。
- 至少 1 个关系记忆 ablation 可运行：No Subjective Memory / No Relationship Edge / Shuffled Memory Owner 三选一。
- Eval 输出 mean/std/n，不只输出 pass/fail。
- 至少 1 张 ablation_comparison.json 能比较 Full vs Hard Delegation vs No Memory。
- 任意关键目标状态变化必须能追溯到 source_event_ids 或 trace_refs。
```

## 3. `agent_loop_architecture.md` 建议修改

### 3.1 Eval Framework 中新增 baseline

在 10.2 / 10.3 之间加入：

```text
Hard Delegation baseline：Director 将目标反推为显式 todo，并把 todo 直接委派给 NPC 执行。它代表传统 task delegation / parent-worker agent 模式，是 Phase 2 必须加入的强 baseline。Full 系统如果只比 direct setter 强，不足以证明 Motivational Delegation 的价值；必须证明在 process fidelity、agent autonomy、side effect、relationship memory causal use 等指标上优于 Hard Delegation。
```

### 3.2 核心指标新增

```python
process_fidelity_score: float
shortcut_violation_rate: float
forced_action_rate: float
agent_initiated_action_ratio: float
intervention_overreach_rate: float
relationship_memory_causal_use_rate: float
memory_ablation_delta: float
side_effect_score: float
```

## 4. `docs/README.md` 建议新增

在核心文档列表中加入：

```text
- `research_framing_motivational_delegation.md`：研究定位与核心反论点，定义 narrative-primary / task-secondary、Motivational Delegation、Process Fidelity Eval。
- `process_fidelity_eval_spec.md`：研究向 Eval 指标、hard delegation baseline、ablation protocol、dataset 输出规格。
- `cross_domain_adapter.md`：跨域 adapter 接口，保证小镇 primary，同时为 task-secondary 验证保留路径。
```

## 5. `package.json` scripts 建议

```json
{
  "scripts": {
    "eval:rule": "python scripts/run_agent_eval.py --provider rule --suite default",
    "eval:process": "python scripts/run_agent_eval.py --provider rule --suite process_fidelity",
    "eval:ablate": "python scripts/run_agent_eval.py --provider rule --suite process_fidelity --run-ablation",
    "eval:delegation": "python scripts/run_agent_eval.py --provider rule --suite process_fidelity --baseline hard_delegation"
  }
}
```
