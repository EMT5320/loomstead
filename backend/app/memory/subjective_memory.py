from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from app.runtime.schema_registry import require_schema_version

MemoryPerspective = Literal["objective", "subjective"]
MemoryStatus = Literal["active", "archived"]

DEFAULT_MEMORY_DECAY_RATE = 0.006
MEMORY_MIN_DECAY_FACTOR = 0.08
MEMORY_ARCHIVE_MIN_AGE_TICKS = 96
MEMORY_ARCHIVE_SALIENCE_THRESHOLD = 0.14
MEMORY_ARCHIVE_VALENCE_THRESHOLD = 0.12


@dataclass
class SubjectiveMemoryRecord:
    record_id: str
    agent_id: str
    source_event_id: str | None
    perspective: MemoryPerspective
    text: str
    emotional_valence: float = 0.0
    confidence: float = 1.0
    tags: tuple[str, ...] = ()
    created_tick: int | None = None
    last_accessed_tick: int | None = None
    salience: float = 0.0
    decay_rate: float = DEFAULT_MEMORY_DECAY_RATE
    consolidation_count: int = 0
    status: MemoryStatus = "active"
    archived_tick: int | None = None
    archived_reason: str | None = None

    def to_dict(self, world_tick: int | None = None) -> dict[str, Any]:
        return {
            "recordId": self.record_id,
            "agentId": self.agent_id,
            "sourceEventId": self.source_event_id,
            "perspective": self.perspective,
            "text": self.text,
            "emotionalValence": self.effective_emotional_valence(world_tick),
            "baseEmotionalValence": self.emotional_valence,
            "confidence": self.confidence,
            "tags": list(self.tags),
            "createdTick": self.created_tick,
            "lastAccessedTick": self.last_accessed_tick,
            "salience": self.salience,
            "effectiveSalience": self.effective_salience(world_tick),
            "decayRate": self.decay_rate,
            "consolidationCount": self.consolidation_count,
            "status": self.status,
            "archivedTick": self.archived_tick,
            "archivedReason": self.archived_reason,
        }

    def effective_salience(self, world_tick: int | None = None) -> float:
        age_ticks = self._age_ticks(world_tick)
        if age_ticks <= 0:
            return max(0.0, min(1.0, self.salience))
        consolidation_factor = max(0.35, 1.0 - min(0.65, float(self.consolidation_count) * 0.12))
        decay_factor = max(MEMORY_MIN_DECAY_FACTOR, 1.0 - float(age_ticks) * self.decay_rate * consolidation_factor)
        return max(0.0, min(1.0, self.salience * decay_factor))

    def effective_emotional_valence(self, world_tick: int | None = None) -> float:
        age_ticks = self._age_ticks(world_tick)
        if age_ticks <= 0:
            return max(-1.0, min(1.0, self.emotional_valence))
        decay_factor = max(0.25, 1.0 - float(age_ticks) * self.decay_rate * 0.5)
        return max(-1.0, min(1.0, self.emotional_valence * decay_factor))

    def _age_ticks(self, world_tick: int | None = None) -> int:
        if world_tick is None or self.created_tick is None:
            return 0
        try:
            return max(0, int(world_tick) - int(self.created_tick))
        except (TypeError, ValueError):
            return 0


