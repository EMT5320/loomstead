"""统一的环境变量兼容层。

Loomstead 计划长期使用 `LOOMSTEAD_*` 前缀；但为了保留既有脚本、`config/models.local.json`、
本机 smoke 流程等环境的兼容性，旧的 `AGENT_TOWN_*` 前缀仍作为 fallback 保留。

新代码请优先读取本模块函数；不要再直接 `os.getenv("AGENT_TOWN_*")`。
"""

from __future__ import annotations

import os


# 长期前缀 → 兼容旧前缀。第一个值优先生效。
LOOM_TO_LEGACY = {
    "LOOMSTEAD_MODEL_CONFIG": "AGENT_TOWN_MODEL_CONFIG",
    "LOOMSTEAD_PROVIDER": "AGENT_TOWN_PROVIDER",
    "LOOMSTEAD_API_KEY": "AGENT_TOWN_API_KEY",
    "LOOMSTEAD_BASE_URL": "AGENT_TOWN_BASE_URL",
    "LOOMSTEAD_MODEL": "AGENT_TOWN_MODEL",
    "LOOMSTEAD_TEMPERATURE": "AGENT_TOWN_TEMPERATURE",
    "LOOMSTEAD_REQUIRE_REAL_LLM_SMOKE": "AGENT_TOWN_REQUIRE_REAL_LLM_SMOKE",
    "LOOMSTEAD_ENABLE_REAL_LLM_SMOKE": "AGENT_TOWN_ENABLE_REAL_LLM_SMOKE",
    "LOOMSTEAD_HTTP_LOG": "AGENT_TOWN_HTTP_LOG",
    "LOOMSTEAD_NEVER_SET_API_KEY": "AGENT_TOWN_NEVER_SET_API_KEY",
}

# 反向索引：从旧前缀查长期前缀，便于 set_compat_env 同步赋值。
LEGACY_TO_LOOM = {legacy: loom for loom, legacy in LOOM_TO_LEGACY.items()}


def loom_env(name: str, default: str | None = None) -> str | None:
    """读取 Loomstead 长期环境变量，自动 fallback 到旧 `AGENT_TOWN_*` 前缀。

    name 必须是 `LOOMSTEAD_*` 形式；调用者应该优先使用新名。
    """
    if name in os.environ:
        return os.environ[name]
    legacy = LOOM_TO_LEGACY.get(name)
    if legacy and legacy in os.environ:
        return os.environ[legacy]
    return default


def loom_env_truthy(name: str) -> bool:
    """常见 truthy 值（1 / true / yes）判定，含旧前缀兼容。"""
    return str(loom_env(name) or "").lower() in {"1", "true", "yes"}


def known_secret_env_names() -> tuple[str, ...]:
    """供日志脱敏使用的密钥环境变量名，统一来源。"""
    return ("OPENAI_API_KEY", "DEEPSEEK_API_KEY", "LOOMSTEAD_API_KEY", "AGENT_TOWN_API_KEY")
