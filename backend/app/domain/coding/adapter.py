from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.domain.base import DomainGoalSpec, DomainIntervention, DomainObservation, InterventionType
from app.eval.process_fidelity import build_process_metrics


CODING_GOAL_IDS = ("coding.skill_prototype_dryrun",)


class CodingDomainAdapter:
    """Secondary coding domain skeleton：用确定性 dry-run 验证接口可迁移。"""

    domain_id = "loomstead.coding.v0"
    kind = "task"

    def build_initial_world(self, scenario_id: str, seed: int) -> dict[str, Any]:
        goal = self.parse_goal(scenario_id)
        return {
            "tick": 0,
            "seed": seed,
            "goalId": goal.goal_id,
            "agents": {
                "pm": {"role": "PM", "state": "scoping"},
                "architect": {"role": "Architect", "state": "waiting"},
                "implementer": {"role": "Implementer", "state": "waiting"},
                "reviewer": {"role": "Reviewer", "state": "waiting"},
            },
            "constraints": [],
            "artifacts": {},
            "dependencies": {},
            "events": [
                {
                    "id": "coding_evt_000",
                    "type": "domain.goal_loaded",
                    "payload": {"domainId": self.domain_id, "goalId": goal.goal_id},
                }
            ],
        }

    def parse_goal(self, raw_goal: str) -> DomainGoalSpec:
        known_goal_text = "Develop a skill prototype through design, tests, and review."
        if raw_goal not in CODING_GOAL_IDS and raw_goal != known_goal_text:
            raise ValueError(f"未知 coding goal：{raw_goal}")
        required_process = [
            {"id": "design_review_loaded", "predicate": "design review event is loaded before implementation"},
            {"id": "implementation_diff", "predicate": "implementer creates an artifact diff"},
            {"id": "tests_executed", "predicate": "evaluation checkpoint runs tests"},
            {"id": "review_completed", "predicate": "reviewer records approval with source evidence"},
            {"id": "failure_pattern_memory", "predicate": "review cites a prior failure or constraint memory"},
        ]
        return DomainGoalSpec(
            goal_id="coding.skill_prototype_dryrun",
            natural_language_goal="Develop a skill prototype through design, tests, and review.",
            desired_outcome={"artifact": "skill_prototype", "reviewStatus": "approved", "tests": "passed"},
            forbidden_shortcuts=[
                "direct_artifact_without_design",
                "review_status_set_without_review",
                "delete_failing_test",
            ],
            required_process=required_process,
            allowed_interventions=["event_skill_load", "constraint_injection", "evaluation_checkpoint"],
            success_evidence=["design_event", "diff_event", "test_event", "review_event"],
            max_steps=4,
        )

    def observe(self, world: dict[str, Any], goal: DomainGoalSpec) -> DomainObservation:
        return DomainObservation(
            tick=int(world.get("tick", 0)),
            world_summary={
                "artifactCount": float(len(world.get("artifacts", {}))),
                "constraintCount": float(len(world.get("constraints", []))),
            },
            agent_summaries={agent_id: dict(summary) for agent_id, summary in world.get("agents", {}).items()},
            recent_events=[dict(event) for event in world.get("events", [])[-12:]],
            goal_progress=self.evaluate(world, goal),
            eval_signals={"eventCount": float(len(world.get("events", [])))},
        )

    def propose_default_milestones(self, goal: DomainGoalSpec) -> list[dict[str, Any]]:
        return [
            {"id": item["id"], "domainId": self.domain_id, "predicate": item["predicate"]}
            for item in goal.required_process
        ]

    def list_allowed_interventions(
        self, observation: DomainObservation, goal: DomainGoalSpec
    ) -> list[InterventionType]:
        return list(goal.allowed_interventions)

    def apply_intervention(self, world: dict[str, Any], intervention: DomainIntervention) -> list[dict[str, Any]]:
        if intervention.intervention_type == "constraint_injection":
            world.setdefault("constraints", []).append(
                {
                    "id": intervention.payload.get("constraintId", "must_run_tests"),
                    "sourceInterventionId": intervention.intervention_id,
                }
            )
        event = _append_event(
            world,
            "domain.intervention_applied",
            {
                "domainId": self.domain_id,
                "intervention": intervention.to_dict(),
                "shortcutMutationApplied": False,
            },
        )
        return [event]

    def step_world(self, world: dict[str, Any], ticks: int) -> list[dict[str, Any]]:
        emitted: list[dict[str, Any]] = []
        for _ in range(max(1, ticks)):
            world["tick"] = int(world.get("tick", 0)) + 1
            emitted.extend(_advance_coding_world(world))
        return emitted

    def evaluate(self, world: dict[str, Any], goal: DomainGoalSpec) -> dict[str, float]:
        event_types = {str(event.get("type") or "") for event in world.get("events", [])}
        review_event = _first_event(world, "coding.review_completed")
        process_checks = {
            "design_review_loaded": "coding.design_review_loaded" in event_types,
            "implementation_diff": "coding.implementation_diff_created" in event_types,
            "tests_executed": "coding.tests_executed" in event_types,
            "review_completed": bool(review_event),
            "failure_pattern_memory": bool(review_event and review_event.get("payload", {}).get("citedMemoryIds")),
        }
        # Coding domain 用 review dependency trace 对齐通用 relationship_consistency 指标。
        process_checks["relationship_edge_trace"] = process_checks["review_completed"]
        coding_events = [
            event for event in world.get("events", []) if event.get("type", "").startswith("coding.")
        ]
        domain_interventions = [
            event for event in world.get("events", []) if event.get("type") == "domain.intervention_applied"
        ]
        has_review_source = bool(review_event and review_event.get("payload", {}).get("sourceEventIds"))
        return build_process_metrics(
            process_checks=process_checks,
            required_process_ids=tuple(str(item["id"]) for item in goal.required_process),
            shortcut_events=0,
            goal_relevant_state_changes=1,
            forced_actions=0,
            goal_relevant_actions=max(1, len(coding_events)),
            overreaching_interventions=0,
            total_interventions=max(1, len(domain_interventions)),
            state_changes_with_source=1 if has_review_source else 0,
            relationship_relevant_decisions=1,
            decisions_with_relationship_memory=1 if process_checks["failure_pattern_memory"] else 0,
            goal_success_override=process_checks["review_completed"] and process_checks["tests_executed"],
        )

    def export_trace(self, world: dict[str, Any], run_dir: str) -> None:
        # skeleton 保留最小导出，后续可接 Eval manifest 统一索引。
        path = Path(run_dir)
        path.mkdir(parents=True, exist_ok=True)
        (path / "coding_events.jsonl").write_text(
            "".join(json.dumps(event, ensure_ascii=False) + "\n" for event in world.get("events", [])),
            encoding="utf-8",
        )


