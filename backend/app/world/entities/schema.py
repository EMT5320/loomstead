from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

EntityKind = Literal["farm_plot", "item", "inventory", "shop", "building", "time", "weather"]


@dataclass(frozen=True)
class WorldEntity:
    entity_id: str
    kind: EntityKind
    label: str
    state: dict[str, Any] = field(default_factory=dict)
    tags: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "entityId": self.entity_id,
            "kind": self.kind,
            "label": self.label,
            "state": dict(self.state),
            "tags": list(self.tags),
        }


def world_entities_from_state(world: dict[str, Any]) -> list[WorldEntity]:
    entities: list[WorldEntity] = []
    for plot_id, plot in world.get("farmPlots", {}).items():
        if isinstance(plot, dict):
            entities.append(WorldEntity(entity_id=str(plot_id), kind="farm_plot", label=str(plot.get("name") or plot_id), state=dict(plot), tags=("farm",)))
    clock = world.get("clock", {}) if isinstance(world.get("clock"), dict) else {}
    entities.append(WorldEntity(entity_id="world.clock", kind="time", label="World Clock", state=dict(clock), tags=("time",)))
    return entities
