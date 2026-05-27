from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

ToolTier = Literal["physiological", "vocational", "social_strategic"]
ObserverVisibility = Literal["all_in_location", "participants_only", "private"]


@dataclass(frozen=True)
class Precondition:
    kind: str
    field: str
    expected: Any = None


@dataclass(frozen=True)
class WorldEffect:
    kind: str
    target: str
    delta: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class FailureMode:
    code: str
    reason: str
    emotional_charge: float = 0.0


@dataclass(frozen=True)
class ToolDefinition:
    tool_id: str
    tier: ToolTier
    input_schema: dict[str, Any]
    served_needs: tuple[str, ...] = ()
    preconditions: tuple[Precondition, ...] = ()
    duration_seconds: float = 0.0
    interruptible: bool = True
    interrupt_priority_threshold: float = 0.8
    world_effects: tuple[WorldEffect, ...] = ()
    event_emissions: tuple[str, ...] = ()
    observer_visibility: ObserverVisibility = "participants_only"
    llm_eligible: bool = False
    failure_modes: tuple[FailureMode, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "toolId": self.tool_id,
            "tier": self.tier,
            "inputSchema": dict(self.input_schema),
            "servedNeeds": list(self.served_needs),
            "preconditions": [precondition.__dict__ for precondition in self.preconditions],
            "durationSeconds": self.duration_seconds,
            "interruptible": self.interruptible,
            "interruptPriorityThreshold": self.interrupt_priority_threshold,
            "worldEffects": [effect.__dict__ for effect in self.world_effects],
            "eventEmissions": list(self.event_emissions),
            "observerVisibility": self.observer_visibility,
            "llmEligible": self.llm_eligible,
            "failureModes": [failure.__dict__ for failure in self.failure_modes],
        }
