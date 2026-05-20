---
status: active
owner_lane: research-runtime
last_verified: 2026-05-20
startup_load: on-demand
source_of_truth: true
scope: cross-domain adapter interface, narrative primary boundary, optional task domain portability
---

# 跨域 Adapter 接口：Narrative-primary, Task-secondary

> 本文定义跨域 adapter 的最小接口。目的不是把项目扩张成通用 Agent 平台，而是让 `Agent Valley` 的核心研究抽象可以离开小镇被验证。小镇仍是 primary domain；task / coding domain 只作为 secondary validation。

## 1. 设计原则

1. 小镇是第一研究环境，不是临时 demo。
2. Adapter 只抽象“目标、干预、观察、评估”四件事。
3. 核心 Runtime 不依赖具体场景名词，例如 crop、festival、tavern。
4. 任何新 domain 都必须支持 EventStore、AgentState、Memory、Relationship / Dependency Graph、ToolExecutor、EvalTrace。
5. Phase 2 只实现接口和 narrative adapter；coding adapter 只做 skeleton。

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

Phase 2 的 adapter 验收只要求：

```text
1. NarrativeAdapter 可运行至少 3 个 GoalSpec。
2. CodingAdapter 有 skeleton 和 1 个 dry-run scenario。
3. Eval 能用相同 baseline 名称比较不同 domain 的 summary schema。
```

## 6. Directory Proposal

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
