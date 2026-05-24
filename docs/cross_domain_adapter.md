---
status: active
owner_lane: research-runtime
last_verified: 2026-05-24
startup_load: on-demand
source_of_truth: true
scope: cross-domain adapter interface, narrative primary boundary, optional task domain portability
---

# 跨域 Adapter 接口：Narrative-primary, Task-secondary

> 本文定义跨域 adapter 的最小接口，用于让 `Loomstead` 的核心研究抽象离开小镇后仍可验证。小镇仍是 primary domain；task / coding domain 只作为 secondary validation。

## 1. 设计原则

1. 小镇是第一研究环境，承担 primary validation 责任。
2. Adapter 只抽象“目标、干预、观察、评估”四件事。
3. 核心 Runtime 不依赖具体场景名词，例如 crop、festival、tavern。
4. 任何新 domain 都必须支持 EventStore、AgentState、Memory、Relationship / Dependency Graph、ToolExecutor、EvalTrace。
5. Phase 2 实现接口、narrative adapter、coding skeleton 和 7 个 coding dry-run scenario。

当前实现状态（2026-05-24）：`backend/app/domain/base.py` 已落地 shared dataclasses、`DomainAdapter` Protocol、`DEFAULT_TOWN_DOMAIN` / `DEFAULT_CODING_DOMAIN` metadata；`backend/app/domain/narrative/adapter.py` 已接入 3 个 narrative GoalSpec 和现有 AgentRuntime 主路径；`backend/app/domain/coding/adapter.py` 已提供 7 个 repo fixture scenario，加载确定性外部仓库快照，生成 patch、patched file hash、本地 git 源仓库 checkout、fixture metadata 声明的 `testRunner`、adapter runner->commandTemplate 路由、pytest / unittest / node:test 三类真实测试框架 test report、pre-patch failing test report、multi-file metadata / rubric evidence、跨文件 import graph / partial patch failure evidence、JavaScript smoke fixture 和 reviewer disagreement arbitration report 证据；`npm.cmd run eval:domain` 会用统一 `full_motivational_delegation` baseline 输出跨域 summary schema；`npm.cmd run eval:domain:export` 会导出 per-scenario JSON、domain metrics、observation trace、intervention trace、domain evidence JSONL、独立 repo fixture / patch / pre-patch test / partial-patch test / test / review artifacts 和 `phase2.eval_manifest.v1` manifest。

## 2. Core Interface

```python
from dataclasses import dataclass
from typing import Protocol, Any, Iterable, Literal

@dataclass
class DomainGoalSpec:
    goal_id: str
    natural_language_goal: str
    desired_outcome: dict[str, Any]
    forbidden_shortcuts: list[str]
    required_process: list[dict[str, Any]]
    allowed_interventions: list[str]
    success_evidence: list[str]
    max_steps: int | None = None

@dataclass
class DomainObservation:
    tick: int
    world_summary: dict[str, Any]
    agent_summaries: dict[str, dict[str, Any]]
    recent_events: list[dict[str, Any]]
    goal_progress: dict[str, Any]
    eval_signals: dict[str, float]

@dataclass
class DomainIntervention:
    intervention_id: str
    intervention_type: Literal[
        "motivation_bias",
        "event_skill_load",
        "opportunity_schedule",
        "information_exposure",
        "resource_shift",
        "constraint_injection",
        "evaluation_checkpoint"
    ]
    target_agents: list[str]
    payload: dict[str, Any]
    expires_at_tick: int | None
    reason: str

class DomainAdapter(Protocol):
    domain_id: str

    def build_initial_world(self, scenario_id: str, seed: int) -> Any:
        """Create a deterministic initial world for a scenario."""
        ...

    def parse_goal(self, raw_goal: str) -> DomainGoalSpec:
        """Compile natural language goal into process-constrained GoalSpec."""
        ...

    def observe(self, world: Any, goal: DomainGoalSpec) -> DomainObservation:
        """Return compact state needed by DirectorGoalRunner."""
        ...

    def propose_default_milestones(self, goal: DomainGoalSpec) -> list[dict[str, Any]]:
        """Return domain-specific latent preconditions and milestones."""
        ...

    def list_allowed_interventions(self, observation: DomainObservation, goal: DomainGoalSpec) -> list[str]:
        """Return intervention types currently legal in this domain state."""
        ...

    def apply_intervention(self, world: Any, intervention: DomainIntervention) -> list[dict[str, Any]]:
        """Apply intervention through normal event path; no direct shortcut mutation."""
        ...

    def step_world(self, world: Any, ticks: int) -> list[dict[str, Any]]:
        """Advance autonomous agents and return emitted events."""
        ...

    def evaluate(self, world: Any, goal: DomainGoalSpec) -> dict[str, float]:
        """Compute domain-level goal and process fidelity metrics."""
        ...

    def export_trace(self, world: Any, run_dir: str) -> None:
        """Export EventStore, memories, relationships/dependencies, interventions."""
        ...
```

## 3. Narrative Domain Adapter

### 3.1 Domain objects

