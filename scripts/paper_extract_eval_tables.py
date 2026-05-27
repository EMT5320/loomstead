#!/usr/bin/env python3
"""Extract paper-ready Markdown and CSV tables from local eval exports."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RUNS_DIR = ROOT / ".run" / "eval-runs"
DEFAULT_OUT_DIR = ROOT / "paper" / "generated"
SELECTED_METRICS = [
    "goal_success_rate",
    "shortcut_violation_rate",
    "required_process_coverage",
    "forced_action_rate",
    "agent_initiated_action_ratio",
    "relationship_memory_causal_use_rate",
    "counterfactual_tool_selection_change_rate",
    "causal_trace_coverage",
    "process_believability_score",
    "stability_tick_success_rate",
    "tool_failure_rate",
    "tool_interruption_rate",
    "memory_observation_per_tool_result",
    "heuristic_decision_ref_rate",
]

PAPER_TABLE_METRICS = [
    "goal_success_rate",
    "required_process_coverage",
    "shortcut_violation_rate",
    "forced_action_rate",
    "agent_initiated_action_ratio",
    "relationship_memory_causal_use_rate",
    "causal_trace_coverage",
    "process_believability_score",
]

METRIC_LABELS = {
    "goal_success_rate": "Goal",
    "shortcut_violation_rate": "Shortcut",
    "required_process_coverage": "Process",
    "forced_action_rate": "Forced",
    "agent_initiated_action_ratio": "Agent-init.",
    "relationship_memory_causal_use_rate": "Memory",
    "counterfactual_tool_selection_change_rate": "CF route",
    "causal_trace_coverage": "Trace",
    "process_believability_score": "Believ.",
    "stability_tick_success_rate": "Tick success",
    "tool_failure_rate": "Tool fail",
    "tool_interruption_rate": "Interrupt",
    "memory_observation_per_tool_result": "Memory obs.",
    "heuristic_decision_ref_rate": "Heuristic ref.",
}

BASELINE_LABELS = {
    "full_motivational_delegation": "Full",
    "hard_delegation": "Hard",
    "no_subjective_memory": "No memory",
    "no_relationship_edge": "No relation",
    "shuffled_memory_owner": "Shuffled owner",
    "evidence_link_removal": "No evidence link",
    "rule_24h_stability": "24h",
    "rule_72h_stability": "72h",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_time(value: str | None, fallback: float) -> tuple[int, float | str]:
    """Convert manifest time into a sortable key with an mtime fallback."""

    if not value:
        return (0, fallback)
    try:
        normalized = value.replace("Z", "+00:00")
        return (1, dt.datetime.fromisoformat(normalized).timestamp())
    except ValueError:
        return (0, value)


def discover_runs(runs_dir: Path) -> list[dict[str, Any]]:
    """Read every run directory that contains a manifest."""

    runs: list[dict[str, Any]] = []
    if not runs_dir.exists():
        return runs
    for manifest_path in runs_dir.glob("*/manifest.json"):
        run_dir = manifest_path.parent
        manifest = load_json(manifest_path)
        summary_path = run_dir / "summary.json"
        summary = load_json(summary_path) if summary_path.exists() else {}
        runs.append(
            {
                "runDir": run_dir,
                "runDirName": run_dir.name,
                "manifest": manifest,
                "summary": summary,
                "sortKey": parse_time(manifest.get("createdAt"), manifest_path.stat().st_mtime),
            }
        )
    return runs


def latest_by_suite(runs: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Keep the newest run per suite so paper tables do not mix historical results."""

    latest: dict[str, dict[str, Any]] = {}
    for run in runs:
        suite = run["manifest"].get("suite") or run["summary"].get("suite") or "unknown"
        if suite not in latest or run["sortKey"] > latest[suite]["sortKey"]:
            latest[suite] = run
    return latest


def fmt(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.6g}"
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value)


def metric_rows(summary: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for metric in summary.get("metrics") or []:
        if metric.get("metric") in SELECTED_METRICS:
            rows.append(metric)
    return rows


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(fmt(cell).replace("|", "\\|") for cell in row) + " |")
    return "\n".join(lines)


def latex_escape(value: Any) -> str:
    """Escape the small subset of LaTeX-sensitive characters used in tables."""

    text = fmt(value)
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(char, char) for char in text)


def metric_lookup(summary: dict[str, Any], scenario_id: str = "aggregate") -> dict[tuple[str, str], dict[str, Any]]:
    """Index metrics by baseline and metric id for compact generated tables."""

    lookup: dict[tuple[str, str], dict[str, Any]] = {}
    for row in metric_rows(summary):
        if row.get("scenarioId") == scenario_id:
            lookup[(str(row.get("baseline")), str(row.get("metric")))] = row
    return lookup


