---
status: active
owner_lane: research
last_verified: 2026-05-21
startup_load: on-demand
source_of_truth: true
scope: research framing, motivational delegation, process fidelity, baselines, rebuttal map
---

# 研究定位：Motivational Delegation + Process Fidelity Eval

> 本文用于承接 2026-05-20 头脑风暴结论。它不取代 `project_vision.md`、`agent_loop_architecture.md` 或 `production_roadmap.md`，而是定义项目的研究 framing：为什么小镇仍然重要、真正学术卖点是什么、Phase 2 需要新增哪些研究护栏，以及后续如何回答关键反论点。

## 1. 一句话定位

`Loomstead` 是一个 **narrative-primary** 的多 Agent 研究环境，用于研究：当用户目标不能被直接执行、也不能通过硬改最终状态完成时，Director 如何通过动机偏置、事件 Skill、资源/机会调度、信息暴露和约束注入，间接驱动拥有长期记忆与关系的自主 Agent 朝目标演化，并用 Process Fidelity Eval 验证“过程是否可信”。

短句版本：

```text
Motivational Delegation for process-constrained goals in persistent multi-agent narratives.
```

## 2. Framing 决策

### 2.1 Narrative-primary, task-secondary

小镇不是“引言”或“过渡场景”。小镇是第一研究环境，也是最强验证场。

原因：Process Fidelity 需要人类能直觉判断“这个过程像不像真的发生过”。

例如：

- “两名 NPC 结婚”不能只看 `married=true`。
- “布兰娜原谅玩家”不能只看 `forgiven=true`。
- “星灯祭顺利举办”不能只看 `festival_success=true`。

这些目标的价值存在于过程：动机转变、共同经历、误会修复、关系推进、旁观者反应、长期记忆沉淀。小镇场景天然让人类能看出“硬改状态”和“合理发生”的差别。

### 2.2 Task-secondary

跨域任务环境保留，但作为 secondary validation。

软件开发 / Claude Code 工具开发这类任务可以验证框架的可迁移性，但不应反客为主。它更适合证明：同一套 Director / GoalSpec / Trace / Eval 抽象可以离开小镇运行。

首版研究结论优先从叙事社会目标中建立，跨域 adapter 只做接口和一个很小的未来 scenario，不在 Phase 2 大规模实现。

## 3. 真正卖点

### Primary contribution

```text
Motivational Delegation + Process Fidelity Eval
```

即：用户目标不是被中心 Agent 直接执行，也不是被一次性拆成 todo-list，而是被 Director 编译成一组可追踪、可过期、可撤销的间接干预。这些干预改变子 Agent 的动机、机会、信息和约束，使 Agent 自己产生行动链。

### Secondary contribution

```text
统一多层 Agent Runtime 架构
```

统一架构仍然重要，但它是支撑贡献，不是论文主卖点。否则容易被 MetaGPT / ChatDev / Concordia / AutoGen / LangGraph 等系统性工作压住。

## 4. 核心概念定义

### 4.1 Process-constrained Goal

目标不仅包含最终状态，也包含过程约束。

```json
{
  "goal_id": "goal_kai_mira_close_friend",
  "desired_outcome": {
    "relationship_edge": {
      "from": "kai",
      "to": "mira",
      "type": "trusts",
      "min_strength": 0.75
    }
  },
  "process_constraints": [
    "do_not_directly_modify_relationship_edge",
    "require_at_least_two_positive_shared_events",
    "both_agents_must_store_subjective_memories",
    "future_behavior_must_reference_at_least_one_memory"
  ],
  "success_evidence": [
    "event_store_trace",
    "subjective_memory_refs",
    "relationship_edge_delta",
    "future_behavior_change"
  ]
}
```

### 4.2 Motivational Delegation

Director 不直接把子任务交给 Agent，也不直接改最终状态。Director 通过以下干预改变 Agent 的行动分布：

