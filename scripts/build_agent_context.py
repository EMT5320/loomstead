"""生成 Loomstead 上下文 brief，并检查上下文治理文件。"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]

# Windows PowerShell 通过管道读取 Python 输出时可能出现编码漂移，统一用 UTF-8 输出。
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# 这些文件构成多助手共享入口。
INSTRUCTION_FILES = [
    "AGENTS.md",
    "CLAUDE.md",
    ".claude/rules/docs-context.md",
    ".claude/rules/backend.md",
    ".claude/rules/godot-client.md",
    ".claude/rules/assets.md",
]

# 这些文档构成新对话上下文的最小来源集合。
REQUIRED_DOCS = [
    "docs/agent_context.md",
    "docs/goal_board.md",
    "docs/README.md",
    "docs/project_vision.md",
    "docs/current_status.md",
    "docs/open_questions.md",
    "docs/agentic_game_design.md",
    "docs/agent_loop_architecture.md",
    "docs/research_framing_motivational_delegation.md",
]

REQUIRED_METADATA_KEYS = [
    "status",
    "owner_lane",
    "last_verified",
    "startup_load",
    "source_of_truth",
    "scope",
]

VALID_STATUSES = {"active", "snapshot", "archive"}
VALID_STARTUP_LOADS = {"first-read", "after-agent-context", "index", "on-demand"}

# 这些过期短语如果出现在 active 文档中，通常代表口径没有跟随当前事实更新。
STALE_ACTIVE_PATTERNS = [
    "温暖绘本风",
    "真实云端 smoke 尚未执行",
    "当前本机未检测到 `config/models.local.json`",
    "当前登记 21 条已筛选资产",
]

# 路由层显式提到的高价值路径，用于发现移动或重命名后的断链。
ROUTED_PATHS = [
    "backend",
    "clients/godot",
    "clients/godot/README.md",
    "config",
    "assets/manifests/asset_manifest.json",
    "scripts/check.py",
    "docs/gameplay_system_architecture.md",
    "docs/game_client_environment.md",
    "docs/game_content_storyline.md",
    "docs/npc_deep_card_spec.md",
    "docs/model_profile_template_guide.md",
    "docs/art_direction.md",
    "docs/asset_generation_prompts.md",
    "docs/process_fidelity_eval_spec.md",
    "docs/cross_domain_adapter.md",
]


def read_text(relative_path: str) -> str:
    """按 UTF-8 读取仓库内文档。"""
    return (ROOT / relative_path).read_text(encoding="utf-8")


def list_doc_paths() -> list[str]:
    """列出 docs 根目录下所有 Markdown 文档。"""
    return sorted(path.relative_to(ROOT).as_posix() for path in (ROOT / "docs").glob("*.md"))


def parse_frontmatter(text: str) -> dict[str, str]:
    """解析文档顶部的简单 YAML frontmatter。"""
    if not text.startswith("---\n"):
        return {}

    lines = text.splitlines()
    metadata: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip()
    return metadata


def extract_section_after_heading(text: str, heading: str, max_lines: int = 2) -> str:
    """提取某个 Markdown 标题下的首段文本。"""
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.strip() == heading:
            collected: list[str] = []
            for next_line in lines[index + 1 :]:
                stripped = next_line.strip()
                if stripped.startswith("#"):
                    break
                if stripped:
                    collected.append(stripped)
                if len(collected) >= max_lines:
                    break
            return " ".join(collected)
    return ""


def extract_bullet_section(text: str, heading: str, max_items: int = 6) -> list[str]:
    """提取某个标题下的首批列表项，供 brief 输出当前入口。"""
    lines = text.splitlines()
    heading_level = len(heading) - len(heading.lstrip("#"))
    for index, line in enumerate(lines):
        if line.strip() == heading:
            collected: list[str] = []
            for next_line in lines[index + 1 :]:
                stripped = next_line.strip()
                if stripped.startswith("#"):
                    next_level = len(stripped) - len(stripped.lstrip("#"))
                    if next_level <= heading_level:
                        break
                    continue
                if not stripped:
                    continue
                normalized = stripped.lstrip()
                is_numbered = bool(re.match(r"\d+\.\s+", normalized))
                if normalized.startswith("- ") or is_numbered:
                    collected.append(normalized)
                if len(collected) >= max_items:
                    break
            return collected
    return []


def collect_missing_paths(paths: list[str]) -> list[str]:
    """返回当前缺失的仓库路径。"""
    return [path for path in paths if not (ROOT / path).exists()]


def validate_metadata(relative_path: str) -> list[str]:
    """检查文档的治理元信息。"""
    text = read_text(relative_path)
    metadata = parse_frontmatter(text)
    errors: list[str] = []

    if not metadata:
        return [f"{relative_path} 缺少 frontmatter 元信息"]

    for key in REQUIRED_METADATA_KEYS:
        if key not in metadata or not metadata[key]:
            errors.append(f"{relative_path} 缺少元信息字段 `{key}`")

    status = metadata.get("status")
    if status and status not in VALID_STATUSES:
        errors.append(f"{relative_path} 的 status={status} 不在 {sorted(VALID_STATUSES)} 内")

    startup_load = metadata.get("startup_load")
    if startup_load and startup_load not in VALID_STARTUP_LOADS:
        errors.append(f"{relative_path} 的 startup_load={startup_load} 不在 {sorted(VALID_STARTUP_LOADS)} 内")

    source_of_truth = metadata.get("source_of_truth")
    if source_of_truth and source_of_truth not in {"true", "false"}:
        errors.append(f"{relative_path} 的 source_of_truth 需要是 true 或 false")
    if status in {"snapshot", "archive"} and source_of_truth == "true":
        errors.append(f"{relative_path} 是 {status}，source_of_truth 需要为 false")

    last_verified = metadata.get("last_verified")
    if last_verified and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", last_verified):
        errors.append(f"{relative_path} 的 last_verified 需要使用 YYYY-MM-DD")

    return errors


def find_active_doc_stale_patterns() -> list[str]:
    """扫描 active 文档中的明显过期口径。"""
    errors: list[str] = []
    for relative_path in list_doc_paths():
        text = read_text(relative_path)
        metadata = parse_frontmatter(text)
        if metadata.get("status") != "active":
            continue
        for pattern in STALE_ACTIVE_PATTERNS:
            if pattern in text:
                errors.append(f"{relative_path} 包含疑似过期口径：{pattern}")
    return errors


def validate_context() -> tuple[list[str], list[str]]:
    """检查上下文治理入口、关键文档和基础一致性。"""
    errors: list[str] = []
    warnings: list[str] = []

    for label, paths in [
        ("代理入口文件", INSTRUCTION_FILES),
        ("关键上下文文档", REQUIRED_DOCS),
        ("任务线路由路径", ROUTED_PATHS),
    ]:
        missing = collect_missing_paths(paths)
        if missing:
            errors.append(f"{label}缺失：{', '.join(missing)}")

    if not errors:
        claude_text = read_text("CLAUDE.md")
        agents_text = read_text("AGENTS.md")
        gitignore_text = read_text(".gitignore")

        if "@AGENTS.md" not in claude_text:
            errors.append("CLAUDE.md 需要导入 @AGENTS.md")
        for required_reference in ["docs/agent_context.md", "docs/current_status.md", "docs/goal_board.md"]:
            if required_reference not in agents_text:
                errors.append(f"AGENTS.md 缺少入口引用 `{required_reference}`")
        for required_ignore in ["CLAUDE.local.md", ".claude/settings.local.json", "!.claude/rules/"]:
            if required_ignore not in gitignore_text:
                errors.append(f".gitignore 缺少本地 Claude 配置规则 `{required_ignore}`")

    for rule_path in sorted((ROOT / ".claude" / "rules").glob("*.md")):
        rule_text = rule_path.read_text(encoding="utf-8")
        if not rule_text.startswith("---\n") or "paths:" not in rule_text.split("---", 2)[1]:
            errors.append(f"{rule_path.relative_to(ROOT).as_posix()} 需要使用 paths frontmatter")

    doc_paths = list_doc_paths()
    for path in doc_paths:
        errors.extend(validate_metadata(path))
    errors.extend(find_active_doc_stale_patterns())

    agent_context_lines = read_text("docs/agent_context.md").splitlines()
    if len(agent_context_lines) > 160:
        warnings.append(f"docs/agent_context.md 当前 {len(agent_context_lines)} 行，建议保持在 160 行以内")

    current_status_text = read_text("docs/current_status.md")
    if "人工未验收" not in current_status_text and "manual unverified" not in current_status_text:
        warnings.append("docs/current_status.md 未出现人工未验收标记，请确认人工验收边界是否仍清晰")

    return errors, warnings


def build_doc_inventory() -> str:
    """生成面向助手的文档清单表。"""
    rows = [
        "| 文档 | 状态 | 开发线 | 加载策略 | 事实源 |",
        "| --- | --- | --- | --- | --- |",
    ]
    for relative_path in list_doc_paths():
        metadata = parse_frontmatter(read_text(relative_path))
        name = Path(relative_path).name
        rows.append(
            "| "
            + f"`{name}`"
            + f" | {metadata.get('status', '')}"
            + f" | {metadata.get('owner_lane', '')}"
            + f" | {metadata.get('startup_load', '')}"
            + f" | {metadata.get('source_of_truth', '')} |"
        )
    return "\n".join(["# Loomstead 文档清单", "", *rows])


def build_brief() -> str:
    """基于现有文档生成轻量 brief 草稿。"""
    agent_context = read_text("docs/agent_context.md")
    goal_board = read_text("docs/goal_board.md")
    vision = read_text("docs/project_vision.md")
    status = read_text("docs/current_status.md")

    one_liner = extract_section_after_heading(vision, "## 一句话定位", max_lines=1)
    phase_items = extract_bullet_section(status, "## 1. 当前阶段判断", max_items=6)
    next_steps = extract_bullet_section(agent_context, "## 6. 下一轮最短开发入口", max_items=6)
    schedule = extract_bullet_section(goal_board, "## 8. 下一轮推荐排程", max_items=5)

    return "\n".join(
        [
            "# Loomstead brief 草稿",
            "",
            "## 一句话定位",
            "",
            one_liner or "- 未能从 `docs/project_vision.md` 提取定位。",
            "",
            "## 当前阶段",
            "",
            "\n".join(phase_items)
            or extract_section_after_heading(status, "## 1. 当前阶段判断", max_lines=2)
            or "- 未能从 `docs/current_status.md` 提取阶段判断。",
            "",
            "## 最近下一步",
            "",
            "\n".join(next_steps) or "- 未能从 `docs/agent_context.md` 提取下一步。",
            "",
            "## 推荐排程",
            "",
            "\n".join(schedule) or "- 未能从 `docs/goal_board.md` 提取推荐排程。",
            "",
            "## 建议下一步",
            "",
            "- 可先读 `AGENTS.md` 和 `docs/agent_context.md`。",
            "- 可按任务线读取 `docs/goal_board.md` 和对应源文档。",
            "- 调整上下文治理后，建议运行 `npm.cmd run context:check` 与 `git diff --check`。",
        ]
    )


def print_validation_report(errors: list[str], warnings: list[str]) -> None:
    """输出治理校验报告。"""
    if errors:
        print("[agent-context] 治理校验失败：")
        for error in errors:
            print(f"- {error}")
        return

    print("[agent-context] 治理校验通过。")
    if warnings:
        print("[agent-context] 注意事项：")
        for warning in warnings:
            print(f"- {warning}")


def main() -> int:
    """命令行入口：默认输出 brief，--check 只做治理校验。"""
    parser = argparse.ArgumentParser(description="生成或校验 Loomstead 上下文入口。")
    parser.add_argument("--check", action="store_true", help="只运行上下文治理校验。")
    parser.add_argument("--docs", action="store_true", help="输出文档清单。")
    args = parser.parse_args()

    errors, warnings = validate_context()
    print_validation_report(errors, warnings)
    if errors:
        return 1

    if args.check:
        return 0

    if args.docs:
        print()
        print(build_doc_inventory())
        return 0

    print()
    print(build_brief())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
