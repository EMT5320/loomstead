from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.domain.base import DomainGoalSpec, DomainIntervention, DomainObservation, InterventionType
from app.eval.process_fidelity import build_process_metrics
from app.runtime.agent_runtime import AgentRuntime


@dataclass(frozen=True)
class NarrativeGoalTemplate:
    goal_id: str
    natural_language_goal: str
    npc_id: str
    target_npc_id: str
    location_id: str = "plaza"
    anchor_id: str = "plaza_fountain"
    status_overrides: dict[str, int] | None = None


NARRATIVE_GOALS: dict[str, NarrativeGoalTemplate] = {
    "narrative.close_friend_traceable": NarrativeGoalTemplate(
        goal_id="narrative.close_friend_traceable",
        natural_language_goal="Mira and Tomas become close through a traceable shared conversation.",
        npc_id="mira",
        target_npc_id="tomas",
        status_overrides={"energy": 90, "money": 90, "social": 5},
    ),
    "narrative.repair_trust_memory": NarrativeGoalTemplate(
        goal_id="narrative.repair_trust_memory",
        natural_language_goal="Tomas repairs trust with Mira through remembered interaction evidence.",
        npc_id="tomas",
        target_npc_id="mira",
        status_overrides={"energy": 90, "money": 90, "social": 5},
    ),
    "narrative.affiliation_bias_agent_choice": NarrativeGoalTemplate(
        goal_id="narrative.affiliation_bias_agent_choice",
        natural_language_goal=(
            "Lena receives an affiliation bias while retaining arbitration-based social action choice."
        ),
        npc_id="lena",
        target_npc_id="mira",
        status_overrides={"energy": 90, "money": 90, "social": 5},
    ),
}
NARRATIVE_GOAL_IDS = tuple(NARRATIVE_GOALS.keys())
NARRATIVE_COUNTERFACTUAL_REPLAY_VERSION = "narrative.domain_counterfactual_replay.v1"