def _advance_coding_world(world: dict[str, Any]) -> list[dict[str, Any]]:
    emitted: list[dict[str, Any]] = []
    event_types = {str(event.get("type") or "") for event in world.get("events", [])}
    if "coding.design_review_loaded" not in event_types:
        emitted.append(_append_event(world, "coding.design_review_loaded", {"agentId": "architect"}))
        world["agents"]["architect"]["state"] = "design_reviewed"
    elif "coding.implementation_diff_created" not in event_types:
        design_event = _first_event(world, "coding.design_review_loaded")
        world.setdefault("artifacts", {})["skill_prototype.diff"] = {"status": "created"}
        emitted.append(
            _append_event(
                world,
                "coding.implementation_diff_created",
                {"agentId": "implementer", "sourceEventIds": [_event_id(design_event)]},
            )
        )
        world["agents"]["implementer"]["state"] = "diff_created"
    elif "coding.tests_executed" not in event_types:
        diff_event = _first_event(world, "coding.implementation_diff_created")
        emitted.append(
            _append_event(
                world,
                "coding.tests_executed",
                {"agentId": "reviewer", "passed": True, "sourceEventIds": [_event_id(diff_event)]},
            )
        )
    elif "coding.review_completed" not in event_types:
        test_event = _first_event(world, "coding.tests_executed")
        emitted.append(
            _append_event(
                world,
                "coding.review_completed",
                {
                    "agentId": "reviewer",
                    "status": "approved",
                    "sourceEventIds": [_event_id(test_event)],
                    "citedMemoryIds": ["prior_failure.skip_tests"],
                },
            )
        )
        world["agents"]["reviewer"]["state"] = "approved"
    return emitted


def _append_event(world: dict[str, Any], event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    events = world.setdefault("events", [])
    event = {
        "id": f"coding_evt_{len(events):03d}",
        "tick": int(world.get("tick", 0)),
        "type": event_type,
        "payload": dict(payload),
    }
    events.append(event)
    return event


def _first_event(world: dict[str, Any], event_type: str) -> dict[str, Any] | None:
    for event in world.get("events", []):
        if event.get("type") == event_type:
            return event
    return None


def _event_id(event: dict[str, Any] | None) -> str:
    return str(event.get("id") if isinstance(event, dict) else "")
