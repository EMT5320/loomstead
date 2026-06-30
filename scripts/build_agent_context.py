"""生成 Loomstead 上下文 brief，并检查上下文治理文件。"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import subprocess
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
    "docs/context_governance.md",
    "docs/agent_context.md",
    "docs/assistant_continuity.md",
    "docs/README.md",
    "docs/project_vision.md",
    "docs/current_status.md",
    "docs/phase_checkpoints.md",
    "docs/open_questions.md",
    "docs/agent_loop_architecture.md",
    "docs/research_framing_motivational_delegation.md",
    "docs/process_fidelity_eval_spec.md",
    "docs/cross_domain_adapter.md",
    "docs/world_entity_model.md",
    "docs/eval_dataset_archive.md",
    "docs/workflows.md",
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
MANUAL_GATE_MAX_ITEMS = 10

# brief / resume 提取依赖的标题锚点，必须与目标文档保持同步，避免提取静默退化为 fallback。
BRIEF_RESUME_HEADINGS = [
    ("docs/agent_context.md", "## 2. 一句话定位"),
    ("docs/current_status.md", "## 1. 当前阶段"),
    ("docs/current_status.md", "## 5. 人工验收"),
    ("docs/agent_context.md", "## 3. 当前阶段"),
    ("docs/agent_context.md", "## 5. 最近下一步"),
    ("docs/agent_context.md", "## 6. 按开发线读取"),
    ("docs/agent_context.md", "## 7. 验证命令"),
    ("docs/agent_context.md", "## 8. 协作约束"),
]

# 这些过期短语如果出现在 active 文档中，通常代表口径没有跟随当前事实更新。
STALE_ACTIVE_PATTERNS = [
    "温暖绘本风",
    "真实云端 smoke 尚未执行",
    "当前本机未检测到 `config/models.local.json`",
    "当前登记 21 条已筛选资产",
    "今晚优先完成",
    "下一步补 trace 行跳转事件源",
]

# 路由层显式提到的高价值路径，用于发现移动或重命名后的断链。
ROUTED_PATHS = [
    "backend",
    "clients/godot",
    "clients/godot/README.md",
    "config",
    "assets/manifests/asset_manifest.json",
    "scripts/check.py",
    "docs/game_client_environment.md",
    "docs/model_profile_template_guide.md",
    "docs/art_direction.md",
    "docs/asset_generation_prompts.md",
    "docs/process_fidelity_eval_spec.md",
    "docs/cross_domain_adapter.md",
    "docs/eval_dataset_archive.md",
    "docs/assistant_continuity.md",
    "docs/workflows.md",
    "backend/app/eval",
    "backend/app/domain",
]

LANE_RULES = [
    (
        "上下文治理",
        (
            "AGENTS.md",
            "CLAUDE.md",
            "README.md",
            "docs/context_governance.md",
            "docs/agent_context.md",
            "docs/current_status.md",
            "docs/phase_checkpoints.md",
            "docs/assistant_continuity.md",
            "docs/portfolio_story.md",
            "docs/portfolio_capability_map.md",
            "docs/workflows.md",
            "docs/README.md",
            "scripts/build_agent_context.py",
            ".claude/",
        ),
        ("npm.cmd run context:check", "git diff --check"),
    ),
    (
        "后端 Runtime / Agent Loop",
        ("backend/app/runtime/", "backend/app/tools/", "backend/app/memory/", "backend/app/director/"),
        ("npm.cmd run check", "npm.cmd run smoke", "npm.cmd run schema:check"),
    ),
    (
        "Eval / Research",
        (
            "backend/app/eval/",
            "backend/app/domain/",
            "scripts/run_agent_eval.py",
            "scripts/index_eval_runs.py",
            "scripts/build_audit_reviewer_packet.py",
            "scripts/run_audit_llm_smoke.py",
            "scripts/build_audit_llm_supplement.py",
        ),
        (
            "npm.cmd run eval:process",
            "npm.cmd run eval:stability",
            "npm.cmd run eval:stability:determinism",
            "npm.cmd run eval:domain",
            "npm.cmd run eval:audit",
            "npm.cmd run eval:audit:llm-contract",
            "npm.cmd run eval:audit:llm-contract:full",
            "npm.cmd run eval:audit:llm-supplement",
            "npm.cmd run eval:archive:check",
            "npm.cmd run eval:archive:drift",
        ),
    ),
    (
        "Godot 客户端",
        ("clients/godot/", "scripts/open_godot_project.ps1", "scripts/check_game_client_env.py"),
        ("npm.cmd run client:env", "npm.cmd run client:run:check"),
    ),
    (
        "Web Debug",
        ("frontend/", "web-admin/"),
        ("npm.cmd run check", "npm.cmd run smoke"),
    ),
    (
        "Content / NPC",
        ("backend/app/content/",),
        ("npm.cmd run content:check", "npm.cmd run check"),
    ),
    (
        "Assets",
        ("assets/", "docs/asset_generation_prompts.md", "docs/art_direction.md", "docs/map_sprite_style_guide.md"),
        ("npm.cmd run asset:check",),
    ),
    (
        "LLM / Model Config",
        ("config/", "backend/app/providers/", "docs/model_profile_template_guide.md"),
        ("npm.cmd run model:check", "npm.cmd run llm:smoke # only when real provider evidence is required"),
    ),
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


def heading_matches(line: str, heading: str) -> bool:
    """判断标题行是否匹配目标 heading，允许标题带括号或破折号等补充后缀。"""
    stripped = line.strip()
    if stripped == heading:
        return True
    if stripped.startswith(heading):
        suffix = stripped[len(heading):]
        return suffix[:1] in {"（", "(", " ", "\u3000", "—", "-", "：", ":"}
    return False


def extract_section_after_heading(text: str, heading: str, max_lines: int = 2) -> str:
    """提取某个 Markdown 标题下的首段文本。"""
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if heading_matches(line, heading):
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
        if heading_matches(line, heading):
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


def run_git_command(args: list[str]) -> str:
    """运行只读 git 命令，失败时返回可读提示。"""
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"git unavailable: {exc}"

    output = result.stdout.strip("\r\n") or result.stderr.strip("\r\n")
    if result.returncode != 0:
        return output or f"git exited with {result.returncode}"
    return output


def format_block(items: list[str], fallback: str) -> str:
    """格式化 Markdown 列表片段。"""
    return "\n".join(items) if items else fallback


def parse_status_paths(status_text: str) -> list[str]:
    """从 git status --short 输出提取路径。"""
    paths: list[str] = []
    for line in status_text.splitlines():
        if not line.strip():
            continue
        path = line[3:].strip() if len(line) > 3 else line.strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        paths.append(path.replace("\\", "/"))
    return paths


def detect_lanes(paths: list[str]) -> list[tuple[str, tuple[str, ...]]]:
    """根据脏区路径推断触达开发线和建议命令。"""
    detected: list[tuple[str, tuple[str, ...]]] = []
    for lane, prefixes, commands in LANE_RULES:
        if any(path == prefix or path.startswith(prefix) for path in paths for prefix in prefixes):
            detected.append((lane, commands))
    return detected


def unique_commands(lanes: list[tuple[str, tuple[str, ...]]]) -> list[str]:
    """按出现顺序合并推荐命令。"""
    commands: list[str] = []
    for _, lane_commands in lanes:
        for command in lane_commands:
            if command not in commands:
                commands.append(command)
    return commands


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


def find_brief_resume_heading_gaps() -> list[str]:
    """检查 brief / resume 依赖的标题锚点是否仍存在于目标文档。"""
    warnings: list[str] = []
    for relative_path, heading in BRIEF_RESUME_HEADINGS:
        text = read_text(relative_path)
        if not any(heading_matches(line, heading) for line in text.splitlines()):
            warnings.append(
                f"{relative_path} 缺少 brief/resume 锚点标题 `{heading}`，context:brief/resume 会退化为 fallback"
            )
    return warnings


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
        for required_reference in ["docs/agent_context.md", "docs/current_status.md"]:
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

    agent_context_text = read_text("docs/agent_context.md")
    agent_context_lines = agent_context_text.splitlines()
    if len(agent_context_lines) > 160:
        warnings.append(f"docs/agent_context.md 当前 {len(agent_context_lines)} 行，建议保持在 160 行以内")
    if len(agent_context_text) > 12000:
        warnings.append(f"docs/agent_context.md 当前 {len(agent_context_text)} 字符，建议保持在 12000 字符以内")
    long_lines = [index for index, line in enumerate(agent_context_lines, start=1) if len(line) > 1000]
    if long_lines:
        warnings.append(f"docs/agent_context.md 存在超长行：{', '.join(map(str, long_lines[:5]))}")

    current_status_text = read_text("docs/current_status.md")
    if "人工未验收" not in current_status_text and "manual unverified" not in current_status_text:
        warnings.append("docs/current_status.md 未出现人工未验收标记，请确认人工验收边界是否仍清晰")

    warnings.extend(find_brief_resume_heading_gaps())

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
    status = read_text("docs/current_status.md")

    one_liner = extract_section_after_heading(agent_context, "## 2. 一句话定位", max_lines=1)
    phase_items = extract_bullet_section(status, "## 1. 当前阶段", max_items=6)
    next_steps = extract_bullet_section(agent_context, "## 5. 最近下一步", max_items=5)
    collaboration_notes = extract_bullet_section(agent_context, "## 8. 协作约束", max_items=5)

    return "\n".join(
        [
            "# Loomstead brief",
            "",
            "## 一句话定位",
            "",
            one_liner or "- 未能从 `docs/project_vision.md` 提取定位。",
            "",
            "## 当前阶段",
            "",
            format_block(
                phase_items,
                extract_section_after_heading(status, "## 1. 当前阶段", max_lines=2)
                or "- 未能从 `docs/current_status.md` 提取阶段判断。",
            ),
            "",
            "## 最近下一步",
            "",
            format_block(next_steps, "- 未能从 `docs/agent_context.md` 提取下一步。"),
            "",
            "## 协作参考",
            "",
            format_block(collaboration_notes, "- 未能从 `docs/agent_context.md` 提取协作参考。"),
            "",
            "## 建议下一步",
            "",
            "- 可先读 `AGENTS.md` 和 `docs/agent_context.md`。",
            "- 可按任务线读取对应源文档，当前事实以 `docs/current_status.md` 为准。",
            "- 调整上下文治理后，建议运行 `npm.cmd run context:check` 与 `git diff --check`。",
        ]
    )


def build_resume() -> str:
    """生成跨环境和多助手接续用的短摘要。"""
    agent_context = read_text("docs/agent_context.md")
    status = read_text("docs/current_status.md")

    branch = run_git_command(["branch", "--show-current"]) or "unknown"
    dirty = run_git_command(["status", "--short"])
    recent_commits = run_git_command(["log", "--oneline", "-3"])
    one_liner = extract_section_after_heading(agent_context, "## 2. 一句话定位", max_lines=1)
    current_state = extract_bullet_section(agent_context, "## 3. 当前阶段", max_items=5)
    next_steps = extract_bullet_section(agent_context, "## 5. 最近下一步", max_items=4)
    manual_gates = extract_bullet_section(status, "## 5. 人工验收", max_items=MANUAL_GATE_MAX_ITEMS)
    lane_routes = extract_bullet_section(agent_context, "## 6. 按开发线读取", max_items=7)
    validation = extract_bullet_section(agent_context, "## 7. 验证命令", max_items=10)

    return "\n".join(
        [
            "# Loomstead 接续摘要",
            "",
            "## Git 现场",
            "",
            f"- branch: `{branch}`",
            "- dirty files:",
            "",
            "```text",
            dirty or "clean",
            "```",
            "",
            "- recent commits:",
            "",
            "```text",
            recent_commits or "unavailable",
            "```",
            "",
            "## 项目定位",
            "",
            one_liner or "- 未能从 `docs/project_vision.md` 提取定位。",
            "",
            "## 当前状态",
            "",
            format_block(current_state, "- 未能从 `docs/agent_context.md` 提取当前状态。"),
            "",
            "## 当前 manual gates",
            "",
            format_block(manual_gates, "- 未能从 `docs/current_status.md` 提取人工验收状态。"),
            "",
            "## 最近下一步",
            "",
            format_block(next_steps, "- 未能从 `docs/agent_context.md` 提取下一步。"),
            "",
            "## 任务线入口",
            "",
            format_block(lane_routes, "- 按任务读取 `docs/README.md` 和对应源文档。"),
            "",
            "## 最小验证命令",
            "",
            format_block(validation, "- 先运行 `npm.cmd run context:check`，再按开发线选择命令。"),
            "",
            "## 接续规则",
            "",
            "- 先读 `docs/assistant_continuity.md` 和 `docs/agent_context.md`，再按任务线渐进读取。",
            "- 状态更新必须区分 `code integrated`、`command checked`、`manual verified`、`manual unverified`。",
            "- 真实 LLM、真实 Godot 窗口和玩家手感验收不属于默认离线门禁。",
        ]
    )


def build_handoff() -> str:
    """生成收工交接草稿。"""
    agent_context = read_text("docs/agent_context.md")
    status = read_text("docs/current_status.md")

    branch = run_git_command(["branch", "--show-current"]) or "unknown"
    dirty = run_git_command(["status", "--short"])
    recent_commits = run_git_command(["log", "--oneline", "-3"])
    dirty_paths = parse_status_paths(dirty)
    lanes = detect_lanes(dirty_paths)
    commands = unique_commands(lanes)
    next_steps = extract_bullet_section(agent_context, "## 5. 最近下一步", max_items=4)
    manual_gates = extract_bullet_section(status, "## 5. 人工验收", max_items=MANUAL_GATE_MAX_ITEMS)

    lane_lines = [f"- {lane}" for lane, _ in lanes]
    command_lines = [f"- `{command}`" for command in commands]
    path_lines = [f"- `{path}`" for path in dirty_paths[:30]]
    if len(dirty_paths) > 30:
        path_lines.append(f"- ... and {len(dirty_paths) - 30} more")

    return "\n".join(
        [
            "# Loomstead 收工交接草稿",
            "",
            "## Scope",
            "",
            f"- branch: `{branch}`",
            "- touched lanes:",
            format_block(lane_lines, "- TODO: 填写触达开发线"),
            "- touched files:",
            format_block(path_lines, "- clean working tree or no dirty files detected"),
            "",
            "## Changes",
            "",
            "- TODO: 填写本轮已完成的代码、文档或配置变化。",
            "- TODO: 如修改状态文档，注明对应 code integrated / command checked / manual verified 依据。",
            "",
            "## Verification",
            "",
            "- command checked: TODO: 填写实际运行命令和结果。",
            "- artifact backed: TODO: 填写 manifest / trace / eval run，或写 not-needed。",
            "- manual verified: TODO: 填写真实 Godot / 浏览器 / provider 观察结果，或写 not-run。",
            "- manual unverified: TODO: 填写仍需人工或真实服务确认的内容。",
            "",
            "## Suggested Commands",
            "",
            format_block(command_lines, "- `npm.cmd run context:check`\n- `git diff --check`"),
            "",
            "## Known Manual Gates",
            "",
            format_block(manual_gates, "- TODO: 核对 `docs/current_status.md` 的 manual gate。"),
            "",
            "## Risks",
            "",
            "- TODO: 填写跳过的命令、环境限制、回归风险或并行改动风险。",
            "- 不要把本机绝对路径、私有 key、临时 overlay 或未整理 `.run/` artifact 写入提交态。",
            "",
            "## Next Step",
            "",
            format_block(next_steps, "- TODO: 填写下一位助手可直接执行的最小任务。"),
            "",
            "## Git Snapshot",
            "",
            "```text",
            dirty or "clean",
            "```",
            "",
            "## Recent Commits",
            "",
            "```text",
            recent_commits or "unavailable",
            "```",
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
    parser.add_argument("--resume", action="store_true", help="输出跨环境和多助手接续摘要。")
    parser.add_argument("--handoff", action="store_true", help="输出收工交接草稿。")
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

    if args.resume:
        print()
        print(build_resume())
        return 0

    if args.handoff:
        print()
        print(build_handoff())
        return 0

    print()
    print(build_brief())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