def latex_number(value: Any) -> str:
    if value is None:
        return "--"
    if isinstance(value, (int, float)):
        return f"{float(value):.3g}"
    return latex_escape(value)


def write_latex_eval_tables(latest: dict[str, dict[str, Any]], out_dir: Path) -> None:
    """Write compact LaTeX tables that can be input by the draft paper."""

    lines: list[str] = [
        "% Generated by scripts/paper_extract_eval_tables.py.",
        "% Refresh with `npm.cmd run paper:tables` or `npm.cmd run paper:check`.",
        "",
    ]

    process_run = latest.get("process_fidelity")
    if process_run:
        summary = process_run["summary"]
        lookup = metric_lookup(summary)
        baselines = [
            "full_motivational_delegation",
            "hard_delegation",
            "no_subjective_memory",
            "no_relationship_edge",
            "shuffled_memory_owner",
            "evidence_link_removal",
        ]
        lines.extend(
            [
                r"\begin{table}[t]",
                r"\centering",
                r"\small",
                r"\caption{Process Fidelity ablation summary from the latest local rule-level process suite. Lower is better for shortcut and forced-action rates; higher is better for the other metrics.}",
                r"\label{tab:process-ablation}",
                r"\begin{tabular}{lrrrrrrrr}",
                r"\toprule",
                "Baseline & "
                + " & ".join(latex_escape(METRIC_LABELS[metric]) for metric in PAPER_TABLE_METRICS)
                + r" \\",
                r"\midrule",
            ]
        )
        for baseline in baselines:
            cells = [latex_escape(BASELINE_LABELS.get(baseline, baseline))]
            for metric in PAPER_TABLE_METRICS:
                cells.append(latex_number((lookup.get((baseline, metric)) or {}).get("mean")))
            lines.append(" & ".join(cells) + r" \\")
        lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}", ""])

    for suite, caption, label in [
        (
            "stability_24h",
            "Stability metrics from the latest 24-hour local rule-level run.",
            "tab:stability-24h",
        ),
        (
            "stability_72h",
            "Stability metrics from the latest 72-hour local rule-level run.",
            "tab:stability-72h",
        ),
    ]:
        run = latest.get(suite)
        if not run:
            continue
        summary = run["summary"]
        rows = [
            row
            for row in metric_rows(summary)
            if row.get("scenarioId") == "aggregate"
            and row.get("metric")
            in {
                "stability_tick_success_rate",
                "tool_failure_rate",
                "tool_interruption_rate",
                "memory_observation_per_tool_result",
                "heuristic_decision_ref_rate",
            }
        ]
        lines.extend(
            [
                r"\begin{table}[t]",
                r"\centering",
                r"\small",
                rf"\caption{{{caption}}}",
                rf"\label{{{label}}}",
                r"\begin{tabular}{lrrr}",
                r"\toprule",
                r"Metric & Mean & Std. & N \\",
                r"\midrule",
            ]
        )
        for row in rows:
            metric = str(row.get("metric"))
            cells = [
                latex_escape(METRIC_LABELS.get(metric, metric)),
                latex_number(row.get("mean")),
                latex_number(row.get("std")),
                latex_number(row.get("n")),
            ]
            lines.append(" & ".join(cells) + r" \\")
        lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}", ""])

    domain_run = latest.get("cross_domain_adapter")
    if domain_run:
        summary = domain_run["summary"]
        domains = summary.get("domains") or {}
        lines.extend(
            [
                r"\begin{table}[t]",
                r"\centering",
                r"\small",
                r"\caption{Cross-domain adapter suite summary from the latest local dry-run fixtures. Repeats are deterministic export repeats, and CF route reports counterfactual tool-selection change rate.}",
                r"\label{tab:domain-adapter}",
                r"\begin{tabular}{lrrrrr}",
                r"\toprule",
                r"Domain & Passed & Total & Scenarios & Det. repeats & CF route \\",
                r"\midrule",
            ]
        )
        for domain_id, stats in sorted(domains.items()):
            scenario_count = len(stats.get("scenarioIds") or [])
            domain_metrics = metric_lookup(summary, scenario_id=domain_id)
            cf_route = (domain_metrics.get(("full_motivational_delegation", "counterfactual_tool_selection_change_rate")) or {}).get("mean")
            cells = [
                latex_escape(domain_id),
                latex_number(stats.get("passed")),
                latex_number(stats.get("total")),
                latex_number(scenario_count),
                latex_number(stats.get("seedCount") or summary.get("seedCount")),
                latex_number(cf_route),
            ]
            lines.append(" & ".join(cells) + r" \\")
        lines.extend([r"\bottomrule", r"\end{tabular}", r"\end{table}", ""])

    out_dir.joinpath("eval_tables.tex").write_text("\n".join(lines), encoding="utf-8", newline="\n")


