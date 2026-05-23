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


CODING_GOAL_IDS = ("coding.skill_prototype_dryrun",)


class CodingDomainAdapter:
    """Secondary coding domain：用 repo fixture 验证接口可迁移到任务型开发。"""

    domain_id = "loomstead.coding.v0"
    kind = "task"

    def build_initial_world(self, scenario_id: str, seed: int) -> dict[str, Any]:
        goal = self.parse_goal(scenario_id)
        return {
            "tick": 0,
            "seed": seed,
            "goalId": goal.goal_id,
            "repoFixture": _build_repo_fixture(),
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
            "dependencies": {"repoFixtureId": "loomstead-debug-skill-fixture.v1"},
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
                        "repoFixtureId": "loomstead-debug-skill-fixture.v1",
                        "fileCount": 2,
                    },
                },
            ],
        }

    def parse_goal(self, raw_goal: str) -> DomainGoalSpec:
        known_goal_text = "Develop a skill prototype through design, tests, and review."
        if raw_goal not in CODING_GOAL_IDS and raw_goal != known_goal_text:
            raise ValueError(f"未知 coding goal：{raw_goal}")
        required_process = [
            {"id": "repo_fixture_loaded", "predicate": "external repo fixture is loaded before design"},
            {"id": "design_review_loaded", "predicate": "design review event is loaded before implementation"},
            {"id": "implementation_diff", "predicate": "implementer creates an artifact diff"},
            {
                "id": "materialized_checkout_tested",
                "predicate": "evaluation checkpoint materializes checkout and runs command",
            },
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
        test_report = test_reports.get("skill_prototype.tests", {})
        review_report = review_reports.get("skill_prototype.review", {})
        process_checks = {
            "repo_fixture_loaded": "coding.repo_fixture_loaded" in event_types and bool(repo_fixture.get("files")),
            "design_review_loaded": "coding.design_review_loaded" in event_types,
            "implementation_diff": "coding.implementation_diff_created" in event_types
            and "skill_prototype.patch" in artifacts,
            "materialized_checkout_tested": "coding.tests_executed" in event_types
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
            goal_success_override=process_checks["review_completed"] and process_checks["materialized_checkout_tested"],
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
        patch_text = str(world.get("artifacts", {}).get("skill_prototype.patch", {}).get("patchText", ""))
        if patch_text:
            (path / "skill_prototype.patch").write_text(patch_text + "\n", encoding="utf-8")


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
        target_path = "skills/loomstead-debug/SKILL.md"
        artifact = {
            "artifactId": "skill_prototype.patch",
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
        world.setdefault("artifacts", {})["skill_prototype.patch"] = artifact
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
        artifact = world.get("artifacts", {}).get("skill_prototype.patch", {})
        test_cases, execution = _run_materialized_fixture_tests(artifact)
        test_report = {
            "testReportId": "skill_prototype.tests",
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
        world.setdefault("testReports", {})["skill_prototype.tests"] = test_report
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
        test_report = world.get("testReports", {}).get("skill_prototype.tests", {})
        review_report = {
            "reviewReportId": "skill_prototype.review",
            "status": "approved",
            "sourceTestReportId": test_report.get("testReportId", "skill_prototype.tests"),
            "sourceEventIds": [_event_id(test_event)],
            "repoFixtureId": world.get("repoFixture", {}).get("fixtureId", ""),
            "citedMemoryIds": ["prior_failure.skip_tests"],
            "checklist": [
                {"id": "repo_fixture_loaded", "passed": True},
                {"id": "design_before_diff", "passed": True},
                {
                    "id": "materialized_tests_before_review",
                    "passed": bool(test_report.get("execution", {}).get("executed"))
                    and test_report.get("execution", {}).get("exitCode") == 0,
                },
                {"id": "failure_memory_cited", "passed": True},
            ],
        }
        review_report["sha256"] = _stable_digest(json.dumps(review_report, ensure_ascii=False, sort_keys=True))
        world.setdefault("reviewReports", {})["skill_prototype.review"] = review_report
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


def _build_repo_fixture() -> dict[str, Any]:
    """构造可重复的外部仓库 fixture，模拟跨域 coding 输入。"""
    files = {
        "README.md": "# Skill Fixture\n\nThis fixture represents a tiny external skill repository.\n",
        "skills/loomstead-debug/SKILL.md": (
            "# Loomstead Debug Skill\n\n"
            "Use project docs before changing runtime code.\n"
        ),
    }
    return {
        "fixtureId": "loomstead-debug-skill-fixture.v1",
        "repoName": "fixture/loomstead-debug-skill",
        "defaultBranch": "main",
        "files": files,
        "fileHashes": {path: _stable_digest(content) for path, content in files.items()},
        "testCommand": "fixture:check_skill_stub loomstead-debug",
    }


def _build_skill_patch(repo_fixture: dict[str, Any]) -> tuple[str, dict[str, str]]:
    files = dict(repo_fixture.get("files", {})) if isinstance(repo_fixture.get("files"), dict) else {}
    target_path = "skills/loomstead-debug/SKILL.md"
    original = str(files.get(target_path, ""))
    additions = [
        "Use observer trace evidence before proposing runtime changes.",
        "Always run eval:domain before marking adapter changes done.",
    ]
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


def _run_materialized_fixture_tests(artifact: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """把 patched files 写入临时 checkout，并运行真实 Python 检查命令。"""
    patched_files = artifact.get("patchedFiles", {}) if isinstance(artifact.get("patchedFiles"), dict) else {}
    command_template = "python check_fixture.py <temporary_fixture_checkout>"
    started = time.perf_counter()
    try:
        with tempfile.TemporaryDirectory(prefix="loomstead-coding-fixture-") as temp_dir:
            worktree = Path(temp_dir) / "worktree"
            _write_fixture_worktree(worktree, patched_files)
            check_script = Path(temp_dir) / "check_fixture.py"
            check_script.write_text(_fixture_check_script(), encoding="utf-8")
            command = [sys.executable, str(check_script), str(worktree)]
            completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", check=False)
            duration_ms = round((time.perf_counter() - started) * 1000.0, 3)
            parsed_cases = _parse_fixture_test_cases(completed.stdout)
            execution = {
                "executed": True,
                "workspaceKind": "temporary_fixture_checkout",
                "command": command_template,
                "commandTemplate": command_template,
                "pythonExecutable": Path(sys.executable).name,
                "exitCode": completed.returncode,
                "durationMs": duration_ms,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
                "workspaceFiles": sorted(str(path) for path in patched_files.keys()),
                "workspaceFileHashes": {
                    str(path): _stable_digest(str(content)) for path, content in patched_files.items()
                },
            }
            return parsed_cases, execution
    except Exception as exc:
        duration_ms = round((time.perf_counter() - started) * 1000.0, 3)
        return (
            [{"caseId": "materialize_fixture_checkout", "passed": False, "error": repr(exc)}],
            {
                "executed": False,
                "workspaceKind": "temporary_fixture_checkout",
                "command": command_template,
                "commandTemplate": command_template,
                "pythonExecutable": Path(sys.executable).name,
                "exitCode": None,
                "durationMs": duration_ms,
                "stdout": "",
                "stderr": repr(exc),
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


def _fixture_check_script() -> str:
    """返回临时测试脚本源码，命令执行结果会进入 test report。"""
    return "\n".join(
        [
            "from __future__ import annotations",
            "import json",
            "import sys",
            "from pathlib import Path",
            "",
            "worktree = Path(sys.argv[1])",
            "skill_path = worktree / 'skills' / 'loomstead-debug' / 'SKILL.md'",
            "skill_text = skill_path.read_text(encoding='utf-8') if skill_path.exists() else ''",
            "cases = [",
            "    {'caseId': 'loads_skill_md', 'passed': skill_text.startswith('# Loomstead Debug Skill')},",
            "    {'caseId': 'mentions_observer_trace', 'passed': 'observer trace evidence' in skill_text},",
            "    {'caseId': 'requires_eval_domain', 'passed': 'eval:domain' in skill_text},",
            "    {'caseId': 'keeps_existing_doc_guidance', 'passed': 'Use project docs' in skill_text},",
            "]",
            "print(json.dumps({'caseResults': cases}, ensure_ascii=False))",
            "raise SystemExit(0 if all(item['passed'] for item in cases) else 1)",
            "",
        ]
    )


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
