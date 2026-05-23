from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol

DomainKind = Literal["town", "task"]
InterventionType = Literal[
    "motivation_bias",
    "event_skill_load",
    "opportunity_schedule",
    "information_exposure",
    "resource_shift",
    "constraint_injection",
    "evaluation_checkpoint",
]


@dataclass(frozen=True)
class DomainGoalSpec:
    goal_id: str
    natural_language_goal: str
    desired_outcome: dict[str, Any]
    forbidden_shortcuts: list[str] = field(default_factory=list)
    required_process: list[dict[str, Any]] = field(default_factory=list)
    allowed_interventions: list[InterventionType] = field(default_factory=list)
    success_evidence: list[str] = field(default_factory=list)
    max_steps: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "goalId": self.goal_id,
            "naturalLanguageGoal": self.natural_language_goal,
            "desiredOutcome": dict(self.desired_outcome),
            "forbiddenShortcuts": list(self.forbidden_shortcuts),
            "requiredProcess": [dict(item) for item in self.required_process],
            "allowedInterventions": list(self.allowed_interventions),
            "successEvidence": list(self.success_evidence),
            "maxSteps": self.max_steps,
        }


@dataclass(frozen=True)
class DomainObservation:
    tick: int
    world_summary: dict[str, Any]
    agent_summaries: dict[str, dict[str, Any]] = field(default_factory=dict)
    recent_events: list[dict[str, Any]] = field(default_factory=list)
    goal_progress: dict[str, Any] = field(default_factory=dict)
    eval_signals: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tick": self.tick,
            "worldSummary": dict(self.world_summary),
            "agentSummaries": {agent_id: dict(summary) for agent_id, summary in self.agent_summaries.items()},
            "recentEvents": [dict(item) for item in self.recent_events],
            "goalProgress": dict(self.goal_progress),
            "evalSignals": dict(self.eval_signals),
        }


@dataclass(frozen=True)
class DomainIntervention:
    intervention_id: str
    intervention_type: InterventionType
    target_agents: list[str]
    payload: dict[str, Any] = field(default_factory=dict)
    expires_at_tick: int | None = None
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "interventionId": self.intervention_id,
            "interventionType": self.intervention_type,
            "targetAgents": list(self.target_agents),
            "payload": dict(self.payload),
            "expiresAtTick": self.expires_at_tick,
            "reason": self.reason,
        }


class DomainAdapter(Protocol):
    domain_id: str

    def build_initial_world(self, scenario_id: str, seed: int) -> Any:
        ...

    def parse_goal(self, raw_goal: str) -> DomainGoalSpec:
        ...

    def observe(self, world: Any, goal: DomainGoalSpec) -> DomainObservation:
        ...

    def propose_default_milestones(self, goal: DomainGoalSpec) -> list[dict[str, Any]]:
        ...

    def list_allowed_interventions(self, observation: DomainObservation, goal: DomainGoalSpec) -> list[InterventionType]:
        ...

    def apply_intervention(self, world: Any, intervention: DomainIntervention) -> list[dict[str, Any]]:
        ...

    def step_world(self, world: Any, ticks: int) -> list[dict[str, Any]]:
        ...

    def evaluate(self, world: Any, goal: DomainGoalSpec) -> dict[str, float]:
        ...

    def export_trace(self, world: Any, run_dir: str) -> None:
        ...


@dataclass(frozen=True)
class DomainAdapterMetadata:
    """已注册 domain 的只读元数据；具体运行接口由 DomainAdapter Protocol 约束。"""

    domain_id: str
    kind: DomainKind
    description: str
    entity_namespaces: tuple[str, ...] = field(default_factory=tuple)
    supported_tool_namespaces: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "domainId": self.domain_id,
            "kind": self.kind,
            "description": self.description,
            "entityNamespaces": list(self.entity_namespaces),
            "supportedToolNamespaces": list(self.supported_tool_namespaces),
        }


DEFAULT_TOWN_DOMAIN = DomainAdapterMetadata(
    domain_id="loomstead.town.v0",
    kind="town",
    description="Narrative-primary town slice for Phase 2 agent-loop skeleton.",
    entity_namespaces=("farm", "inventory", "shop", "building", "time", "weather"),
    supported_tool_namespaces=("life", "farm", "shop", "social", "strategic"),
)

DEFAULT_CODING_DOMAIN = DomainAdapterMetadata(
    domain_id="loomstead.coding.v0",
    kind="task",
    description="Secondary coding dry-run domain for portability checks.",
    entity_namespaces=("artifact", "dependency", "test", "review", "issue"),
    supported_tool_namespaces=("design", "implement", "test", "review"),
)

DEFAULT_DOMAIN_METADATA = (DEFAULT_TOWN_DOMAIN, DEFAULT_CODING_DOMAIN)
