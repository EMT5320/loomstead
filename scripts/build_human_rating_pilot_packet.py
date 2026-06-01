"""生成中文 Human Rating 盲评 pilot 包。

该脚本只读取 promoted eval artifact，不运行真实 LLM，也不修改 eval run。
输出包含 reviewer 可见材料和单独的内部条件映射，用来支持最小盲评 gate。
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_RUN = ROOT / ".run" / "eval-promoted" / "run_2026-05-29T13-57-50Z"
DEFAULT_OUT_DIR = ROOT / ".run" / "eval-reviewer-packets"
PACKET_VERSION = "human_rating_pilot_packet.v0"
DEFAULT_SCENARIOS = [
    "pf.branna_forgiveness_requires_memory",
    "pf.repair_talk_requires_memory_trace",
    "pf.shared_chat_builds_traceable_trust",
]
DEFAULT_BASELINES = ["full_motivational_delegation", "hard_delegation"]
DEFAULT_SEEDS = [1]

SCENARIO_TITLES = {
    "pf.branna_forgiveness_requires_memory": "失信后的修复谈话",
    "pf.repair_talk_requires_memory_trace": "带记忆证据的修复对话",
    "pf.shared_chat_builds_traceable_trust": "共同聊天建立可追溯信任",
    "pf.affiliation_bias_remains_agent_initiated": "偏置存在时仍保持角色主动",
}


@dataclass(frozen=True)
class ConditionSample:
    """一条内部条件样本；baseline 只写入内部 key。"""

    public_id: str
    scenario_id: str
    scenario_title: str
    baseline: str
    seed: int
    source_path: Path
    source_sha256: str
    data: dict[str, Any]


def main() -> None:
    parser = argparse.ArgumentParser(description="构建中文 Human Rating 盲评 pilot 包。")
    parser.add_argument("--source-run", type=Path, default=DEFAULT_SOURCE_RUN, help="promoted process run 目录。")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR, help="packet 输出根目录。")
    parser.add_argument("--packet-id", type=str, default="", help="packet 目录名；默认自动生成。")
    parser.add_argument("--scenarios", type=str, default=",".join(DEFAULT_SCENARIOS), help="逗号分隔场景 ID。")
    parser.add_argument("--baselines", type=str, default=",".join(DEFAULT_BASELINES), help="逗号分隔内部条件。")
    parser.add_argument("--seeds", type=str, default=",".join(str(item) for item in DEFAULT_SEEDS), help="逗号分隔 seed。")
    parser.add_argument("--shuffle-seed", type=int, default=20260601, help="盲评顺序随机种子。")
    args = parser.parse_args()

    source_run = _abs_path(args.source_run)
    out_dir = _abs_path(args.out_dir)
    packet_id = args.packet_id.strip() or f"human_rating_pilot_{_utc_now_slug()}_zh"
    packet_dir = out_dir / packet_id
    if packet_dir.exists():
        raise RuntimeError(f"packet 目录已存在：{packet_dir}")

    scenarios = _parse_csv_list(args.scenarios)
    baselines = _parse_csv_list(args.baselines)
    seeds = _parse_int_list(args.seeds)
    if len(baselines) < 2:
        raise RuntimeError("盲评 pilot 至少需要两个条件。")

    manifest = _load_json(source_run / "manifest.json")
    summary = _load_json(source_run / "summary.json")
    llm_evidence = _load_json(source_run / "llm_evidence.json") if (source_run / "llm_evidence.json").exists() else {}
    artifact_index = _index_per_scenario_artifacts(manifest)

    samples = _load_condition_samples(
        source_run=source_run,
        artifact_index=artifact_index,
        scenarios=scenarios,
        baselines=baselines,
        seeds=seeds,
    )
    rng = random.Random(args.shuffle_seed)
    shuffled_samples = list(samples)
    rng.shuffle(shuffled_samples)
    public_id_by_key = {
        _condition_key(sample): f"HRP-{idx:03d}" for idx, sample in enumerate(shuffled_samples, start=1)
    }
    public_samples = [
        ConditionSample(
            public_id=public_id_by_key[_condition_key(sample)],
            scenario_id=sample.scenario_id,
            scenario_title=sample.scenario_title,
            baseline=sample.baseline,
            seed=sample.seed,
            source_path=sample.source_path,
            source_sha256=sample.source_sha256,
            data=sample.data,
        )
        for sample in shuffled_samples
    ]
    pairs = _build_pairwise_tasks(samples, baselines=baselines, rng=rng, public_id_by_key=public_id_by_key)

    packet_dir.mkdir(parents=True)
    cards_dir = packet_dir / "reviewer_cards"
    cards_dir.mkdir()

    for sample in public_samples:
        (cards_dir / f"{sample.public_id}.md").write_text(_render_reviewer_card(sample), encoding="utf-8")

    reviewer_packet = _build_reviewer_packet(
        packet_id=packet_id,
        manifest=manifest,
        summary=summary,
        llm_evidence=llm_evidence,
        source_run=source_run,
        public_samples=public_samples,
        pairs=pairs,
        scenarios=scenarios,
        baselines=baselines,
        seeds=seeds,
        shuffle_seed=args.shuffle_seed,
    )
    (packet_dir / "reviewer_packet.json").write_text(
        json.dumps(reviewer_packet, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    _write_blind_score_sheet(packet_dir / "blind_score_sheet.csv", public_samples)
    _write_pairwise_sheet(packet_dir / "pairwise_preference_sheet.csv", pairs)
    _write_internal_key(packet_dir / "INTERNAL_CONDITION_KEY.csv", public_samples)
    (packet_dir / "README_REVIEWERS.md").write_text(_render_reviewer_readme(packet_id, public_samples, pairs), encoding="utf-8")
    (packet_dir / "PILOT_PROTOCOL.md").write_text(_render_protocol(packet_id, source_run), encoding="utf-8")

    output = {
        "ok": True,
        "packetVersion": PACKET_VERSION,
        "packetId": packet_id,
        "packetDir": _repo_relative(packet_dir),
        "reviewerPacketPath": _repo_relative(packet_dir / "reviewer_packet.json"),
        "reviewerCardsDir": _repo_relative(cards_dir),
        "blindScoreSheetPath": _repo_relative(packet_dir / "blind_score_sheet.csv"),
        "pairwisePreferenceSheetPath": _repo_relative(packet_dir / "pairwise_preference_sheet.csv"),
        "internalConditionKeyPath": _repo_relative(packet_dir / "INTERNAL_CONDITION_KEY.csv"),
        "sampleCount": len(public_samples),
        "pairwiseTaskCount": len(pairs),
        "manualGate": reviewer_packet["manualGate"],
    }
    print(json.dumps(output, ensure_ascii=False, indent=2))


def _abs_path(path_like: Path) -> Path:
    """把相对路径解析到仓库根目录。"""

    return path_like if path_like.is_absolute() else ROOT / path_like


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise RuntimeError(f"缺少文件：{path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_csv_list(text: str) -> list[str]:
    items = [item.strip() for item in text.split(",") if item.strip()]
    if not items:
        raise RuntimeError("列表参数不能为空。")
    return items


def _parse_int_list(text: str) -> list[int]:
    values: list[int] = []
    for item in _parse_csv_list(text):
        try:
            values.append(int(item))
        except ValueError as exc:
            raise RuntimeError(f"seed 必须是整数：{item}") from exc
    return values


def _index_per_scenario_artifacts(manifest: dict[str, Any]) -> dict[tuple[str, str, int], dict[str, Any]]:
    index: dict[tuple[str, str, int], dict[str, Any]] = {}
    for artifact in manifest.get("artifacts", []):
        if not isinstance(artifact, dict):
            continue
        if str(artifact.get("kind") or "") != "per_scenario_json":
            continue
        scenario_id = str(artifact.get("scenarioId") or "")
        baseline = str(artifact.get("baseline") or "")
        seed = _extract_seed(str(artifact.get("path") or ""))
        if scenario_id and baseline and seed is not None:
            index[(scenario_id, baseline, seed)] = artifact
    if not index:
        raise RuntimeError("manifest 中没有可用 per_scenario_json artifact。")
    return index


def _load_condition_samples(
    *,
    source_run: Path,
    artifact_index: dict[tuple[str, str, int], dict[str, Any]],
    scenarios: list[str],
    baselines: list[str],
    seeds: list[int],
) -> list[ConditionSample]:
    samples: list[ConditionSample] = []
    for scenario_id in scenarios:
        for seed in seeds:
            for baseline in baselines:
                artifact = artifact_index.get((scenario_id, baseline, seed))
                if artifact is None:
                    raise RuntimeError(f"缺少样本：scenario={scenario_id}, baseline={baseline}, seed={seed}")
                rel_path = Path(str(artifact.get("path") or ""))
                full_path = source_run / rel_path
                data = _load_json(full_path)
                samples.append(
                    ConditionSample(
                        public_id="",
                        scenario_id=scenario_id,
                        scenario_title=SCENARIO_TITLES.get(scenario_id, scenario_id),
                        baseline=baseline,
                        seed=seed,
                        source_path=full_path,
                        source_sha256=str(artifact.get("sha256") or _sha256_file(full_path)),
                        data=data,
                    )
                )
    return samples


def _build_pairwise_tasks(
    samples: list[ConditionSample],
    *,
    baselines: list[str],
    rng: random.Random,
    public_id_by_key: dict[tuple[str, str, int], str],
) -> list[dict[str, str]]:
    pairs: list[dict[str, str]] = []
    first, second = baselines[0], baselines[1]
    grouped: dict[tuple[str, int], dict[str, ConditionSample]] = {}
    for sample in samples:
        grouped.setdefault((sample.scenario_id, sample.seed), {})[sample.baseline] = sample
    for idx, ((scenario_id, seed), by_baseline) in enumerate(sorted(grouped.items()), start=1):
        if first not in by_baseline or second not in by_baseline:
            continue
        left = by_baseline[first]
        right = by_baseline[second]
        a, b = (left, right) if rng.random() < 0.5 else (right, left)
        pairs.append(
            {
                "pair_id": f"PAIR-{idx:03d}",
                "scenario_id": scenario_id,
                "scenario_title": SCENARIO_TITLES.get(scenario_id, scenario_id),
                "seed": str(seed),
                "sample_a_id": public_id_by_key[_condition_key(a)],
                "sample_b_id": public_id_by_key[_condition_key(b)],
            }
        )
    return pairs


def _build_reviewer_packet(
    *,
    packet_id: str,
    manifest: dict[str, Any],
    summary: dict[str, Any],
    llm_evidence: dict[str, Any],
    source_run: Path,
    public_samples: list[ConditionSample],
    pairs: list[dict[str, str]],
    scenarios: list[str],
    baselines: list[str],
    seeds: list[int],
    shuffle_seed: int,
) -> dict[str, Any]:
    public_sample_entries = [
        {
            "publicSampleId": sample.public_id,
            "scenarioTitle": sample.scenario_title,
            "scenarioId": sample.scenario_id,
            "reviewerCardPath": f"reviewer_cards/{sample.public_id}.md",
        }
        for sample in public_samples
    ]
    packet = {
        "packetVersion": PACKET_VERSION,
        "packetId": packet_id,
        "createdAt": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "language": "zh-CN",
        "source": {
            "sourceRunDir": _repo_relative(source_run),
            "suite": summary.get("suite") or manifest.get("suite"),
            "runDirName": manifest.get("runDirName"),
            "manifestSha256": _sha256_file(source_run / "manifest.json"),
            "llmEvidence": {
                "recordCount": llm_evidence.get("recordCount"),
                "cloudCallCount": llm_evidence.get("cloudCallCount"),
                "fallbackCount": llm_evidence.get("fallbackCount"),
            },
        },
        "samplingPolicy": {
            "scenarios": scenarios,
            "conditionCount": len(baselines),
            "seeds": seeds,
            "shuffleSeed": shuffle_seed,
            "reviewerVisibleConditionLabels": False,
            "rule": "中文内部 blind pilot v0：只暴露样本编号、场景和运行记录；内部条件映射单独保存。",
        },
        "manualGate": {
            "status": "manual_review_required",
            "reason": "需要 3-5 名非作者中文 reviewer 盲评；脚本只生成材料，不生成研究结论。",
            "stopCondition": "blind_score_sheet.csv 与 pairwise_preference_sheet.csv 填完后，按 docs/human_rating_pilot_gate.md 的分支判据解读。",
        },
        "publicSamples": public_sample_entries,
        "pairwiseTasks": pairs,
    }
    packet["packetSha256"] = hashlib.sha256(
        json.dumps(packet, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return packet


def _render_reviewer_card(sample: ConditionSample) -> str:
    scenario = sample.data.get("scenario", {}) if isinstance(sample.data.get("scenario"), dict) else {}
    evidence = sample.data.get("evidence", {}) if isinstance(sample.data.get("evidence"), dict) else {}
    lines = [
        f"# 盲评样本 {sample.public_id}",
        "",
        "> 请独立判断这个过程是否可信、结果是否像角色自己发展出来。不要推测样本来自哪种系统条件。",
        "",
        "## 目标场景",
        "",
        f"- 场景：{sample.scenario_title}",
        f"- 目标描述：{scenario.get('description') or sample.scenario_id}",
        f"- 目标角色：{scenario.get('npcId', 'unknown')} → {scenario.get('targetNpcId', 'unknown')}",
        "",
        "## 观测到的运行记录",
        "",
    ]
    lines.extend(_render_observed_events(evidence))
    lines.extend(
        [
            "",
            "## 可见证据线索",
            "",
            f"- 主观记忆引用数量：{_count(evidence.get('subjectiveMemoryRefs'))}",
            f"- 关系来源数量：{_count(evidence.get('relationshipSourceIds'))}",
            f"- 启发式来源数量：{_count(evidence.get('heuristicSourceIds'))}",
            f"- 记忆观察事件数量：{_count(evidence.get('memoryTraceLinks'))}",
            "",
            "## 评分提示",
            "",
            "- 过程可信度：这个结果是否经过可理解的中间过程。",
            "- 结果赚取感：最终结果是否像被角色行为和上下文逐步赚到。",
            "- 角色自主感：角色是否像在根据自身动机、记忆、关系行动。",
            "- Trace 清晰度：材料是否足以让你解释“为什么发生了这件事”。",
        ]
    )
    return "\n".join(lines) + "\n"


def _render_observed_events(evidence: dict[str, Any]) -> list[str]:
    events = evidence.get("goalToolEvents")
    if isinstance(events, list) and events:
        lines: list[str] = []
        for idx, event in enumerate(events[:4], start=1):
            details = event.get("details", {}) if isinstance(event.get("details"), dict) else {}
            lines.append(f"{idx}. {event.get('summary') or event.get('eventType') or '无摘要事件'}")
            tool_id = details.get("toolId")
            if tool_id:
                lines.append(f"   - 行为/工具：`{tool_id}`")
            source_links = event.get("sourceLinks")
            if isinstance(source_links, list):
                matched = [item for item in source_links if isinstance(item, dict) and item.get("matched")]
                if matched:
                    summary = "；".join(str(item.get("summary") or item.get("eventType") or "") for item in matched[:2])
                    lines.append(f"   - 可追溯来源：{summary}")
        return lines

    delegation = evidence.get("delegation")
    if isinstance(delegation, dict):
        actions = ", ".join(str(item) for item in delegation.get("requiredActions", []))
        return [
            f"1. 可见记录显示：{delegation.get('assignee', 'unknown')} 被要求面向 {delegation.get('targetNpcId', 'unknown')} 完成 `{actions}`。",
            "2. 材料中未展示额外的主观记忆、关系边或后续观察事件。",
        ]
    return ["1. 材料中没有可读运行事件。"]


def _write_blind_score_sheet(path: Path, samples: list[ConditionSample]) -> None:
    fieldnames = [
        "public_sample_id",
        "scenario_title",
        "process_believability_1_to_5",
        "earned_outcome_1_to_5",
        "character_autonomy_1_to_5",
        "trace_clarity_1_to_5",
        "protocol_issue_flag",
        "reviewer_notes",
    ]
    with path.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        for sample in sorted(samples, key=lambda item: item.public_id):
            writer.writerow(
                {
                    "public_sample_id": sample.public_id,
                    "scenario_title": sample.scenario_title,
                    "process_believability_1_to_5": "",
                    "earned_outcome_1_to_5": "",
                    "character_autonomy_1_to_5": "",
                    "trace_clarity_1_to_5": "",
                    "protocol_issue_flag": "",
                    "reviewer_notes": "",
                }
            )


def _write_pairwise_sheet(path: Path, pairs: list[dict[str, str]]) -> None:
    fieldnames = [
        "pair_id",
        "scenario_title",
        "sample_a_id",
        "sample_b_id",
        "preference_process_believability_A_B_Tie_Unclear",
        "preference_earned_outcome_A_B_Tie_Unclear",
        "confidence_1_to_5",
        "reviewer_notes",
    ]
    with path.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        for pair in pairs:
            writer.writerow(
                {
                    "pair_id": pair["pair_id"],
                    "scenario_title": pair["scenario_title"],
                    "sample_a_id": pair["sample_a_id"],
                    "sample_b_id": pair["sample_b_id"],
                    "preference_process_believability_A_B_Tie_Unclear": "",
                    "preference_earned_outcome_A_B_Tie_Unclear": "",
                    "confidence_1_to_5": "",
                    "reviewer_notes": "",
                }
            )


def _write_internal_key(path: Path, samples: list[ConditionSample]) -> None:
    fieldnames = [
        "public_sample_id",
        "scenario_id",
        "baseline",
        "seed",
        "source_per_scenario_path",
        "source_sha256",
        "goal_success_rate",
        "process_believability_score_auto",
        "agent_initiated_action_ratio",
        "shortcut_violation_rate",
    ]
    with path.open("w", encoding="utf-8", newline="") as fp:
        writer = csv.DictWriter(fp, fieldnames=fieldnames)
        writer.writeheader()
        for sample in sorted(samples, key=lambda item: item.public_id):
            metrics = sample.data.get("metrics", {}) if isinstance(sample.data.get("metrics"), dict) else {}
            writer.writerow(
                {
                    "public_sample_id": sample.public_id,
                    "scenario_id": sample.scenario_id,
                    "baseline": sample.baseline,
                    "seed": sample.seed,
                    "source_per_scenario_path": _repo_relative(sample.source_path),
                    "source_sha256": sample.source_sha256,
                    "goal_success_rate": metrics.get("goal_success_rate"),
                    "process_believability_score_auto": metrics.get("process_believability_score"),
                    "agent_initiated_action_ratio": metrics.get("agent_initiated_action_ratio"),
                    "shortcut_violation_rate": metrics.get("shortcut_violation_rate"),
                }
            )


def _render_reviewer_readme(packet_id: str, samples: list[ConditionSample], pairs: list[dict[str, str]]) -> str:
    return "\n".join(
        [
            f"# Human Rating Pilot Reviewer README：{packet_id}",
            "",
            "## 使用方法",
            "",
            "1. 逐条阅读 `reviewer_cards/HRP-*.md`。",
            "2. 在 `blind_score_sheet.csv` 中填写 1-5 分与备注。",
            "3. 再填写 `pairwise_preference_sheet.csv`，只比较 A/B 哪个过程更可信、结果更赚取。",
            "4. 如果材料看不懂、缺上下文或无法评分，在 `protocol_issue_flag` 标记 `yes` 并写明原因。",
            "",
            "## 评分锚点",
            "",
            "- 1 = 明显硬推、跳跃或脚本化。",
            "- 2 = 有少量过程，但关键因果缺失。",
            "- 3 = 基本合理，但动机或证据偏薄。",
            "- 4 = 过程自然，有可理解动机与上下文。",
            "- 5 = 非常自然，像角色自己发展出的结果。",
            "",
            "## 本包规模",
            "",
            f"- 单样本评分：{len(samples)} 条。",
            f"- Pairwise 比较：{len(pairs)} 组。",
            "- 条件标签已隐藏；请不要询问内部映射。",
        ]
    ) + "\n"


def _render_protocol(packet_id: str, source_run: Path) -> str:
    return "\n".join(
        [
            f"# Human Rating Pilot Protocol：{packet_id}",
            "",
            "## Scope",
            "",
            "- 语言：中文。",
            "- reviewer：3-5 名非作者协助者。",
            "- 样本：3 个叙事场景 × 2 个隐藏条件 × 1 个 seed。",
            f"- source run：`{_repo_relative(source_run)}`。",
            "- 本包用于 pilot gate；正信号只解锁扩样本与正式 protocol，不能直接升级论文 claim。",
            "",
            "## Green signal",
            "",
            "- 隐藏 Full 条件在 process believability 或 earned outcome 上平均高于隐藏 Hard 条件 0.5-0.75 / 5。",
            "- Full 至少在 2/3 场景中胜过 Hard。",
            "- Full 绝对均分不低于 3.5 / 5。",
            "- Pairwise preference 中 Full 胜 Hard / Direct 约 65%-70% 或更高。",
            "- 自动 Process Fidelity 排序与人类评分排序在至少 2/3 场景一致。",
            "",
            "## Red signal",
            "",
            "- Full 与 Hard 基本无差异，或 Full 低于 Hard。",
            "- Full 绝对均分低于 3.0 / 5。",
            "- reviewer 评论集中指出脚本化、跳跃、动机不清或被导演硬推。",
            "- 自动 Process Fidelity 排序与人类评分长期不一致。",
            "",
            "## Protocol failure",
            "",
            "- reviewer 普遍看不懂 packet。",
            "- 评分分歧完全无结构，且自由文本显示材料或 rubric 有系统性问题。",
            "- 协议失败时只允许修一次 packet 表达或 rubric，再重新收集；不能改样本解释结果。",
        ]
    ) + "\n"


def _extract_seed(path_text: str) -> int | None:
    marker = "seed"
    idx = path_text.rfind(marker)
    if idx < 0:
        return None
    digits = []
    for ch in path_text[idx + len(marker) :]:
        if ch.isdigit():
            digits.append(ch)
        else:
            break
    return int("".join(digits)) if digits else None


def _condition_key(sample: ConditionSample) -> tuple[str, str, int]:
    return (sample.scenario_id, sample.baseline, sample.seed)


def _count(value: Any) -> int:
    if isinstance(value, list):
        return len(value)
    if isinstance(value, dict):
        return len(value)
    return 0


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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
