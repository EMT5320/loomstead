from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

MemoryPerspective = Literal["objective", "subjective"]


@dataclass(frozen=True)
class SubjectiveMemoryRecord:
    record_id: str
    agent_id: str
    source_event_id: str | None
    perspective: MemoryPerspective
    text: str
    emotional_valence: float = 0.0
    confidence: float = 1.0
    tags: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "recordId": self.record_id,
            "agentId": self.agent_id,
            "sourceEventId": self.source_event_id,
            "perspective": self.perspective,
            "text": self.text,
            "emotionalValence": self.emotional_valence,
            "confidence": self.confidence,
            "tags": list(self.tags),
        }


class SubjectiveMemoryStore:
    def __init__(self) -> None:
        self._records: list[SubjectiveMemoryRecord] = []

    def add(self, record: SubjectiveMemoryRecord) -> SubjectiveMemoryRecord:
        self._records.append(record)
        return record

    def list(self, agent_id: str | None = None, limit: int = 20) -> list[SubjectiveMemoryRecord]:
        records = [record for record in self._records if agent_id is None or record.agent_id == agent_id]
        return records[-limit:]

    def recall(self, *, agent_id: str, query: str = "", limit: int = 8) -> list[SubjectiveMemoryRecord]:
        """按关键词召回主观记忆；Phase 2 先用规则匹配，后续可替换为向量检索。"""
        terms = [term for term in str(query or "").lower().split() if term]
        records = [record for record in self._records if record.agent_id == agent_id]
        if terms:
            records = [
                record
                for record in records
                if any(term in record.text.lower() or any(term in tag.lower() for tag in record.tags) for term in terms)
            ]
        records.sort(key=lambda record: (record.confidence + abs(record.emotional_valence), record.record_id), reverse=True)
        return records[:limit]

    def debug_snapshot(self, agent_id: str | None = None, limit: int = 20) -> dict[str, Any]:
        records = self.list(agent_id=agent_id, limit=limit)
        return {
            "version": "subjective_memory_store.v0",
            "agentId": agent_id,
            "count": len(records),
            "items": [record.to_dict() for record in records],
        }
