from __future__ import annotations

from pathlib import Path
import argparse
import json
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.eval import (  # noqa: E402
    run_cross_domain_adapter_scenarios,
    run_process_fidelity_scenarios,
    run_rule_scenarios,
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
        "passed": result.get("passed"),
        "total": result.get("total"),
        "metrics": result.get("metrics"),
        "ablation_comparison": result.get("ablation_comparison"),
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


def _compact_domain_output(result: dict) -> dict:
    return {
        "ok": result.get("ok"),
        "suite": result.get("suite"),
        "baseline": result.get("baseline"),
        "passed": result.get("passed"),
        "total": result.get("total"),
        "domains": result.get("domains"),
        "metrics": result.get("metrics"),
        "export": result.get("export"),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="运行 Loomstead Phase 2 Eval。")
    parser.add_argument(
        "--suite",
        choices=("rule", "process", "stability", "domain"),
        default="rule",
        help="选择 L1 rule、Process Fidelity、stability 或 cross-domain adapter suite。",
    )
    parser.add_argument("--full", action="store_true", help="输出完整 scenario 明细。")
    parser.add_argument("--export-dir", type=Path, default=None, help="导出 Process Fidelity / stability / domain 数据集。")
    parser.add_argument("--hours", type=int, default=24, help="stability suite 推进的游戏小时数。")
    args = parser.parse_args()

    if args.suite == "process":
        result = run_process_fidelity_scenarios(export_dir=args.export_dir)
        output = result if args.full else _compact_process_output(result)
    elif args.suite == "stability":
        result = run_stability_scenarios(hours=args.hours, export_dir=args.export_dir)
        output = result if args.full else _compact_stability_output(result)
    elif args.suite == "domain":
        result = run_cross_domain_adapter_scenarios(export_dir=args.export_dir)
        output = result if args.full else _compact_domain_output(result)
    else:
        result = run_rule_scenarios()
        # 默认保持简短输出，避免 npm.cmd run check 被 scenario 明细刷屏；需要明细时用 --full。
        output = result if args.full else _compact_rule_output(result)

    print(json.dumps(output, ensure_ascii=False, indent=2))
    if not result.get("ok"):
        raise SystemExit(1)
