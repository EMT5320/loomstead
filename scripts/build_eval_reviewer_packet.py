"""从本地 Eval manifests 抽样生成人工 reviewer 审核包。

该脚本只读取 `.run/eval-runs/*/manifest.json`，不运行真实 LLM，不修改已有 eval run。
输出用于人工审核的 packet + 打分表模板，默认写入 `.run/eval-reviewer-packets/`。
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNS_DIR = ROOT / ".run" / "eval-runs"
DEFAULT_OUT_DIR = ROOT / ".run" / "eval-reviewer-packets"
PACKET_VERSION = "phase2.eval_reviewer_sampling_packet.v1"


@dataclass(frozen=True)
class RunRecord:
    """内存中的 run 索引。"""

    run_dir: Path
    manifest_path: Path
    manifest: dict[str, Any]
    created_at: datetime


def main() -> None:
    parser = argparse.ArgumentParser(description="构建 Eval reviewer 抽样审核包。")
    parser.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS_DIR, help="Eval run 根目录。")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR, help="审核包输出根目录。")
    parser.add_argument("--packet-id", type=str, default="", help="审核包目录名；默认自动生成。")
    parser.add_argument(
        "--process-run",
        type=str,
        default="",
        help="指定 process run 目录名（例如 run_2026-05-27T13-37-33Z），留空时自动选最新 ok run。",
    )
    parser.add_argument(
        "--domain-run",
        type=str,
        default="",
        help="指定 domain run 目录名（例如 domain_2026-05-27T13-29-21Z），留空时自动选最新 ok run。",
    )
    parser.add_argument("--process-samples", type=int, default=6, help="process suite 抽样条目数。")
    parser.add_argument("--domain-samples", type=int, default=6, help="domain suite 抽样条目数。")
    parser.add_argument("--seed", type=int, default=20260527, help="抽样随机种子，保证可复现。")
    parser.add_argument("--allow-dirty-runs", action="store_true", help="允许从 git.dirty=true 的 run 生成审核包。")
    args = parser.parse_args()

    runs_dir = _abs_path(args.runs_dir)
    out_dir = _abs_path(args.out_dir)
    records = _load_run_records(runs_dir)
    process_record = _pick_run(
        records,
        suite="process_fidelity",
        run_dir_name=args.process_run.strip() or None,
        allow_dirty=bool(args.allow_dirty_runs),
    )
    domain_record = _pick_run(
        records,
        suite="cross_domain_adapter",
        run_dir_name=args.domain_run.strip() or None,
        allow_dirty=bool(args.allow_dirty_runs),
    )

    rng = random.Random(int(args.seed))
    process_samples = _sample_suite(
        record=process_record,
        sample_count=max(1, int(args.process_samples)),
        rng=rng,
    )
    domain_samples = _sample_suite(
        record=domain_record,
        sample_count=max(1, int(args.domain_samples)),
        rng=rng,
    )
    packet_id = args.packet_id.strip() or f"packet_{_utc_now_slug()}"
    packet_dir = out_dir / packet_id
    packet_dir.mkdir(parents=True, exist_ok=False)

    packet = _build_packet(
        packet_id=packet_id,
        process_record=process_record,
        domain_record=domain_record,
        process_samples=process_samples,
        domain_samples=domain_samples,
        seed=int(args.seed),
    )
    packet_path = packet_dir / "reviewer_sampling_packet.json"
    packet_path.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    csv_path = packet_dir / "reviewer_score_sheet.csv"
    _write_score_sheet(csv_path, packet["samples"])

    guide_path = packet_dir / "REVIEWER_GUIDE.md"
    _write_reviewer_guide(guide_path, packet)

    output = {
        "ok": True,
        "packetVersion": PACKET_VERSION,
        "packetId": packet_id,
        "packetDir": _repo_relative(packet_dir),
        "packetPath": _repo_relative(packet_path),
        "scoreSheetPath": _repo_relative(csv_path),
        "reviewerGuidePath": _repo_relative(guide_path),
        "sampleCount": len(packet["samples"]),
        "manualGate": packet["manualGate"],
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


def _abs_path(path_like: Path) -> Path:
    return path_like if path_like.is_absolute() else ROOT / path_like


def _load_run_records(runs_dir: Path) -> list[RunRecord]:
    if not runs_dir.exists():
        raise RuntimeError(f"runs 目录不存在：{runs_dir}")
    records: list[RunRecord] = []
    for manifest_path in sorted(runs_dir.glob("*/manifest.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        created_at = _parse_manifest_time(manifest_path.parent, manifest.get("createdAt"))
        records.append(
            RunRecord(
                run_dir=manifest_path.parent,
                manifest_path=manifest_path,
                manifest=manifest,
                created_at=created_at,
            )
        )
    if not records:
        raise RuntimeError(f"未找到 manifest：{runs_dir}")
    return records


def _pick_run(records: list[RunRecord], *, suite: str, run_dir_name: str | None, allow_dirty: bool) -> RunRecord:
    if run_dir_name:
        for record in records:
            if record.run_dir.name == run_dir_name:
                found_suite = str(record.manifest.get("suite") or "")
                if found_suite != suite:
                    raise RuntimeError(f"{run_dir_name} 的 suite={found_suite}，期望 {suite}")
                if _manifest_dirty(record) and not allow_dirty:
                    raise RuntimeError(f"{run_dir_name} 的 git.dirty=true；若确认要审核 dirty run，请添加 --allow-dirty-runs。")
                return record
        raise RuntimeError(f"未找到指定 run：{run_dir_name}")
    candidates = [
        record
        for record in records
        if str(record.manifest.get("suite") or "") == suite
        and bool(record.manifest.get("ok"))
        and (allow_dirty or not _manifest_dirty(record))
    ]
    if not candidates:
        dirty_hint = "；如需选择 dirty run 请添加 --allow-dirty-runs" if not allow_dirty else ""
        raise RuntimeError(f"未找到 suite={suite}、ok=true 且符合 dirty policy 的 run{dirty_hint}")
    return sorted(candidates, key=lambda item: item.created_at, reverse=True)[0]


def _manifest_dirty(record: RunRecord) -> bool:
    git = record.manifest.get("git")
    return bool(git.get("dirty")) if isinstance(git, dict) else False


def _sample_suite(record: RunRecord, *, sample_count: int, rng: random.Random) -> list[dict[str, Any]]:
    artifacts = [item for item in record.manifest.get("artifacts", []) if isinstance(item, dict)]
    per_scenario = [item for item in artifacts if str(item.get("kind") or "") == "per_scenario_json"]
    if not per_scenario:
        raise RuntimeError(f"{record.run_dir.name} 没有 per_scenario_json artifact")

    grouped: dict[str, list[dict[str, Any]]] = {}
    for artifact in per_scenario:
        scenario_id = str(artifact.get("scenarioId") or "unknown_scenario")
        grouped.setdefault(scenario_id, []).append(artifact)

    scenario_ids = sorted(grouped.keys())
    rng.shuffle(scenario_ids)
    suite = str(record.manifest.get("suite") or "")

    picked: list[dict[str, Any]] = []
    used_scenarios: set[str] = set()
    # cross-domain suite 优先覆盖 narrative + coding 两条线，避免样本偏到单一域。
    if suite == "cross_domain_adapter" and sample_count >= 2:
        for prefix in ("narrative.", "coding."):
            scoped = [scenario_id for scenario_id in scenario_ids if scenario_id.startswith(prefix)]
            if not scoped:
                continue
            chosen_scenario = rng.choice(scoped)
            candidates = sorted(grouped[chosen_scenario], key=lambda item: str(item.get("path") or ""))
            picked.append(rng.choice(candidates))
            used_scenarios.add(chosen_scenario)
            if len(picked) >= sample_count:
                break

    # 先确保每个场景至少抽到一个 seed，优先覆盖场景广度。
    for scenario_id in scenario_ids:
        if scenario_id in used_scenarios:
            continue
        candidates = sorted(grouped[scenario_id], key=lambda item: str(item.get("path") or ""))
        picked.append(rng.choice(candidates))
        if len(picked) >= sample_count:
            break

    # 若需要更多样本，再从剩余 per_scenario 条目补齐。
    if len(picked) < sample_count:
        used = {str(item.get("path") or "") for item in picked}
        remaining = [item for item in per_scenario if str(item.get("path") or "") not in used]
        rng.shuffle(remaining)
        needed = sample_count - len(picked)
        picked.extend(remaining[:needed])

    return [
        _build_sample_item(
            record=record,
            per_scenario_artifact=artifact,
            suite_artifacts=artifacts,
        )
        for artifact in picked[:sample_count]
    ]


def _build_sample_item(
    *,
    record: RunRecord,
    per_scenario_artifact: dict[str, Any],
    suite_artifacts: list[dict[str, Any]],
) -> dict[str, Any]:
    scenario_id = str(per_scenario_artifact.get("scenarioId") or "unknown_scenario")
    baseline = str(per_scenario_artifact.get("baseline") or record.manifest.get("baseline") or "")
    rel_path = str(per_scenario_artifact.get("path") or "")
    seed = _extract_seed(rel_path)
    companion = _collect_companion_artifacts(
        run_dir=record.run_dir,
        suite=str(record.manifest.get("suite") or ""),
        scenario_id=scenario_id,
        seed=seed,
        artifacts=suite_artifacts,
    )
    sample_id = f"{record.run_dir.name}:{scenario_id}:seed{seed:02d}" if seed else f"{record.run_dir.name}:{scenario_id}"
    return {
        "sampleId": sample_id,
        "suite": str(record.manifest.get("suite") or ""),
        "runDirName": record.run_dir.name,
        "runManifestPath": _repo_relative(record.manifest_path),
        "scenarioId": scenario_id,
        "baseline": baseline,
        "seed": seed,
        "perScenarioArtifact": _artifact_entry(record.run_dir, per_scenario_artifact),
        "companionArtifacts": companion,
    }


def _collect_companion_artifacts(
    *,
    run_dir: Path,
    suite: str,
    scenario_id: str,
    seed: int | None,
    artifacts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    seed_tag = f"seed{seed:02d}" if seed is not None else ""
    for artifact in artifacts:
        kind = str(artifact.get("kind") or "")
        path = str(artifact.get("path") or "")
        same_scenario = str(artifact.get("scenarioId") or "") == scenario_id
        if suite == "cross_domain_adapter":
            if not kind.startswith("domain_evidence_"):
                continue
            if same_scenario and seed_tag and seed_tag in path:
                selected.append(artifact)
        elif suite == "process_fidelity":
            # process suite 的 scenario 级附件当前主要是 per_scenario_json；其余 traces 为 run 级共享证据。
            if kind in {"counterfactual_replay_jsonl", "memory_ablation_trace_jsonl"}:
                selected.append(artifact)
    dedup: dict[str, dict[str, Any]] = {}
    for artifact in selected:
        key = str(artifact.get("path") or "")
        if key:
            dedup[key] = artifact
    # 控制单条样本的附件数量，保持人工 reviewer 包可读。
    limited = sorted(dedup.values(), key=lambda item: str(item.get("path") or ""))[:6]
    return [_artifact_entry(run_dir, artifact) for artifact in limited]


def _artifact_entry(run_dir: Path, artifact: dict[str, Any]) -> dict[str, Any]:
    rel_path = str(artifact.get("path") or "")
    full_path = run_dir / rel_path
    return {
        "path": rel_path,
        "repoPath": _repo_relative(full_path) if full_path.is_absolute() else rel_path,
        "kind": str(artifact.get("kind") or ""),
        "bytes": int(artifact.get("bytes") or 0),
        "sha256": str(artifact.get("sha256") or ""),
    }


def _build_packet(
    *,
    packet_id: str,
    process_record: RunRecord,
    domain_record: RunRecord,
    process_samples: list[dict[str, Any]],
    domain_samples: list[dict[str, Any]],
    seed: int,
) -> dict[str, Any]:
    samples = process_samples + domain_samples
    packet = {
        "packetVersion": PACKET_VERSION,
        "packetId": packet_id,
        "createdAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "samplingPolicy": {
            "seed": seed,
            "suiteSampleCounts": {
                "process_fidelity": len(process_samples),
                "cross_domain_adapter": len(domain_samples),
            },
            "rule": "优先场景覆盖，每个场景先抽 1 个 seed，再按需要补齐。",
        },
        "sourceRuns": [
            _run_entry(process_record),
            _run_entry(domain_record),
        ],
        "manualGate": {
            "status": "manual_review_required",
            "reason": "需要人工 reviewer 对抽样条目进行 1-5 分主观打分与文字判断；脚本不自动评分。",
            "stopCondition": "完成 reviewer_score_sheet.csv 后，人工在 PR/报告中回填结论。",
        },
        "reviewChecklist": [
            "核对 per_scenario 与 companionArtifacts 的 sha256 与 manifest 一致。",
            "给每条样本填写 process_believability_score_1_to_5。",
            "给每条样本填写 causal_trace_clarity_1_to_5，并补充一句证据解释。",
            "若发现 shortcut 或 trace 断链，标记 pass_fail_judgement=fail 并记录原因。",
        ],
        "samples": samples,
    }
    packet["packetSha256"] = hashlib.sha256(
        json.dumps(packet, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return packet


def _run_entry(record: RunRecord) -> dict[str, Any]:
    manifest_sha = hashlib.sha256(record.manifest_path.read_bytes()).hexdigest()
    return {
        "suite": str(record.manifest.get("suite") or ""),
        "runDirName": record.run_dir.name,
        "manifestPath": _repo_relative(record.manifest_path),
        "manifestSha256": manifest_sha,
        "createdAt": record.manifest.get("createdAt"),
        "ok": bool(record.manifest.get("ok")),
        "git": {
            "commit": str(record.manifest.get("git", {}).get("commit") or ""),
            "shortCommit": str(record.manifest.get("git", {}).get("shortCommit") or ""),
            "dirty": bool(record.manifest.get("git", {}).get("dirty")),
        },
    }


def _write_score_sheet(path: Path, samples: list[dict[str, Any]]) -> None:
    fieldnames = [
        "sample_id",
        "suite",
        "run_dir_name",
        "scenario_id",
        "baseline",
        "seed",
        "per_scenario_path",
        "process_believability_score_1_to_5",
        "causal_trace_clarity_1_to_5",
        "pass_fail_judgement",
        "reviewer_notes",
    ]
    with path.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        for sample in samples:
            artifact = sample.get("perScenarioArtifact", {}) if isinstance(sample.get("perScenarioArtifact"), dict) else {}
            writer.writerow(
                {
                    "sample_id": sample.get("sampleId"),
                    "suite": sample.get("suite"),
                    "run_dir_name": sample.get("runDirName"),
                    "scenario_id": sample.get("scenarioId"),
                    "baseline": sample.get("baseline"),
                    "seed": sample.get("seed"),
                    "per_scenario_path": artifact.get("repoPath"),
                    "process_believability_score_1_to_5": "",
                    "causal_trace_clarity_1_to_5": "",
                    "pass_fail_judgement": "",
                    "reviewer_notes": "",
                }
            )


def _write_reviewer_guide(path: Path, packet: dict[str, Any]) -> None:
    lines = [
        "# Reviewer Sampling Packet Guide",
        "",
        f"- packetId: `{packet.get('packetId')}`",
        f"- packetVersion: `{packet.get('packetVersion')}`",
        f"- createdAt: `{packet.get('createdAt')}`",
        "",
        "## Manual Gate",
        "",
        "- status: `manual_review_required`",
        "- 该包只负责抽样与路径整理；主观评分必须人工完成。",
        "",
        "## Suggested Review Steps",
        "",
        "1. 逐条打开 `reviewer_sampling_packet.json` 的 `perScenarioArtifact.repoPath`。",
        "2. 结合 `companionArtifacts` 里的 trace / replay / evidence 文件复核过程证据。",
        "3. 在 `reviewer_score_sheet.csv` 填写 1-5 分和结论备注。",
        "4. 保留 fail 条目的具体证据路径，便于后续追溯。",
        "",
        "## Stop Condition",
        "",
        "- 该阶段到人工打分为止；脚本不自动生成最终结论。",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _parse_manifest_time(run_dir: Path, created_at: Any) -> datetime:
    if isinstance(created_at, str):
        text = created_at.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(text)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except ValueError:
            pass
    return datetime.fromtimestamp(run_dir.stat().st_mtime, tz=timezone.utc)


def _extract_seed(path_text: str) -> int | None:
    match = re.search(r"seed(?P<seed>\d+)", path_text)
    if not match:
        return None
    return int(match.group("seed"))


def _repo_relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path.resolve()).replace("\\", "/")


def _utc_now_slug() -> str:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    return now.strftime("%Y-%m-%dT%H-%M-%SZ")


if __name__ == "__main__":
    main()
