from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
from typing import Any


DEFAULT_CONFIG: dict[str, Any] = {
    "activeProvider": "rule",
    "defaultProfile": "default_deepseek",
    "profiles": {
        "default_deepseek": {
            "provider": "cloud",
            "baseUrl": "https://api.deepseek.com",
            "apiKeyEnv": "DEEPSEEK_API_KEY",
            "model": "deepseek-v4-flash",
            "temperature": 0.8,
            "maxTokens": 900,
            "timeoutSeconds": 60,
        },
        "rule_fallback": {"provider": "rule"},
    },
    "npcProfiles": {},
    "featureProfiles": {"agent_decision": "default_deepseek"},
    "fallbackProfile": "rule_fallback",
}


class ModelConfigStore:
    """模型配置中心，负责按功能和 NPC 解析最终模型 Profile。"""

    def __init__(self, config_path: str | None = None) -> None:
        self.config_path = Path(config_path or os.getenv("AGENT_TOWN_MODEL_CONFIG", "config/models.json"))
        self.local_config_path = self.config_path.with_name("models.local.json")
        self.config = self._load_config()

    def reload(self) -> dict[str, Any]:
        """重新读取公开配置和本地私密覆盖，供长运行服务热重载。"""
        self.config = self._load_config()
        return self.public_config()

    def _load_config(self) -> dict[str, Any]:
        """读取 JSON 配置，并叠加本地私密覆盖文件。"""
        config = deepcopy(DEFAULT_CONFIG)
        if self.config_path.exists():
            config = self._deep_merge(config, self._read_json(self.config_path))
        if self.local_config_path.exists():
            config = self._deep_merge(config, self._read_json(self.local_config_path))
        return config

    def _read_json(self, path: Path) -> dict[str, Any]:
        """读取 UTF-8/UTF-8 BOM JSON 文件。"""
        with path.open("r", encoding="utf-8-sig") as file:
            return json.load(file)

    def _deep_merge(self, base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        """递归合并配置，支持只覆盖某个 profile 的少数字段。"""
        result = deepcopy(base)
        for key, value in override.items():
            if isinstance(value, dict) and isinstance(result.get(key), dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = deepcopy(value)
        return result

    def active_provider(self) -> str:
        """读取当前全局 Provider 模式，环境变量拥有最高优先级。"""
        return os.getenv("AGENT_TOWN_PROVIDER", self.config.get("activeProvider", "rule"))

    def resolve_profile(self, agent_id: str | None = None, feature: str = "agent_decision") -> dict[str, Any]:
        """按 NPC > 功能 > 默认 的顺序选择模型 Profile。"""
        profiles = self.config.get("profiles", {})
        profile_name = None
        if agent_id:
            profile_name = self.config.get("npcProfiles", {}).get(agent_id)
        if not profile_name:
            profile_name = self.config.get("featureProfiles", {}).get(feature)
        if not profile_name:
            profile_name = self.config.get("defaultProfile")
        profile = deepcopy(profiles.get(profile_name, {}))
        if not profile:
            fallback_name = self.config.get("fallbackProfile", "rule_fallback")
            profile = deepcopy(profiles.get(fallback_name, {"provider": "rule"}))
            profile_name = fallback_name
        profile["profileName"] = profile_name
        return self._apply_env_overrides(profile)

    def fallback_profile(self) -> dict[str, Any]:
        """返回规则兜底 Profile。"""
        fallback_name = self.config.get("fallbackProfile", "rule_fallback")
        profile = deepcopy(self.config.get("profiles", {}).get(fallback_name, {"provider": "rule"}))
        profile["profileName"] = fallback_name
        return profile

    def public_config(self) -> dict[str, Any]:
        """输出可展示配置，隐藏密钥，仅保留密钥是否已配置。"""
        config = deepcopy(self.config)
        config["configPath"] = str(self.config_path)
        config["localConfigPath"] = str(self.local_config_path)
        config["localConfigLoaded"] = self.local_config_path.exists()
        config["validation"] = self.validate()
        profiles = config.get("profiles", {})
        if isinstance(profiles, dict):
            for profile in profiles.values():
                if not isinstance(profile, dict):
                    continue
                profile["apiKeyConfigured"] = self._profile_key_configured(profile)
                if self._looks_like_inline_secret(profile.get("apiKeyEnv")):
                    # 兼容把真实 key 误填到 apiKeyEnv 的本地配置，同时避免 Web 面板泄漏。
                    profile["apiKeyEnv"] = "[redacted-inline-secret]"
                profile.pop("apiKey", None)
        return config

    def validate(self) -> dict[str, Any]:
        """校验模型配置结构，给命令行和 Web 配置面板提供同一套诊断结果。"""
        errors: list[str] = []
        warnings: list[str] = []
        profiles = self.config.get("profiles")
        if not isinstance(profiles, dict) or not profiles:
            errors.append("profiles 必须是非空对象。")
            profiles = {}

        active_provider = self.config.get("activeProvider", "rule")
        if active_provider not in {"rule", "cloud", "auto"}:
            errors.append("activeProvider 只支持 rule、cloud 或 auto。")

        for field in ("defaultProfile", "fallbackProfile"):
            profile_name = self.config.get(field)
            if not profile_name:
                errors.append(f"{field} 不能为空。")
            elif profile_name not in profiles:
                errors.append(f"{field} 指向不存在的 profile：{profile_name}。")

        for mapping_name in ("npcProfiles", "featureProfiles"):
            mapping = self.config.get(mapping_name, {})
            if not isinstance(mapping, dict):
                errors.append(f"{mapping_name} 必须是对象。")
                continue
            for key, profile_name in mapping.items():
                if profile_name not in profiles:
                    errors.append(f"{mapping_name}.{key} 指向不存在的 profile：{profile_name}。")

        for profile_name, profile in profiles.items():
            if not isinstance(profile, dict):
                errors.append(f"profiles.{profile_name} 必须是对象。")
                continue
            provider = profile.get("provider", "cloud")
            if provider not in {"rule", "cloud", "local"}:
                errors.append(f"profiles.{profile_name}.provider 不受支持：{provider}。")
                continue
            if provider != "cloud":
                continue
            if not profile.get("baseUrl"):
                warnings.append(f"profiles.{profile_name} 未配置 baseUrl，将使用 Provider 默认值。")
            if not profile.get("model"):
                warnings.append(f"profiles.{profile_name} 未配置 model，将使用 Provider 默认值。")
            if not profile.get("apiKeyEnv") and not profile.get("apiKey"):
                warnings.append(f"profiles.{profile_name} 未配置 apiKeyEnv 或本地 apiKey，真实调用会依赖 OPENAI_API_KEY 兜底。")
            if self._looks_like_inline_secret(profile.get("apiKeyEnv")):
                warnings.append(f"profiles.{profile_name}.apiKeyEnv 看起来像真实密钥，建议改为 apiKey 或环境变量名。")
            self._validate_number(profile_name, profile, "temperature", errors, warnings, minimum=0, maximum=2)
            self._validate_number(profile_name, profile, "maxTokens", errors, warnings, minimum=1)
            self._validate_number(profile_name, profile, "timeoutSeconds", errors, warnings, minimum=1)

        return {"ok": not errors, "errors": errors, "warnings": warnings}

    def _profile_key_configured(self, profile: dict[str, Any]) -> bool:
        """只返回密钥是否存在，不向公开配置泄漏真实密钥。"""
        has_inline_key = bool(profile.get("apiKey"))
        env_name = profile.get("apiKeyEnv")
        if self._looks_like_inline_secret(env_name):
            return True
        env_configured = bool(os.getenv(str(env_name))) if env_name else False
        if profile.get("provider") == "cloud":
            env_configured = env_configured or bool(os.getenv("AGENT_TOWN_API_KEY")) or bool(os.getenv("OPENAI_API_KEY"))
        return has_inline_key or env_configured

    def _looks_like_inline_secret(self, value: Any) -> bool:
        """识别误填进公开字段的密钥形态，用于本地保护和展示脱敏。"""
        text = str(value or "")
        return text.startswith(("sk-", "sk_", "sk-proj-"))

    def _validate_number(
        self,
        profile_name: str,
        profile: dict[str, Any],
        field: str,
        errors: list[str],
        warnings: list[str],
        *,
        minimum: float | None = None,
        maximum: float | None = None,
    ) -> None:
        """检查数值字段，避免一次配置错误拖垮后续 LLM smoke。"""
        if field not in profile:
            return
        value = profile[field]
        if not isinstance(value, int | float):
            errors.append(f"profiles.{profile_name}.{field} 必须是数字。")
            return
        if minimum is not None and value < minimum:
            errors.append(f"profiles.{profile_name}.{field} 必须大于等于 {minimum}。")
        if maximum is not None and value > maximum:
            warnings.append(f"profiles.{profile_name}.{field} 当前为 {value}，请确认供应商是否支持。")

    def _apply_env_overrides(self, profile: dict[str, Any]) -> dict[str, Any]:
        """兼容早期环境变量，方便主人临时覆盖模型。"""
        if profile.get("provider") == "cloud":
            profile["baseUrl"] = os.getenv("AGENT_TOWN_BASE_URL", profile.get("baseUrl", "https://api.deepseek.com"))
            profile["model"] = os.getenv("AGENT_TOWN_MODEL", profile.get("model", "deepseek-v4-flash"))
            if os.getenv("AGENT_TOWN_TEMPERATURE"):
                profile["temperature"] = float(os.getenv("AGENT_TOWN_TEMPERATURE", "0.8"))
        return profile
