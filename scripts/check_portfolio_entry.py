"""Portfolio 入口健康检查：校验 case-card-first 展示路径依赖的关键文档与 artifact。"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable

from build_portfolio_evidence_snippets import OUTPUT_PATH, build_markdown


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class RequiredPath:
    """记录对外展示入口必须能访问的文件或目录。"""

    path: str
    category: str
    description: str


@dataclass(frozen=True)
class PathCheck:
    """单个路径检查结果，便于 JSON 报告与人工复核。"""

    path: str
    category: str
    description: str
    exists: bool
    kind: str | None


REQUIRED_PATHS: tuple[RequiredPath, ...] = (
    RequiredPath("README.md", "entry", "repository first screen"),
    RequiredPath("docs/portfolio_case_cards.md", "entry", "case-card-first portfolio path"),
    RequiredPath("docs/portfolio_evidence_snippets.md", "entry", "case-card evidence snippets"),
    RequiredPath("docs/portfolio_capability_map.md", "entry", "interview capability map"),
    RequiredPath("docs/portfolio_story.md", "entry", "final portfolio story"),
    RequiredPath("paper/blog_main.md", "appendix", "technical overview appendix"),
    RequiredPath(
        "paper/trace_walkthroughs/figure3_trace_walkthrough_pf_branna_seed01.md",
        "appendix",
        "trace walkthrough appendix",
    ),
    RequiredPath(
        ".run/eval-promoted/run_2026-05-29T13-57-50Z",
        "process",
        "promoted process evidence bundle",
    ),
    RequiredPath(
        ".run/eval-promoted/run_2026-05-29T13-57-50Z/manifest.json",
        "process",
        "process manifest",
    ),
    RequiredPath(
        ".run/eval-promoted/run_2026-05-29T13-57-50Z/summary.json",
        "process",
        "process summary",
    ),
    RequiredPath(
        ".run/eval-promoted/run_2026-05-29T13-57-50Z/counterfactual_replay.jsonl",
        "process",
        "counterfactual replay evidence",
    ),
    RequiredPath(
        ".run/eval-promoted/run_2026-05-29T13-57-50Z/ablation_comparison.json",
        "process",
        "ablation comparison evidence",
    ),
    RequiredPath(
        ".run/eval-promoted/run_2026-05-29T13-57-50Z/llm_evidence.json",
        "process",
        "cloud-backed LLM evidence",
    ),
    RequiredPath(
        ".run/eval-promoted/run_2026-05-29T13-57-50Z/PROMOTION.md",
        "process",
        "owner-approved promoted-with-caveat note",
    ),
    RequiredPath(
        ".run/eval-reviewer-packets/audit_reviewer_packet_2026-06-06T08-58-33Z/README_REVIEWERS.md",
        "audit",
        "deterministic audit reviewer guide",
    ),
    RequiredPath(
        ".run/eval-reviewer-packets/audit_reviewer_packet_2026-06-06T08-58-33Z/reviewer_packet.json",
        "audit",
        "deterministic audit packet metadata",
    ),
    RequiredPath(
        ".run/eval-reviewer-packets/audit_llm_supplement_2026-06-06T10-59-22Z/README.md",
        "audit",
        "LLM audit supplement guide",
    ),
    RequiredPath(
        ".run/eval-reviewer-packets/audit_llm_supplement_2026-06-06T10-59-22Z/LLM_CASE_COMPARISONS.md",
        "audit",
        "LLM audit case comparisons",
    ),
    RequiredPath(
        ".run/eval-reviewer-packets/audit_llm_supplement_2026-06-06T10-59-22Z/packet_summary.json",
        "audit",
        "LLM audit supplement summary",
    ),
)


TEXT_EXPECTATIONS: dict[str, tuple[str, ...]] = {
    "README.md": (
        "docs/portfolio_case_cards.md",
        "case-card",
        "Human-validated believability is out of scope",
    ),
    "docs/portfolio_case_cards.md": (
        "Card A",
        "Card B",
        "Card C",
        "promoted with caveat",
        "engineering showcase",
        "failure analysis",
    ),
    "docs/portfolio_evidence_snippets.md": (
        "Card A",
        "Card B",
        "Card C",
        "engineering showcase",
        "failure analysis",
        "portfolio:snippets",
    ),
    "docs/portfolio_story.md": ("docs/portfolio_case_cards.md", "case-card-first"),
    "docs/portfolio_capability_map.md": ("docs/portfolio_case_cards.md", "case cards"),
    "paper/trace_walkthroughs/figure3_trace_walkthrough_pf_branna_seed01.md": (
        "portfolio appendix",
        "metric / explainability level",
    ),
}

MARKDOWN_LINK_SOURCE_FILES = (
    "README.md",
    "docs/portfolio_case_cards.md",
    "docs/portfolio_evidence_snippets.md",
    "docs/portfolio_story.md",
    "docs/portfolio_capability_map.md",
)

_MARKDOWN_LINK_PATTERN = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
_FENCED_CODE_BLOCK_PATTERN = re.compile(r"```.*?```", re.DOTALL)


def relative(path: Path) -> str:
    """把绝对路径转成仓库相对路径，方便报告稳定输出。"""

    return path.relative_to(ROOT).as_posix()


def path_kind(path: Path) -> str | None:
    """返回路径类型；缺失时返回 None。"""

    if path.is_file():
        return "file"
    if path.is_dir():
        return "directory"
    return None


def check_required_paths() -> tuple[list[PathCheck], list[str]]:
    """检查入口文档和 artifact 路径是否存在。"""

    checks: list[PathCheck] = []
    errors: list[str] = []
    for required in REQUIRED_PATHS:
        full_path = ROOT / required.path
        exists = full_path.exists()
        kind = path_kind(full_path)
        checks.append(
            PathCheck(
                path=required.path,
                category=required.category,
                description=required.description,
                exists=exists,
                kind=kind,
            )
        )
        if not exists:
            errors.append(f"missing required portfolio path: {required.path}")
    return checks, errors


def read_text(path: Path, errors: list[str]) -> str:
    """读取 UTF-8 文本，失败时记录错误并返回空字符串。"""

    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        errors.append(f"cannot read UTF-8 text: {relative(path)} -> {exc}")
    except OSError as exc:
        errors.append(f"cannot read text: {relative(path)} -> {exc}")
    return ""


def strip_fenced_code_blocks(text: str) -> str:
    """移除 fenced code block，避免把代码样例里的括号误判为 Markdown 链接。"""

    return _FENCED_CODE_BLOCK_PATTERN.sub("", text)


def is_external_link(target: str) -> bool:
    """判断链接是否属于外部 URL、邮件或纯锚点。"""

    lowered = target.lower()
    return (
        lowered.startswith(("http://", "https://", "mailto:"))
        or target.startswith("#")
        or not target
    )


def resolve_markdown_link(source_file: Path, target: str) -> Path:
    """按 Markdown 文件所在目录解析相对链接。"""

    clean_target = target.split("#", 1)[0]
    return (source_file.parent / clean_target).resolve()


def check_markdown_links() -> list[str]:
    """扫描显式 Markdown 链接，确保对外入口没有坏链接。"""

    errors: list[str] = []
    for rel_path in MARKDOWN_LINK_SOURCE_FILES:
        source_file = ROOT / rel_path
        if not source_file.exists():
            continue
        text = strip_fenced_code_blocks(read_text(source_file, errors))
        for match in _MARKDOWN_LINK_PATTERN.finditer(text):
            target = match.group(1).strip()
            if is_external_link(target):
                continue
            resolved = resolve_markdown_link(source_file, target)
            if not resolved.exists():
                errors.append(f"{rel_path} has broken Markdown link: {target}")
    return errors


def check_snippets_current() -> list[str]:
    """检查 snippets 是否与当前源 artifact 生成结果一致。"""

    errors: list[str] = []
    if not OUTPUT_PATH.exists():
        errors.append(f"missing generated snippets: {OUTPUT_PATH.relative_to(ROOT).as_posix()}")
        return errors
    current = read_text(OUTPUT_PATH, errors)
    expected = build_markdown()
    if current != expected:
        errors.append("docs/portfolio_evidence_snippets.md is stale; run npm.cmd run portfolio:snippets")
    return errors


def check_text_expectations() -> list[str]:
    """检查对外入口文档是否包含必要锚点与边界口径。"""

    errors: list[str] = []
    for rel_path, phrases in TEXT_EXPECTATIONS.items():
        path = ROOT / rel_path
        if not path.exists():
            continue
        text = read_text(path, errors)
        for phrase in phrases:
            if phrase not in text:
                errors.append(f"{rel_path} missing required phrase: {phrase}")
    return errors


def load_json(path: Path, errors: list[str]) -> Any:
    """读取 JSON artifact，失败时返回 None。"""

    try:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except json.JSONDecodeError as exc:
        errors.append(f"invalid JSON: {relative(path)} -> {exc}")
    except OSError as exc:
        errors.append(f"cannot read JSON: {relative(path)} -> {exc}")
    return None


def expect_json(
    rel_path: str,
    predicate: Callable[[Any], bool],
    description: str,
    errors: list[str],
) -> None:
    """对 JSON artifact 执行轻量语义检查。"""

    path = ROOT / rel_path
    if not path.exists():
        return
    data = load_json(path, errors)
    if data is None:
        return
    try:
        ok = predicate(data)
    except (KeyError, TypeError, ValueError) as exc:
        errors.append(f"JSON check crashed: {rel_path} -> {description} -> {exc}")
        return
    if not ok:
        errors.append(f"JSON check failed: {rel_path} -> {description}")


def check_json_artifacts() -> list[str]:
    """检查关键 JSON artifact 的最小可展示语义。"""

    errors: list[str] = []
    expect_json(
        ".run/eval-promoted/run_2026-05-29T13-57-50Z/manifest.json",
        lambda data: data.get("ok") is True
        and data.get("suite") == "process_fidelity"
        and int(data.get("llmEvidence", {}).get("recordCount", 0)) >= 100,
        "process manifest must be ok with >=100 LLM evidence records",
        errors,
    )
    expect_json(
        ".run/eval-reviewer-packets/audit_llm_supplement_2026-06-06T10-59-22Z/packet_summary.json",
        lambda data: data.get("ok") is True
        and data.get("providerMode") == "cloud"
        and data.get("passed") == data.get("total") == 10
        and data.get("scenarioCount") == 5
        and data.get("caseCount") == 10,
        "audit LLM supplement must cover 5 scenarios and 10/10 passed cases",
        errors,
    )
    expect_json(
        ".run/eval-reviewer-packets/audit_reviewer_packet_2026-06-06T08-58-33Z/reviewer_packet.json",
        lambda data: data.get("goNoGo", {}).get("pass") is True
        and len(data.get("caseStudyFiles", [])) >= 5,
        "deterministic audit packet must pass go/no-go and include case studies",
        errors,
    )
    return errors


def main() -> int:
    """CLI 主入口：输出稳定 JSON 报告，errors 非空时返回 1。"""

    path_checks, path_errors = check_required_paths()
    text_errors = check_text_expectations()
    json_errors = check_json_artifacts()
    markdown_link_errors = check_markdown_links()
    snippets_errors = check_snippets_current()
    errors = path_errors + text_errors + json_errors + markdown_link_errors + snippets_errors
    report = {
        "ok": not errors,
        "check": "portfolio.entry",
        "errors": errors,
        "warnings": [],
        "paths": [asdict(check) for check in path_checks],
        "textExpectationFiles": sorted(TEXT_EXPECTATIONS),
        "markdownLinkFiles": list(MARKDOWN_LINK_SOURCE_FILES),
        "snippetsCurrent": not snippets_errors,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
