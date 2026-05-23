---
status: active
owner_lane: eval
last_verified: 2026-05-23
startup_load: on-demand
source_of_truth: true
scope: process fidelity metrics, hard delegation baseline, ablation protocol, dataset outputs
---

# Process Fidelity Eval 规格

> 本文扩展 `agent_loop_architecture.md` 的 Eval Framework。原 Eval 偏 Agent loop 正确性与可解释性；本文新增研究向指标：Process Fidelity、Motivational Delegation、Hard Delegation baseline、关系记忆因果性 ablation。

## 1. 设计目标

Eval 需要超越 sanity check。它必须回答三个审稿级问题：

```text
Q1. 为什么不直接 task delegation？
Q2. 关系记忆真的影响结果吗？
Q3. 与已有 generative agents / social simulation 相比，我们评估的新能力是什么？
```

因此 Eval 必须同时覆盖：

- 最终目标是否达成。
- 过程是否满足约束。
- Director 是否越权。
- 子 Agent 是否保留自主性。
- 记忆和关系边是否真的影响后续行为。
- Debug Trace 是否能复盘因果链。

## 2. Eval 输入输出

### 2.1 输入

```json
{
  "scenario_id": "E1_close_friend_goal",
  "goal_spec": "configs/goals/e1_close_friend.json",
  "baseline": "full_motivational_delegation",
  "seed": 1,
  "max_game_hours": 24,
  "provider": "rule",
  "ablation": []
}
```

### 2.2 输出目录

当前本地导出根目录默认为 `.run/eval-runs/`；可通过 `--export-dir <path>` 覆盖。

Process suite 导出结构：

```text
.run/eval-runs/run_YYYY-MM-DDTHH-MM-SSZ/
├── summary.json
├── ablation_comparison.json
├── manifest.json
├── per_scenario/
│   ├── E1_close_friend_goal_full_motivational_delegation.json
│   └── E1_close_friend_goal_hard_delegation.json
├── intervention_trace.jsonl
├── goal_progress_trace.jsonl
├── counterfactual_replay.jsonl
└── memory_ablation_trace.jsonl
```

Stability suite 导出结构：

```text
.run/eval-runs/stability_YYYY-MM-DDTHH-MM-SSZ/
├── summary.json
├── stability_trace.jsonl
├── final_evidence.json
└── manifest.json
```

`manifest.json` 当前使用 `phase2.eval_manifest.v1`，至少包含：

- `exportKind`、`createdAt`、`suite`、`baseline`、`ok` 和 `runDirName`。
- Git 快照：`commit`、`shortCommit`、`branch`、`dirty`、`statusShort`。
- `schemaRegistry` 快照，当前由 `backend/app/runtime/schema_registry.py` 生成。
- `metricIds`、`baselines`、`scenarioIds`。
- `artifacts[]`：每个导出文件的相对 `path`、`kind`、`bytes`、`sha256`；JSONL 文件额外记录 `rowCount`。

### 2.3 本地导出索引与归档

`npm.cmd run eval:archive:check` 会读取 `.run/eval-runs/*/manifest.json`，复核 manifest 版本、run 目录名、artifact `bytes`、`sha256` 和 JSONL `rowCount`。

`npm.cmd run eval:archive:index` 会写入 `.run/eval-runs/index.json`，生成 `phase2.eval_run_index.v1` 索引，并按 suite 给 run 标记 `keep_latest` 或 `historical_candidate`。当前工具只标记保留建议，不自动删除或搬运 run。完整策略见 `docs/eval_dataset_archive.md`。

`npm.cmd run eval:archive:drift` 会写入 `.run/eval-runs/drift_report.json`，比较每个 suite 最新两次 run 的 metric、baseline、scenario、schema 和 artifact 数量变化。

`npm.cmd run eval:archive:promote -- <runDirName>` 会把已校验 run 复制到 `.run/eval-promoted/`，并写入 `phase2.eval_promotion.v1` 记录；若导出时 `git.dirty=true` 或 drift 缺少解释，promotion 状态会保持 `needs_manual_review`。

## 3. Baseline 定义

### 3.1 Direct State Setter

直接修改最终状态。

示例：

```python
world.relationship_edges.upsert("kai", "mira", "trusts", strength=0.8)
```

预期：goal_success 高，process_fidelity 极低，shortcut_violation 高。