class NarrativeDomainAdapter:
    """小镇 primary domain adapter：把 DomainGoalSpec 接到现有 AgentRuntime 主路径。"""

    domain_id = "loomstead.town.v0"
    kind = "town"

    def build_initial_world(self, scenario_id: str, seed: int) -> AgentRuntime:
        goal = self.parse_goal(scenario_id)
        runtime = AgentRuntime(provider_mode="rule")
        runtime.event_store.append(
            "domain.goal_loaded",
            {"domainId": self.domain_id, "goalId": goal.goal_id, "seed": seed},
        )
        self._apply_goal_setup(runtime, goal)
        return runtime

    def parse_goal(self, raw_goal: str) -> DomainGoalSpec:
        template = NARRATIVE_GOALS.get(raw_goal)
        if template is None:
            matched = next(
                (item for item in NARRATIVE_GOALS.values() if item.natural_language_goal == raw_goal),
                None,
            )
            template = matched
        if template is None:
            raise ValueError(f"未知 narrative goal：{raw_goal}")
        required_process = [
            {"id": "goal_relevant_tool_event", "predicate": "exists social tool event for the target pair"},
            {"id": "subjective_memory_refs", "predicate": "subjective memory cites the social tool event"},
            {"id": "relationship_edge_trace", "predicate": "relationship edge keeps source event ids"},
            {"id": "causal_trace", "predicate": "tool event links to memory and relationship evidence"},
            {"id": "future_behavior_reference", "predicate": "later decision can cite relationship or heuristic refs"},
        ]
        return DomainGoalSpec(
            goal_id=template.goal_id,
            natural_language_goal=template.natural_language_goal,
            desired_outcome={
                "npcId": template.npc_id,
                "targetNpcId": template.target_npc_id,
                "relationshipEdge": {"edgeType": "trust", "minStrength": 0.5},
            },
            forbidden_shortcuts=[
                "direct_relationship_set",
                "manual_memory_insert_without_event",
                "force_dialogue_outcome",
            ],
            required_process=required_process,
            allowed_interventions=["motivation_bias", "opportunity_schedule", "evaluation_checkpoint"],
            success_evidence=["tool_event", "subjective_memory", "relationship_edge", "decision_trace"],
            max_steps=2,
        )

    def observe(self, world: AgentRuntime, goal: DomainGoalSpec) -> DomainObservation:
        npc_id = str(goal.desired_outcome.get("npcId") or "")
        snapshot = world.get_phase2_debug_snapshot({"agentId": npc_id, "limit": 30})
        clock = dict(world.world.get("clock", {}))
        agent = dict(world.world.get("agents", {}).get(npc_id, {}))
        return DomainObservation(
            tick=int(clock.get("tick", 0)),
            world_summary={"clock": clock, "activeFocus": world.world.get("activeFocus")},
            agent_summaries={
                npc_id: {
                    "id": agent.get("id"),
                    "name": agent.get("name"),
                    "locationId": agent.get("locationId"),
                    "anchorId": agent.get("anchorId"),
                    "activity": agent.get("activity"),
                    "status": dict(agent.get("status", {})) if isinstance(agent.get("status"), dict) else {},
                }
            },
            recent_events=[_compact_event(event) for event in world.event_store.list()[-12:]],
            goal_progress=self.evaluate(world, goal),
            eval_signals={
                "recentTraceEventCount": float(len(snapshot.get("recentTraceEvents", []))),
                "relationshipEdgeCount": float(snapshot.get("relationshipEdges", {}).get("count", 0)),
            },
        )

    def propose_default_milestones(self, goal: DomainGoalSpec) -> list[dict[str, Any]]:
        return [
            {"id": item["id"], "domainId": self.domain_id, "predicate": item["predicate"]}
            for item in goal.required_process
        ]

    def list_allowed_interventions(
        self, observation: DomainObservation, goal: DomainGoalSpec
    ) -> list[InterventionType]:
        return [item for item in goal.allowed_interventions if item != "resource_shift"]

    def apply_intervention(self, world: AgentRuntime, intervention: DomainIntervention) -> list[dict[str, Any]]:
        world.world["activeFocus"] = {
            "targetAgents": list(intervention.target_agents),
            "brief": intervention.reason or f"Domain intervention: {intervention.intervention_type}",
            "source": "domain_adapter",
        }
        event = world.event_store.append(
            "domain.intervention_applied",
            {
                "domainId": self.domain_id,
                "intervention": intervention.to_dict(),
                "shortcutMutationApplied": False,
            },
        )
        return [event]

    def step_world(self, world: AgentRuntime, ticks: int) -> list[dict[str, Any]]:
        before = len(world.event_store.list())
        world.tick(float(max(1, ticks)) * 3600.0, speed=1.0)
        return [dict(event) for event in world.event_store.list()[before:]]

    def evaluate(self, world: AgentRuntime, goal: DomainGoalSpec) -> dict[str, float]:
        npc_id = str(goal.desired_outcome.get("npcId") or "")
        target_npc_id = str(goal.desired_outcome.get("targetNpcId") or "")
        events = world.event_store.list()
        goal_tool_events = [
            event
            for event in events
            if event.get("type") == "tool.execution_completed"
            and event.get("payload", {}).get("npcId") == npc_id
            and event.get("payload", {}).get("targetNpcId") == target_npc_id
        ]
        goal_event_ids = {str(event.get("id") or "") for event in goal_tool_events}
        memories = [record.to_dict() for record in world.subjective_memory_store.list(agent_id=npc_id, limit=40)]
        memory_source_ids = {str(item.get("sourceEventId") or "") for item in memories}
        relationship_edges = [
            edge.to_dict()
            for edge in world.relationship_edge_store.list(agent_id=npc_id, limit=40)
            if edge.target_agent_id == target_npc_id or edge.source_agent_id == target_npc_id
        ]
        relationship_source_ids = {
            str(source_id)
            for edge in relationship_edges
            for source_id in edge.get("sourceEventIds", [])
        }
        process_checks = {
            "goal_relevant_tool_event": bool(goal_tool_events),
            "subjective_memory_refs": bool(goal_event_ids & memory_source_ids),
            "relationship_edge_trace": bool(goal_event_ids & relationship_source_ids),
            "causal_trace": bool(goal_event_ids and goal_event_ids & memory_source_ids & relationship_source_ids),
            "future_behavior_reference": bool(relationship_edges),
        }
        counterfactual_replay = _ensure_narrative_counterfactual_replay(
            world,
            goal=goal,
            npc_id=npc_id,
            target_npc_id=target_npc_id,
            goal_event_ids=goal_event_ids,
        )
        return build_process_metrics(
            process_checks=process_checks,
            required_process_ids=tuple(str(item["id"]) for item in goal.required_process),
            shortcut_events=0,
            goal_relevant_state_changes=max(1, len(relationship_edges)),
            forced_actions=0,
            goal_relevant_actions=max(1, len(goal_tool_events)),
            overreaching_interventions=0,
            total_interventions=max(1, _count_domain_interventions(events)),
            state_changes_with_source=sum(1 for edge in relationship_edges if edge.get("sourceEventIds")),
            relationship_relevant_decisions=max(1, len(goal_tool_events)),
            decisions_with_relationship_memory=1 if process_checks["relationship_edge_trace"] else 0,
            counterfactual_tool_selection_change_rate=float(
                counterfactual_replay.get("changeRate", 0.0)
            ),
            goal_success_override=(
                process_checks["goal_relevant_tool_event"] and process_checks["relationship_edge_trace"]
            ),
        )

    def export_trace(self, world: AgentRuntime, run_dir: str) -> None:
        # 当前 adapter dry-run 不主动写文件；Eval manifest 线负责统一归档。
        return None

    def _apply_goal_setup(self, runtime: AgentRuntime, goal: DomainGoalSpec) -> None:
        npc_id = str(goal.desired_outcome.get("npcId") or "")
        target_npc_id = str(goal.desired_outcome.get("targetNpcId") or "")
        template = NARRATIVE_GOALS[goal.goal_id]
        for agent_id in (npc_id, target_npc_id):
            agent = runtime.world["agents"][agent_id]
            agent["locationId"] = template.location_id
            agent["anchorId"] = template.anchor_id
            agent["activity"] = "available_for_domain_goal"
            for key, value in (template.status_overrides or {}).items():
                agent.setdefault("status", {})[key] = value
        runtime.world["activeFocus"] = {
            "targetAgents": [npc_id],
            "brief": f"Cross-domain narrative GoalSpec: {goal.goal_id}",
            "source": "domain_adapter",
        }


