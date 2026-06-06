from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))


def main() -> None:
    parser = argparse.ArgumentParser(description="生成真实 audit LLM smoke 的 reviewer supplement。")
    parser.add_argument("--run-dir", type=Path, default=None, help="指定 audit_llm_smoke run 目录；默认选择最新 cloud 且 ok 的 run。")
    parser.add_argument("--runs-dir", type=Path, default=Path(".run/eval-runs"), help="用于自动发现最新 run 的根目录。")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path(".run/eval-reviewer-packets"),
        help="supplement 输出根目录。",
    )
    args = parser.parse_args()

    run_dir = args.run_dir or _latest_cloud_run(args.runs_dir)
    if run_dir is None:
        raise SystemExit("未找到 providerMode=cloud 且 ok=true 的 audit_llm_smoke run。")
    output_dir = _unique_dir(args.output_root / f"audit_llm_supplement_{_timestamp_slug()}")
    packet = build_audit_llm_supplement(run_dir=run_dir, output_dir=output_dir)
    print(json.dumps(packet, ensure_ascii=False, indent=2))


def build_audit_llm_supplement(*, run_dir: Path, output_dir: Path) -> dict[str, Any]:
    """把真实 LLM smoke artifact 压成 reviewer 可读补充材料，避免 reviewer 直接翻 raw JSON。"""

    run_dir = run_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_dir = output_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    summary = _read_json(run_dir / "summary.json")
    manifest = _read_json(run_dir / "manifest.json")
    go_no_go = _read_json(run_dir / "go_no_go.json")
    llm_evidence = _read_json(run_dir / "llm_evidence.json") if (run_dir / "llm_evidence.json").exists() else {}
    cases = _load_cases(run_dir)
    pairs = _pair_cases(cases)

    readme_path = output_dir / "README.md"
    readme_path.write_text(
        _render_readme(
            run_dir=run_dir,
            summary=summary,
            manifest=manifest,
            go_no_go=go_no_go,
            llm_evidence=llm_evidence,
            pairs=pairs,
        ),
        encoding="utf-8",
    )

    case_path = output_dir / "LLM_CASE_COMPARISONS.md"
    case_path.write_text(_render_case_comparisons(pairs), encoding="utf-8")

    score_sheet_path = output_dir / "REVIEWER_MICRO_SCORE_SHEET.csv"
    score_sheet_path.write_text(_render_score_sheet(pairs), encoding="utf-8")

    for name in ("summary.json", "go_no_go.json", "llm_evidence.json", "manifest.json"):
        source = run_dir / name
        if source.exists():
            shutil.copy2(source, raw_dir / name)
    per_case_raw_dir = raw_dir / "per_case"
    per_case_raw_dir.mkdir(exist_ok=True)
    for case in cases:
        source = Path(case["_path"])
        shutil.copy2(source, per_case_raw_dir / source.name)

    packet_summary = {
        "packetVersion": "audit.llm_supplement_packet.v1",
        "sourceRunDir": str(run_dir),
        "outputDir": str(output_dir),
        "ok": bool(summary.get("ok")),
        "providerMode": summary.get("providerMode"),
        "passed": summary.get("passed"),
        "total": summary.get("total"),
        "scenarioCount": len(pairs),
        "caseCount": len(cases),
        "tokens": (llm_evidence.get("totals") or {}).get("tokens"),
        "costUsd": (llm_evidence.get("totals") or {}).get("cost"),
        "artifacts": [
            str(readme_path.relative_to(output_dir)),
            str(case_path.relative_to(output_dir)),
            str(score_sheet_path.relative_to(output_dir)),
            "raw/",
        ],
    }
    (output_dir / "packet_summary.json").write_text(json.dumps(packet_summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return packet_summary


def _latest_cloud_run(runs_dir: Path) -> Path | None:
    candidates: list[tuple[str, Path]] = []
    for run_dir in sorted(runs_dir.glob("audit_llm_smoke_*")):
        summary_path = run_dir / "summary.json"
        manifest_path = run_dir / "manifest.json"
        if not summary_path.exists() or not manifest_path.exists():
            continue
        summary = _read_json(summary_path)
        manifest = _read_json(manifest_path)
        if summary.get("suite") != "audit_llm_smoke" or summary.get("providerMode") != "cloud" or not summary.get("ok"):
            continue
        candidates.append((str(manifest.get("createdAt") or run_dir.name), run_dir))
    return max(candidates, default=(None, None))[1]


def _load_cases(run_dir: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for path in sorted((run_dir / "per_case").glob("*.json")):
        payload = _read_json(path)
        payload["_path"] = str(path)
        cases.append(payload)
    return cases


def _pair_cases(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, int], dict[str, Any]] = {}
    for case in cases:
        seed = case.get("seed", {}) if isinstance(case.get("seed"), dict) else {}
        key = (str(case.get("scenarioId") or ""), int(seed.get("seedIndex") or 1))
        grouped.setdefault(key, {"scenarioId": key[0], "seedIndex": key[1]})
        grouped[key][str(case.get("baseline") or "")] = case
    return [grouped[key] for key in sorted(grouped)]


def _render_readme(
    *,
    run_dir: Path,
    summary: dict[str, Any],
    manifest: dict[str, Any],
    go_no_go: dict[str, Any],
    llm_evidence: dict[str, Any],
    pairs: list[dict[str, Any]],
) -> str:
    totals = llm_evidence.get("totals", {}) if isinstance(llm_evidence.get("totals"), dict) else {}
    checks = go_no_go.get("checks", []) if isinstance(go_no_go.get("checks"), list) else []
    rows = [
        "| Check | Pass | Detail |",
        "|---|---:|---|",
    ]
    for check in checks:
        if not isinstance(check, dict):
            continue
        detail = ", ".join(f"{key}={value}" for key, value in check.items() if key not in {"checkId", "pass"})
        rows.append(f"| `{check.get('checkId')}` | {check.get('pass')} | {detail} |")

    pair_rows = [
        "| Scenario | Full decision | Missing-evidence decision | Changed | Normalization |",
        "|---|---|---|---:|---|",
    ]
    for pair in pairs:
        full = pair.get("full_runtime", {})
        missing = pair.get("no_policy_evidence", {})
        full_desc = _decision_desc(full)
        missing_desc = _decision_desc(missing)
        changed = full_desc != missing_desc
        normalization = "; ".join(_normalization_rules(full) + _normalization_rules(missing)) or "none"
        pair_rows.append(f"| `{pair['scenarioId']}` | {full_desc} | {missing_desc} | {changed} | {normalization} |")

    return "\n".join(
        [
            "# Audit LLM Smoke Supplement",
            "",
            "## Scope",
            "",
            "本补充包把真实 `CloudApiProvider` audit LLM smoke 压缩成 reviewer 可读证据，用于判断 trace-grounded audit contract 是否在高风险工具场景中呈现稳定差异。",
            "",
            "## Source Run",
            "",
            f"- source run: `{run_dir}`",
            f"- createdAt: `{manifest.get('createdAt')}`",
            f"- providerMode: `{summary.get('providerMode')}`",
            f"- passed: `{summary.get('passed')}/{summary.get('total')}`",
            f"- tokens / cost: `{totals.get('tokens')}` / `{totals.get('cost')}` USD",
            "",
            "## Go / No-Go",
            "",
            "\n".join(rows),
            "",
            "## Scenario Pair Overview",
            "",
            "\n".join(pair_rows),
            "",
            "## Limitation Box",
            "",
            "- 这是最小真实 LLM smoke，不代表企业级生产可用性。",
            "- prompt 显式给出 required evidence 与 decision rules，因此结果只能支持 contract-following / evidence-linking 可行性。",
            "- normalization 已记录在 per-case artifact 中；本轮主要出现 `traceRefs_strings_to_objects`，需在后续实验中持续统计。",
            "- 还缺真人审阅信号、跨模型统计和更开放任务输入。",
            "",
            "## Reviewer Task",
            "",
            "请阅读 `LLM_CASE_COMPARISONS.md`，对每个 scenario 判断：Full 条件是否有足够证据允许高风险工具；No-policy 条件是否正确转向安全审阅工具。",
            "",
        ]
    )


def _render_case_comparisons(pairs: list[dict[str, Any]]) -> str:
    sections = ["# LLM Case Comparisons", ""]
    for pair in pairs:
        scenario_id = pair["scenarioId"]
        full = pair.get("full_runtime", {})
        missing = pair.get("no_policy_evidence", {})
        scenario = full.get("scenario") if isinstance(full.get("scenario"), dict) else missing.get("scenario", {})
        required = scenario.get("requiredEvidence", []) if isinstance(scenario.get("requiredEvidence"), list) else []
        sections.extend(
            [
                f"## `{scenario_id}`",
                "",
                str(scenario.get("description") or ""),
                "",
                "### Required Evidence",
                "",
            ]
        )
        for evidence in required:
            if isinstance(evidence, dict):
                sections.append(f"- `{evidence.get('sourceEventId')}` — {evidence.get('summary')}")
        sections.extend(
            [
                "",
                "### Full Runtime",
                "",
                _case_block(full),
                "",
                "### No Policy Evidence",
                "",
                _case_block(missing),
                "",
            ]
        )
    return "\n".join(sections)


def _case_block(case: dict[str, Any]) -> str:
    parsed = case.get("parsed", {}) if isinstance(case.get("parsed"), dict) else {}
    validation = case.get("validation", {}) if isinstance(case.get("validation"), dict) else {}
    lines = [
        f"- caseId: `{case.get('caseId')}`",
        f"- ok: `{case.get('ok')}`",
        f"- selectedToolId: `{parsed.get('selectedToolId')}`",
        f"- policyVerdict: `{_verdict(parsed)}`",
        f"- sourceEventIds: `{len(parsed.get('sourceEventIds', []) if isinstance(parsed.get('sourceEventIds'), list) else [])}`",
        f"- traceRefs: `{len(parsed.get('traceRefs', []) if isinstance(parsed.get('traceRefs'), list) else [])}`",
        f"- unsupportedSourceEventIds: `{validation.get('unsupportedSourceEventIds')}`",
        f"- normalization: `{_normalization_rules(case) or ['none']}`",
        f"- humanSummary: {parsed.get('humanSummary')}",
    ]
    return "\n".join(lines)


def _render_score_sheet(pairs: list[dict[str, Any]]) -> str:
    rows = ["scenarioId,full_has_sufficient_evidence,no_policy_should_block,summary_clear,notes"]
    for pair in pairs:
        rows.append(f"{pair['scenarioId']},,,," )
    return "\n".join(rows) + "\n"


def _decision_desc(case: dict[str, Any]) -> str:
    parsed = case.get("parsed", {}) if isinstance(case.get("parsed"), dict) else {}
    return f"`{parsed.get('selectedToolId')}` / `{_verdict(parsed)}`"


def _verdict(parsed: dict[str, Any]) -> str:
    verdict = parsed.get("policyVerdict", {}) if isinstance(parsed, dict) else {}
    if isinstance(verdict, dict):
        return str(verdict.get("verdict") or "")
    return str(verdict or "")


def _normalization_rules(case: dict[str, Any]) -> list[str]:
    normalization = case.get("normalization", {}) if isinstance(case.get("normalization"), dict) else {}
    rules = normalization.get("rules", [])
    return [str(rule) for rule in rules if str(rule)] if isinstance(rules, list) else []


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _timestamp_slug() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z").replace(":", "-")


def _unique_dir(path: Path) -> Path:
    if not path.exists():
        return path
    for index in range(1, 100):
        candidate = path.with_name(f"{path.name}_{index:02d}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"无法创建唯一 supplement 目录：{path}")


if __name__ == "__main__":
    main()
