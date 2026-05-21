from __future__ import annotations

from pathlib import Path
import argparse
import json
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.eval import run_process_fidelity_scenarios, run_rule_scenarios  # noqa: E402


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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="?? Loomstead Phase 2 Eval?")
    parser.add_argument("--suite", choices=("rule", "process"), default="rule", help="?? L1 rule suite ? Process Fidelity suite?")
    parser.add_argument("--full", action="store_true", help="???? scenario ???")
    parser.add_argument("--export-dir", type=Path, default=None, help="? Process Fidelity ????????????")
    args = parser.parse_args()

    if args.suite == "process":
        result = run_process_fidelity_scenarios(export_dir=args.export_dir)
        output = result if args.full else _compact_process_output(result)
    else:
        result = run_rule_scenarios()
        # ??????????? npm.cmd run check ??? scenario ?????????????? --full?
        output = result if args.full else _compact_rule_output(result)

    print(json.dumps(output, ensure_ascii=False, indent=2))
    if not result.get("ok"):
        raise SystemExit(1)
