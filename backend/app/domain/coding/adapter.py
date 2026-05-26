from __future__ import annotations

import difflib
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from app.domain.base import DomainGoalSpec, DomainIntervention, DomainObservation, InterventionType
from app.eval.process_fidelity import build_process_metrics


FAILING_TEST_REPAIR_GOAL_ID = "coding.skill_failing_test_repair_dryrun"
MULTIFILE_REVIEW_GOAL_ID = "coding.skill_multifile_review_dryrun"
MULTIFILE_DEPENDENCY_REPAIR_GOAL_ID = "coding.skill_multifile_dependency_repair_dryrun"
CROSS_FILE_REGRESSION_GOAL_ID = "coding.skill_cross_file_regression_dryrun"
REVIEWER_DISAGREEMENT_GOAL_ID = "coding.skill_reviewer_disagreement_dryrun"
JAVASCRIPT_SMOKE_GOAL_ID = "coding.skill_javascript_smoke_dryrun"

TEST_RUNNER_COMMAND_TEMPLATES = {
    "pytest": "python -m pytest tests/test_skill.py -q",
    "unittest": "python -m unittest discover -s tests -p test_skill.py -q",
    "node_test": "node --test tests/skill_summary.test.mjs",
}

CODING_GOAL_IDS = (
    "coding.skill_prototype_dryrun",
    "coding.skill_regression_fix_dryrun",
    FAILING_TEST_REPAIR_GOAL_ID,
    MULTIFILE_REVIEW_GOAL_ID,
    MULTIFILE_DEPENDENCY_REPAIR_GOAL_ID,
    CROSS_FILE_REGRESSION_GOAL_ID,
    REVIEWER_DISAGREEMENT_GOAL_ID,
    JAVASCRIPT_SMOKE_GOAL_ID,
)
CODING_GOAL_TEXT = {
    "coding.skill_prototype_dryrun": "Develop a skill prototype through design, tests, and review.",
    "coding.skill_regression_fix_dryrun": "Fix a skill regression through design, checkout tests, and review.",
    FAILING_TEST_REPAIR_GOAL_ID: (
        "Repair a failing skill test through checkout, patch, passing tests, and review."
    ),
    MULTIFILE_REVIEW_GOAL_ID: (
        "Update a skill and its metadata through a multi-file patch, checkout tests, and rubric review."
    ),
    MULTIFILE_DEPENDENCY_REPAIR_GOAL_ID: (
        "Repair a cross-file dependency bug where tests pass only after coordinated source edits."
    ),
    CROSS_FILE_REGRESSION_GOAL_ID: (
        "Repair a cross-file regression where a normalization helper and its caller must change together."
    ),
    REVIEWER_DISAGREEMENT_GOAL_ID: (
        "Resolve conflicting rule-reviewer judgments through traceable arbitration."
    ),
    JAVASCRIPT_SMOKE_GOAL_ID: (
        "Validate a non-Python skill fixture through Node's built-in test runner."
    ),
}


