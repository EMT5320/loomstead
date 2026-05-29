from __future__ import annotations

import os
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from app.config.env_compat import loom_env


FEATURE_AGENT_DECISION = "agent_decision"
FEATURE_DIALOGUE = "dialogue"
FEATURE_EVENT_REACTION = "event_reaction"
FEATURE_NIGHT_REFLECTION = "night_reflection"


@dataclass(slots=True)
class FeatureProfileSelection:
    """记录一次功能级模型 Profile 选择路径，便于复用和调试。"""

    feature: str
    provider_mode: str
    selected_provider: str
    profile: dict[str, Any]
    profile_name: str | None
    api_key_configured: bool


def resolve_feature_profile(
    *,
    model_config: Any,
    feature: str,
    agent_id: str | None,
    provider_mode: str,
) -> FeatureProfileSelection:
    """按功能解析 profile，并产出统一可调试选择结果。"""
    profile = deepcopy(model_config.resolve_profile(agent_id=agent_id, feature=feature))
    effective_provider_mode = provider_mode if provider_mode != "auto" else str(profile.get("provider") or "rule")
    selected_provider = "cloud" if effective_provider_mode == "cloud" and str(profile.get("provider") or "rule") == "cloud" else "rule"
    return FeatureProfileSelection(
        feature=feature,
        provider_mode=effective_provider_mode,
        selected_provider=selected_provider,
        profile=profile,
        profile_name=profile.get("profileName"),
        api_key_configured=is_profile_api_key_configured(profile),
    )


def is_profile_api_key_configured(profile: dict[str, Any]) -> bool:
    """判断 profile 对应密钥是否可用，不返回实际密钥。"""
    if profile.get("apiKey"):
        return True
    env_name = profile.get("apiKeyEnv")
    if _looks_like_inline_secret(env_name):
        return True
    if env_name:
        return bool(os.getenv(str(env_name))) or bool(loom_env("LOOMSTEAD_API_KEY")) or bool(os.getenv("OPENAI_API_KEY"))
    return bool(loom_env("LOOMSTEAD_API_KEY")) or bool(os.getenv("OPENAI_API_KEY"))


def sanitize_profile_for_debug(profile: dict[str, Any]) -> dict[str, Any]:
    """用于 debug 展示的 profile 副本，移除密钥并补充状态。"""
    safe_profile = deepcopy(profile)
    safe_profile.pop("apiKey", None)
    if _looks_like_inline_secret(safe_profile.get("apiKeyEnv")):
        safe_profile["apiKeyEnv"] = "[redacted-inline-secret]"
    safe_profile["apiKeyConfigured"] = is_profile_api_key_configured(profile)
    return safe_profile


def _looks_like_inline_secret(value: Any) -> bool:
    """识别常见 API key 前缀，供 Debug 脱敏和状态判断复用。"""
    text = str(value or "")
    return text.startswith(("sk-", "sk_", "sk-proj-"))
