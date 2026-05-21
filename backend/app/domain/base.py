from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

DomainKind = Literal["town", "task"]


@dataclass(frozen=True)
class DomainAdapter:
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


DEFAULT_TOWN_DOMAIN = DomainAdapter(
    domain_id="loomstead.town.v0",
    kind="town",
    description="Narrative-primary town slice for Phase 2 agent-loop skeleton.",
    entity_namespaces=("farm", "inventory", "shop", "building", "time", "weather"),
    supported_tool_namespaces=("life", "farm", "shop", "social", "strategic"),
)