- `motivation_bias`：临时提高某类需求或目标权重。
- `event_skill_load`：加载带约束的事件压力源。
- `opportunity_schedule`：安排可被 Agent 自主利用的机会。
- `resource_shift`：改变资源可得性，但不指定 Agent 必须怎么做。
- `information_exposure`：让某些 Agent 看见或听见特定事件。
- `constraint_injection`：限制捷径或越权工具。
- `evaluation_checkpoint`：阶段性检查目标进展和过程质量。

### 4.3 Process Fidelity

Process Fidelity 衡量“目标达成过程是否像一个可信的多 Agent 世界自然演化出来的结果”。

它至少包含：

- 没有直接硬改最终状态。
- 中间过程满足用户约束。
- Agent 行动与其动机、记忆、关系一致。
- 关键状态变化存在可追踪证据。
- Director 干预不过度、不替 Agent 做决定。
- 旁观 Agent 的反应能长期进入记忆或关系系统。

## 5. 研究问题

### RQ1：为什么不直接 task delegation？

在 process-constrained goals 中，直接 task delegation 是否更容易产生捷径、过度脚本化或缺失社会副作用？

对照：

```text
Hard Delegation Baseline:
Director 将目标反推为显式 todo，并把 todo 直接分配给 NPC。
例如：
1. Kai 去和 Mira 聊天。
2. Kai 送 Mira 礼物。
3. Kai 表白。
```

我们的系统：

```text
Director 不能指定 Kai 必须执行哪个动作。
它只能改变 Kai 的 motivation / opportunity / information / event context。
Kai 是否行动、如何行动、是否失败，由 Agent loop 仲裁决定。
```

预期差异：Hard Delegation 的 goal success 可能较高，但 shortcut violation、forced_action_rate、low autonomy、process believability 低。

### RQ2：关系记忆真的影响最终结果吗？

必须用 ablation 回答，不能只展示漂亮 memory UI。

需要设计“关系记忆是必要条件”的 scenario：

```text
Scenario: Branna Forgiveness
玩家曾经失信，Branna 对玩家 trust 降低。
目标是让 Branna 原谅玩家。
如果系统没有长期关系记忆，Branna 不知道为什么生气，也无法判断补偿是否足够。
```

实验：

- Full system：主观记忆 + 关系边 + recall。
- No relationship memory：关闭关系边参与决策。
- Shuffled memory owner：把记忆随机分配给错误 NPC。
- No evidence link：关系边保留，但 source_event_ids 清空。

如果 Full 相比 ablation 在 goal_success、relationship_consistency、process_fidelity 上没有显著差异，则不能声称关系记忆是核心贡献，只能降级为可解释/展示层。

### RQ3：和 Generative Agents / Smallville 比，新在哪？

不要声称“我们也有记忆、反思、社交模拟”是新意。

新意应表述为：

```text
Generative Agents 主要研究 believable simulation：Agent 如何记忆、反思、计划并产生可信社会行为。
Loomstead 研究 goal-conditioned orchestration：用户给出过程约束目标后，Director 如何通过间接动机干预推动多 Agent 世界朝目标演化，并如何评估过程保真度。
```

换句话说：

- Smallville 的重点是模拟可信人类行为。
- Loomstead 的重点是“目标 → 间接干预 → 多主体反应 → 过程保真评估”。

## 6. Baseline Matrix

| Baseline | 描述 | 主要用于证明 |
| --- | --- | --- |
| Direct State Setter | 直接修改最终状态，例如 `married=true` / `trust=0.8` | 区分真完成与假完成 |
| Static Todo Planner | 一次性生成 todo-list，Agent 按列表执行，不动态重规划 | 证明动态干预和反馈循环必要 |
| Hard Delegation | Director 把明确子任务直接委派给 NPC，NPC 作为 worker 执行 | 回答“为什么不直接 task delegation” |
| Director w/o Subjective Memory | 保留 Director 干预，关闭主观记忆/关系边参与决策 | 证明关系记忆不是装饰 |
| Director w/o Event Skill | 保留动机偏置，关闭事件 Skill | 证明事件压力源对复杂过程有贡献 |
| Full Motivational Delegation | 完整系统 | 目标方法 |

