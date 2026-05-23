from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from app.domain.base import DomainGoalSpec, DomainIntervention, DomainObservation, InterventionType
from app.eval.process_fidelity import build_process_metrics


CODING_GOAL_IDS = ("coding.skill_prototype_dryrun", "coding.skill_regression_fix_dryrun")
CODING_GOAL_TEXT = {
    "coding.skill_prototype_dryrun": "Develop a skill prototype through design, tests, and review.",
    "coding.skill_regression_fix_dryrun": "Fix a skill regression through design, checkout tests, and review.",
}


class CodingDomainAdapter:
    """Secondary coding domain：用 repo fixture 验证接口可迁移到任务型开发。"""

    domain_id = "loomstead.coding.v0"
    kind = "task"

    def build_initial_world(self, scenario_id: str, seed: int) -> dict[str, Any]:
        goal = self.parse_goal(scenario_id)
        repo_fixture = _build_repo_fixture(goal.goal_id)
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
            },
            "constraints": [],
            "artifacts": {},
            "testReports": {},
            "reviewReports": {},
            "dependencies": {"repoFixtureId": repo_fixture.get("fixtureId", "")},
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
                        "testCommand": repo_fixture.get("testCommand"),
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
        desired_artifact = (
            "skill_regression_fix" if goal_id == "coding.skill_regression_fix_dryrun" else "skill_prototype"
        )
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
            success_evidence=["design_event", "diff_event", "test_event", "review_event"],
            max_steps=4,
        )

    def observe(self, world: dict[str, Any], goal: DomainGoalSpec) -> DomainObservation:
        return DomainObservation(
            tick=int(world.get("tick", 0)),
            world_summary={
                "artifactCount": float(len(world.get("artifacts", {}))),
                "testReportCount": float(len(world.get("testReports", {}))),
                "reviewReportCount": float(len(world.get("reviewReports", {}))),
                "constraintCount": float(len(world.get("constraints", []))),
                "repoFixtureId": str(world.get("repoFixture", {}).get("fixtureId", "")),
                "repoFileRefs": sorted(str(key) for key in world.get("repoFixture", {}).get("files", {}).keys())
                if isinstance(world.get("repoFixture"), dict)
                else [],
                "artifactRefs": sorted(str(key) for key in world.get("artifacts", {}).keys()),
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
        test_reports = world.get("testReports", {}) if isinstance(world.get("testReports"), dict) else {}
        review_reports = world.get("reviewReports", {}) if isinstance(world.get("reviewReports"), dict) else {}
        repo_fixture = world.get("repoFixture", {}) if isinstance(world.get("repoFixture"), dict) else {}
        artifact_id = str(repo_fixture.get("artifactId") or "skill_prototype.patch")
        test_report_id = str(repo_fixture.get("testReportId") or "skill_prototype.tests")
        review_report_id = str(repo_fixture.get("reviewReportId") or "skill_prototype.review")
        test_report = test_reports.get(test_report_id, {})
        review_report = review_reports.get(review_report_id, {})
        process_checks = {
            "repo_fixture_loaded": "coding.repo_fixture_loaded" in event_types and bool(repo_fixture.get("files")),
            "design_review_loaded": "coding.design_review_loaded" in event_types,
            "implementation_diff": "coding.implementation_diff_created" in event_types
            and artifact_id in artifacts,
            "external_repo_checkout_tested": "coding.tests_executed" in event_types
            and bool(test_report.get("passed"))
            and bool(test_report.get("execution", {}).get("executed"))
            and test_report.get("execution", {}).get("exitCode") == 0,
            "review_completed": bool(review_event) and review_report.get("status") == "approved",
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
        emitted.append(
            _append_event(
                world,
                "coding.design_review_loaded",
                {
                    "agentId": "architect",
                    "designDocRef": "design.skill_prototype.v1",
                    "repoFixtureId": world.get("repoFixture", {}).get("fixtureId", ""),
                    "acceptedConstraints": ["must_run_tests"],
                },
            )
        )
        world["agents"]["architect"]["state"] = "design_reviewed"
    elif "coding.implementation_diff_created" not in event_types:
        design_event = _first_event(world, "coding.design_review_loaded")
        repo_fixture = world.get("repoFixture", {}) if isinstance(world.get("repoFixture"), dict) else {}
        patch_text, patched_files = _build_skill_patch(repo_fixture)
        base_files = repo_fixture.get("files", {}) if isinstance(repo_fixture.get("files"), dict) else {}
        target_path = str(repo_fixture.get("targetPath") or "skills/loomstead-debug/SKILL.md")
        artifact_id = str(repo_fixture.get("artifactId") or "skill_prototype.patch")
        artifact = {
            "artifactId": artifact_id,
            "kind": "repo_patch",
            "repoFixtureId": repo_fixture.get("fixtureId", ""),
            "path": target_path,
            "status": "created",
            "sourceEventIds": [_event_id(design_event)],
            "changedFiles": [target_path],
            "baseFileSha256": _stable_digest(str(base_files.get(target_path, ""))),
            "patchedFileSha256": _stable_digest(str(patched_files.get(target_path, ""))),
            "patchText": patch_text,
            "patchedFiles": patched_files,
            "sha256": _stable_digest(patch_text),
        }
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
        test_cases, execution = _run_external_checkout_fixture_tests(artifact, repo_fixture)
        test_report = {
            "testReportId": test_report_id,
            "command": execution.get("command", "python check_fixture.py <worktree>"),
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
                    "workspaceKind": execution.get("workspaceKind"),
                    "sourceArtifactId": test_report["sourceArtifactId"],
                    "sourceEventIds": test_report["sourceEventIds"],
                    "testReportSha256": test_report["sha256"],
                },
            )
        )
    elif "coding.review_completed" not in event_types:
        test_event = _first_event(world, "coding.tests_executed")
        repo_fixture = world.get("repoFixture", {}) if isinstance(world.get("repoFixture"), dict) else {}
        test_report_id = str(repo_fixture.get("testReportId") or "skill_prototype.tests")
        review_report_id = str(repo_fixture.get("reviewReportId") or "skill_prototype.review")
        test_report = world.get("testReports", {}).get(test_report_id, {})
        review_report = {
            "reviewReportId": review_report_id,
            "status": "approved",
            "sourceTestReportId": test_report.get("testReportId", test_report_id),
            "sourceEventIds": [_event_id(test_event)],
            "repoFixtureId": world.get("repoFixture", {}).get("fixtureId", ""),
            "citedMemoryIds": ["prior_failure.skip_tests"],
            "checklist": [
                {"id": "repo_fixture_loaded", "passed": True},
                {"id": "design_before_diff", "passed": True},
                {
                    "id": "external_checkout_tests_before_review",
                    "passed": bool(test_report.get("execution", {}).get("executed"))
                    and test_report.get("execution", {}).get("exitCode") == 0,
                },
                {"id": "failure_memory_cited", "passed": True},
            ],
        }
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


def _build_repo_fixture(goal_id: str) -> dict[str, Any]:
    """构造可重复的外部仓库 fixture，模拟跨域 coding 输入。"""
    if goal_id == "coding.skill_regression_fix_dryrun":
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

    files = {
        "README.md": "# Skill Fixture\n\nThis fixture represents a tiny external skill repository.\n",
        "skills/loomstead-debug/SKILL.md": (
            "# Loomstead Debug Skill\n\n"
            "Use project docs before changing runtime code.\n"
        ),
        "check_skill.py": _repo_fixture_test_script(test_expectations),
    }
    return {
        "fixtureId": fixture_id,
        "repoName": "fixture/loomstead-debug-skill",
        "defaultBranch": "main",
        "files": files,
        "fileHashes": {path: _stable_digest(content) for path, content in files.items()},
        "targetPath": "skills/loomstead-debug/SKILL.md",
        "artifactId": artifact_id,
        "testReportId": test_report_id,
        "reviewReportId": review_report_id,
        "testCommand": "python check_skill.py",
        "testCommandSource": "repo_fixture",
        "plannedAdditions": planned_additions,
        "testExpectations": test_expectations,
        "sourceRepoKind": "deterministic_local_git_repository",
    }


def _build_skill_patch(repo_fixture: dict[str, Any]) -> tuple[str, dict[str, str]]:
    files = dict(repo_fixture.get("files", {})) if isinstance(repo_fixture.get("files"), dict) else {}
    target_path = str(repo_fixture.get("targetPath") or "skills/loomstead-debug/SKILL.md")
    original = str(files.get(target_path, ""))
    planned_additions = repo_fixture.get("plannedAdditions", [])
    additions = [str(item) for item in planned_additions] if isinstance(planned_additions, list) else []
    patched = original.rstrip() + "\n" + "\n".join(additions) + "\n"
    files[target_path] = patched
    patch_text = "\n".join(
        [
            f"--- a/{target_path}",
            f"+++ b/{target_path}",
            "@@",
            *[f"+{line}" for line in additions],
        ]
    )
    return patch_text, files


def _run_external_checkout_fixture_tests(
    artifact: dict[str, Any], repo_fixture: dict[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """创建独立 git 仓库、执行真实 checkout，并运行仓库自带测试命令。"""
    patched_files = artifact.get("patchedFiles", {}) if isinstance(artifact.get("patchedFiles"), dict) else {}
    repo_files = repo_fixture.get("files", {}) if isinstance(repo_fixture.get("files"), dict) else {}
    command_template = str(repo_fixture.get("testCommand") or "python check_skill.py")
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
            _write_fixture_worktree(checkout, patched_files)
            checkout_status = _run_git_command(["status", "--short"], cwd=checkout, check=True)["stdout"].splitlines()
            command = _repo_test_command(command_template)
            completed = subprocess.run(command, cwd=checkout, capture_output=True, text=True, encoding="utf-8", check=False)
            duration_ms = round((time.perf_counter() - started) * 1000.0, 3)
            parsed_cases = _parse_fixture_test_cases(completed.stdout)
            execution = {
                "executed": True,
                "workspaceKind": "git_external_repo_checkout",
                "sourceRepoKind": repo_fixture.get("sourceRepoKind", "deterministic_local_git_repository"),
                "checkoutMethod": "git clone",
                "command": command_template,
                "commandTemplate": command_template,
                "testCommandSource": repo_fixture.get("testCommandSource", "repo_fixture"),
                "pythonExecutable": Path(sys.executable).name,
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
                "workspaceFiles": sorted(str(path) for path in patched_files.keys()),
                "workspaceFileHashes": {
                    str(path): _stable_digest(str(content)) for path, content in patched_files.items()
                },
            }
            return parsed_cases, execution
    except Exception as exc:
        duration_ms = round((time.perf_counter() - started) * 1000.0, 3)
        return (
            [{"caseId": "external_repo_checkout", "passed": False, "error": repr(exc)}],
            {
                "executed": False,
                "workspaceKind": "git_external_repo_checkout",
                "sourceRepoKind": repo_fixture.get("sourceRepoKind", "deterministic_local_git_repository"),
                "checkoutMethod": "git clone",
                "command": command_template,
                "commandTemplate": command_template,
                "testCommandSource": repo_fixture.get("testCommandSource", "repo_fixture"),
                "pythonExecutable": Path(sys.executable).name,
                "exitCode": None,
                "durationMs": duration_ms,
                "stdout": "",
                "stderr": repr(exc),
                "checkoutSteps": checkout_steps,
                "sourceRepoFiles": sorted(str(path) for path in repo_files.keys()),
                "workspaceFiles": sorted(str(path) for path in patched_files.keys()),
                "workspaceFileHashes": {
                    str(path): _stable_digest(str(content)) for path, content in patched_files.items()
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


def _repo_fixture_test_script(expectations: list[dict[str, str]]) -> str:
    """返回仓库自带测试脚本源码，随外部 fixture repo 一起 checkout。"""
    expectation_json = json.dumps(expectations, ensure_ascii=False, sort_keys=True)
    return "\n".join(
        [
            "from __future__ import annotations",
            "import json",
            "from pathlib import Path",
            "",
            f"EXPECTATIONS = {expectation_json!r}",
            "expectations = json.loads(EXPECTATIONS)",
            "repo_root = Path(__file__).resolve().parent",
            "skill_path = repo_root / 'skills' / 'loomstead-debug' / 'SKILL.md'",
            "skill_text = skill_path.read_text(encoding='utf-8') if skill_path.exists() else ''",
            "cases = []",
            "for item in expectations:",
            "    value = str(item.get('value', ''))",
            "    check_type = item.get('type')",
            "    if check_type == 'startswith':",
            "        passed = skill_text.startswith(value)",
            "    elif check_type == 'contains':",
            "        passed = value in skill_text",
            "    else:",
            "        passed = False",
            "    cases.append({'caseId': item.get('caseId', 'unknown_case'), 'passed': passed})",
            "print(json.dumps({'caseResults': cases}, ensure_ascii=False))",
            "raise SystemExit(0 if all(item['passed'] for item in cases) else 1)",
            "",
        ]
    )


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


def _repo_test_command(command_template: str) -> list[str]:
    """把 repo fixture 的测试命令转换为无 shell 的 subprocess 参数。"""
    if command_template != "python check_skill.py":
        raise ValueError(f"不支持的 repo fixture 测试命令：{command_template}")
    return [sys.executable, "check_skill.py"]


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


def _parse_fixture_test_cases(stdout: str) -> list[dict[str, Any]]:
    """解析真实命令输出；解析失败时返回单个失败 case 便于 Eval 定位。"""
    try:
        payload = json.loads(stdout.strip() or "{}")
    except json.JSONDecodeError as exc:
        return [{"caseId": "parse_fixture_test_output", "passed": False, "error": repr(exc)}]
    cases = payload.get("caseResults", [])
    if not isinstance(cases, list):
        return [{"caseId": "parse_fixture_test_output", "passed": False, "error": "caseResults_not_list"}]
    parsed_cases = [dict(item) for item in cases if isinstance(item, dict)]
    if len(parsed_cases) != len(cases):
        return [{"caseId": "parse_fixture_test_output", "passed": False, "error": "caseResult_not_object"}]
    if not parsed_cases:
        return [{"caseId": "parse_fixture_test_output", "passed": False, "error": "caseResults_empty"}]
    return parsed_cases


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


def _stable_digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