def _count_domain_interventions(events: list[dict[str, Any]]) -> int:
    return sum(1 for event in events if event.get("type") == "domain.intervention_applied")


def _ensure_narrative_counterfactual_replay(
    world: AgentRuntime,
    *,
    goal: DomainGoalSpec,
    npc_id: str,
    target_npc_id: str,
    goal_event_ids: set[str],
) -> dict[str, Any]:
    """缓存 narrative domain 的 route-level 反事实 replay，供 metrics 与 export 共用。"""
    if not goal_event_ids:
        return {}
    replay_map = world.world.setdefault("counterfactualReplays", {})
    if not isinstance(replay_map, dict):
        replay_map = {}
        world.world["counterfactualReplays"] = replay_map
    replay_id = f"{goal.goal_id}.route_replay"
    existing = replay_map.get(replay_id)
    if isinstance(existing, dict):
        return existing

    replay = _build_narrative_counterfactual_replay(
        world,
        goal=goal,
        npc_id=npc_id,
        target_npc_id=target_npc_id,
        goal_event_ids=goal_event_ids,
    )
    if replay:
        replay_map[replay_id] = replay
    return replay


def _build_narrative_counterfactual_replay(
    world: AgentRuntime,
    *,
    goal: DomainGoalSpec,
    npc_id: str,
    target_npc_id: str,
    goal_event_ids: set[str],
) -> dict[str, Any]:
    relationship_edges = [
        edge.to_dict()
        for edge in world.relationship_edge_store.list(agent_id=npc_id, limit=40)
    ]
    subjective_memory_records = [
        record.to_dict() for record in world.subjective_memory_store.list(agent_id=npc_id, limit=40)
    ]
    heuristics = [item.to_dict() for item in world.heuristic_library.list(agent_id=npc_id, limit=40)]
    goal_subjective_memory_ids = {
        str(record.get("recordId") or "")
        for record in subjective_memory_records
        if str(record.get("sourceEventId") or "") in goal_event_ids
        and str(record.get("recordId") or "")
    }
    goal_heuristic_ids = {
        str(item.get("heuristicId") or "")
        for item in heuristics
        if str(item.get("sourceEventId") or "") in goal_event_ids
        and str(item.get("heuristicId") or "")
    }
    goal_relationship_edge_ids = {
        str(edge.get("edgeId") or "")
        for edge in relationship_edges
        if _same_relationship_pair(edge, npc_id, target_npc_id)
    }
    if not (goal_subjective_memory_ids or goal_relationship_edge_ids or goal_heuristic_ids):
        return {}

    baseline_decision = world.motivation_engine.evaluate_npc(
        world.world,
        npc_id,
        delta_minutes=20.0,
        relationship_edges=relationship_edges,
        subjective_memory_records=subjective_memory_records,
        heuristics=heuristics,
    )
    baseline_payload = _decision_payload(baseline_decision)
    selected_with = str(baseline_payload.get("selectedToolId") or "")
    if not selected_with:
        return {}

    ablation_specs = (
        {
            "ablationId": "remove_goal_relationship_edges",
            "kind": "critical",
            "removeRelationships": True,
            "reason": "Remove relationship edges sourced from the narrative goal route.",
        },
        {
            "ablationId": "remove_goal_subjective_memories",
            "kind": "critical",
            "removeMemories": True,
            "reason": "Remove subjective memories written by the goal-relevant tool events.",
        },
        {
            "ablationId": "remove_goal_learned_heuristics",
            "kind": "critical",
            "removeHeuristics": True,
            "reason": "Remove heuristics learned from the goal-relevant tool events.",
        },
        {
            "ablationId": "remove_all_memory_context",
            "kind": "critical",
            "removeAllMemoryContext": True,
            "reason": "Remove relationship, subjective memory, and heuristic context together.",
        },
    )
    comparisons: list[dict[str, Any]] = []
    changed_count = 0
    for spec in ablation_specs:
        ablated_edges = list(relationship_edges)
        ablated_memories = list(subjective_memory_records)
        ablated_heuristics = list(heuristics)
        removed_evidence_ids: list[str] = []

        if spec.get("removeAllMemoryContext"):
            removed_evidence_ids.extend(
                [
                    *[str(edge.get("edgeId") or "") for edge in relationship_edges if str(edge.get("edgeId") or "")],
                    *[
                        str(record.get("recordId") or "")
                        for record in subjective_memory_records
                        if str(record.get("recordId") or "")
                    ],
                    *[str(item.get("heuristicId") or "") for item in heuristics if str(item.get("heuristicId") or "")],
                ]
            )
            ablated_edges = []
            ablated_memories = []
            ablated_heuristics = []
        else:
            if spec.get("removeRelationships"):
                removed_evidence_ids.extend(sorted(goal_relationship_edge_ids))
                ablated_edges = [
                    edge for edge in ablated_edges if str(edge.get("edgeId") or "") not in goal_relationship_edge_ids
                ]
            if spec.get("removeMemories"):
                removed_evidence_ids.extend(sorted(goal_subjective_memory_ids))
                ablated_memories = [
                    record
                    for record in ablated_memories
                    if str(record.get("recordId") or "") not in goal_subjective_memory_ids
                ]
            if spec.get("removeHeuristics"):
                removed_evidence_ids.extend(sorted(goal_heuristic_ids))
                ablated_heuristics = [
                    item for item in ablated_heuristics if str(item.get("heuristicId") or "") not in goal_heuristic_ids
                ]

        ablated_decision = world.motivation_engine.evaluate_npc(
            world.world,
            npc_id,
            delta_minutes=20.0,
            relationship_edges=ablated_edges,
            subjective_memory_records=ablated_memories,
            heuristics=ablated_heuristics,
        )
        ablated_payload = _decision_payload(ablated_decision)
        selected_without = str(ablated_payload.get("selectedToolId") or "")
        changed = bool(selected_without) and selected_without != selected_with
        changed_count += 1 if changed else 0
        comparisons.append(
            {
                "ablationId": spec.get("ablationId"),
                "kind": spec.get("kind"),
                "removedEvidenceIds": sorted(set(removed_evidence_ids)),
                "selectedWithEvidence": selected_with,
                "selectedWithoutEvidence": selected_without or None,
                "changed": changed,
                "scoreChanged": _candidate_scores_changed(
                    list(baseline_payload.get("candidateScores", [])),
                    list(ablated_payload.get("candidateScores", [])),
                ),
                "reason": spec.get("reason"),
            }
        )

    return {
        "replayVersion": NARRATIVE_COUNTERFACTUAL_REPLAY_VERSION,
        "goalId": goal.goal_id,
        "npcId": npc_id,
        "targetNpcId": target_npc_id,
        "selectedWithEvidence": selected_with,
        "goalEventIds": sorted(goal_event_ids),
        "goalRelationshipEdgeIds": sorted(goal_relationship_edge_ids),
        "goalSubjectiveMemoryRecordIds": sorted(goal_subjective_memory_ids),
        "goalHeuristicIds": sorted(goal_heuristic_ids),
        "comparisonCount": len(comparisons),
        "changedDecisionCount": changed_count,
        "changeRate": round(_safe_ratio(changed_count, len(comparisons)), 6),
        "comparisons": comparisons,
    }