class SubjectiveMemoryStore:
    def __init__(self) -> None:
        self._records: list[SubjectiveMemoryRecord] = []
        self._archived_records: list[SubjectiveMemoryRecord] = []

    def add(self, record: SubjectiveMemoryRecord, world_tick: int | None = None) -> SubjectiveMemoryRecord:
        if record.created_tick is None:
            record.created_tick = self._safe_tick(world_tick)
        if record.salience <= 0.0:
            record.salience = self._initial_salience(record)
        if record.decay_rate <= 0.0:
            record.decay_rate = DEFAULT_MEMORY_DECAY_RATE
        self._records.append(record)
        return record

    def list(self, agent_id: str | None = None, limit: int = 20) -> list[SubjectiveMemoryRecord]:
        records = [record for record in self._records if record.status == "active" and (agent_id is None or record.agent_id == agent_id)]
        return records[-limit:]

    def recall(self, *, agent_id: str, query: str = "", limit: int = 8, world_tick: int | None = None) -> list[SubjectiveMemoryRecord]:
        """按关键词召回主观记忆；Phase 2 先用规则匹配，后续可替换为向量检索。"""
        terms = [term for term in str(query or "").lower().split() if term]
        indexed_records = [(index, record) for index, record in enumerate(self._records) if record.agent_id == agent_id and record.status == "active"]
        if terms:
            indexed_records = [
                (index, record)
                for index, record in indexed_records
                if any(term in record.text.lower() or any(term in tag.lower() for tag in record.tags) for term in terms)
            ]
        # record_id 来自事件 id，当前事件 id 带 uuid；召回排序不能依赖它，否则 Eval 的同分样本会漂移。
        indexed_records.sort(
            key=lambda item: (
                self._recall_score(item[1], terms, world_tick),
                item[0],
            ),
            reverse=True,
        )
        selected = [record for _, record in indexed_records[:limit]]
        tick = self._safe_tick(world_tick)
        if tick is not None:
            for record in selected:
                record.last_accessed_tick = tick
        return selected

    def apply_decay(self, *, world_tick: int | None = None) -> dict[str, Any]:
        """按当前 tick 计算有效显著性，并把低显著性、低情绪强度记忆移入归档区。"""
        tick = self._safe_tick(world_tick)
        archived: list[SubjectiveMemoryRecord] = []
        active_records: list[SubjectiveMemoryRecord] = []
        for record in self._records:
            if record.status != "active":
                self._archived_records.append(record)
                continue
            age_ticks = record._age_ticks(tick)
            effective_salience = record.effective_salience(tick)
            effective_valence = abs(record.effective_emotional_valence(tick))
            should_archive = (
                age_ticks >= MEMORY_ARCHIVE_MIN_AGE_TICKS
                and effective_salience < MEMORY_ARCHIVE_SALIENCE_THRESHOLD
                and effective_valence < MEMORY_ARCHIVE_VALENCE_THRESHOLD
            )
            if should_archive:
                record.status = "archived"
                record.archived_tick = tick
                record.archived_reason = "low_salience_decay"
                archived.append(record)
                self._archived_records.append(record)
            else:
                active_records.append(record)
        self._records = active_records
        return {
            "worldTick": tick,
            "archivedCount": len(archived),
            "activeCount": len(self._records),
            "totalCount": len(self._records) + len(self._archived_records),
            "archivedRecordIds": [record.record_id for record in archived[:12]],
        }

    def debug_snapshot(self, agent_id: str | None = None, limit: int = 20, world_tick: int | None = None) -> dict[str, Any]:
        records = self.list(agent_id=agent_id, limit=limit)
        active_count = len([record for record in self._records if agent_id is None or record.agent_id == agent_id])
        archived_records = [record for record in self._archived_records if agent_id is None or record.agent_id == agent_id]
        return {
            "version": require_schema_version("subjective_memory_store"),
            "agentId": agent_id,
            "count": len(records),
            "activeCount": active_count,
            "archivedCount": len(archived_records),
            "totalCount": active_count + len(archived_records),
            "worldTick": self._safe_tick(world_tick),
            "archivePolicy": {
                "minAgeTicks": MEMORY_ARCHIVE_MIN_AGE_TICKS,
                "salienceThreshold": MEMORY_ARCHIVE_SALIENCE_THRESHOLD,
                "valenceThreshold": MEMORY_ARCHIVE_VALENCE_THRESHOLD,
                "minDecayFactor": MEMORY_MIN_DECAY_FACTOR,
            },
            "items": [record.to_dict(world_tick=world_tick) for record in records],
            "archivedItems": [record.to_dict(world_tick=world_tick) for record in archived_records[-min(limit, 8):]],
        }

    def _initial_salience(self, record: SubjectiveMemoryRecord) -> float:
        valence_weight = min(1.0, abs(float(record.emotional_valence)))
        confidence = max(0.0, min(1.0, float(record.confidence)))
        tag_bonus = 0.04 if record.tags else 0.0
        return max(0.05, min(1.0, 0.42 + confidence * 0.22 + valence_weight * 0.28 + tag_bonus))

    def _recall_score(self, record: SubjectiveMemoryRecord, terms: list[str], world_tick: int | None) -> float:
        text = record.text.lower()
        tags = [tag.lower() for tag in record.tags]
        relevance = 0.0
        for term in terms:
            if term in text:
                relevance += 0.08
            if any(term in tag for tag in tags):
                relevance += 0.12
        return (
            record.effective_salience(world_tick) * 0.52
            + max(0.0, min(1.0, record.confidence)) * 0.22
            + abs(record.effective_emotional_valence(world_tick)) * 0.18
            + min(0.4, relevance)
        )

    def _safe_tick(self, world_tick: int | None) -> int | None:
        if world_tick is None:
            return None
        try:
            return int(world_tick)
        except (TypeError, ValueError):
            return None