class CodingDomainAdapter:
    """Secondary coding domain：用 repo fixture 验证接口可迁移到任务型开发。"""

    domain_id = "loomstead.coding.v0"
    kind = "task"

    def build_initial_world(self, scenario_id: str, seed: int) -> dict[str, Any]:
        goal = self.parse_goal(scenario_id)
        repo_fixture = _build_repo_fixture(goal.goal_id)
        fixture_metadata = (
            repo_fixture.get("metadata", {}) if isinstance(repo_fixture.get("metadata"), dict) else {}
        )
        dependencies = {"repoFixtureId": repo_fixture.get("fixtureId", "")}
        for key in ("metadataPath", "reviewRubricPath"):
            if repo_fixture.get(key):
                dependencies[key] = repo_fixture[key]
        dependencies["testRunner"] = str(fixture_metadata.get("testRunner") or "")
        return {
            "tick": 0,
            "seed": seed,
            "goalId": goal.goal_id,
            "repoFixture": repo_fixture,
            "agents": {
                "pm": {"role": "PM", "state": "scoping"},
                "architect": {"role": "Architect", "state": "waiting"},
                "implementer": {"role": "Implementer", "state": "waiting"},
                "reviewer": {"role": "Reviewer", "state": "waiting"},
                "process_reviewer": {"role": "Process Reviewer", "state": "waiting"},
                "risk_reviewer": {"role": "Risk Reviewer", "state": "waiting"},
            },
            "constraints": [],
            "artifacts": {},
            "prePatchTestReports": {},
            "partialPatchTestReports": {},
            "testReports": {},
            "reviewReports": {},
            "dependencies": dependencies,
            "events": [
                {
                    "id": "coding_evt_000",
                    "type": "domain.goal_loaded",
                    "payload": {"domainId": self.domain_id, "goalId": goal.goal_id},
                },
                {
                    "id": "coding_evt_001",
                    "type": "coding.repo_fixture_loaded",
                    "payload": {
                        "repoFixtureId": repo_fixture.get("fixtureId", ""),
                        "fileCount": len(repo_fixture.get("files", {})),
                        "metadataPath": repo_fixture.get("metadataPath"),
                        "reviewRubricPath": repo_fixture.get("reviewRubricPath"),
                        "testCommand": repo_fixture.get("testCommand"),
                        "testRunner": fixture_metadata.get("testRunner"),
                        "commandTemplate": fixture_metadata.get("commandTemplate"),
                    },
                },
            ],
        }

    def parse_goal(self, raw_goal: str) -> DomainGoalSpec:
        goal_id = raw_goal
        if raw_goal in CODING_GOAL_TEXT.values():
            goal_id = next(key for key, value in CODING_GOAL_TEXT.items() if value == raw_goal)
        if goal_id not in CODING_GOAL_IDS:
            raise ValueError(f"未知 coding goal：{raw_goal}")
        required_process = [
            {"id": "repo_fixture_loaded", "predicate": "external repo fixture is loaded before design"},
            {"id": "design_review_loaded", "predicate": "design review event is loaded before implementation"},
            {"id": "implementation_diff", "predicate": "implementer creates an artifact diff"},
            {
                "id": "external_repo_checkout_tested",
                "predicate": "evaluation checkpoint checks out external repo and runs its test command",
            },
            {"id": "review_completed", "predicate": "reviewer records approval with source evidence"},
            {"id": "failure_pattern_memory", "predicate": "review cites a prior failure or constraint memory"},
        ]
        if goal_id in (
            FAILING_TEST_REPAIR_GOAL_ID,
            MULTIFILE_DEPENDENCY_REPAIR_GOAL_ID,
            CROSS_FILE_REGRESSION_GOAL_ID,
        ):
            required_process.insert(
                3,
                {
                    "id": "pre_patch_failure_observed",
                    "predicate": "evaluation checkpoint records the failing test before implementation",
                },
            )
        if goal_id == MULTIFILE_REVIEW_GOAL_ID:
            required_process.insert(
                2,
                {
                    "id": "review_rubric_loaded",
                    "predicate": "review rubric is loaded before implementation",
                },
            )
            required_process.insert(
                4,
                {
                    "id": "metadata_dependency_updated",
                    "predicate": "implementation updates dependency metadata alongside skill content",
                },
            )
        if goal_id in (MULTIFILE_DEPENDENCY_REPAIR_GOAL_ID, CROSS_FILE_REGRESSION_GOAL_ID):
            required_process.insert(
                2,
                {
                    "id": "import_graph_recorded",
                    "predicate": "fixture records source import graph before the patch",
                },
            )
            required_process.insert(
                3,
                {
                    "id": "real_dependency_graph_recorded",
                    "predicate": "adapter derives a dependency graph from actual fixture imports",
                },
            )
            required_process.insert(
                6,
                {
                    "id": "patch_covers_multiple_source_files",
                    "predicate": "patch changes at least two dependency-linked source files",
                },
            )
            required_process.insert(
                7,
                {
                    "id": "single_file_patch_still_fails",
                    "predicate": "single-file partial patch replay still fails the repo tests",
                },
            )
            required_process.insert(
                8,
                {
                    "id": "dependency_evidence_chain_confirmed",
                    "predicate": "review report links pre/partial/post test evidence with command and exitCode",
                },
            )
        if goal_id == CROSS_FILE_REGRESSION_GOAL_ID:
            required_process.insert(
                9,
                {
                    "id": "regression_case_covered",
                    "predicate": "cross-file regression case remains red until both linked files are patched",
                },
            )
        if goal_id == REVIEWER_DISAGREEMENT_GOAL_ID:
            required_process.insert(
                5,
                {
                    "id": "reviewer_conflict_observed",
                    "predicate": "two rule reviewers produce approve and request_changes judgments",
                },
            )
            required_process.insert(
                6,
                {
                    "id": "arbitration_contributing_sources",
                    "predicate": "ArbitrationLayer records each reviewer scoring basis",
                },
            )
            required_process.insert(
                7,
                {
                    "id": "review_trace_ref_recorded",
                    "predicate": "review report records conflict resolution path and final trace ref",
                },
            )
        if goal_id == JAVASCRIPT_SMOKE_GOAL_ID:
            required_process.insert(
                2,
                {
                    "id": "non_python_fixture_loaded",
                    "predicate": "fixture metadata selects a non-Python runner and JavaScript source files",
                },
            )
        desired_artifact = {
            "coding.skill_prototype_dryrun": "skill_prototype",
            "coding.skill_regression_fix_dryrun": "skill_regression_fix",
            FAILING_TEST_REPAIR_GOAL_ID: "skill_failing_test_repair",
            MULTIFILE_REVIEW_GOAL_ID: "skill_multifile_review",
            MULTIFILE_DEPENDENCY_REPAIR_GOAL_ID: "skill_multifile_dependency_repair",
            CROSS_FILE_REGRESSION_GOAL_ID: "skill_cross_file_regression",
            REVIEWER_DISAGREEMENT_GOAL_ID: "skill_reviewer_disagreement",
            JAVASCRIPT_SMOKE_GOAL_ID: "skill_javascript_smoke",
        }[goal_id]
        success_evidence = ["design_event", "diff_event", "test_event", "review_event"]
        if goal_id in (
            FAILING_TEST_REPAIR_GOAL_ID,
            MULTIFILE_DEPENDENCY_REPAIR_GOAL_ID,
            CROSS_FILE_REGRESSION_GOAL_ID,
        ):
            success_evidence.insert(1, "pre_patch_test_event")
        if goal_id == REVIEWER_DISAGREEMENT_GOAL_ID:
            success_evidence.append("review_arbitration_trace")
        return DomainGoalSpec(
            goal_id=goal_id,
            natural_language_goal=CODING_GOAL_TEXT[goal_id],
            desired_outcome={"artifact": desired_artifact, "reviewStatus": "approved", "tests": "passed"},
            forbidden_shortcuts=[
                "direct_artifact_without_design",
                "review_status_set_without_review",
                "delete_failing_test",
                "mark_regression_fixed_without_checkout_test",
            ],
            required_process=required_process,
            allowed_interventions=["event_skill_load", "constraint_injection", "evaluation_checkpoint"],
            success_evidence=success_evidence,
            max_steps=5
            if goal_id in (
                FAILING_TEST_REPAIR_GOAL_ID,
                MULTIFILE_DEPENDENCY_REPAIR_GOAL_ID,
                CROSS_FILE_REGRESSION_GOAL_ID,
            )
            else 4,
        )

    def observe(self, world: dict[str, Any], goal: DomainGoalSpec) -> DomainObservation:
        return DomainObservation(
            tick=int(world.get("tick", 0)),
            world_summary={
                "artifactCount": float(len(world.get("artifacts", {}))),
                "prePatchTestReportCount": float(len(world.get("prePatchTestReports", {}))),
                "partialPatchTestReportCount": float(len(world.get("partialPatchTestReports", {}))),
                "testReportCount": float(len(world.get("testReports", {}))),
                "reviewReportCount": float(len(world.get("reviewReports", {}))),
                "constraintCount": float(len(world.get("constraints", []))),
                "repoFixtureId": str(world.get("repoFixture", {}).get("fixtureId", "")),
                "testRunner": str(
                    (
                        world.get("repoFixture", {}).get("metadata", {})
                        if isinstance(world.get("repoFixture", {}).get("metadata"), dict)
                        else {}
                    ).get("testRunner", "")
                ),
                "repoFileRefs": sorted(str(key) for key in world.get("repoFixture", {}).get("files", {}).keys())
                if isinstance(world.get("repoFixture"), dict)
                else [],
                "artifactRefs": sorted(str(key) for key in world.get("artifacts", {}).keys()),
                "prePatchTestReportRefs": sorted(
                    str(key) for key in world.get("prePatchTestReports", {}).keys()
                ),
                "partialPatchTestReportRefs": sorted(
                    str(key) for key in world.get("partialPatchTestReports", {}).keys()
                ),
                "testReportRefs": sorted(str(key) for key in world.get("testReports", {}).keys()),
                "reviewReportRefs": sorted(str(key) for key in world.get("reviewReports", {}).keys()),
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
        artifacts = world.get("artifacts", {}) if isinstance(world.get("artifacts"), dict) else {}
        pre_patch_reports = (
            world.get("prePatchTestReports", {}) if isinstance(world.get("prePatchTestReports"), dict) else {}
        )
        partial_patch_reports = (
            world.get("partialPatchTestReports", {}) if isinstance(world.get("partialPatchTestReports"), dict) else {}
        )
        test_reports = world.get("testReports", {}) if isinstance(world.get("testReports"), dict) else {}
        review_reports = world.get("reviewReports", {}) if isinstance(world.get("reviewReports"), dict) else {}
        repo_fixture = world.get("repoFixture", {}) if isinstance(world.get("repoFixture"), dict) else {}
        fixture_metadata = (
            repo_fixture.get("metadata", {}) if isinstance(repo_fixture.get("metadata"), dict) else {}
        )
        repo_files = repo_fixture.get("files", {}) if isinstance(repo_fixture.get("files"), dict) else {}
        artifact_id = str(repo_fixture.get("artifactId") or "skill_prototype.patch")
        pre_patch_test_report_id = str(repo_fixture.get("prePatchTestReportId") or "skill_prototype.pre_patch_tests")
        test_report_id = str(repo_fixture.get("testReportId") or "skill_prototype.tests")
        review_report_id = str(repo_fixture.get("reviewReportId") or "skill_prototype.review")
        pre_patch_report = pre_patch_reports.get(pre_patch_test_report_id, {})
        test_report = test_reports.get(test_report_id, {})
        review_report = review_reports.get(review_report_id, {})
        artifact = artifacts.get(artifact_id, {}) if isinstance(artifacts.get(artifact_id), dict) else {}
        changed_files = [str(path) for path in artifact.get("changedFiles", [])] if isinstance(
            artifact.get("changedFiles"), list
        ) else []
        metadata_path = str(repo_fixture.get("metadataPath") or "")
        review_rubric_path = str(repo_fixture.get("reviewRubricPath") or "")
        import_graph = repo_fixture.get("importGraph", {}) if isinstance(repo_fixture.get("importGraph"), dict) else {}
        derived_dependency_graph = (
            repo_fixture.get("derivedDependencyGraph", {})
            if isinstance(repo_fixture.get("derivedDependencyGraph"), dict)
            else {}
        )
        dependency_evidence = artifact.get("dependencyEvidence", {}) if isinstance(artifact.get("dependencyEvidence"), dict) else {}
        patch_coverage_file_count = int(artifact.get("patchCoverageFileCount") or 0)
        source_changed_files = [
            path
            for path in changed_files
            if path.startswith("src/") and path.endswith(".py")
        ]
        partial_reports = [
            report for report in partial_patch_reports.values() if isinstance(report, dict)
        ]
        single_file_patch_still_fails = bool(partial_reports) and all(
            bool(report.get("expectedFailure"))
            and bool(report.get("failureObserved"))
            and report.get("execution", {}).get("exitCode") not in (None, 0)
            for report in partial_reports
        )
        dependency_evidence_chain = (
            review_report.get("dependencyEvidenceChain", {})
            if isinstance(review_report.get("dependencyEvidenceChain"), dict)
            else {}
        )
        dependency_chain_pre = (
            dependency_evidence_chain.get("prePatch", {})
            if isinstance(dependency_evidence_chain.get("prePatch"), dict)
            else {}
        )
        dependency_chain_post = (
            dependency_evidence_chain.get("postPatch", {})
            if isinstance(dependency_evidence_chain.get("postPatch"), dict)
            else {}
        )
        dependency_chain_partials = (
            dependency_evidence_chain.get("partialPatchFailures", [])
            if isinstance(dependency_evidence_chain.get("partialPatchFailures"), list)
            else []
        )
        dependency_chain_confirmed = bool(dependency_evidence_chain) and all(
            (
                dependency_evidence_chain.get("chainVersion") == "coding.dependency_evidence_chain.v2",
                bool(dependency_chain_pre.get("testRunner")),
                bool(dependency_chain_pre.get("command")),
                dependency_chain_pre.get("exitCode") not in (None, 0),
                bool(dependency_chain_post.get("testRunner")),
                bool(dependency_chain_post.get("command")),
                dependency_chain_post.get("exitCode") == 0,
                bool(dependency_chain_partials),
                all(
                    isinstance(item, dict)
                    and bool(item.get("testRunner"))
                    and bool(item.get("command"))
                    and item.get("exitCode") not in (None, 0)
                    for item in dependency_chain_partials
                ),
                bool(dependency_evidence_chain.get("allExpectedFailuresObserved")),
                bool(dependency_evidence_chain.get("consistentRunner")),
                bool(dependency_evidence_chain.get("transitionEdges")),
                bool(dependency_evidence_chain.get("caseEvidence")),
            )
        )
        reviewer_evaluations = (
            review_report.get("reviewerEvaluations", [])
            if isinstance(review_report.get("reviewerEvaluations"), list)
            else []
        )
        reviewer_decisions = {
            str(item.get("decision") or "")
            for item in reviewer_evaluations
            if isinstance(item, dict)
        }
        arbitration_layer = (
            review_report.get("arbitrationLayer", {})
            if isinstance(review_report.get("arbitrationLayer"), dict)
            else {}
        )
        pre_patch_cases = (
            pre_patch_report.get("caseResults", []) if isinstance(pre_patch_report.get("caseResults"), list) else []
        )
        pre_patch_failure_observed = (
            "coding.pre_patch_tests_failed" in event_types
            and bool(pre_patch_report.get("expectedFailure"))
            and bool(pre_patch_report.get("execution", {}).get("executed"))
            and pre_patch_report.get("execution", {}).get("exitCode") not in (None, 0)
            and any(not bool(case.get("passed")) for case in pre_patch_cases if isinstance(case, dict))
        )
        process_checks = {
            "repo_fixture_loaded": "coding.repo_fixture_loaded" in event_types and bool(repo_fixture.get("files")),
            "non_python_fixture_loaded": fixture_metadata.get("testRunner") == "node_test"
            and any(str(path).endswith((".js", ".mjs", ".cjs")) for path in repo_files.keys()),
            "design_review_loaded": "coding.design_review_loaded" in event_types,
            "review_rubric_loaded": "coding.review_rubric_loaded" in event_types
            and bool(review_rubric_path)
            and review_rubric_path in repo_fixture.get("files", {}),
            "pre_patch_failure_observed": pre_patch_failure_observed,
            "implementation_diff": "coding.implementation_diff_created" in event_types
            and artifact_id in artifacts,
            "metadata_dependency_updated": bool(metadata_path)
            and metadata_path in changed_files
            and bool(artifact.get("fileSha256", {}).get(metadata_path)),
            "import_graph_recorded": bool(import_graph.get("nodes")) and bool(import_graph.get("edges")),
            "real_dependency_graph_recorded": bool(derived_dependency_graph.get("nodes"))
            and bool(derived_dependency_graph.get("edges"))
            and not derived_dependency_graph.get("missingDeclaredEdges"),
            "patch_covers_multiple_source_files": patch_coverage_file_count >= 2
            and len(source_changed_files) >= 2
            and bool(dependency_evidence.get("importGraph")),
            "single_file_patch_still_fails": single_file_patch_still_fails,
            "dependency_evidence_chain_confirmed": dependency_chain_confirmed,
            "regression_case_covered": _regression_case_covered(
                goal.goal_id,
                pre_patch_report if isinstance(pre_patch_report, dict) else {},
                test_report if isinstance(test_report, dict) else {},
                partial_reports,
            ),
            "external_repo_checkout_tested": "coding.tests_executed" in event_types
            and bool(test_report.get("passed"))
            and test_report.get("testPhase") == "post_patch"
            and bool(test_report.get("execution", {}).get("executed"))
            and test_report.get("execution", {}).get("testPhase") == "post_patch"
            and test_report.get("execution", {}).get("exitCode") == 0,
            "review_completed": bool(review_event) and review_report.get("status") == "approved",
            "reviewer_conflict_observed": bool(review_report.get("conflict", {}).get("conflictDetected"))
            and {"approve", "request_changes"}.issubset(reviewer_decisions),
            "arbitration_contributing_sources": len(arbitration_layer.get("contributing_sources", [])) >= 2
            and all(
                isinstance(item, dict) and bool(item.get("sourceEventId"))
                for item in arbitration_layer.get("contributing_sources", [])
            ),
            "review_trace_ref_recorded": bool(
                review_report.get("finalDecisionTraceRef", {}).get("eventId")
            ),
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
        counterfactual_replay = _ensure_coding_counterfactual_replay(
            world,
            goal_id=goal.goal_id,
            repo_fixture=repo_fixture,
            artifact=artifact,
            pre_patch_report=pre_patch_report if isinstance(pre_patch_report, dict) else {},
            partial_patch_reports=partial_patch_reports,
            test_report=test_report if isinstance(test_report, dict) else {},
            review_report=review_report if isinstance(review_report, dict) else {},
        )
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
            counterfactual_tool_selection_change_rate=float(
                counterfactual_replay.get("changeRate", 0.0)
            ),
            goal_success_override=process_checks["review_completed"] and process_checks["external_repo_checkout_tested"],
        )

    def export_trace(self, world: dict[str, Any], run_dir: str) -> None:
        # 导出 coding dry-run 的可审计工件，便于单独复核 artifact / test / review 链路。
        path = Path(run_dir)
        path.mkdir(parents=True, exist_ok=True)
        (path / "coding_events.jsonl").write_text(
            "".join(json.dumps(event, ensure_ascii=False) + "\n" for event in world.get("events", [])),
            encoding="utf-8",
        )
        for key, filename in (
            ("repoFixture", "coding_repo_fixture.json"),
            ("artifacts", "coding_artifacts.json"),
            ("prePatchTestReports", "coding_pre_patch_test_reports.json"),
            ("partialPatchTestReports", "coding_partial_patch_test_reports.json"),
            ("testReports", "coding_test_reports.json"),
            ("reviewReports", "coding_review_reports.json"),
        ):
            (path / filename).write_text(
                json.dumps(world.get(key, {}), ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        for artifact_id, artifact in sorted(world.get("artifacts", {}).items()):
            if not isinstance(artifact, dict):
                continue
            patch_text = str(artifact.get("patchText", ""))
            if patch_text:
                patch_filename = artifact_id if str(artifact_id).endswith(".patch") else f"{artifact_id}.patch"
                (path / patch_filename).write_text(patch_text + "\n", encoding="utf-8")


def _advance_coding_world(world: dict[str, Any]) -> list[dict[str, Any]]:
    emitted: list[dict[str, Any]] = []
    event_types = {str(event.get("type") or "") for event in world.get("events", [])}
    if "coding.design_review_loaded" not in event_types:
        repo_fixture = world.get("repoFixture", {}) if isinstance(world.get("repoFixture"), dict) else {}
        design_event = _append_event(
            world,
            "coding.design_review_loaded",
            {
                "agentId": "architect",
                "designDocRef": repo_fixture.get("designDocRef", "design.skill_prototype.v1"),
                "repoFixtureId": repo_fixture.get("fixtureId", ""),
                "acceptedConstraints": ["must_run_tests"],
                "reviewRubricPath": repo_fixture.get("reviewRubricPath"),
            },
        )
        emitted.append(design_event)
        if repo_fixture.get("reviewRubricPath"):
            emitted.append(
                _append_event(
                    world,
                    "coding.review_rubric_loaded",
                    {
                        "agentId": "architect",
                        "reviewRubricPath": repo_fixture.get("reviewRubricPath"),
                        "sourceEventIds": [_event_id(design_event)],
                    },
                )
            )
        world["agents"]["architect"]["state"] = "design_reviewed"
    elif _requires_pre_patch_failure(world) and "coding.pre_patch_tests_failed" not in event_types:
        design_event = _first_event(world, "coding.design_review_loaded")
        repo_fixture = world.get("repoFixture", {}) if isinstance(world.get("repoFixture"), dict) else {}
        pre_patch_test_report_id = str(
            repo_fixture.get("prePatchTestReportId") or "skill_failing_test_repair.pre_patch_tests"
        )
        base_artifact = {
            "artifactId": "pre_patch_fixture_state",
            "patchedFiles": repo_fixture.get("files", {}) if isinstance(repo_fixture.get("files"), dict) else {},
        }
        test_cases, execution = _run_external_checkout_fixture_tests(
            base_artifact,
            repo_fixture,
            test_phase="pre_patch",
        )
        failing_case_ids = [
            str(item.get("caseId") or "unknown_case")
            for item in test_cases
            if isinstance(item, dict) and not bool(item.get("passed"))
        ]
        failure_observed = execution.get("exitCode") not in (None, 0) and bool(failing_case_ids)
        pre_patch_report = {
            "testReportId": pre_patch_test_report_id,
            "command": execution.get("command", "python check_fixture.py <worktree>"),
            "testRunner": execution.get("testRunner"),
            "durationMs": execution.get("durationMs"),
            "exitCode": execution.get("exitCode"),
            "testPhase": "pre_patch",
            "passed": False,
            "expectedFailure": True,
            "failureObserved": failure_observed,
            "failingCaseIds": failing_case_ids,
            "caseResults": test_cases,
            "execution": execution,
            "sourceArtifactId": base_artifact["artifactId"],
            "sourceEventIds": [_event_id(design_event)],
        }
        pre_patch_report["sha256"] = _stable_digest(
            json.dumps(pre_patch_report, ensure_ascii=False, sort_keys=True)
        )
        world.setdefault("prePatchTestReports", {})[pre_patch_test_report_id] = pre_patch_report
        emitted.append(
            _append_event(
                world,
                "coding.pre_patch_tests_failed",
                {
                    "agentId": "reviewer",
                    "testReportId": pre_patch_report["testReportId"],
                    "expectedFailure": True,
                    "failureObserved": failure_observed,
                    "failingCaseIds": failing_case_ids,
                    "exitCode": execution.get("exitCode"),
                    "testRunner": execution.get("testRunner"),
                    "command": execution.get("command"),
                    "workspaceKind": execution.get("workspaceKind"),
                    "sourceEventIds": pre_patch_report["sourceEventIds"],
                    "testReportSha256": pre_patch_report["sha256"],
                },
            )
        )
        world["agents"]["reviewer"]["state"] = "pre_patch_failure_observed"
    elif "coding.implementation_diff_created" not in event_types:
        design_event = _first_event(world, "coding.design_review_loaded")
        repo_fixture = world.get("repoFixture", {}) if isinstance(world.get("repoFixture"), dict) else {}
        patch_text, patched_files, changed_files = _build_skill_patch(repo_fixture)
        base_files = repo_fixture.get("files", {}) if isinstance(repo_fixture.get("files"), dict) else {}
        dependency_evidence = _build_dependency_patch_evidence(repo_fixture, base_files, patched_files, changed_files)
        target_path = changed_files[0] if changed_files else str(
            repo_fixture.get("targetPath") or "skills/loomstead-debug/SKILL.md"
        )
        artifact_id = str(repo_fixture.get("artifactId") or "skill_prototype.patch")
        artifact = {
            "artifactId": artifact_id,
            "kind": "repo_patch",
            "repoFixtureId": repo_fixture.get("fixtureId", ""),
            "path": target_path,
            "status": "created",
            "sourceEventIds": [_event_id(design_event)],
            "changedFiles": changed_files,
            "patchCoverageFileCount": len(changed_files),
            "baseFileSha256": _stable_digest(str(base_files.get(target_path, ""))),
            "patchedFileSha256": _stable_digest(str(patched_files.get(target_path, ""))),
            "fileSha256": {
                path: {
                    "base": _stable_digest(str(base_files.get(path, ""))),
                    "patched": _stable_digest(str(patched_files.get(path, ""))),
                }
                for path in changed_files
            },
            "patchText": patch_text,
            "patchedFiles": patched_files,
            "sha256": _stable_digest(patch_text),
        }
        if dependency_evidence:
            artifact["dependencyEvidence"] = dependency_evidence
        world.setdefault("artifacts", {})[artifact_id] = artifact
        emitted.append(
            _append_event(
                world,
                "coding.implementation_diff_created",
                {
                    "agentId": "implementer",
                    "artifactId": artifact["artifactId"],
                    "sourceEventIds": artifact["sourceEventIds"],
                    "artifactSha256": artifact["sha256"],
                    "changedFiles": artifact["changedFiles"],
                    "patchCoverageFileCount": artifact["patchCoverageFileCount"],
                },
            )
        )
        world["agents"]["implementer"]["state"] = "diff_created"
    elif "coding.tests_executed" not in event_types:
        diff_event = _first_event(world, "coding.implementation_diff_created")
        repo_fixture = world.get("repoFixture", {}) if isinstance(world.get("repoFixture"), dict) else {}
        artifact_id = str(repo_fixture.get("artifactId") or "skill_prototype.patch")
        test_report_id = str(repo_fixture.get("testReportId") or "skill_prototype.tests")
        artifact = world.get("artifacts", {}).get(artifact_id, {})
        test_cases, execution = _run_external_checkout_fixture_tests(
            artifact,
            repo_fixture,
            test_phase="post_patch",
        )
        test_report = {
            "testReportId": test_report_id,
            "command": execution.get("command", "python check_fixture.py <worktree>"),
            "testRunner": execution.get("testRunner"),
            "durationMs": execution.get("durationMs"),
            "exitCode": execution.get("exitCode"),
            "testPhase": "post_patch",
            "passed": execution.get("exitCode") == 0
            and bool(test_cases)
            and all(bool(item.get("passed")) for item in test_cases),
            "caseResults": test_cases,
            "execution": execution,
            "sourceArtifactId": artifact.get("artifactId", "skill_prototype.patch"),
            "sourceEventIds": [_event_id(diff_event)],
        }
        test_report["sha256"] = _stable_digest(json.dumps(test_report, ensure_ascii=False, sort_keys=True))
        world.setdefault("testReports", {})[test_report_id] = test_report
        emitted.append(
            _append_event(
                world,
                "coding.tests_executed",
                {
                    "agentId": "reviewer",
                    "testReportId": test_report["testReportId"],
                    "passed": bool(test_report["passed"]),
                    "exitCode": execution.get("exitCode"),
                    "testRunner": execution.get("testRunner"),
                    "command": execution.get("command"),
                    "workspaceKind": execution.get("workspaceKind"),
                    "sourceArtifactId": test_report["sourceArtifactId"],
                    "sourceEventIds": test_report["sourceEventIds"],
                    "testReportSha256": test_report["sha256"],
                },
            )
        )
        if repo_fixture.get("requiresSingleFileFailureEvidence"):
            partial_reports = _run_single_file_partial_patch_reports(artifact, repo_fixture)
            for report in partial_reports.values():
                if isinstance(report, dict):
                    report["sourceEventIds"] = [_event_id(diff_event)]
                    report["sourcePostPatchTestReportId"] = test_report["testReportId"]
                    report["sourcePrePatchTestReportId"] = repo_fixture.get("prePatchTestReportId")
                    report["sha256"] = _stable_digest(json.dumps(report, ensure_ascii=False, sort_keys=True))
            world.setdefault("partialPatchTestReports", {}).update(partial_reports)
            failing_report_ids = [
                report_id
                for report_id, report in partial_reports.items()
                if isinstance(report, dict) and bool(report.get("failureObserved"))
            ]
            emitted.append(
                _append_event(
                    world,
                    "coding.partial_patch_tests_failed",
                    {
                        "agentId": "reviewer",
                        "partialPatchTestReportIds": sorted(failing_report_ids),
                        "expectedFailure": True,
                        "failureObserved": len(failing_report_ids) == len(partial_reports),
                        "testRunner": _fixture_test_runner(repo_fixture),
                        "command": _command_template_for_runner(_fixture_test_runner(repo_fixture)),
                        "sourceArtifactId": artifact.get("artifactId", "skill_prototype.patch")
                        if isinstance(artifact, dict)
                        else "skill_prototype.patch",
                        "sourceEventIds": [_event_id(diff_event)],
                    },
                )
            )
    elif "coding.review_completed" not in event_types:
        test_event = _first_event(world, "coding.tests_executed")
        pre_patch_event = _first_event(world, "coding.pre_patch_tests_failed")
        repo_fixture = world.get("repoFixture", {}) if isinstance(world.get("repoFixture"), dict) else {}
        pre_patch_test_report_id = str(
            repo_fixture.get("prePatchTestReportId") or "skill_failing_test_repair.pre_patch_tests"
        )
        test_report_id = str(repo_fixture.get("testReportId") or "skill_prototype.tests")
        review_report_id = str(repo_fixture.get("reviewReportId") or "skill_prototype.review")
        requires_pre_patch = _requires_pre_patch_failure(world)
        artifact_id = str(repo_fixture.get("artifactId") or "skill_prototype.patch")
        artifact = world.get("artifacts", {}).get(artifact_id, {})
        changed_files = [str(path) for path in artifact.get("changedFiles", [])] if isinstance(
            artifact, dict
        ) and isinstance(artifact.get("changedFiles"), list) else []
        metadata_path = str(repo_fixture.get("metadataPath") or "")
        review_rubric_path = str(repo_fixture.get("reviewRubricPath") or "")
        pre_patch_report = world.get("prePatchTestReports", {}).get(pre_patch_test_report_id, {})
        test_report = world.get("testReports", {}).get(test_report_id, {})
        source_event_ids = [_event_id(test_event)]
        if requires_pre_patch:
            source_event_ids.insert(0, _event_id(pre_patch_event))
        checklist = [
            {"id": "repo_fixture_loaded", "passed": True},
            {"id": "design_before_diff", "passed": True},
            {
                "id": "external_checkout_tests_before_review",
                "passed": bool(test_report.get("execution", {}).get("executed"))
                and test_report.get("execution", {}).get("exitCode") == 0,
            },
            {"id": "failure_memory_cited", "passed": True},
        ]
        if review_rubric_path:
            checklist.insert(
                2,
                {
                    "id": "review_rubric_loaded",
                    "passed": "coding.review_rubric_loaded" in event_types
                    and review_rubric_path in repo_fixture.get("files", {}),
                },
            )
        if metadata_path:
            checklist.insert(
                3 if review_rubric_path else 2,
                {
                    "id": "metadata_dependency_updated",
                    "passed": metadata_path in changed_files
                    and bool(artifact.get("fileSha256", {}).get(metadata_path))
                    if isinstance(artifact, dict)
                    else False,
                },
            )
        if requires_pre_patch:
            checklist.insert(
                2,
                {
                    "id": "pre_patch_failure_observed",
                    "passed": bool(pre_patch_report.get("failureObserved"))
                    and pre_patch_report.get("execution", {}).get("exitCode") not in (None, 0),
                },
            )
        if repo_fixture.get("requiresSingleFileFailureEvidence"):
            partial_patch_reports = (
                world.get("partialPatchTestReports", {})
                if isinstance(world.get("partialPatchTestReports"), dict)
                else {}
            )
            derived_dependency_graph = (
                repo_fixture.get("derivedDependencyGraph", {})
                if isinstance(repo_fixture.get("derivedDependencyGraph"), dict)
                else {}
            )
            partial_failures = [
                report
                for report in partial_patch_reports.values()
                if isinstance(report, dict) and bool(report.get("failureObserved"))
            ]
            checklist.insert(
                3,
                {
                    "id": "single_file_patch_still_fails",
                    "passed": bool(partial_failures)
                    and len(partial_failures) == len(partial_patch_reports),
                },
            )
            checklist.insert(
                3,
                {
                    "id": "real_dependency_graph_recorded",
                    "passed": bool(derived_dependency_graph.get("nodes"))
                    and bool(derived_dependency_graph.get("edges"))
                    and not derived_dependency_graph.get("missingDeclaredEdges"),
                },
            )
            dependency_chain = _build_dependency_evidence_chain(
                pre_patch_report=pre_patch_report if isinstance(pre_patch_report, dict) else {},
                post_patch_report=test_report if isinstance(test_report, dict) else {},
                partial_patch_reports=partial_patch_reports,
            )
            checklist.insert(
                4,
                {
                    "id": "dependency_evidence_chain_confirmed",
                    "passed": bool(dependency_chain.get("allExpectedFailuresObserved"))
                    and bool(dependency_chain.get("consistentRunner"))
                    and bool(dependency_chain.get("transitionEdges"))
                    and bool(dependency_chain.get("caseEvidence"))
                    and dependency_chain.get("prePatch", {}).get("exitCode") not in (None, 0)
                    and dependency_chain.get("postPatch", {}).get("exitCode") == 0,
                },
            )
            if world.get("goalId") == CROSS_FILE_REGRESSION_GOAL_ID:
                checklist.insert(
                    5,
                    {
                        "id": "regression_case_covered",
                        "passed": _regression_case_covered(
                            str(world.get("goalId") or ""),
                            pre_patch_report if isinstance(pre_patch_report, dict) else {},
                            test_report if isinstance(test_report, dict) else {},
                            partial_failures,
                        ),
                    },
                )
        else:
            dependency_chain = {}
        cited_memory_ids = ["prior_failure.skip_tests"]
        if requires_pre_patch:
            cited_memory_ids.append("prior_failure.failing_test_first")
        if repo_fixture.get("requiresReviewerDisagreement"):
            cited_memory_ids.append("prior_review.conflict_resolution")
        reviewer_evaluations = _build_rule_reviewer_evaluations(
            repo_fixture=repo_fixture,
            artifact=artifact if isinstance(artifact, dict) else {},
            test_report=test_report if isinstance(test_report, dict) else {},
            checklist=checklist,
        )
        if reviewer_evaluations:
            enriched_evaluations: list[dict[str, Any]] = []
            for evaluation in reviewer_evaluations:
                if not isinstance(evaluation, dict):
                    continue
                # reviewer judgment 先落事件，再进入 ArbitrationLayer，保证分歧来源可追溯。
                judgment_event = _append_event(
                    world,
                    "coding.reviewer_judgment_recorded",
                    {
                        "agentId": str(evaluation.get("reviewerId") or "reviewer"),
                        "reviewReportId": review_report_id,
                        "decision": evaluation.get("decision"),
                        "score": evaluation.get("score"),
                        "focus": evaluation.get("focus"),
                        "grounds": evaluation.get("grounds", []),
                        "sourceEventIds": list(source_event_ids),
                    },
                )
                emitted.append(judgment_event)
                enriched = dict(evaluation)
                enriched["sourceEventId"] = _event_id(judgment_event)
                enriched["sourceEventIds"] = list(source_event_ids) + [_event_id(judgment_event)]
                enriched_evaluations.append(enriched)
            reviewer_evaluations = enriched_evaluations
        arbitration_layer = _arbitrate_reviewer_disagreement(
            reviewer_evaluations=reviewer_evaluations,
            test_report=test_report if isinstance(test_report, dict) else {},
            source_event_ids=source_event_ids,
            review_report_id=review_report_id,
        )
        review_report = {
            "reviewReportId": review_report_id,
            "status": "approved",
            "sourcePrePatchTestReportId": pre_patch_report.get("testReportId", pre_patch_test_report_id)
            if requires_pre_patch
            else None,
            "sourceTestReportId": test_report.get("testReportId", test_report_id),
            "sourceEventIds": source_event_ids,
            "repoFixtureId": world.get("repoFixture", {}).get("fixtureId", ""),
            "reviewRubricPath": review_rubric_path or None,
            "metadataPath": metadata_path or None,
            "citedMemoryIds": cited_memory_ids,
            "checklist": checklist,
        }
        if reviewer_evaluations:
            review_report["reviewerEvaluations"] = reviewer_evaluations
            review_report["conflict"] = {
                "conflictDetected": {"approve", "request_changes"}.issubset(
                    {str(item.get("decision") or "") for item in reviewer_evaluations}
                ),
                "conflictingReviewerIds": [
                    str(item.get("reviewerId") or "")
                    for item in reviewer_evaluations
                    if str(item.get("decision") or "") in {"approve", "request_changes"}
                ],
            }
            review_report["arbitrationLayer"] = arbitration_layer
            review_report["conflictResolutionPath"] = arbitration_layer.get("resolutionPath", [])
            review_report["status"] = str(arbitration_layer.get("finalDecision") or "approved")
            conflict_event = _append_event(
                world,
                "coding.review_conflict_arbitrated",
                {
                    "agentId": "reviewer",
                    "reviewReportId": review_report_id,
                    "traceId": arbitration_layer.get("traceId"),
                    "finalDecision": review_report["status"],
                    "contributing_sources": arbitration_layer.get("contributing_sources", []),
                    "sourceEventIds": list(source_event_ids),
                },
            )
            emitted.append(conflict_event)
            source_event_ids.append(_event_id(conflict_event))
            review_report["sourceEventIds"] = list(source_event_ids)
            review_report["finalDecisionTraceRef"] = {
                "type": "coding_review_arbitration",
                "traceId": arbitration_layer.get("traceId"),
                "eventId": _event_id(conflict_event),
                "finalDecision": review_report["status"],
            }
        if dependency_chain:
            review_report["dependencyEvidenceChain"] = dependency_chain
        review_report["sha256"] = _stable_digest(json.dumps(review_report, ensure_ascii=False, sort_keys=True))
        world.setdefault("reviewReports", {})[review_report_id] = review_report
        emitted.append(
            _append_event(
                world,
                "coding.review_completed",
                {
                    "agentId": "reviewer",
                    "reviewReportId": review_report["reviewReportId"],
                    "status": review_report["status"],
                    "sourceTestReportId": review_report["sourceTestReportId"],
                    "sourceEventIds": review_report["sourceEventIds"],
                    "citedMemoryIds": review_report["citedMemoryIds"],
                    "reviewReportSha256": review_report["sha256"],
                },
            )
        )
        world["agents"]["reviewer"]["state"] = "approved"
    return emitted


def _requires_pre_patch_failure(world: dict[str, Any]) -> bool:
    """判断当前 fixture 是否要求先记录失败测试，再进入修复补丁。"""
    repo_fixture = world.get("repoFixture", {}) if isinstance(world.get("repoFixture"), dict) else {}
    return bool(repo_fixture.get("requiresPrePatchFailure"))


def _build_repo_fixture(goal_id: str) -> dict[str, Any]:
    """构造可重复的外部仓库 fixture，模拟跨域 coding 输入。"""
    requires_pre_patch_failure = False
    requires_single_file_failure_evidence = False
    requires_reviewer_disagreement = False
    pre_patch_test_report_id = None
    metadata_path = None
    review_rubric_path = None
    test_runner = "pytest"
    target_path = "skills/loomstead-debug/SKILL.md"
    import_graph: dict[str, Any] = {}
    reviewer_rubrics: list[dict[str, Any]] = []
    planned_file_updates: list[dict[str, Any]] = []
    if goal_id == FAILING_TEST_REPAIR_GOAL_ID:
        fixture_id = "loomstead-debug-failing-test-fixture.v1"
        artifact_id = "skill_failing_test_repair.patch"
        test_report_id = "skill_failing_test_repair.tests"
        pre_patch_test_report_id = "skill_failing_test_repair.pre_patch_tests"
        review_report_id = "skill_failing_test_repair.review"
        requires_pre_patch_failure = True
        planned_additions = [
            "Add failing test evidence before repair.",
            "Run eval:domain after the repair passes.",
        ]
        test_expectations = [
            {"caseId": "loads_skill_md", "type": "startswith", "value": "# Loomstead Debug Skill"},
            {"caseId": "keeps_existing_doc_guidance", "type": "contains", "value": "Use project docs"},
            {
                "caseId": "requires_failing_test_evidence",
                "type": "contains",
                "value": "failing test evidence before repair",
            },
            {"caseId": "requires_eval_domain_after_repair", "type": "contains", "value": "eval:domain"},
        ]
    elif goal_id == MULTIFILE_REVIEW_GOAL_ID:
        test_runner = "unittest"
        fixture_id = "loomstead-debug-multifile-fixture.v1"
        artifact_id = "skill_multifile_review.patch"
        test_report_id = "skill_multifile_review.tests"
        review_report_id = "skill_multifile_review.review"
        metadata_path = "skills/loomstead-debug/metadata.json"
        review_rubric_path = "docs/review_rubric.md"
        planned_additions = [
            "Review against docs/review_rubric.md before approving metadata-sensitive changes.",
            "Record eval:domain evidence in skill metadata quality gates.",
        ]
        planned_file_updates = [
            {
                "path": "skills/loomstead-debug/SKILL.md",
                "appendLines": planned_additions,
            },
            {
                "path": metadata_path,
                "jsonMerge": {
                    "version": "0.2.0",
                    "requiresReviewRubric": True,
                    "qualityGates": ["manual_review", "eval:domain", "review_rubric"],
                },
            },
            {
                "path": review_rubric_path,
                "appendLines": [
                    "Verify metadata qualityGates includes eval:domain.",
                    "Verify skill instructions cite docs/review_rubric.md.",
                ],
            },
        ]
        test_expectations = [
            {
                "caseId": "loads_skill_md",
                "type": "startswith",
                "path": "skills/loomstead-debug/SKILL.md",
                "value": "# Loomstead Debug Skill",
            },
            {
                "caseId": "skill_cites_review_rubric",
                "type": "contains",
                "path": "skills/loomstead-debug/SKILL.md",
                "value": "Review against docs/review_rubric.md",
            },
            {
                "caseId": "metadata_requires_rubric",
                "type": "json_field_equals",
                "path": metadata_path,
                "field": "requiresReviewRubric",
                "value": True,
            },
            {
                "caseId": "metadata_eval_domain_gate",
                "type": "json_array_contains",
                "path": metadata_path,
                "field": "qualityGates",
                "value": "eval:domain",
            },
            {
                "caseId": "rubric_mentions_metadata_gate",
                "type": "contains",
                "path": review_rubric_path,
                "value": "metadata qualityGates includes eval:domain",
            },
        ]
    elif goal_id == MULTIFILE_DEPENDENCY_REPAIR_GOAL_ID:
        fixture_id = "loomstead-debug-multifile-dependency-fixture.v1"
        artifact_id = "skill_multifile_dependency_repair.patch"
        test_report_id = "skill_multifile_dependency_repair.tests"
        pre_patch_test_report_id = "skill_multifile_dependency_repair.pre_patch_tests"
        review_report_id = "skill_multifile_dependency_repair.review"
        requires_pre_patch_failure = True
        requires_single_file_failure_evidence = True
        target_path = "src/formatter.py"
        import_graph = {
            "nodes": [
                "src/formatter.py",
                "src/workflow.py",
                "tests/test_skill.py",
            ],
            "edges": [
                {"from": "src/workflow.py", "imports": "src/formatter.py", "symbols": ["display_name", "slugify"]},
                {"from": "tests/test_skill.py", "imports": "src/workflow.py", "symbols": ["build_ticket"]},
            ],
        }
        planned_additions = []
        planned_file_updates = [
            {
                "path": "src/formatter.py",
                "replace": {
                    "def slugify(name: str) -> str:\n    return name\n": (
                        "def slugify(name: str) -> str:\n"
                        "    return '-'.join(name.lower().split())\n"
                    ),
                },
            },
            {
                "path": "src/workflow.py",
                "replace": {
                    '    return {"ok": True, "label": name, "slug": name}\n': (
                        '    return {"ok": True, "label": name, "slug": slugify(name)}\n'
                    ),
                },
            },
        ]
        test_expectations = []
    elif goal_id == CROSS_FILE_REGRESSION_GOAL_ID:
        fixture_id = "loomstead-debug-cross-file-regression-fixture.v1"
        artifact_id = "skill_cross_file_regression.patch"
        test_report_id = "skill_cross_file_regression.tests"
        pre_patch_test_report_id = "skill_cross_file_regression.pre_patch_tests"
        review_report_id = "skill_cross_file_regression.review"
        requires_pre_patch_failure = True
        requires_single_file_failure_evidence = True
        target_path = "src/normalizer.py"
        import_graph = {
            "nodes": [
                "src/normalizer.py",
                "src/report.py",
                "tests/test_skill.py",
            ],
            "edges": [
                {
                    "from": "src/report.py",
                    "imports": "src/normalizer.py",
                    "symbols": ["normalize_status", "severity_label"],
                },
                {"from": "tests/test_skill.py", "imports": "src/report.py", "symbols": ["build_status_report"]},
            ],
        }
        planned_additions = []
        planned_file_updates = [
            {
                "path": "src/normalizer.py",
                "replace": {
                    "def severity_label(priority: str) -> str:\n    return priority\n": (
                        "def severity_label(priority: str) -> str:\n"
                        "    return priority.strip().lower()\n"
                    ),
                },
            },
            {
                "path": "src/report.py",
                "replace": {
                    '    return {"status": status, "severity": priority, "display": f"{status}:{priority}"}\n': (
                        "    severity = severity_label(priority)\n"
                        '    return {"status": status, "severity": severity, "display": f"{status}:{severity}"}\n'
                    ),
                },
            },
        ]
        test_expectations = []
    elif goal_id == REVIEWER_DISAGREEMENT_GOAL_ID:
        test_runner = "unittest"
        fixture_id = "loomstead-debug-reviewer-disagreement-fixture.v1"
        artifact_id = "skill_reviewer_disagreement.patch"
        test_report_id = "skill_reviewer_disagreement.tests"
        review_report_id = "skill_reviewer_disagreement.review"
        requires_reviewer_disagreement = True
        planned_additions = [
            "Record test-backed reviewer disagreements before approval.",
            "Attach arbitration trace refs when reviewers disagree.",
        ]
        reviewer_rubrics = [
            {
                "reviewerId": "process_reviewer",
                "focus": "process_fidelity",
                "decision": "approve",
                "score": 0.92,
                "grounds": [
                    "external checkout tests passed",
                    "patch keeps design-before-diff process evidence",
                ],
            },
            {
                "reviewerId": "risk_reviewer",
                "focus": "risk_control",
                "decision": "request_changes",
                "score": 0.58,
                "grounds": [
                    "rollback note is absent",
                    "risk reviewer weights operational safety above test pass",
                ],
            },
        ]
        test_expectations = [
            {"caseId": "loads_skill_md", "type": "startswith", "value": "# Loomstead Debug Skill"},
            {
                "caseId": "records_reviewer_disagreement",
                "type": "contains",
                "value": "reviewer disagreements",
            },
            {
                "caseId": "records_arbitration_trace_refs",
                "type": "contains",
                "value": "arbitration trace refs",
            },
            {"caseId": "keeps_existing_doc_guidance", "type": "contains", "value": "Use project docs"},
        ]
    elif goal_id == JAVASCRIPT_SMOKE_GOAL_ID:
        test_runner = "node_test"
        target_path = "src/skill_summary.mjs"
        fixture_id = "loomstead-debug-javascript-fixture.v1"
        artifact_id = "skill_javascript_smoke.patch"
        test_report_id = "skill_javascript_smoke.tests"
        review_report_id = "skill_javascript_smoke.review"
        planned_additions = []
        planned_file_updates = [
            {
                "path": target_path,
                "replace": {
                    (
                        "export function summarizeSkillChange(input = {}) {\n"
                        "  const title = String(input.title ?? '').trim();\n"
                        "  return { title, evidenceCount: 0, readyForReview: false };\n"
                        "}\n"
                    ): (
                        "export function summarizeSkillChange(input = {}) {\n"
                        "  const title = String(input.title ?? '').trim();\n"
                        "  const evidence = Array.isArray(input.evidence) ? input.evidence.filter(Boolean) : [];\n"
                        "  const risk = String(input.risk ?? 'low').toLowerCase();\n"
                        "  return { title, evidenceCount: evidence.length, readyForReview: evidence.length > 0 && risk !== 'high' };\n"
                        "}\n"
                    ),
                },
            }
        ]
        test_expectations = []
    elif goal_id == "coding.skill_regression_fix_dryrun":
        test_runner = "unittest"
        fixture_id = "loomstead-debug-regression-fixture.v1"
        artifact_id = "skill_regression_fix.patch"
        test_report_id = "skill_regression_fix.tests"
        review_report_id = "skill_regression_fix.review"
        planned_additions = [
            "Check regression evidence before approving fixes.",
            "Run npm.cmd run check for runtime-facing skill changes.",
        ]
        test_expectations = [
            {"caseId": "loads_skill_md", "type": "startswith", "value": "# Loomstead Debug Skill"},
            {"caseId": "keeps_existing_doc_guidance", "type": "contains", "value": "Use project docs"},
            {
                "caseId": "requires_regression_evidence",
                "type": "contains",
                "value": "regression evidence before approving fixes",
            },
            {"caseId": "requires_repo_check_command", "type": "contains", "value": "npm.cmd run check"},
        ]
    else:
        fixture_id = "loomstead-debug-skill-fixture.v1"
        artifact_id = "skill_prototype.patch"
        test_report_id = "skill_prototype.tests"
        review_report_id = "skill_prototype.review"
        planned_additions = [
            "Use observer trace evidence before proposing runtime changes.",
            "Always run eval:domain before marking adapter changes done.",
        ]
        test_expectations = [
            {"caseId": "loads_skill_md", "type": "startswith", "value": "# Loomstead Debug Skill"},
            {"caseId": "mentions_observer_trace", "type": "contains", "value": "observer trace evidence"},
            {"caseId": "requires_eval_domain", "type": "contains", "value": "eval:domain"},
            {"caseId": "keeps_existing_doc_guidance", "type": "contains", "value": "Use project docs"},
        ]

    command_template = _command_template_for_runner(test_runner)
    if goal_id == MULTIFILE_DEPENDENCY_REPAIR_GOAL_ID:
        files = _dependency_repair_fixture_files()
    elif goal_id == CROSS_FILE_REGRESSION_GOAL_ID:
        files = _cross_file_regression_fixture_files()
    elif goal_id == JAVASCRIPT_SMOKE_GOAL_ID:
        files = _javascript_smoke_fixture_files()
    else:
        files = _skill_fixture_files(test_expectations, test_runner)
    derived_dependency_graph = _derive_dependency_graph_from_files(files)
    if import_graph:
        derived_dependency_graph = _compare_declared_and_derived_graph(import_graph, derived_dependency_graph)
    return {
        "fixtureId": fixture_id,
        "repoName": "fixture/loomstead-debug-skill",
        "defaultBranch": "main",
        "files": files,
        "fileHashes": {path: _stable_digest(content) for path, content in files.items()},
        "targetPath": target_path,
        "targetPaths": [
            str(update.get("path"))
            for update in planned_file_updates
            if isinstance(update, dict) and update.get("path")
        ]
        or ["skills/loomstead-debug/SKILL.md"],
        "artifactId": artifact_id,
        "prePatchTestReportId": pre_patch_test_report_id,
        "testReportId": test_report_id,
        "reviewReportId": review_report_id,
        "metadataPath": metadata_path,
        "reviewRubricPath": review_rubric_path,
        "metadata": {
            "testRunner": test_runner,
            "commandTemplate": command_template,
            "language": "javascript" if test_runner == "node_test" else "python",
        },
        "testCommand": command_template,
        "commandTemplate": command_template,
        "testCommandSource": "metadata.testRunner",
        "importGraph": import_graph,
        "derivedDependencyGraph": derived_dependency_graph,
        "reviewerRubrics": reviewer_rubrics,
        "plannedAdditions": planned_additions,
        "plannedFileUpdates": planned_file_updates,
        "testExpectations": test_expectations,
        "requiresPrePatchFailure": requires_pre_patch_failure,
        "requiresSingleFileFailureEvidence": requires_single_file_failure_evidence,
        "requiresReviewerDisagreement": requires_reviewer_disagreement,
        "sourceRepoKind": "deterministic_local_git_repository",
    }


def _skill_fixture_files(expectations: list[dict[str, Any]], test_runner: str) -> dict[str, str]:
    """构造 Python skill fixture，并按 runner 放入真实测试框架入口。"""
    test_script = (
        _repo_fixture_pytest_script(expectations)
        if test_runner == "pytest"
        else _repo_fixture_unittest_script(expectations)
    )
    return {
        "README.md": "# Skill Fixture\n\nThis fixture represents a tiny external skill repository.\n",
        "skills/loomstead-debug/SKILL.md": (
            "# Loomstead Debug Skill\n\n"
            "Use project docs before changing runtime code.\n"
        ),
        "skills/loomstead-debug/metadata.json": json.dumps(
            {
                "id": "loomstead-debug",
                "version": "0.1.0",
                "qualityGates": ["manual_review"],
                "requiresReviewRubric": False,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        "docs/review_rubric.md": (
            "# Review Rubric\n\n"
            "- Confirm existing doc guidance remains intact.\n"
        ),
        "tests/test_skill.py": test_script,
    }


def _dependency_repair_fixture_files() -> dict[str, str]:
    """构造包含真实 import 链和测试入口的跨文件依赖修复 fixture。"""
    return {
        "README.md": "# Dependency Repair Fixture\n\nA tiny Python repo with cross-file imports.\n",
        "src/__init__.py": "",
        "src/formatter.py": "\n".join(
            [
                "from __future__ import annotations",
                "",
                "",
                "def display_name(raw: str) -> str:",
                "    return ' '.join(raw.strip().split())",
                "",
                "",
                "def slugify(name: str) -> str:",
                "    return name",
                "",
            ]
        ),
        "src/workflow.py": "\n".join(
            [
                "from __future__ import annotations",
                "",
                "from src.formatter import display_name, slugify",
                "",
                "",
                "def build_ticket(raw_name: str) -> dict[str, object]:",
                "    name = display_name(raw_name)",
                "    if not name:",
                "        return {'ok': False, 'label': '', 'slug': ''}",
                "    return {\"ok\": True, \"label\": name, \"slug\": name}",
                "",
            ]
        ),
        "tests/test_skill.py": "\n".join(
            [
                "from __future__ import annotations",
                "",
                "from pathlib import Path",
                "import sys",
                "",
                "repo_root = Path(__file__).resolve().parents[1]",
                "sys.path.insert(0, str(repo_root))",
                "",
                "from src.workflow import build_ticket",
                "",
                "",
                "def test_slug_uses_formatter_dependency():",
                "    ticket = build_ticket('  Mira Bloom  ')",
                "    assert ticket == {'ok': True, 'label': 'Mira Bloom', 'slug': 'mira-bloom'}",
                "",
                "",
                "def test_blank_name_stays_invalid():",
                "    blank = build_ticket('   ')",
                "    assert blank == {'ok': False, 'label': '', 'slug': ''}",
                "",
            ]
        ),
    }


def _cross_file_regression_fixture_files() -> dict[str, str]:
    """构造跨文件回归 fixture：helper 与调用者需要一起修，单文件补丁会保持红灯。"""
    return {
        "README.md": "# Cross-file Regression Fixture\n\nA tiny Python repo where status report formatting crosses two source files.\n",
        "src/__init__.py": "",
        "src/normalizer.py": "\n".join(
            [
                "from __future__ import annotations",
                "",
                "",
                "def normalize_status(raw: str) -> str:",
                "    return ' '.join(raw.strip().lower().split())",
                "",
                "",
                "def severity_label(priority: str) -> str:",
                "    return priority",
                "",
            ]
        ),
        "src/report.py": "\n".join(
            [
                "from __future__ import annotations",
                "",
                "from src.normalizer import normalize_status, severity_label",
                "",
                "",
                "def build_status_report(raw_status: str, priority: str) -> dict[str, str]:",
                "    status = normalize_status(raw_status)",
                '    return {"status": status, "severity": priority, "display": f"{status}:{priority}"}',
                "",
            ]
        ),
        "tests/test_skill.py": "\n".join(
            [
                "from __future__ import annotations",
                "",
                "from pathlib import Path",
                "import sys",
                "",
                "repo_root = Path(__file__).resolve().parents[1]",
                "sys.path.insert(0, str(repo_root))",
                "",
                "from src.report import build_status_report",
                "",
                "",
                "def test_status_report_normalizes_cross_file_severity():",
                "    report = build_status_report('  Ready  ', ' LOW ')",
                "    assert report == {'status': 'ready', 'severity': 'low', 'display': 'ready:low'}",
                "",
                "",
                "def test_status_report_preserves_status_word_spacing():",
                "    report = build_status_report('Needs   Review', ' Medium ')",
                "    assert report == {'status': 'needs review', 'severity': 'medium', 'display': 'needs review:medium'}",
                "",
            ]
        ),
    }


def _derive_dependency_graph_from_files(files: dict[str, str]) -> dict[str, Any]:
    """从 fixture 的真实源码 import 语句派生依赖图，避免只依赖手写 graph 声明。"""
    source_paths = {path for path in files if path.startswith("src/") and path.endswith(".py")}
    test_paths = {path for path in files if path.startswith("tests/") and path.endswith(".py")}
    nodes = sorted(source_paths | test_paths)
    edges: list[dict[str, Any]] = []
    for path in nodes:
        content = str(files.get(path, ""))
        for line_number, raw_line in enumerate(content.splitlines(), start=1):
            match = re.match(r"^\s*from\s+(src(?:\.[\w_]+)*)\s+import\s+(.+)$", raw_line)
            if not match:
                continue
            imported_path = "%s.py" % match.group(1).replace(".", "/")
            if imported_path not in source_paths:
                continue
            symbols = [symbol.strip().split(" as ")[0] for symbol in match.group(2).split(",") if symbol.strip()]
            edges.append(
                {
                    "from": path,
                    "imports": imported_path,
                    "symbols": symbols,
                    "sourceLine": line_number,
                }
            )
    return {
        "graphVersion": "coding.derived_dependency_graph.v1",
        "nodes": nodes,
        "edges": edges,
    }


def _compare_declared_and_derived_graph(declared_graph: dict[str, Any], derived_graph: dict[str, Any]) -> dict[str, Any]:
    """把手写 importGraph 与源码派生图对齐，供 Eval 判断依赖图是否来自真实文件。"""
    declared_edges = {
        (str(edge.get("from")), str(edge.get("imports")))
        for edge in declared_graph.get("edges", [])
        if isinstance(edge, dict)
    }
    derived_edges = {
        (str(edge.get("from")), str(edge.get("imports")))
        for edge in derived_graph.get("edges", [])
        if isinstance(edge, dict)
    }
    compared = dict(derived_graph)
    compared["declaredGraphVersion"] = str(declared_graph.get("graphVersion") or "manual_import_graph.v1")
    compared["declaredEdgeCount"] = len(declared_edges)
    compared["derivedEdgeCount"] = len(derived_edges)
    compared["missingDeclaredEdges"] = [
        {"from": source, "imports": target}
        for source, target in sorted(declared_edges - derived_edges)
    ]
    compared["extraDerivedEdges"] = [
        {"from": source, "imports": target}
        for source, target in sorted(derived_edges - declared_edges)
    ]
    compared["declaredEdgesCovered"] = not compared["missingDeclaredEdges"] and bool(declared_edges)
    return compared


def _javascript_smoke_fixture_files() -> dict[str, str]:
    """构造 Node.js 内置 test runner 的最小非 Python fixture。"""
    return {
        "README.md": "# JavaScript Fixture\n\nA tiny ESM repo verified with node --test.\n",
        "package.json": json.dumps(
            {
                "name": "loomstead-javascript-smoke-fixture",
                "private": True,
                "type": "module",
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        "src/skill_summary.mjs": "\n".join(
            [
                "export function summarizeSkillChange(input = {}) {",
                "  const title = String(input.title ?? '').trim();",
                "  return { title, evidenceCount: 0, readyForReview: false };",
                "}",
                "",
            ]
        ),
        "tests/skill_summary.test.mjs": "\n".join(
            [
                "import test from 'node:test';",
                "import assert from 'node:assert/strict';",
                "",
                "import { summarizeSkillChange } from '../src/skill_summary.mjs';",
                "",
                "test('summarizeSkillChange counts evidence before review', () => {",
                "  const result = summarizeSkillChange({",
                "    title: '  Debug adapter  ',",
                "    evidence: ['patch', 'test-report'],",
                "    risk: 'low',",
                "  });",
                "  assert.deepEqual(result, {",
                "    title: 'Debug adapter',",
                "    evidenceCount: 2,",
                "    readyForReview: true,",
                "  });",
                "});",
                "",
                "test('summarizeSkillChange blocks high-risk review readiness', () => {",
                "  const result = summarizeSkillChange({ title: 'Risky', evidence: ['patch'], risk: 'high' });",
                "  assert.equal(result.readyForReview, false);",
                "});",
                "",
            ]
        ),
    }



def _build_skill_patch(repo_fixture: dict[str, Any]) -> tuple[str, dict[str, str], list[str]]:
    files = dict(repo_fixture.get("files", {})) if isinstance(repo_fixture.get("files"), dict) else {}
    planned_file_updates = (
        repo_fixture.get("plannedFileUpdates", []) if isinstance(repo_fixture.get("plannedFileUpdates"), list) else []
    )
    if not planned_file_updates:
        target_path = str(repo_fixture.get("targetPath") or "skills/loomstead-debug/SKILL.md")
        planned_additions = repo_fixture.get("plannedAdditions", [])
        planned_file_updates = [
            {
                "path": target_path,
                "appendLines": [str(item) for item in planned_additions]
                if isinstance(planned_additions, list)
                else [],
            }
        ]

    patch_sections: list[str] = []
    changed_files: list[str] = []
    for update in planned_file_updates:
        if not isinstance(update, dict):
            continue
        target_path = str(update.get("path") or repo_fixture.get("targetPath") or "skills/loomstead-debug/SKILL.md")
        original = str(files.get(target_path, ""))
        patched = _apply_fixture_file_update(original, update)
        files[target_path] = patched
        changed_files.append(target_path)
        patch_sections.extend(_build_patch_section(target_path, original, patched))

    return "\n".join(patch_sections), files, changed_files


def _apply_fixture_file_update(original: str, update: dict[str, Any]) -> str:
    """按 fixture 描述生成单文件补丁结果，支持替换、文本追加和简单 JSON 合并。"""
    if isinstance(update.get("replace"), dict):
        patched = original
        for old_text, new_text in update["replace"].items():
            patched = patched.replace(str(old_text), str(new_text), 1)
        return patched

    if isinstance(update.get("jsonMerge"), dict):
        try:
            payload = json.loads(original or "{}")
        except json.JSONDecodeError:
            payload = {}
        if not isinstance(payload, dict):
            payload = {}
        payload.update(update["jsonMerge"])
        return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"

    append_lines = update.get("appendLines", [])
    additions = [str(item) for item in append_lines] if isinstance(append_lines, list) else []
    return original.rstrip() + "\n" + "\n".join(additions) + "\n"


def _build_patch_section(target_path: str, original: str, patched: str) -> list[str]:
    """生成稳定的轻量 patch 片段，供 Eval artifact 审阅变更范围。"""
    return list(
        difflib.unified_diff(
            original.splitlines(),
            patched.splitlines(),
            fromfile=f"a/{target_path}",
            tofile=f"b/{target_path}",
            lineterm="",
        )
    )


def _build_dependency_patch_evidence(
    repo_fixture: dict[str, Any],
    base_files: dict[str, Any],
    patched_files: dict[str, str],
    changed_files: list[str],
) -> dict[str, Any]:
    """记录跨文件依赖修复所需的全文件 hash、import 图和补丁覆盖范围。"""
    import_graph = repo_fixture.get("importGraph", {}) if isinstance(repo_fixture.get("importGraph"), dict) else {}
    derived_dependency_graph = (
        repo_fixture.get("derivedDependencyGraph", {})
        if isinstance(repo_fixture.get("derivedDependencyGraph"), dict)
        else {}
    )
    if not import_graph:
        return {}
    return {
        "baseFileHashes": {
            str(path): _stable_digest(str(content)) for path, content in sorted(base_files.items())
        },
        "patchedFileHashes": {
            str(path): _stable_digest(str(content)) for path, content in sorted(patched_files.items())
        },
        "importGraph": import_graph,
        "derivedDependencyGraph": derived_dependency_graph,
        "patchCoverageFileCount": len(changed_files),
        "changedFiles": list(changed_files),
        "changedSourceFiles": [
            path for path in changed_files if path.startswith("src/") and path.endswith(".py")
        ],
    }


def _run_single_file_partial_patch_reports(
    artifact: dict[str, Any],
    repo_fixture: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """逐个只应用一个源文件补丁并运行测试，证明依赖修复需要多文件同时覆盖。"""
    repo_files = repo_fixture.get("files", {}) if isinstance(repo_fixture.get("files"), dict) else {}
    patched_files = artifact.get("patchedFiles", {}) if isinstance(artifact.get("patchedFiles"), dict) else {}
    changed_files = [
        str(path)
        for path in artifact.get("changedFiles", [])
        if str(path).startswith("src/") and str(path).endswith(".py")
    ] if isinstance(artifact.get("changedFiles"), list) else []
    reports: dict[str, dict[str, Any]] = {}
    for changed_file in changed_files:
        partial_files = {str(path): str(content) for path, content in repo_files.items()}
        partial_files[changed_file] = str(patched_files.get(changed_file, partial_files.get(changed_file, "")))
        partial_artifact = {
            "artifactId": f"{artifact.get('artifactId', 'repo_patch')}:single_file:{changed_file}",
            "patchedFiles": partial_files,
        }
        test_cases, execution = _run_external_checkout_fixture_tests(
            partial_artifact,
            repo_fixture,
            test_phase="single_file_patch",
        )
        failing_case_ids = [
            str(item.get("caseId") or "unknown_case")
            for item in test_cases
            if isinstance(item, dict) and not bool(item.get("passed"))
        ]
        report_id = (
            f"{repo_fixture.get('artifactId', 'repo_patch')}.single_file."
            f"{_safe_report_id_part(changed_file)}.tests"
        )
        report = {
            "testReportId": report_id,
            "command": execution.get("command", "python check_skill.py"),
            "testRunner": execution.get("testRunner"),
            "durationMs": execution.get("durationMs"),
            "exitCode": execution.get("exitCode"),
            "testPhase": "single_file_patch",
            "patchedFile": changed_file,
            "passed": False,
            "expectedFailure": True,
            "failureObserved": execution.get("exitCode") not in (None, 0) and bool(failing_case_ids),
            "failingCaseIds": failing_case_ids,
            "caseResults": test_cases,
            "execution": execution,
            "sourceArtifactId": artifact.get("artifactId", "repo_patch"),
        }
        report["sha256"] = _stable_digest(json.dumps(report, ensure_ascii=False, sort_keys=True))
        reports[report_id] = report
    return reports


def _build_dependency_evidence_chain(
    *,
    pre_patch_report: dict[str, Any],
    post_patch_report: dict[str, Any],
    partial_patch_reports: dict[str, Any],
) -> dict[str, Any]:
    """聚合依赖修复场景的 pre/partial/post 证据链，便于 review 一次性复核关键字段。"""
    partial_rows: list[dict[str, Any]] = []
    for report_id, report in sorted(partial_patch_reports.items()):
        if not isinstance(report, dict):
            continue
        partial_rows.append(
            {
                "testReportId": report_id,
                "patchedFile": report.get("patchedFile"),
                "testRunner": report.get("testRunner"),
                "command": report.get("command"),
                "exitCode": report.get("exitCode"),
                "failureObserved": bool(report.get("failureObserved")),
                "failingCaseIds": list(report.get("failingCaseIds", []))
                if isinstance(report.get("failingCaseIds"), list)
                else [],
                "sourceEventIds": list(report.get("sourceEventIds", []))
                if isinstance(report.get("sourceEventIds"), list)
                else [],
                "sha256": report.get("sha256"),
            }
        )
    pre_cases = pre_patch_report.get("caseResults", []) if isinstance(pre_patch_report.get("caseResults"), list) else []
    post_cases = post_patch_report.get("caseResults", []) if isinstance(post_patch_report.get("caseResults"), list) else []
    evidence = {
        "chainVersion": "coding.dependency_evidence_chain.v2",
        "prePatch": {
            "testReportId": pre_patch_report.get("testReportId"),
            "testRunner": pre_patch_report.get("testRunner"),
            "command": pre_patch_report.get("command"),
            "exitCode": pre_patch_report.get("exitCode"),
            "failingCaseIds": [
                str(item.get("caseId") or "unknown_case")
                for item in pre_cases
                if isinstance(item, dict) and not bool(item.get("passed"))
            ],
            "sourceEventIds": list(pre_patch_report.get("sourceEventIds", []))
            if isinstance(pre_patch_report.get("sourceEventIds"), list)
            else [],
            "sha256": pre_patch_report.get("sha256"),
        },
        "postPatch": {
            "testReportId": post_patch_report.get("testReportId"),
            "testRunner": post_patch_report.get("testRunner"),
            "command": post_patch_report.get("command"),
            "exitCode": post_patch_report.get("exitCode"),
            "passingCaseIds": [
                str(item.get("caseId") or "unknown_case")
                for item in post_cases
                if isinstance(item, dict) and bool(item.get("passed"))
            ],
            "sourceEventIds": list(post_patch_report.get("sourceEventIds", []))
            if isinstance(post_patch_report.get("sourceEventIds"), list)
            else [],
            "sha256": post_patch_report.get("sha256"),
        },
        "partialPatchFailures": partial_rows,
    }
    all_reports = [evidence["prePatch"], evidence["postPatch"], *partial_rows]
    runners = {str(item.get("testRunner") or "") for item in all_reports if isinstance(item, dict)}
    evidence["consistentRunner"] = len(runners) == 1 and bool(next(iter(runners), ""))
    evidence["allExpectedFailuresObserved"] = bool(partial_rows) and all(
        bool(item.get("failureObserved")) and item.get("exitCode") not in (None, 0)
        for item in partial_rows
    )
    evidence["transitionEdges"] = _dependency_chain_transition_edges(evidence)
    evidence["caseEvidence"] = {
        "prePatchFailingCaseIds": list(evidence["prePatch"].get("failingCaseIds", [])),
        "partialPatchFailingCaseIdsByFile": {
            str(item.get("patchedFile")): list(item.get("failingCaseIds", []))
            for item in partial_rows
        },
        "postPatchPassingCaseIds": list(evidence["postPatch"].get("passingCaseIds", [])),
    }
    return evidence


def _dependency_chain_transition_edges(evidence: dict[str, Any]) -> list[dict[str, Any]]:
    """把 pre -> partial -> post 串成可审计边，导出时可直接查看依赖证据路径。"""
    pre_report = evidence.get("prePatch", {}) if isinstance(evidence.get("prePatch"), dict) else {}
    post_report = evidence.get("postPatch", {}) if isinstance(evidence.get("postPatch"), dict) else {}
    partial_rows = evidence.get("partialPatchFailures", []) if isinstance(evidence.get("partialPatchFailures"), list) else []
    edges: list[dict[str, Any]] = []
    for partial in partial_rows:
        if not isinstance(partial, dict):
            continue
        edges.append(
            {
                "from": pre_report.get("testReportId"),
                "to": partial.get("testReportId"),
                "reason": "single_file_partial_patch_replays_pre_patch_failure",
                "patchedFile": partial.get("patchedFile"),
            }
        )
        edges.append(
            {
                "from": partial.get("testReportId"),
                "to": post_report.get("testReportId"),
                "reason": "coordinated_cross_file_patch_resolves_failure",
                "patchedFile": partial.get("patchedFile"),
            }
        )
    return edges


def _regression_case_covered(
    goal_id: str,
    pre_patch_report: dict[str, Any],
    post_patch_report: dict[str, Any],
    partial_patch_reports: list[dict[str, Any]],
) -> bool:
    """确认跨文件回归场景具备红灯、单文件仍红、双文件变绿的完整用例证据。"""
    if goal_id != CROSS_FILE_REGRESSION_GOAL_ID:
        return True
    pre_cases = pre_patch_report.get("caseResults", []) if isinstance(pre_patch_report.get("caseResults"), list) else []
    post_cases = post_patch_report.get("caseResults", []) if isinstance(post_patch_report.get("caseResults"), list) else []
    partial_case_ids = {
        str(case.get("caseId") or "")
        for report in partial_patch_reports
        if isinstance(report, dict)
        for case in report.get("caseResults", [])
        if isinstance(case, dict) and not bool(case.get("passed"))
    }
    regression_case_ids = {
        str(case.get("caseId") or "")
        for case in pre_cases
        if isinstance(case, dict) and not bool(case.get("passed"))
    }
    post_passing_case_ids = {
        str(case.get("caseId") or "")
        for case in post_cases
        if isinstance(case, dict) and bool(case.get("passed"))
    }
    return bool(regression_case_ids) and regression_case_ids.issubset(partial_case_ids) and regression_case_ids.issubset(post_passing_case_ids)


def _ensure_coding_counterfactual_replay(
    world: dict[str, Any],
    *,
    goal_id: str,
    repo_fixture: dict[str, Any],
    artifact: dict[str, Any],
    pre_patch_report: dict[str, Any],
    partial_patch_reports: dict[str, Any],
    test_report: dict[str, Any],
    review_report: dict[str, Any],
) -> dict[str, Any]:
    """缓存 coding domain 的证据移除 replay，避免 evaluate / observe 重复生成不一致结构。"""
    if not review_report:
        return {}
    replay_id = str(review_report.get("reviewReportId") or f"{goal_id}.counterfactual_replay")
    replay_map = world.setdefault("counterfactualReplays", {})
    if not isinstance(replay_map, dict):
        replay_map = {}
        world["counterfactualReplays"] = replay_map
    existing = replay_map.get(replay_id)
    if isinstance(existing, dict):
        return existing
    replay = _build_coding_counterfactual_replay(
        goal_id=goal_id,
        repo_fixture=repo_fixture,
        artifact=artifact,
        pre_patch_report=pre_patch_report,
        partial_patch_reports=partial_patch_reports,
        test_report=test_report,
        review_report=review_report,
    )
    replay_map[replay_id] = replay
    return replay


def _build_coding_counterfactual_replay(
    *,
    goal_id: str,
    repo_fixture: dict[str, Any],
    artifact: dict[str, Any],
    pre_patch_report: dict[str, Any],
    partial_patch_reports: dict[str, Any],
    test_report: dict[str, Any],
    review_report: dict[str, Any],
) -> dict[str, Any]:
    """逐项移除证据，复算 review 路由，给 cross-domain suite 提供可区分的因果信号。"""
    features = _coding_evidence_features(
        goal_id=goal_id,
        repo_fixture=repo_fixture,
        artifact=artifact,
        pre_patch_report=pre_patch_report,
        partial_patch_reports=partial_patch_reports,
        test_report=test_report,
        review_report=review_report,
    )
    selected_with = _select_coding_process_tool(goal_id, features)
    comparisons: list[dict[str, Any]] = []
    changed_count = 0
    for spec in _coding_counterfactual_ablation_specs(goal_id, repo_fixture):
        ablated_features = dict(features)
        removed_evidence_ids = [str(item) for item in spec.get("removeEvidenceIds", [])]
        for evidence_id in removed_evidence_ids:
            ablated_features[evidence_id] = False
        selected_without = _select_coding_process_tool(goal_id, ablated_features)
        changed = selected_with != selected_without
        changed_count += 1 if changed else 0
        comparisons.append(
            {
                "ablationId": spec.get("ablationId"),
                "kind": spec.get("kind", "critical"),
                "removedEvidenceIds": removed_evidence_ids,
                "selectedWithEvidence": selected_with,
                "selectedWithoutEvidence": selected_without,
                "changed": changed,
                "reason": spec.get("reason"),
            }
        )
    critical_rows = [row for row in comparisons if row.get("kind") == "critical"]
    control_rows = [row for row in comparisons if row.get("kind") == "control"]
    return {
        "replayVersion": "coding.domain_counterfactual_replay.v1",
        "goalId": goal_id,
        "selectedWithEvidence": selected_with,
        "featureSnapshot": features,
        "comparisonCount": len(comparisons),
        "changedDecisionCount": changed_count,
        "criticalChangeCount": sum(1 for row in critical_rows if row.get("changed")),
        "controlStableCount": sum(1 for row in control_rows if not row.get("changed")),
        "changeRate": round(_safe_ratio(changed_count, len(comparisons)), 6),
        "criticalChangeRate": round(
            _safe_ratio(sum(1 for row in critical_rows if row.get("changed")), len(critical_rows)),
            6,
        ),
        "controlStabilityRate": round(
            _safe_ratio(sum(1 for row in control_rows if not row.get("changed")), len(control_rows)),
            6,
        ),
        "comparisons": comparisons,
    }


def _coding_evidence_features(
    *,
    goal_id: str,
    repo_fixture: dict[str, Any],
    artifact: dict[str, Any],
    pre_patch_report: dict[str, Any],
    partial_patch_reports: dict[str, Any],
    test_report: dict[str, Any],
    review_report: dict[str, Any],
) -> dict[str, bool]:
    """把 patch / test / review 证据压缩为确定性路由特征。"""
    changed_files = artifact.get("changedFiles", []) if isinstance(artifact.get("changedFiles"), list) else []
    metadata_path = str(repo_fixture.get("metadataPath") or "")
    derived_graph = (
        repo_fixture.get("derivedDependencyGraph", {})
        if isinstance(repo_fixture.get("derivedDependencyGraph"), dict)
        else {}
    )
    dependency_chain = (
        review_report.get("dependencyEvidenceChain", {})
        if isinstance(review_report.get("dependencyEvidenceChain"), dict)
        else {}
    )
    reviewer_evaluations = (
        review_report.get("reviewerEvaluations", [])
        if isinstance(review_report.get("reviewerEvaluations"), list)
        else []
    )
    reviewer_decisions = {
        str(item.get("decision") or "")
        for item in reviewer_evaluations
        if isinstance(item, dict)
    }
    arbitration_layer = (
        review_report.get("arbitrationLayer", {})
        if isinstance(review_report.get("arbitrationLayer"), dict)
        else {}
    )
    partial_reports = [
        report for report in partial_patch_reports.values() if isinstance(report, dict)
    ]
    return {
        "repo_fixture_loaded": bool(repo_fixture.get("files")),
        "non_python_fixture_loaded": (
            repo_fixture.get("metadata", {}).get("testRunner") == "node_test"
            if isinstance(repo_fixture.get("metadata"), dict)
            else False
        ),
        "implementation_diff": bool(artifact.get("patchText")) and bool(changed_files),
        "metadata_dependency_updated": bool(metadata_path)
        and metadata_path in {str(path) for path in changed_files}
        and bool(artifact.get("fileSha256", {}).get(metadata_path))
        if isinstance(artifact.get("fileSha256"), dict)
        else False,
        "pre_patch_failure_observed": bool(pre_patch_report.get("failureObserved"))
        and pre_patch_report.get("exitCode") not in (None, 0),
        "post_patch_tests_passed": bool(test_report.get("passed")) and test_report.get("exitCode") == 0,
        "derived_dependency_graph_recorded": bool(derived_graph.get("nodes"))
        and bool(derived_graph.get("edges"))
        and not derived_graph.get("missingDeclaredEdges"),
        "single_file_replay_failed": bool(partial_reports)
        and all(
            bool(report.get("failureObserved")) and report.get("exitCode") not in (None, 0)
            for report in partial_reports
        ),
        "dependency_chain_confirmed": bool(dependency_chain)
        and dependency_chain.get("chainVersion") == "coding.dependency_evidence_chain.v2"
        and bool(dependency_chain.get("transitionEdges"))
        and bool(dependency_chain.get("caseEvidence"))
        and bool(dependency_chain.get("allExpectedFailuresObserved")),
        "reviewer_conflict_observed": {"approve", "request_changes"}.issubset(reviewer_decisions),
        "arbitration_contributing_sources": len(arbitration_layer.get("contributing_sources", [])) >= 2
        and all(
            isinstance(item, dict) and bool(item.get("sourceEventId"))
            for item in arbitration_layer.get("contributing_sources", [])
        ),
        "review_source_links": bool(review_report.get("sourceEventIds")),
        "review_approved": review_report.get("status") == "approved",
        # control 特征只用于 stable ablation，帮助指标显示“关键证据变化”和“无关信息移除”的差异。
        "optional_readme_context": True,
    }


def _select_coding_process_tool(goal_id: str, features: dict[str, bool]) -> str:
    """用证据特征复算 coding review 下一步路由，作为 task-domain 的 tool-selection proxy。"""
    if not features.get("repo_fixture_loaded", False):
        return "design.load_repo_fixture"
    if goal_id == JAVASCRIPT_SMOKE_GOAL_ID and not features.get("non_python_fixture_loaded", False):
        return "evaluation.select_node_test_runner"
    if goal_id in {
        FAILING_TEST_REPAIR_GOAL_ID,
        MULTIFILE_DEPENDENCY_REPAIR_GOAL_ID,
        CROSS_FILE_REGRESSION_GOAL_ID,
    } and not features.get("pre_patch_failure_observed", False):
        return "evaluation.record_pre_patch_failure"
    if not features.get("implementation_diff", False):
        return "implement.create_patch"
    if goal_id == MULTIFILE_REVIEW_GOAL_ID and not features.get("metadata_dependency_updated", False):
        return "implement.sync_metadata_dependency"
    if not features.get("post_patch_tests_passed", False):
        return "evaluation.run_external_checkout_tests"
    if goal_id in {MULTIFILE_DEPENDENCY_REPAIR_GOAL_ID, CROSS_FILE_REGRESSION_GOAL_ID}:
        if not features.get("derived_dependency_graph_recorded", False):
            return "evaluation.derive_dependency_graph"
        if not features.get("single_file_replay_failed", False):
            return "evaluation.run_single_file_replays"
        if not features.get("dependency_chain_confirmed", False):
            return "review.request_dependency_evidence_chain"
    if goal_id == REVIEWER_DISAGREEMENT_GOAL_ID:
        if not features.get("reviewer_conflict_observed", False):
            return "review.collect_reviewer_judgments"
        if not features.get("arbitration_contributing_sources", False):
            return "arbitration.collect_contributing_sources"
    if not features.get("review_source_links", False):
        return "review.request_source_event_links"
    if not features.get("review_approved", False):
        return "review.request_changes"
    return "review.approve_patch"


def _coding_counterfactual_ablation_specs(goal_id: str, repo_fixture: dict[str, Any]) -> list[dict[str, Any]]:
    """列出每个 scenario 应移除的关键证据和一个稳定 control。"""
    specs: list[dict[str, Any]] = [
        {
            "ablationId": "remove_post_patch_tests",
            "kind": "critical",
            "removeEvidenceIds": ["post_patch_tests_passed"],
            "reason": "post-patch checkout test is the final approval gate",
        },
        {
            "ablationId": "remove_review_source_links",
            "kind": "critical",
            "removeEvidenceIds": ["review_source_links"],
            "reason": "review approval must stay linked to test/source events",
        },
        {
            "ablationId": "remove_optional_readme_context",
            "kind": "control",
            "removeEvidenceIds": ["optional_readme_context"],
            "reason": "non-gating context removal should keep the process route stable",
        },
    ]
    if goal_id == JAVASCRIPT_SMOKE_GOAL_ID:
        specs.insert(
            0,
            {
                "ablationId": "remove_non_python_runner_metadata",
                "kind": "critical",
                "removeEvidenceIds": ["non_python_fixture_loaded"],
                "reason": "JavaScript fixture requires node_test runner metadata",
            },
        )
    if goal_id in {
        FAILING_TEST_REPAIR_GOAL_ID,
        MULTIFILE_DEPENDENCY_REPAIR_GOAL_ID,
        CROSS_FILE_REGRESSION_GOAL_ID,
    }:
        specs.insert(
            0,
            {
                "ablationId": "remove_pre_patch_failure",
                "kind": "critical",
                "removeEvidenceIds": ["pre_patch_failure_observed"],
                "reason": "repair scenarios must show the red test before applying a fix",
            },
        )
    if goal_id == MULTIFILE_REVIEW_GOAL_ID and repo_fixture.get("metadataPath"):
        specs.insert(
            1,
            {
                "ablationId": "remove_metadata_dependency_update",
                "kind": "critical",
                "removeEvidenceIds": ["metadata_dependency_updated"],
                "reason": "metadata-sensitive skill changes must update the paired dependency file",
            },
        )
    if goal_id in {MULTIFILE_DEPENDENCY_REPAIR_GOAL_ID, CROSS_FILE_REGRESSION_GOAL_ID}:
        specs.extend(
            [
                {
                    "ablationId": "remove_derived_dependency_graph",
                    "kind": "critical",
                    "removeEvidenceIds": ["derived_dependency_graph_recorded"],
                    "reason": "cross-file repair needs import graph evidence derived from real files",
                },
                {
                    "ablationId": "remove_single_file_replay_failures",
                    "kind": "critical",
                    "removeEvidenceIds": ["single_file_replay_failed"],
                    "reason": "single-file partial replay proves the repair needs coordinated edits",
                },
                {
                    "ablationId": "remove_dependency_chain",
                    "kind": "critical",
                    "removeEvidenceIds": ["dependency_chain_confirmed"],
                    "reason": "review requires pre/partial/post dependency evidence chain",
                },
            ]
        )
    if goal_id == REVIEWER_DISAGREEMENT_GOAL_ID:
        specs.extend(
            [
                {
                    "ablationId": "remove_reviewer_conflict",
                    "kind": "critical",
                    "removeEvidenceIds": ["reviewer_conflict_observed"],
                    "reason": "disagreement scenario must preserve opposing reviewer judgments",
                },
                {
                    "ablationId": "remove_arbitration_sources",
                    "kind": "critical",
                    "removeEvidenceIds": ["arbitration_contributing_sources"],
                    "reason": "arbitration must cite reviewer judgment sources",
                },
            ]
        )
    return specs


def _build_rule_reviewer_evaluations(
    *,
    repo_fixture: dict[str, Any],
    artifact: dict[str, Any],
    test_report: dict[str, Any],
    checklist: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """生成规则版双 reviewer 评分，用于构造可复核的分歧样例。"""
    rubrics = repo_fixture.get("reviewerRubrics", [])
    if not isinstance(rubrics, list) or not rubrics:
        return []
    checklist_pass_rate = _safe_ratio(
        sum(1 for item in checklist if isinstance(item, dict) and bool(item.get("passed"))),
        max(1, len(checklist)),
    )
    evaluations: list[dict[str, Any]] = []
    for rubric in rubrics:
        if not isinstance(rubric, dict):
            continue
        evaluations.append(
            {
                "reviewerId": str(rubric.get("reviewerId") or "reviewer"),
                "focus": str(rubric.get("focus") or "general"),
                "decision": str(rubric.get("decision") or "approve"),
                "score": float(rubric.get("score") or 0.0),
                "grounds": [str(item) for item in rubric.get("grounds", []) if str(item)]
                if isinstance(rubric.get("grounds"), list)
                else [],
                "scoringBasis": {
                    "testPassed": bool(test_report.get("passed")),
                    "changedFileCount": len(artifact.get("changedFiles", []))
                    if isinstance(artifact.get("changedFiles"), list)
                    else 0,
                    "checklistPassRate": round(checklist_pass_rate, 6),
                },
            }
        )
    return evaluations


def _arbitrate_reviewer_disagreement(
    *,
    reviewer_evaluations: list[dict[str, Any]],
    test_report: dict[str, Any],
    source_event_ids: list[str],
    review_report_id: str,
) -> dict[str, Any]:
    """用确定性 ArbitrationLayer 记录 reviewer 分歧来源和最终决策路径。"""
    if not reviewer_evaluations:
        return {}
    approve_votes = [item for item in reviewer_evaluations if item.get("decision") == "approve"]
    request_change_votes = [item for item in reviewer_evaluations if item.get("decision") == "request_changes"]
    final_decision = "approved" if bool(test_report.get("passed")) and approve_votes else "request_changes"
    return {
        "layer": "ArbitrationLayer",
        "traceId": f"trace.review_arbitration.{_safe_report_id_part(review_report_id)}",
        "conflictDetected": bool(approve_votes and request_change_votes),
        "finalDecision": final_decision,
        "resolutionPath": [
            "collect_rule_reviewer_scores",
            "detect_approve_vs_request_changes_conflict",
            "prioritize_test_backed_process_evidence",
            "record_followup_for_risk_reviewer_concern",
            f"final_decision:{final_decision}",
        ],
        "contributing_sources": [
            {
                "type": "reviewer_score",
                "reviewerId": item.get("reviewerId"),
                "decision": item.get("decision"),
                "score": item.get("score"),
                "grounds": item.get("grounds", []),
                "scoringBasis": item.get("scoringBasis", {}),
                "sourceEventId": item.get("sourceEventId"),
                "sourceEventIds": list(item.get("sourceEventIds", []))
                if isinstance(item.get("sourceEventIds"), list)
                else [],
            }
            for item in reviewer_evaluations
        ],
        "sourceEventIds": list(source_event_ids),
    }


def _run_external_checkout_fixture_tests(
    artifact: dict[str, Any], repo_fixture: dict[str, Any], *, test_phase: str = "post_patch"
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """创建独立 git 仓库、执行真实 checkout，并运行仓库自带测试命令。"""
    repo_files = repo_fixture.get("files", {}) if isinstance(repo_fixture.get("files"), dict) else {}
    patched_files = artifact.get("patchedFiles", {}) if isinstance(artifact.get("patchedFiles"), dict) else {}
    workspace_files = repo_files if test_phase == "pre_patch" else patched_files
    test_runner = _fixture_test_runner(repo_fixture)
    command_template = _command_template_for_runner(test_runner)
    checkout_steps: list[dict[str, Any]] = []
    started = time.perf_counter()
    try:
        with tempfile.TemporaryDirectory(prefix="loomstead-coding-fixture-") as temp_dir:
            source_repo = Path(temp_dir) / "source-repo"
            checkout = Path(temp_dir) / "checkout"
            _write_fixture_worktree(source_repo, repo_files)
            checkout_steps.extend(_initialise_git_repo(source_repo))
            source_head = _run_git_command(["rev-parse", "HEAD"], cwd=source_repo, check=True)["stdout"].strip()
            checkout_steps.append(
                _run_git_command(
                    ["clone", "--quiet", str(source_repo), str(checkout)],
                    cwd=Path(temp_dir),
                    check=True,
                )
            )
            checkout_head = _run_git_command(["rev-parse", "HEAD"], cwd=checkout, check=True)["stdout"].strip()
            _write_fixture_worktree(checkout, workspace_files)
            checkout_status = _run_git_command(["status", "--short"], cwd=checkout, check=True)["stdout"].splitlines()
            command = _repo_test_command(test_runner)
            completed = subprocess.run(command, cwd=checkout, capture_output=True, text=True, encoding="utf-8", check=False)
            duration_ms = round((time.perf_counter() - started) * 1000.0, 3)
            parsed_cases = _parse_fixture_test_cases(
                completed.stdout,
                completed.stderr,
                exit_code=completed.returncode,
                test_runner=test_runner,
            )
            execution = {
                "executed": True,
                "testPhase": test_phase,
                "testRunner": test_runner,
                "workspaceKind": "git_external_repo_checkout",
                "sourceRepoKind": repo_fixture.get("sourceRepoKind", "deterministic_local_git_repository"),
                "checkoutMethod": "git clone",
                "command": command_template,
                "commandTemplate": command_template,
                "testCommandSource": repo_fixture.get("testCommandSource", "repo_fixture"),
                "pythonExecutable": Path(sys.executable).name if test_runner in {"pytest", "unittest"} else None,
                "exitCode": completed.returncode,
                "durationMs": duration_ms,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
                "checkoutSteps": checkout_steps,
                "git": {
                    "defaultBranch": repo_fixture.get("defaultBranch", "main"),
                    "sourceHead": source_head,
                    "checkoutHead": checkout_head,
                    "statusAfterPatch": checkout_status,
                },
                "sourceRepoFiles": sorted(str(path) for path in repo_files.keys()),
                "workspaceFiles": sorted(str(path) for path in workspace_files.keys()),
                "workspaceFileHashes": {
                    str(path): _stable_digest(str(content)) for path, content in workspace_files.items()
                },
            }
            return parsed_cases, execution
    except Exception as exc:
        duration_ms = round((time.perf_counter() - started) * 1000.0, 3)
        return (
            [{"caseId": "external_repo_checkout", "passed": False, "error": repr(exc)}],
            {
                "executed": False,
                "testPhase": test_phase,
                "testRunner": test_runner,
                "workspaceKind": "git_external_repo_checkout",
                "sourceRepoKind": repo_fixture.get("sourceRepoKind", "deterministic_local_git_repository"),
                "checkoutMethod": "git clone",
                "command": command_template,
                "commandTemplate": command_template,
                "testCommandSource": repo_fixture.get("testCommandSource", "repo_fixture"),
                "pythonExecutable": Path(sys.executable).name if test_runner in {"pytest", "unittest"} else None,
                "exitCode": None,
                "durationMs": duration_ms,
                "stdout": "",
                "stderr": repr(exc),
                "checkoutSteps": checkout_steps,
                "sourceRepoFiles": sorted(str(path) for path in repo_files.keys()),
                "workspaceFiles": sorted(str(path) for path in workspace_files.keys()),
                "workspaceFileHashes": {
                    str(path): _stable_digest(str(content)) for path, content in workspace_files.items()
                },
            },
        )


def _write_fixture_worktree(worktree: Path, files: dict[str, Any]) -> None:
    """按 repo 相对路径写入临时 worktree，避免测试只读内存对象。"""
    worktree.mkdir(parents=True, exist_ok=True)
    resolved_worktree = worktree.resolve()
    for rel_path, content in files.items():
        path = (worktree / str(rel_path)).resolve()
        if not path.is_relative_to(resolved_worktree):
            raise ValueError(f"fixture path 越出临时 worktree：{rel_path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(str(content), encoding="utf-8")


def _repo_fixture_expectation_helpers(expectations: list[dict[str, Any]]) -> list[str]:
    """返回 fixture expectation 的共享测试辅助源码片段。"""
    expectation_json = json.dumps(expectations, ensure_ascii=False, sort_keys=True)
    return [
        "from __future__ import annotations",
        "import json",
        "from pathlib import Path",
        "",
        f"EXPECTATIONS = {expectation_json!r}",
        "expectations = json.loads(EXPECTATIONS)",
        "repo_root = Path(__file__).resolve().parents[1]",
        "",
        "def read_text(rel_path):",
        "    path = repo_root / rel_path",
        "    return path.read_text(encoding='utf-8') if path.exists() else ''",
        "",
        "def read_json(rel_path):",
        "    text = read_text(rel_path)",
        "    return json.loads(text) if text else None",
        "",
        "def get_field(payload, dotted):",
        "    current = payload",
        "    for part in str(dotted).split('.'):",
        "        if not isinstance(current, dict) or part not in current:",
        "            return None",
        "        current = current[part]",
        "    return current",
        "",
        "def evaluate_expectation(item):",
        "    value = str(item.get('value', ''))",
        "    check_type = item.get('type')",
        "    rel_path = Path(str(item.get('path') or 'skills/loomstead-debug/SKILL.md'))",
        "    file_text = read_text(rel_path)",
        "    if check_type == 'startswith':",
        "        return file_text.startswith(value)",
        "    if check_type == 'contains':",
        "        return value in file_text",
        "    if check_type == 'json_field_equals':",
        "        payload = read_json(rel_path)",
        "        return get_field(payload, item.get('field')) == item.get('value')",
        "    if check_type == 'json_array_contains':",
        "        payload = read_json(rel_path)",
        "        actual = get_field(payload, item.get('field'))",
        "        return isinstance(actual, list) and item.get('value') in actual",
        "    return False",
        "",
    ]


def _repo_fixture_pytest_script(expectations: list[dict[str, Any]]) -> str:
    """返回 pytest 测试源码，确保 fixture 走真实 pytest runner。"""
    lines = _repo_fixture_expectation_helpers(expectations)
    lines.extend(
        [
            "import pytest",
            "",
            "",
            "@pytest.mark.parametrize('item', expectations, ids=lambda item: item.get('caseId', 'unknown_case'))",
            "def test_fixture_expectation(item):",
            "    assert evaluate_expectation(item)",
            "",
        ]
    )
    return "\n".join(lines)


def _repo_fixture_unittest_script(expectations: list[dict[str, Any]]) -> str:
    """返回 unittest 测试源码，确保 fixture 走真实 unittest runner。"""
    lines = _repo_fixture_expectation_helpers(expectations)
    lines.extend(
        [
            "import unittest",
            "",
            "",
            "class FixtureExpectationTests(unittest.TestCase):",
            "    def test_fixture_expectations(self):",
            "        for item in expectations:",
            "            with self.subTest(caseId=item.get('caseId', 'unknown_case')):",
            "                self.assertTrue(evaluate_expectation(item))",
            "",
            "",
            "if __name__ == '__main__':",
            "    unittest.main()",
            "",
        ]
    )
    return "\n".join(lines)


def _initialise_git_repo(repo_dir: Path) -> list[dict[str, Any]]:
    """初始化本地 git 源仓库，模拟真实外部仓库 checkout 起点。"""
    steps: list[dict[str, Any]] = []
    steps.append(_run_git_command(["init", "--quiet"], cwd=repo_dir, check=True))
    steps.append(_run_git_command(["checkout", "-B", "main"], cwd=repo_dir, check=True))
    steps.append(_run_git_command(["config", "user.email", "fixture@example.invalid"], cwd=repo_dir, check=True))
    steps.append(_run_git_command(["config", "user.name", "Loomstead Fixture"], cwd=repo_dir, check=True))
    steps.append(_run_git_command(["add", "--all"], cwd=repo_dir, check=True))
    steps.append(_run_git_command(["commit", "--quiet", "-m", "initial fixture repo"], cwd=repo_dir, check=True))
    return steps


def _run_git_command(command: list[str], *, cwd: Path, check: bool) -> dict[str, Any]:
    """执行 git 命令并记录可复核结果，降低临时路径噪声。"""
    completed = subprocess.run(["git", *command], cwd=cwd, capture_output=True, text=True, encoding="utf-8", check=False)
    result = {
        "command": "git " + " ".join(_display_command_part(part) for part in command),
        "exitCode": completed.returncode,
        "stdout": _sanitize_temp_paths(completed.stdout),
        "stderr": _sanitize_temp_paths(completed.stderr),
    }
    if check and completed.returncode != 0:
        raise RuntimeError(f"git command failed: {result}")
    return result


def _fixture_test_runner(repo_fixture: dict[str, Any]) -> str:
    """从 fixture metadata 读取 testRunner，并做集中校验。"""
    metadata = repo_fixture.get("metadata", {}) if isinstance(repo_fixture.get("metadata"), dict) else {}
    test_runner = str(metadata.get("testRunner") or repo_fixture.get("testRunner") or "pytest")
    if test_runner not in TEST_RUNNER_COMMAND_TEMPLATES:
        raise ValueError(f"不支持的 repo fixture testRunner：{test_runner}")
    return test_runner


def _command_template_for_runner(test_runner: str) -> str:
    """由 adapter 统一把 runner 映射为命令模板，fixture 只声明 runner 类型。"""
    try:
        return TEST_RUNNER_COMMAND_TEMPLATES[test_runner]
    except KeyError as exc:
        raise ValueError(f"不支持的 repo fixture testRunner：{test_runner}") from exc


def _repo_test_command(test_runner: str) -> list[str]:
    """把 runner 类型转换为无 shell 的 subprocess 参数。"""
    if test_runner == "pytest":
        return [sys.executable, "-m", "pytest", "tests/test_skill.py", "-q"]
    if test_runner == "unittest":
        return [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_skill.py", "-q"]
    if test_runner == "node_test":
        node_executable = shutil.which("node") or shutil.which("node.exe") or "node"
        return [node_executable, "--test", "tests/skill_summary.test.mjs"]
    raise ValueError(f"不支持的 repo fixture testRunner：{test_runner}")


def _sanitize_temp_paths(value: str) -> str:
    """减少测试报告中的临时绝对路径噪声，保留命令结果主体。"""
    return value.replace("\\", "/")


def _display_command_part(value: str) -> str:
    """把临时 checkout 路径压缩成稳定占位符，避免 artifact 随路径漂移。"""
    normalized = value.replace("\\", "/")
    if "loomstead-coding-fixture-" not in normalized and ":" not in normalized:
        return value
    name = Path(value).name or "path"
    return f"<{name}>"


def _parse_fixture_test_cases(
    stdout: str,
    stderr: str = "",
    *,
    exit_code: int | None = None,
    test_runner: str = "pytest",
) -> list[dict[str, Any]]:
    """解析真实测试框架输出；无法逐项解析时保留 suite 级 case 便于 Eval 定位。"""
    try:
        payload = json.loads(stdout.strip() or "{}")
    except json.JSONDecodeError as exc:
        output = (stdout + "\n" + stderr).strip()
        return [_framework_suite_case(test_runner, exit_code=exit_code, output=output, error=repr(exc))]
    cases = payload.get("caseResults", [])
    output = (stdout + "\n" + stderr).strip()
    if not isinstance(cases, list):
        return [_framework_suite_case(test_runner, exit_code=exit_code, output=output, error="caseResults_not_list")]
    parsed_cases = [dict(item) for item in cases if isinstance(item, dict)]
    if len(parsed_cases) != len(cases):
        return [_framework_suite_case(test_runner, exit_code=exit_code, output=output, error="caseResult_not_object")]
    if not parsed_cases:
        return [_framework_suite_case(test_runner, exit_code=exit_code, output=output, error="caseResults_empty")]
    return parsed_cases


def _framework_suite_case(
    test_runner: str,
    *,
    exit_code: int | None,
    output: str,
    error: str | None = None,
) -> dict[str, Any]:
    """把 pytest / unittest / node:test 的原生命令输出压缩成稳定 suite case。"""
    passed = exit_code == 0
    case = {
        "caseId": f"{test_runner}_suite",
        "passed": passed,
        "runner": test_runner,
        "exitCode": exit_code,
        "passedCount": _extract_runner_count(output, "passed")
        + _extract_runner_count(output, "pass"),
        "failedCount": _extract_runner_count(output, "failed")
        + _extract_runner_count(output, "fail"),
    }
    summary = _first_nonempty_output_line(output)
    if summary:
        case["summary"] = summary
    if error and not passed:
        case["parseNote"] = error
    return case


def _extract_runner_count(output: str, label: str) -> int:
    """从常见框架 summary 中提取 passed / failed / pass / fail 计数。"""
    total = 0
    for match in re.finditer(rf"(?:#\s*)?(\d+)\s+{re.escape(label)}\b", output, flags=re.IGNORECASE):
        total += int(match.group(1))
    return total


def _first_nonempty_output_line(output: str) -> str:
    """保留首条非空输出用于人工复核，避免写入过长 stdout 副本。"""
    for line in output.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped[:200]
    return ""


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


def _safe_ratio(numerator: int | float, denominator: int | float) -> float:
    return float(numerator) / float(denominator) if float(denominator) else 0.0


def _safe_report_id_part(value: str) -> str:
    return "".join(char if char.isalnum() or char in {"-", "_", "."} else "_" for char in value)


def _stable_digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