def _decision_payload(decision: dict[str, Any]) -> dict[str, Any]:
    payload = decision.get("decision") if isinstance(decision, dict) else None
    return payload if isinstance(payload, dict) else {}


def _same_relationship_pair(edge: dict[str, Any], source_id: str, target_id: str) -> bool:
    return {str(edge.get("sourceAgentId") or ""), str(edge.get("targetAgentId") or "")} == {
        source_id,
        target_id,
    }


def _candidate_scores_changed(with_scores: list[Any], without_scores: list[Any]) -> bool:
    without_by_tool = {
        str(item.get("toolId") or ""): item
        for item in without_scores
        if isinstance(item, dict)
    }
    for item in with_scores:
        if not isinstance(item, dict):
            continue
        tool_id = str(item.get("toolId") or "")
        other = without_by_tool.get(tool_id, {})
        for field in ("score", "relationshipBonus", "subjectiveMemoryBonus", "heuristicBonus"):
            if round(float(item.get(field) or 0.0), 6) != round(float(other.get(field) or 0.0), 6):
                return True
    return False


def _safe_ratio(numerator: int | float, denominator: int | float) -> float:
    return float(numerator) / float(denominator) if float(denominator) else 0.0


def _compact_event(event: dict[str, Any]) -> dict[str, Any]:
    payload = event.get("payload", {}) if isinstance(event.get("payload"), dict) else {}
    compact_payload = {
        key: payload.get(key)
        for key in (
            "domainId",
            "npcId",
            "targetNpcId",
            "toolId",
            "traceSchemaVersion",
            "replacementToolId",
            "reason",
        )
        if key in payload
    }
    if "intervention" in payload:
        intervention = payload.get("intervention", {})
        compact_payload["interventionType"] = (
            intervention.get("interventionType") if isinstance(intervention, dict) else None
        )
    return {
        "id": event.get("id"),
        "type": event.get("type"),
        "payload": compact_payload,
    }