### 3.2 Static Todo Planner

开始时生成 todo-list，后续不根据 Agent 反应重规划。

示例：

```text
1. Kai talk_with Mira
2. Kai give_gift Mira
3. Kai ask_for_help Mira
```

预期：在简单任务表现可接受，在复杂动态关系中遇到失败后恢复差。

### 3.3 Hard Delegation

Director 将目标拆为明确子任务并委派给具体 Agent。NPC 作为 worker 接收任务。

示例：

```json
{
  "delegation": {
    "assignee": "kai",
    "task": "increase_mira_affection",
    "required_actions": ["social.chat_with", "social.give_gift"],
    "deadline": "day1.evening"
  }
}
```

这个 baseline 是关键对照，用来代表传统 task delegation / todo-list agent 思路。

预期：goal_success 可能高，但 forced_action_rate、director_overreach_rate、process_believability_score 差。

### 3.4 Director w/o Subjective Memory

保留 Director 干预和 Event Skill，但 Agent 决策时无法召回 subjective memory；relationship edge 由独立 ablation 覆盖。

预期：涉及信任、失信、补偿、谣言传播的 scenario 中退化明显。

### 3.5 Full Motivational Delegation

Director 只允许间接干预：motivation bias、event skill、opportunity schedule、resource shift、information exposure、constraint injection、evaluation checkpoint。

Agent 是否行动由 MotivationEngine + ArbitrationLayer 决定。

## 4. Metric 公式

### 4.1 Goal Success

```python
goal_success = all(success_evidence_satisfied)
```

不允许仅靠最终 state 判断。`success_evidence` 必须包含 trace 证据。

### 4.2 Shortcut Violation Rate

```python
shortcut_violation_rate = shortcut_events / total_goal_relevant_state_changes
```

Shortcut 例子：

- 直接修改 relationship stage。
- 直接设置 married / forgiven / festival_success。
- 生成无 source_event_ids 的关键关系边。
- NPC 未观察/未得知事件却引用该事件。

### 4.3 Required Process Coverage

```python
required_process_coverage = satisfied_process_constraints / total_process_constraints
```

每条 constraint 必须是可验证谓词，不允许只写自然语言。

### 4.4 Forced Action Rate

```python
forced_action_rate = actions_with_explicit_director_assignment / goal_relevant_agent_actions
```

Full Motivational Delegation 中该值应接近 0。Hard Delegation 中会显著更高。

### 4.5 Agent-Initiated Action Ratio

```python
agent_initiated_action_ratio = actions_selected_by_arbitration / goal_relevant_agent_actions
```

被 Director 允许、诱导、提供机会，但最终由 ArbitrationLayer 选择的行动，算 agent-initiated。

### 4.6 Intervention Overreach Rate

```python
intervention_overreach_rate = overreaching_interventions / total_interventions
```

Overreach 包括：

- 直接指定 NPC 必须执行某动作。
- 直接改内部情感或关系强度。
- 直接指定对话结果。
- 绕过 ToolExecutor 修改世界状态。

### 4.7 Relationship Memory Causal Use Rate

```python
relationship_memory_causal_use_rate = decisions_with_relationship_memory_contribution / relationship_relevant_decisions
```

要求：Decision trace 的 `contributing_sources.memory_relevance` 或 `relationship_edge_refs` 对 winner tool 的分数有实际贡献。

仅仅“检索到了记忆”不算 causal use。必须证明如果去掉该记忆，winner 会变化或分数差距显著缩小。

### 4.8 Memory Ablation Delta

```python
memory_ablation_delta = metric_full - metric_no_relationship_memory
```

重点比较：

- `goal_success_rate`
- `required_process_coverage`
- `relationship_consistency`
- `process_believability_score`
- `relationship_memory_causal_use_rate`

### 4.9 Causal Trace Coverage

```python
causal_trace_coverage = state_changes_with_source_event_ids / goal_relevant_state_changes
```

关键状态变化必须能追到：

```text
intervention -> event -> subjective_memory -> relationship_edge/heuristic -> later_decision -> outcome
```

### 4.10 Process Believability Score

自动指标 + 少量人工评分。

自动部分：

```python
auto_believability = weighted_mean([
    1 - shortcut_violation_rate,
    required_process_coverage,
    agent_initiated_action_ratio,
    causal_trace_coverage,
    relationship_consistency,
])
```