## 7. Metric Families

### 7.1 Goal Achievement

- `goal_success_rate`
- `milestone_completion_rate`
- `time_to_goal`
- `blocked_goal_detection_rate`

### 7.2 Process Fidelity

- `shortcut_violation_rate`
- `required_process_coverage`
- `state_transition_legality`
- `process_believability_score`

### 7.3 Delegation / Autonomy

- `forced_action_rate`
- `agent_initiated_action_ratio`
- `goal_internalization_rate`
- `intervention_overreach_rate`

### 7.4 Memory Causality

- `relationship_memory_causal_use_rate`
- `memory_grounding_precision`
- `evidence_link_coverage`
- `memory_ablation_delta`

### 7.5 Trace / Explainability

- `causal_trace_coverage`
- `causal_trace_depth_avg`
- `intervention_to_outcome_attribution`
- `debug_trace_replay_success_rate`

### 7.6 Side Effects

- `unintended_relationship_delta`
- `negative_memory_spillover`
- `social_side_effect_score`

## 8. Phase 2 增补项

当前 Phase 2 计划基本不需要大改。只新增三项硬护栏：

1. 新增研究文档：本文，或拆分为 `research_framing_motivational_delegation.md`。
2. 新增跨域 adapter 接口：保证小镇是 primary domain，但核心抽象可移植。
3. Eval 增加 hard delegation baseline：不能只和 direct setter / no-memory 对比。

此外，Phase 2 必须把 ablation 数据当作硬验收，不允许 Eval 退化成 sanity check。

## 9. 最小可行实验集

### E1：Close Friend Goal

目标：让 Kai 与 Mira 发展到 close_friend，禁止直接修改关系边。

必须证据：

- 至少 2 个 positive shared events。
- 双方 subjective memory 中都有事件记录。
- 关系边 source_event_ids 可追溯。
- 第二天至少一次行为由该记忆或关系边影响。

### E2：Forgiveness Goal

目标：让 Branna 原谅玩家的一次失信行为。

必须证据：

- 系统保留失信记忆。
- 玩家补偿行为被 Branna 观察或确认。
- 原谅不是直接写入，而是关系边从 distrust → repaired。
- 无关系记忆 ablation 下结果明显退化。

### E3：Festival Success Goal

目标：星灯祭成功举办，并让至少 3 个 NPC 形成不同主观记忆。

必须证据：

- festival_success 不由 direct setter 产生。
- Event Skill 激活并施加资源/社会压力。
- 至少 3 个 NPC 的 memory 具有可量化 divergence。
- 事件后至少一个 NPC 的后续行为引用该记忆。

## 10. 目标 venue 现实定位

第一目标应是 workshop / demo / datasets-and-evaluation 类型，而不是直接 full paper。

推荐表述：

```text
A research prototype and benchmark environment for evaluating motivational delegation and process fidelity in persistent multi-agent narratives.
```

适配方向：

- AAMAS workshop：EMAS / EXTRAAMAS / MABS / agent evaluation 相关 workshop。
- Evaluations & Datasets 类型 track：重点包装为 evaluation methodology + benchmark environment + public traces。
- arXiv 技术报告：用于抢先公开 framing、指标和 baseline。

## 11. Non-goals

- 不做通用多 Agent 操作系统。
- 不和 coding agent 产品拼任务完成速度。
- 不以“统一架构”作为 primary novelty。
- 不把小镇降级为开场 demo。
- 不声称关系记忆有用，除非 ablation 数据支持。

## 12. 成功判据

Phase 2 研究向收口至少要产出：

```text
1. 3 个 process-constrained goal specs。
2. 5 个 baseline / ablation 配置。
3. 每个 scenario 至少 5 次种子运行，成本允许时扩到 10 次。
4. 每次运行导出 EventStore、SubjectiveMemory、RelationshipEdges、Interventions、EvalSummary。
5. 一张 ablation 表能回答：
   - 为什么不直接 task delegation？
   - 关系记忆是不是装饰？
   - 与 Smallville 类模拟相比，新问题在哪？
```