def write_eval_summary(latest: dict[str, dict[str, Any]], out_dir: Path) -> None:
    """Write the main paper evidence summary tables."""

    lines: list[str] = [
        "# Generated Eval Summary Tables",
        "",
        "This file is generated by `scripts/paper_extract_eval_tables.py`. Re-run it before publication so tables reflect the latest eval exports.",
        "",
        "## Latest runs by suite",
        "",
    ]
    latest_rows = []
    for suite, run in sorted(latest.items()):
        manifest = run["manifest"]
        summary = run["summary"]
        latest_rows.append(
            [
                suite,
                run["runDirName"],
                manifest.get("ok"),
                manifest.get("git", {}).get("shortCommit"),
                manifest.get("git", {}).get("dirty"),
                len(manifest.get("artifacts") or []),
                summary.get("seedCount"),
                summary.get("passed"),
                summary.get("total"),
            ]
        )
    lines.append(markdown_table(["Suite", "Run", "OK", "Git", "Dirty", "Artifacts", "Seeds", "Passed", "Total"], latest_rows))

    for suite, run in sorted(latest.items()):
        summary = run["summary"]
        rows = metric_rows(summary)
        if not rows:
            continue
        lines.extend(["", f"## Metrics: {suite}", ""])
        lines.append(
            markdown_table(
                ["Metric", "Baseline", "Scenario", "Mean", "Std", "N"],
                [[row.get("metric"), row.get("baseline"), row.get("scenarioId"), row.get("mean"), row.get("std"), row.get("n")] for row in rows],
            )
        )

    out_dir.joinpath("eval_summary_tables.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def write_ablation_csv(latest: dict[str, dict[str, Any]], out_dir: Path) -> None:
    """Flatten the process-suite ablation comparison into CSV."""

    process_run = latest.get("process_fidelity")
    rows: list[dict[str, Any]] = []
    if process_run:
        comparison = (process_run["summary"].get("ablation_comparison") or {}).get("comparison") or {}
        for baseline, metrics in comparison.items():
            for metric, stats in metrics.items():
                rows.append(
                    {
                        "baseline": baseline,
                        "metric": metric,
                        "mean": stats.get("mean"),
                        "std": stats.get("std"),
                        "n": stats.get("n"),
                    }
                )
    path = out_dir / "ablation_table.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["baseline", "metric", "mean", "std", "n"])
        writer.writeheader()
        writer.writerows(rows)


def write_manifest_inventory(latest: dict[str, dict[str, Any]], out_dir: Path) -> None:
    """Write a manifest artifact inventory for paper evidence tracking."""

    lines = [
        "# Generated Manifest Inventory",
        "",
        "This file lists manifest summaries and artifact entrypoints for each latest suite.",
        "",
    ]
    for suite, run in sorted(latest.items()):
        manifest = run["manifest"]
        artifacts = manifest.get("artifacts") or []
        lines.extend([
            f"## {suite}",
            "",
            f"- run: `{run['runDirName']}`",
            f"- exportKind: `{manifest.get('exportKind')}`",
            f"- ok: `{manifest.get('ok')}`",
            f"- git: `{manifest.get('git', {}).get('shortCommit')}` dirty=`{manifest.get('git', {}).get('dirty')}`",
            f"- artifactCount: `{len(artifacts)}`",
            "",
        ])
        preview = artifacts[:20]
        if preview:
            lines.append(markdown_table(["Path", "Kind", "Bytes", "Rows", "SHA256"], [[a.get("path"), a.get("kind"), a.get("bytes"), a.get("rowCount"), a.get("sha256")] for a in preview]))
            lines.append("")
        if len(artifacts) > len(preview):
            lines.append(f"_Additional artifacts omitted from preview: {len(artifacts) - len(preview)}._\n")
    out_dir.joinpath("manifest_inventory.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def write_latest_json(latest: dict[str, dict[str, Any]], out_dir: Path) -> None:
    """Write a machine-readable summary for future plotting scripts."""

    payload = {
        suite: {
            "runDirName": run["runDirName"],
            "manifest": run["manifest"],
            "summary": run["summary"],
        }
        for suite, run in sorted(latest.items())
    }
    out_dir.joinpath("latest_runs.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS_DIR, help="Eval run export directory.")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR, help="Paper generated-table output directory.")
    parser.add_argument("--json", action="store_true", help="Print latest suite summary JSON.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    runs = discover_runs(args.runs_dir)
    latest = latest_by_suite(runs)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    write_eval_summary(latest, args.out_dir)
    write_ablation_csv(latest, args.out_dir)
    write_manifest_inventory(latest, args.out_dir)
    write_latest_json(latest, args.out_dir)
    write_latex_eval_tables(latest, args.out_dir)
    summary = {suite: run["runDirName"] for suite, run in sorted(latest.items())}
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(f"generated={args.out_dir} suites={len(summary)} latest={summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