```text
Agent          NPC / Player
Relationship   trust / affection / owes / envies / respects
Memory         subjective event memory
Resource       item / gold / crop / location availability
Event Skill    festival_shortage / lost_mooncat / rumor_conflict
Outcome        relationship edge delta / memory write / future behavior change
```

### 3.2 Example Goal

```text
Goal: Let Kai and Mira become close friends through believable shared experiences.
```

Allowed interventions:

- motivation_bias：提高 Kai 的 affiliation 或 recognition 权重。
- event_skill_load：加载共同活动事件。
- opportunity_schedule：安排两人在同一地点有交集。
- information_exposure：让 Mira 看见 Kai 的善意行为。
- constraint_injection：禁止直接修改关系边。

Forbidden shortcuts:

- 直接设置 `relationship_stage=close_friend`。
- 直接插入双方“我们是朋友”的记忆。
- 强制指定对话结果。

## 4. Coding / Task Domain Adapter（Secondary）

### 4.1 Domain objects

```text
Agent          PM / Architect / Implementer / Reviewer / Eval Agent
Relationship   trust / reliability / disagreement / dependency
Memory         prior review findings / design decisions / failure patterns
Resource       files / tests / APIs / issue tickets
Event Skill    design_review / failing_test / user_feedback / regression_alert
Outcome        artifact diff / test pass / review approval / heuristic update
```

### 4.2 Example Goal

```text
Goal: Develop a small Claude Code skill prototype with design, implementation, tests, and review.
```

Allowed interventions:

- event_skill_load：加载 design_review 或 failing_eval。
- information_exposure：把用户反馈暴露给 PM 和 Reviewer。
- constraint_injection：禁止 Implementer 跳过测试。
- evaluation_checkpoint：运行测试或 review rubric。

Forbidden shortcuts:

- 直接生成最终 artifact 并绕过子 Agent。
- 直接把 review_status 设置成 approved。
- 直接删除 failing test。

## 5. Adapter 不是通用平台承诺

本接口只保证研究抽象可迁移，不承诺：

- 支持任意外部工具生态。
- 支持真实多人开发工作流。
- 复刻 Claude Code / Codex / OpenClaw 的产品能力。
- 在 Phase 2 完成 coding domain 全实现。

Phase 2 的 adapter 当前验收点：

```text
1. NarrativeAdapter 已运行 3 个 GoalSpec：close_friend_traceable / repair_trust_memory / affiliation_bias_agent_choice。
2. CodingAdapter 已有 7 个 repo fixture 级 scenario：coding.skill_prototype_dryrun / coding.skill_regression_fix_dryrun / coding.skill_failing_test_repair_dryrun / coding.skill_multifile_review_dryrun / coding.skill_multifile_dependency_repair_dryrun / coding.skill_reviewer_disagreement_dryrun / coding.skill_javascript_smoke_dryrun，覆盖 repo fixture loaded -> design -> patch -> git checkout -> repo test command -> review；每个 fixture 在 metadata 声明 `testRunner`，adapter 按 runner 映射 `commandTemplate`，test report 记录 `testRunner`、`command`、`durationMs`、`exitCode`；failing-test repair 额外覆盖 pre-patch failing test -> patch -> post-patch passing test -> review，multi-file review 额外覆盖三文件补丁、metadata quality gate 与 review rubric checklist，multi-file dependency repair 额外覆盖 import graph、双源文件补丁和 single-file partial patch failure，reviewer disagreement 额外覆盖 approve / request_changes 冲突和 ArbitrationLayer contributing_sources，JavaScript smoke 额外覆盖 `node --test` 非 Python fixture。
3. Eval 已用相同 baseline 名称比较 town / coding domain 的 summary schema：npm.cmd run eval:domain。
4. Eval 导出已接入 manifest、domain evidence JSONL 和独立 coding evidence artifacts，包括 pre-patch failing test report、partial-patch failure report、multi-file patch、metadata evidence、rubric review report 与 reviewer arbitration report：npm.cmd run eval:domain:export。
5. 后续收紧项：人工 reviewer 抽样复核可在 `eval:archive:promote` promotion 阶段补充为备注或附件，不强制进入常规 CI。
```

## 6. Scenario Inventory and Directory Proposal

当前 coding scenario 数量为 7：

```text
1. coding.skill_prototype_dryrun                  pytest
2. coding.skill_regression_fix_dryrun             unittest
3. coding.skill_failing_test_repair_dryrun        pytest
4. coding.skill_multifile_review_dryrun           unittest
5. coding.skill_multifile_dependency_repair_dryrun pytest
6. coding.skill_reviewer_disagreement_dryrun      unittest
7. coding.skill_javascript_smoke_dryrun           node:test
```

目录规划保持：

```text
backend/app/domain/
├── base.py                     # DomainAdapter Protocol + shared dataclasses
├── narrative/
│   ├── adapter.py
│   ├── goals.py
│   ├── interventions.py
│   └── eval.py
└── coding/
    ├── adapter.py              # skeleton only in Phase 2
    ├── goals.py
    └── eval.py                 # dry-run only

configs/goals/
├── narrative_close_friend.json
├── narrative_forgiveness.json
├── narrative_festival_success.json
└── coding_claude_skill_dryrun.json
```
