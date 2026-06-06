from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.eval.audit_llm_smoke import (  # noqa: E402
    AUDIT_LLM_BASELINES,
    ALL_AUDIT_LLM_SCENARIO_IDS,
    DEFAULT_AUDIT_LLM_SCENARIO_IDS,
    run_audit_llm_smoke,
    sanitized_live_profile_debug,
)


def _compact_output(result: dict[str, Any]) -> dict[str, Any]:
    """压缩命令行输出，完整 prompt / response 留在导出 artifact 中复核。"""

    export = result.get("export", {}) if isinstance(result.get("export"), dict) else {}
    llm_evidence = result.get("llmEvidence", {}) if isinstance(result.get("llmEvidence"), dict) else {}
    return {
        "ok": result.get("ok"),
        "suite": result.get("suite"),
        "baseline": result.get("baseline"),
        "providerMode": result.get("providerMode"),
        "seedCount": result.get("seedCount"),
        "passed": result.get("passed"),
        "total": result.get("total"),
        "scenarioIds": sorted({str(item.get("scenarioId") or "") for item in result.get("items", [])}),
        "conditions": sorted({str(item.get("baseline") or "") for item in result.get("items", [])}),
        "goNoGo": result.get("goNoGo"),
        "llmEvidence": {
            "providerUsageSchemaVersion": llm_evidence.get("providerUsageSchemaVersion"),
            "providerMode": llm_evidence.get("providerMode"),
            "recordCount": llm_evidence.get("recordCount"),
            "totals": llm_evidence.get("totals"),
            "note": llm_evidence.get("note"),
        },
        "export": {
            "runDir": export.get("runDir"),
            "manifest": export.get("manifest"),
            "artifactCount": export.get("artifactCount"),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="运行 Auditable Agents 最小 LLM 契约 smoke。")
    parser.add_argument("--live", action="store_true", help="调用真实 CloudApiProvider；需要显式环境变量授权。")
    parser.add_argument("--export-dir", type=Path, default=None, help="导出 smoke artifact 的根目录。")
    parser.add_argument("--all-scenarios", action="store_true", help="覆盖 deterministic audit suite 的全部 5 个高风险场景。")
    parser.add_argument("--scenario", action="append", default=[], help="指定 audit scenario id；可重复传入。")
    parser.add_argument(
        "--condition",
        choices=AUDIT_LLM_BASELINES,
        action="append",
        default=[],
        help="指定 evidence 条件；默认 full_runtime + no_policy_evidence。",
    )
    parser.add_argument("--seeds", type=int, default=1, help="每个 scenario / condition 的重复次数。")
    parser.add_argument("--full", action="store_true", help="输出完整结果；默认只输出摘要。")
    args = parser.parse_args()

    if args.all_scenarios and args.scenario:
        parser.error("--all-scenarios 与 --scenario 不能同时使用。")
    scenario_ids = ALL_AUDIT_LLM_SCENARIO_IDS if args.all_scenarios else tuple(args.scenario) if args.scenario else DEFAULT_AUDIT_LLM_SCENARIO_IDS
    conditions = tuple(args.condition) if args.condition else AUDIT_LLM_BASELINES
    if args.live:
        print("[audit-llm-smoke] live profile", json.dumps(sanitized_live_profile_debug(), ensure_ascii=False))

    result = run_audit_llm_smoke(
        export_dir=args.export_dir,
        scenario_ids=scenario_ids,
        baselines=conditions,
        seed_count=args.seeds,
        live=args.live,
    )
    print(json.dumps(result if args.full else _compact_output(result), ensure_ascii=False, indent=2))
    if not result.get("ok"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
