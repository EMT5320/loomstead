"""索引并校验 Phase 2 Eval 本地导出。

该脚本只读取 `.run/eval-runs/**/manifest.json` 与其登记的 artifacts。
默认不删除任何历史 run；`--write-index` 只写入一个本地 index，方便后续归档和人工筛选。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNS_DIR = ROOT / ".run" / "eval-runs"
DEFAULT_PROMOTE_DIR = ROOT / ".run" / "eval-promoted"
INDEX_VERSION = "phase2.eval_run_index.v1"
DRIFT_REPORT_VERSION = "phase2.eval_run_drift.v1"
PROMOTION_RECORD_VERSION = "phase2.eval_promotion.v1"
MANIFEST_VERSION = "phase2.eval_manifest.v1"
REQUIRED_MANIFEST_KEYS = (
    "manifestVersion",
    "exportKind",
    "createdAt",
    "suite",
    "baseline",
    "ok",
    "runDirName",
    "git",
    "schemaRegistry",
    "metricIds",
    "baselines",
    "scenarioIds",
    "artifacts",
)


def main() -> None:
    parser = argparse.ArgumentParser(description="索引并校验 Phase 2 Eval 导出 manifest。")
    parser.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS_DIR, help="Eval run 根目录。")
    parser.add_argument("--index-path", type=Path, default=None, help="index 输出路径，默认写到 runs-dir/index.json。")
    parser.add_argument("--drift-path", type=Path, default=None, help="drift report 输出路径，默认写到 runs-dir/drift_report.json。")
    parser.add_argument("--promote", type=str, default=None, help="把指定 runDirName 或 run 路径复制到长期候选归档。")
    parser.add_argument("--promote-dir", type=Path, default=DEFAULT_PROMOTE_DIR, help="promote 输出根目录。")
    parser.add_argument("--promotion-id", type=str, default=None, help="promote 目标目录名，默认沿用 runDirName。")
    parser.add_argument("--promotion-note", type=str, default="", help="写入 promotion record 的人工备注。")
    parser.add_argument("--write-index", action="store_true", help="写入本地 index.json。")
    parser.add_argument("--write-drift-report", action="store_true", help="写入跨 run 漂移报告。")
    parser.add_argument("--allow-empty", action="store_true", help="允许 runs-dir 中没有 manifest。")
    parser.add_argument("--keep-latest-per-suite", type=int, default=3, help="每个 suite 标记为 keep 的最新 run 数。")
    args = parser.parse_args()

    runs_dir = args.runs_dir if args.runs_dir.is_absolute() else ROOT / args.runs_dir
    index_path = args.index_path or runs_dir / "index.json"
    drift_path = args.drift_path or runs_dir / "drift_report.json"
    promote_dir = args.promote_dir if args.promote_dir.is_absolute() else ROOT / args.promote_dir
    index = build_eval_run_index(
        runs_dir,
        keep_latest_per_suite=max(1, int(args.keep_latest_per_suite)),
    )
    if not index["runs"] and not args.allow_empty:
        index["errors"].append(f"未找到 Eval manifest：{runs_dir}")

    if args.write_index:
        index_path.parent.mkdir(parents=True, exist_ok=True)
        index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        index["indexPath"] = _repo_relative(index_path)
    if args.write_drift_report:
        drift_path.parent.mkdir(parents=True, exist_ok=True)
        drift_path.write_text(json.dumps(index["driftReport"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        index["driftPath"] = _repo_relative(drift_path)
    if args.promote:
        promotion = promote_eval_run(
            index,
            args.promote,
            promote_dir=promote_dir,
            promotion_id=args.promotion_id,
            promotion_note=args.promotion_note,
        )
        index["promotion"] = promotion

    print(json.dumps(_compact_output(index), ensure_ascii=False, indent=2))
    if index["errors"]:
        raise SystemExit(1)


def build_eval_run_index(runs_dir: Path, *, keep_latest_per_suite: int) -> dict[str, Any]:
    """读取所有 manifest，生成稳定索引并校验 artifact 完整性。"""
    created_at = _utc_now()
    manifests = sorted(runs_dir.glob("*/manifest.json")) if runs_dir.exists() else []
    run_records: list[dict[str, Any]] = []
    errors: list[str] = []
    warnings: list[str] = []

    for manifest_path in manifests:
        record, manifest_errors, manifest_warnings = _read_manifest_record(manifest_path)
        run_records.append(record)
        errors.extend(manifest_errors)
        warnings.extend(manifest_warnings)

    _apply_retention_tiers(run_records, keep_latest_per_suite=keep_latest_per_suite)
    summary = _build_summary(run_records)
    return {
        "indexVersion": INDEX_VERSION,
        "createdAt": created_at,
        "runsDir": _repo_relative(runs_dir),
        "summary": summary,
        "runs": run_records,
        "errors": errors,
        "warnings": warnings,
        "driftReport": _build_drift_report(run_records, created_at=created_at),
        "retentionPolicy": {
            "keepLatestPerSuite": keep_latest_per_suite,
            "deleteAutomatically": False,
            "note": "只标记保留建议；删除和长期搬运必须人工确认。",
        },
    }


def _read_manifest_record(manifest_path: Path) -> tuple[dict[str, Any], list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    run_dir = manifest_path.parent
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return (
            {
                "runDir": _repo_relative(run_dir),
                "manifestPath": _repo_relative(manifest_path),
                "valid": False,
                "error": repr(exc),
            },
            [f"manifest 读取失败：{manifest_path} {exc!r}"],
            warnings,
        )

    for key in REQUIRED_MANIFEST_KEYS:
        if key not in manifest:
            errors.append(f"{manifest_path}: 缺少 manifest 字段 {key}")
    if manifest.get("manifestVersion") != MANIFEST_VERSION:
        errors.append(f"{manifest_path}: manifestVersion={manifest.get('manifestVersion')}，期望 {MANIFEST_VERSION}")
    if manifest.get("runDirName") != run_dir.name:
        errors.append(f"{manifest_path}: runDirName 与目录名不一致")

    artifact_records: list[dict[str, Any]] = []
    for artifact in manifest.get("artifacts", []) if isinstance(manifest.get("artifacts"), list) else []:
        artifact_record, artifact_errors, artifact_warnings = _validate_artifact(run_dir, artifact)
        artifact_records.append(artifact_record)
        errors.extend(f"{manifest_path}: {item}" for item in artifact_errors)
        warnings.extend(f"{manifest_path}: {item}" for item in artifact_warnings)

    if not isinstance(manifest.get("artifacts"), list):
        errors.append(f"{manifest_path}: artifacts 不是列表")

    return (
        {
            "runDir": _repo_relative(run_dir),
            "manifestPath": _repo_relative(manifest_path),
            "manifestSha256": _sha256_file(manifest_path),
            "manifestVersion": manifest.get("manifestVersion"),
            "exportKind": manifest.get("exportKind"),
            "suite": manifest.get("suite"),
            "baseline": manifest.get("baseline"),
            "ok": bool(manifest.get("ok")),
            "createdAt": manifest.get("createdAt"),
            "git": _compact_git(manifest.get("git", {})),
            "schemaRegistryVersion": _schema_registry_version(manifest.get("schemaRegistry", {})),
            "metricIds": list(manifest.get("metricIds", [])) if isinstance(manifest.get("metricIds"), list) else [],
            "baselines": list(manifest.get("baselines", [])) if isinstance(manifest.get("baselines"), list) else [],
            "scenarioIds": list(manifest.get("scenarioIds", [])) if isinstance(manifest.get("scenarioIds"), list) else [],
            "artifactCount": len(artifact_records),
            "artifacts": artifact_records,
            "valid": not errors,
        },
        errors,
        warnings,
    )


def promote_eval_run(
    index: dict[str, Any],
    run_ref: str,
    *,
    promote_dir: Path,
    promotion_id: str | None,
    promotion_note: str,
) -> dict[str, Any]:
    """复制一个已校验 run 到 promote 目录，并写入晋级记录。"""
    if index["errors"]:
        raise SystemExit("存在 archive 校验错误，禁止 promote。")
    record = _find_run_record(index["runs"], run_ref)
    if record is None:
        raise SystemExit(f"未找到可 promote 的 run：{run_ref}")
    if not bool(record.get("valid")):
        raise SystemExit(f"run 校验未通过，禁止 promote：{run_ref}")

    source_dir = ROOT / str(record["runDir"])
    if not source_dir.exists():
        raise SystemExit(f"run 目录不存在：{source_dir}")
    target_name = promotion_id or source_dir.name
    if not re_match_safe_name(target_name):
        raise SystemExit(f"promotion-id 只能包含字母、数字、点、下划线和短横线：{target_name}")
    target_dir = promote_dir / target_name
    if target_dir.exists():
        raise SystemExit(f"promote 目标已存在，避免覆盖：{target_dir}")

    promote_dir.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_dir, target_dir)
    promotion_record = _build_promotion_record(index, record, source_dir=source_dir, target_dir=target_dir, note=promotion_note)
    (target_dir / "promotion_record.json").write_text(
        json.dumps(promotion_record, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (target_dir / "PROMOTION.md").write_text(_promotion_markdown(promotion_record), encoding="utf-8")
    return {
        "promoted": True,
        "sourceRunDir": record["runDir"],
        "promotedRunDir": _repo_relative(target_dir),
        "promotionStatus": promotion_record["promotionStatus"],
        "manualReviewItems": promotion_record["manualReviewItems"],
    }


def _find_run_record(run_records: list[dict[str, Any]], run_ref: str) -> dict[str, Any] | None:
    ref_path = Path(run_ref)
    ref_name = ref_path.name if ref_path.name else run_ref
    for record in run_records:
        run_dir = str(record.get("runDir") or "")
        if run_ref == run_dir or ref_name == Path(run_dir).name:
            return record
    return None


def _build_promotion_record(
    index: dict[str, Any],
    record: dict[str, Any],
    *,
    source_dir: Path,
    target_dir: Path,
    note: str,
) -> dict[str, Any]:
    manual_items: list[str] = []
    git = record.get("git", {}) if isinstance(record.get("git"), dict) else {}
    if bool(git.get("dirty")):
        manual_items.append("manifest git.dirty=true；需要说明导出时工作区改动原因，或重新从干净 commit 导出。")
    if not bool(record.get("ok")):
        manual_items.append("manifest ok=false；不能作为 paper-grade 证据。")

    suite = str(record.get("suite") or "unknown")
    drift_for_suite = _drift_comparison_for_suite(index.get("driftReport", {}), suite)
    if drift_for_suite is None:
        manual_items.append("当前 suite 缺少上一 run 对比；drift 需要人工解释或补充历史 run。")
    elif bool(drift_for_suite.get("hasDrift")):
        manual_items.append("drift report 发现 metric / baseline / scenario / schema / artifact 漂移，需要人工解释。")

    promotion_status = "paper_grade_candidate" if not manual_items else "needs_manual_review"
    return {
        "promotionVersion": PROMOTION_RECORD_VERSION,
        "promotedAt": _utc_now(),
        "promotionStatus": promotion_status,
        "sourceRunDir": _repo_relative(source_dir),
        "promotedRunDir": _repo_relative(target_dir),
        "promotionNote": note,
        "suite": suite,
        "baseline": record.get("baseline"),
        "ok": bool(record.get("ok")),
        "manifestVersion": record.get("manifestVersion"),
        "manifestSha256": record.get("manifestSha256"),
        "git": record.get("git"),
        "schemaRegistryVersion": record.get("schemaRegistryVersion"),
        "metricIds": record.get("metricIds", []),
        "baselines": record.get("baselines", []),
        "scenarioIds": record.get("scenarioIds", []),
        "artifactCount": record.get("artifactCount"),
        "archiveChecks": {
            "archiveIndexVersion": index.get("indexVersion"),
            "archiveCheckPassed": not index.get("errors"),
            "manifestValid": bool(record.get("valid")),
            "artifactCount": record.get("artifactCount"),
        },
        "driftComparison": drift_for_suite,
        "manualReviewItems": manual_items,
        "paperGradeChecklist": {
            "okTrue": bool(record.get("ok")),
            "archiveCheckPassed": not index.get("errors"),
            "gitCleanAtExport": not bool(git.get("dirty")),
            "schemaRegistryV1": record.get("schemaRegistryVersion") == "schema_registry.v1",
            "driftExplained": drift_for_suite is not None and not bool(drift_for_suite.get("hasDrift")),
            "manualWindowVerified": False,
            "externalModelVerifiedIfNeeded": False,
        },
    }


def _drift_comparison_for_suite(drift_report: Any, suite: str) -> dict[str, Any] | None:
    if not isinstance(drift_report, dict):
        return None
    comparisons = drift_report.get("comparisons", [])
    if not isinstance(comparisons, list):
        return None
    for item in comparisons:
        if isinstance(item, dict) and item.get("suite") == suite:
            return item
    return None


def _promotion_markdown(record: dict[str, Any]) -> str:
    manual_items = record.get("manualReviewItems", [])
    if manual_items:
        manual_text = "\n".join(f"- {item}" for item in manual_items)
    else:
        manual_text = "- 暂无自动发现的人工复核项。"
    checklist = record.get("paperGradeChecklist", {})
    checklist_text = "\n".join(f"- {key}: {value}" for key, value in checklist.items())
    return (
        "# Eval Run Promotion\n\n"
        f"- status: `{record.get('promotionStatus')}`\n"
        f"- promotedAt: `{record.get('promotedAt')}`\n"
        f"- sourceRunDir: `{record.get('sourceRunDir')}`\n"
        f"- suite: `{record.get('suite')}`\n"
        f"- baseline: `{record.get('baseline')}`\n"
        f"- manifestSha256: `{record.get('manifestSha256')}`\n"
        f"- note: {record.get('promotionNote') or '-'}\n\n"
        "## Manual review items\n\n"
        f"{manual_text}\n\n"
        "## Paper-grade checklist\n\n"
        f"{checklist_text}\n"
    )


def re_match_safe_name(value: str) -> bool:
    return bool(value) and all(ch.isalnum() or ch in {"-", "_", "."} for ch in value)


def _validate_artifact(run_dir: Path, artifact: Any) -> tuple[dict[str, Any], list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    if not isinstance(artifact, dict):
        return {"valid": False, "error": "artifact_not_object"}, ["artifact 不是对象"], warnings

    rel_path = str(artifact.get("path") or "")
    artifact_path = run_dir / rel_path
    record: dict[str, Any] = {
        "path": rel_path,
        "kind": artifact.get("kind"),
        "baseline": artifact.get("baseline"),
        "scenarioId": artifact.get("scenarioId"),
    }
    if not rel_path:
        errors.append("artifact 缺少 path")
        record["valid"] = False
        return record, errors, warnings

    try:
        resolved_run_dir = run_dir.resolve()
        resolved_artifact = artifact_path.resolve()
        if not resolved_artifact.is_relative_to(resolved_run_dir):
            errors.append(f"artifact path 越出 run 目录：{rel_path}")
    except OSError as exc:
        errors.append(f"artifact path 无法解析：{rel_path} {exc!r}")

    if not artifact_path.exists():
        errors.append(f"artifact 不存在：{rel_path}")
        record["valid"] = False
        return record, errors, warnings

    actual_bytes = artifact_path.stat().st_size
    expected_bytes = artifact.get("bytes")
    actual_sha = _sha256_file(artifact_path)
    expected_sha = artifact.get("sha256")
    record.update(
        {
            "bytes": actual_bytes,
            "sha256": actual_sha,
            "rowCount": artifact.get("rowCount"),
            "valid": True,
        }
    )
    if expected_bytes != actual_bytes:
        errors.append(f"{rel_path}: bytes 不匹配，manifest={expected_bytes} actual={actual_bytes}")
        record["valid"] = False
    if expected_sha != actual_sha:
        errors.append(f"{rel_path}: sha256 不匹配")
        record["valid"] = False
    if str(rel_path).endswith(".jsonl") or "jsonl" in str(artifact.get("kind") or ""):
        actual_rows = _jsonl_row_count(artifact_path)
        record["actualRowCount"] = actual_rows
        if artifact.get("rowCount") is None:
            errors.append(f"{rel_path}: JSONL artifact 缺少 rowCount")
            record["valid"] = False
        elif int(artifact.get("rowCount")) != actual_rows:
            errors.append(f"{rel_path}: rowCount 不匹配，manifest={artifact.get('rowCount')} actual={actual_rows}")
            record["valid"] = False
    return record, errors, warnings


def _apply_retention_tiers(run_records: list[dict[str, Any]], *, keep_latest_per_suite: int) -> None:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in run_records:
        grouped[str(record.get("suite") or "unknown")].append(record)
    for suite, records in grouped.items():
        records.sort(key=lambda item: str(item.get("createdAt") or ""), reverse=True)
        for index, record in enumerate(records, start=1):
            record["retention"] = {
                "suiteRankNewestFirst": index,
                "tier": "keep_latest" if index <= keep_latest_per_suite else "historical_candidate",
                "suite": suite,
            }


def _build_summary(run_records: list[dict[str, Any]]) -> dict[str, Any]:
    by_suite: dict[str, int] = defaultdict(int)
    by_export_kind: dict[str, int] = defaultdict(int)
    artifact_count = 0
    for record in run_records:
        by_suite[str(record.get("suite") or "unknown")] += 1
        by_export_kind[str(record.get("exportKind") or "unknown")] += 1
        artifact_count += int(record.get("artifactCount") or 0)
    return {
        "runCount": len(run_records),
        "validRunCount": sum(1 for record in run_records if record.get("valid")),
        "artifactCount": artifact_count,
        "bySuite": dict(sorted(by_suite.items())),
        "byExportKind": dict(sorted(by_export_kind.items())),
    }


def _build_drift_report(run_records: list[dict[str, Any]], *, created_at: str) -> dict[str, Any]:
    """比较每个 suite 最新两次 run，暴露 metric、baseline、scenario 与 schema 漂移。"""
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in run_records:
        grouped[str(record.get("suite") or "unknown")].append(record)

    comparisons: list[dict[str, Any]] = []
    single_run_suites: list[str] = []
    for suite, records in sorted(grouped.items()):
        records.sort(key=lambda item: str(item.get("createdAt") or ""), reverse=True)
        if len(records) < 2:
            single_run_suites.append(suite)
            continue
        comparisons.append(_compare_latest_runs(suite, latest=records[0], previous=records[1]))

    return {
        "reportVersion": DRIFT_REPORT_VERSION,
        "createdAt": created_at,
        "summary": {
            "suiteCount": len(grouped),
            "comparisonCount": len(comparisons),
            "changedComparisonCount": sum(1 for item in comparisons if item["hasDrift"]),
            "singleRunSuites": single_run_suites,
        },
        "comparisons": comparisons,
    }


def _compare_latest_runs(suite: str, *, latest: dict[str, Any], previous: dict[str, Any]) -> dict[str, Any]:
    """生成单个 suite 的最新 run 与上一 run 对比。"""
    schema_change = {
        "latest": latest.get("schemaRegistryVersion"),
        "previous": previous.get("schemaRegistryVersion"),
        "changed": latest.get("schemaRegistryVersion") != previous.get("schemaRegistryVersion"),
    }
    export_kind_change = {
        "latest": latest.get("exportKind"),
        "previous": previous.get("exportKind"),
        "changed": latest.get("exportKind") != previous.get("exportKind"),
    }
    ok_change = {
        "latest": bool(latest.get("ok")),
        "previous": bool(previous.get("ok")),
        "changed": bool(latest.get("ok")) != bool(previous.get("ok")),
    }
    artifact_count_delta = int(latest.get("artifactCount") or 0) - int(previous.get("artifactCount") or 0)
    deltas = {
        "metricIds": _list_delta(latest.get("metricIds", []), previous.get("metricIds", [])),
        "baselines": _list_delta(latest.get("baselines", []), previous.get("baselines", [])),
        "scenarioIds": _list_delta(latest.get("scenarioIds", []), previous.get("scenarioIds", [])),
    }
    has_drift = (
        schema_change["changed"]
        or export_kind_change["changed"]
        or ok_change["changed"]
        or artifact_count_delta != 0
        or any(delta["added"] or delta["removed"] for delta in deltas.values())
    )
    return {
        "suite": suite,
        "latestRunDir": latest.get("runDir"),
        "previousRunDir": previous.get("runDir"),
        "latestCreatedAt": latest.get("createdAt"),
        "previousCreatedAt": previous.get("createdAt"),
        "latestGit": latest.get("git"),
        "previousGit": previous.get("git"),
        "schemaRegistryVersion": schema_change,
        "exportKind": export_kind_change,
        "ok": ok_change,
        "artifactCountDelta": artifact_count_delta,
        "metricIds": deltas["metricIds"],
        "baselines": deltas["baselines"],
        "scenarioIds": deltas["scenarioIds"],
        "hasDrift": has_drift,
    }


def _list_delta(latest_values: Any, previous_values: Any) -> dict[str, list[str]]:
    """返回两个字符串列表的新增、移除和稳定交集。"""
    latest_set = {str(value) for value in latest_values if value is not None} if isinstance(latest_values, list) else set()
    previous_set = {str(value) for value in previous_values if value is not None} if isinstance(previous_values, list) else set()
    return {
        "added": sorted(latest_set - previous_set),
        "removed": sorted(previous_set - latest_set),
        "unchanged": sorted(latest_set & previous_set),
    }


def _compact_output(index: dict[str, Any]) -> dict[str, Any]:
    """命令行输出保持短；完整详情在 index 文件里。"""
    output = {
        "ok": not index["errors"],
        "indexVersion": index["indexVersion"],
        "runsDir": index["runsDir"],
        "indexPath": index.get("indexPath"),
        "summary": index["summary"],
        "errors": index["errors"],
        "warnings": index["warnings"],
    }
    if index.get("driftPath"):
        output["driftPath"] = index["driftPath"]
        output["driftSummary"] = index["driftReport"]["summary"]
    if index.get("promotion"):
        output["promotion"] = index["promotion"]
    return output


def _compact_git(git: Any) -> dict[str, Any]:
    if not isinstance(git, dict):
        return {}
    return {
        "shortCommit": git.get("shortCommit"),
        "branch": git.get("branch"),
        "dirty": bool(git.get("dirty")),
    }


def _schema_registry_version(schema_registry: Any) -> str | None:
    if not isinstance(schema_registry, dict):
        return None
    return schema_registry.get("registryVersion")


def _jsonl_row_count(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    if text == "":
        return 0
    return len(text.splitlines())


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _repo_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


if __name__ == "__main__":
    main()