人工部分用于研究报告，不进入 CI：

```text
1 = 明显硬改/脚本化
2 = 有部分过程，但很多跳跃
3 = 基本合理
4 = 过程自然，有可理解动机
5 = 非常自然，像角色自己发展出来的结果
```

## 5. Ablation Protocol

### 5.1 最小 ablation 集

```text
A0 Full Motivational Delegation
A1 Direct State Setter
A2 Static Todo Planner
A3 Hard Delegation
A4 No Subjective Memory
A5 No Relationship Edge in Arbitration
A6 Shuffled Memory Owner
A7 Evidence-Link Removal
A8 No Event Skill
```

### 5.2 运行次数

Phase 2 alpha：每 scenario 每 baseline 至少 5 个 seed。

Phase 3 研究报告：每 scenario 每 baseline 至少 10 个 seed。若使用 cloud LLM，记录 provider、model、temperature、cost、latency。

### 5.3 统计输出

`summary.json` 至少包含：

```json
{
  "metric": "process_believability_score",
  "mean": 0.74,
  "std": 0.08,
  "n": 10,
  "baseline": "full_motivational_delegation",
  "scenario_id": "E1_close_friend_goal"
}
```

Phase 2 可以先不给显著性检验，但必须有均值、方差、样本数。

## 6. 关系记忆是否装饰：专项测试

### 6.1 Memory Necessary Scenario

设计原则：没有记忆时不能合理完成。

例子：

```text
Branna 因玩家失信降低 trust。
玩家后续做补偿。
Branna 是否原谅，必须取决于：
1. 她是否记得失信事件。
2. 她是否观察到补偿事件。
3. 她是否能把两个事件连接成 repair narrative。
```

### 6.2 Shuffled Memory Owner

将 Branna 的失信记忆转移给 Kai，保留事件总量不变。

如果结果仍然一样，说明系统没有真正使用“谁记得什么”。

### 6.3 Evidence-Link Removal

保留 relationship edge，但删除 `source_event_ids` / `trace_refs`。

如果 Debug Trace 仍声称能解释关系变化，则 trace 机制不可信。

### 6.4 Counterfactual Replay

对一次已完成运行，重放时删除某条关键 memory，重新计算 Arbitration winner。

```python
counterfactual_effect = selected_tool_original != selected_tool_without_memory
```

这比只看最终成功率更能证明记忆对单次决策有因果作用。

## 7. Process Fidelity GoalSpec Schema

```json
{
  "goal_id": "E1_close_friend_goal",
  "description": "Kai and Mira become close friends through believable shared experiences.",
  "desired_outcome": {
    "relationship_edge": {
      "from": "kai",
      "to": "mira",
      "edge_type": "trusts",
      "min_strength": 0.75
    }
  },
  "forbidden_shortcuts": [
    "direct_relationship_set",
    "force_dialogue_outcome",
    "manual_memory_insert_without_event"
  ],
  "required_process": [
    {
      "id": "two_positive_shared_events",
      "predicate": "count(shared_events(kai, mira, valence='positive')) >= 2"
    },
    {
      "id": "both_subjective_memories",
      "predicate": "has_memory(kai, shared_event) && has_memory(mira, shared_event)"
    },
    {
      "id": "future_behavior_reference",
      "predicate": "exists(decision where memory_ref in shared_event_memories)"
    }
  ],
  "allowed_interventions": [
    "motivation_bias",
    "event_skill_load",
    "opportunity_schedule",
    "information_exposure",
    "resource_shift",
    "constraint_injection"
  ],
  "success_evidence": [
    "relationship_edge_delta",
    "subjective_memory_refs",
    "causal_trace",
    "future_behavior_reference"
  ]
}
```

## 8. Phase 2 验收升级

Phase 2 不达成以下条件，不进入 Phase 3：

```text
1. 至少 3 个 process-constrained GoalSpec。
2. 至少 1 个 Hard Delegation baseline 可运行。
3. 至少 1 个记忆专项 ablation 可运行。
4. Eval 输出包含 mean/std/n，而不只是 pass/fail。
5. 至少 1 张 ablation_comparison.json 能展示 Full vs Hard Delegation vs No Subjective Memory / No Relationship Edge 的差异。
6. 所有关键状态变化都有 source_event_ids 或 trace_refs。
```
