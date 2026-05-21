from __future__ import annotations

from pathlib import Path
import argparse
import json
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.eval import run_rule_scenarios  # noqa: E402


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="运行 Loomstead Phase 2 规则 Eval。")
    parser.add_argument("--full", action="store_true", help="输出完整 scenario 明细。")
    args = parser.parse_args()

    result = run_rule_scenarios()
    # 默认输出压缩摘要，避免 npm.cmd run check 日志被 scenario 明细淹没；需要完整证据时使用 --full。
    output = result
    if not args.full:
        output = {
            "ok": result.get("ok"),
            "baseline": result.get("baseline"),
            "passed": result.get("passed"),
            "total": result.get("total"),
            "metrics": result.get("metrics"),
            "ablation_comparison": result.get("ablation_comparison"),
        }
    print(json.dumps(output, ensure_ascii=False, indent=2))
    if not result.get("ok"):
        raise SystemExit(1)
