from __future__ import annotations

from pathlib import Path
import argparse
import json
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.eval import (  # noqa: E402
    DEFAULT_PROCESS_GOALS,
    ProcessGoalSpec,
    run_cross_domain_adapter_scenarios,
    run_evidence_robustness_scenarios,
    run_process_fidelity_scenarios,
    run_rule_scenarios,
    run_stability_determinism_check,
    run_stability_scenarios,
)


def _compact_rule_output(result: dict) -> dict:
    return {
        "ok": result.get("ok"),
        "baseline": result.get("baseline"),
        "passed": result.get("passed"),
        "total": result.get("total"),
        "metrics": result.get("metrics"),
        "ablation_comparison": result.get("ablation_comparison"),
    }


def _compact_process_output(result: dict) -> dict:
    return {
        "ok": result.get("ok"),
        "suite": result.get("suite"),
        "baseline": result.get("baseline"),
        "providerMode": result.get("providerMode"),
        "seedCount": result.get("seedCount"),
        "passed": result.get("passed"),
        "total": result.get("total"),
        "metrics": result.get("metrics"),
        "ablation_comparison": result.get("ablation_comparison"),
        "llmEvidence": result.get("llmEvidence"),
        "export": result.get("export"),
    }


def _compact_stability_output(result: dict) -> dict:
    return {
        "ok": result.get("ok"),
        "suite": result.get("suite"),
        "baseline": result.get("baseline"),
        "hours": result.get("hours"),
        "ticksCompleted": result.get("ticksCompleted"),
        "checks": result.get("checks"),
        "metrics": result.get("metrics"),
        "evidence": result.get("evidence"),
        "export": result.get("export"),
    }


def _compact_stability_determinism_output(result: dict) -> dict:
    return {
        "ok": result.get("ok"),
        "suite": result.get("suite"),
        "baseline": result.get("baseline"),
        "hours": result.get("hours"),
        "repeats": result.get("repeats"),
        "invariantSignature": result.get("invariantSignature"),
        "mismatches": result.get("mismatches"),
        "runSpecificEvidence": result.get("runSpecificEvidence"),
        "notes": result.get("notes"),
    }


def _compact_domain_output(result: dict) -> dict:
    return {
        "ok": result.get("ok"),
        "suite": result.get("suite"),
        "baseline": result.get("baseline"),
        "seedCount": result.get("seedCount"),
        "passed": result.get("passed"),
        "total": result.get("total"),
        "domains": result.get("domains"),
        "metrics": result.get("metrics"),
        "export": result.get("export"),
    }


def _compact_robustness_output(result: dict) -> dict:
    return {
        "ok": result.get("ok"),
        "suite": result.get("suite"),
        "baseline": result.get("baseline"),
        "providerMode": result.get("providerMode"),
        "robustnessChecksPass": result.get("robustnessChecksPass"),
        "seedCount": result.get("seedCount"),
        "passed": result.get("passed"),
        "total": result.get("total"),
        "metrics": result.get("metrics"),
        "process": {
            "baseEvalOk": result.get("process", {}).get("baseEvalOk"),
            "scenarioCount": result.get("process", {}).get("scenarioCount"),
            "selectedScenarioIds": result.get("process", {}).get("selectedScenarioIds"),
            "overallInvarianceRate": result.get("process", {}).get("overallInvarianceRate"),
            "perturbations": result.get("process", {}).get("perturbations"),
        },
        "domain": {
            "baseEvalOk": result.get("domain", {}).get("baseEvalOk"),
            "scenarioCount": result.get("domain", {}).get("scenarioCount"),
            "overallInvarianceRate": result.get("domain", {}).get("overallInvarianceRate"),
            "perturbations": result.get("domain", {}).get("perturbations"),
        },
        "export": result.get("export"),
    }


def _select_process_scenarios(scenario_ids: list[str]) -> tuple[ProcessGoalSpec, ...]:
    """按 CLI 指定的 GoalSpec id 过滤 process suite，未指定时保持完整 suite。"""
    if not scenario_ids:
        return DEFAULT_PROCESS_GOALS
    wanted = {str(item).strip() for item in scenario_ids if str(item).strip()}
    by_id = {scenario.scenario_id: scenario for scenario in DEFAULT_PROCESS_GOALS}
    missing = sorted(wanted - set(by_id))
    if missing:
        raise SystemExit(f"未知 process scenario：{', '.join(missing)}")
    return tuple(scenario for scenario in DEFAULT_PROCESS_GOALS if scenario.scenario_id in wanted)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="运行 Loomstead Phase 2 Eval。")
    parser.add_argument(
        "--suite",
        choices=("rule", "process", "stability", "domain", "robustness"),
        default="rule",
        help="选择 L1 rule、Process Fidelity、stability、cross-domain adapter 或 evidence robustness suite。",
    )
    parser.add_argument("--full", action="store_true", help="输出完整 scenario 明细。")
    parser.add_argument("--export-dir", type=Path, default=None, help="导出 Process Fidelity / stability / domain / robustness 数据集。")
    parser.add_argument("--hours", type=int, default=24, help="stability suite 推进的游戏小时数。")
    parser.add_argument("--determinism-check", action="store_true", help="对 stability suite 连跑多次并比较硬门禁不变量。")
    parser.add_argument("--repeats", type=int, default=3, help="stability determinism check 连续运行次数。")
    parser.add_argument("--provider", choices=("rule", "cloud", "mixed"), default="rule", help="process suite 的 provider 模式。")
    parser.add_argument("--scenario", action="append", default=[], help="只运行指定 Process GoalSpec id，可重复传入。")
    parser.add_argument("--seeds", type=int, default=1, help="对 process / domain suite 追加 seed 重复次数。")
    args = parser.parse_args()

    seed_count = max(1, int(args.seeds))
    if args.suite == "process":
        result = run_process_fidelity_scenarios(
            scenarios=_select_process_scenarios(args.scenario),
            export_dir=args.export_dir,
            provider_mode=args.provider,
            seed_count=seed_count,
            attach_latest_llm_evidence=args.export_dir is not None and args.provider == "rule",
        )
        output = result if args.full else _compact_process_output(result)
    elif args.suite == "stability":
        if args.determinism_check:
            result = run_stability_determinism_check(hours=args.hours, repeats=args.repeats)
            output = result if args.full else _compact_stability_determinism_output(result)
        else:
            result = run_stability_scenarios(hours=args.hours, export_dir=args.export_dir)
            output = result if args.full else _compact_stability_output(result)
    elif args.suite == "domain":
        result = run_cross_domain_adapter_scenarios(export_dir=args.export_dir, seed_count=seed_count)
        output = result if args.full else _compact_domain_output(result)
    elif args.suite == "robustness":
        result = run_evidence_robustness_scenarios(
            process_scenarios=_select_process_scenarios(args.scenario),
            process_seed_count=seed_count,
            domain_seed_count=seed_count,
            export_dir=args.export_dir,
        )
        output = result if args.full else _compact_robustness_output(result)
    else:
        result = run_rule_scenarios()
        # 默认保持简短输出，避免 npm.cmd run check 被 scenario 明细刷屏；需要明细时用 --full。
        output = result if args.full else _compact_rule_output(result)

    print(json.dumps(output, ensure_ascii=False, indent=2))
    if not result.get("ok"):
        raise SystemExit(1)
