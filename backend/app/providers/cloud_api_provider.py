from __future__ import annotations

import json
import os
import time
from typing import Any, Callable
from urllib.error import HTTPError
import urllib.request

from app.config.env_compat import loom_env


MILLION_TOKENS = 1_000_000


DEEPSEEK_PRICING_BY_MODEL: dict[str, dict[str, Any]] = {
    # 价格来自 DeepSeek 官方价格页，按 2026-05-16 的 V4 Flash 公开价格估算调试成本。
    "deepseek-v4-flash": {
        "currency": "USD",
        "inputCacheHitPerMillionTokens": 0.0028,
        "inputCacheMissPerMillionTokens": 0.14,
        "outputPerMillionTokens": 0.28,
        "source": "deepseek_official_2026_05_16",
    },
    # DeepSeek 官方说明 deepseek-chat 兼容映射到 V4 Flash 非思考模式。
    "deepseek-chat": {
        "currency": "USD",
        "inputCacheHitPerMillionTokens": 0.0028,
        "inputCacheMissPerMillionTokens": 0.14,
        "outputPerMillionTokens": 0.28,
        "source": "deepseek_official_2026_05_16",
    },
}


class CloudApiProvider:
    """OpenAI-compatible 云端 Provider，按模型 Profile 发起调用。"""

    name = "CloudApiProvider"

    def decide(
        self,
        _context: dict[str, Any],
        messages: list[dict[str, str]],
        profile: dict[str, Any] | None = None,
        output_parser: Callable[[str], dict[str, Any] | None] | None = None,
    ) -> dict[str, Any]:
        """使用传入 Profile 调用模型，支持不同 NPC 或功能使用不同模型。"""
        profile = profile or {}
        api_key_env = profile.get("apiKeyEnv") or "DEEPSEEK_API_KEY"
        inline_api_key = str(api_key_env) if self._looks_like_inline_secret(api_key_env) else None
        api_key = (
            profile.get("apiKey")
            or inline_api_key
            or os.getenv(str(api_key_env))
            or loom_env("LOOMSTEAD_API_KEY")
            or os.getenv("OPENAI_API_KEY")
        )
        if not api_key:
            safe_api_key_env = "[redacted-inline-secret]" if self._looks_like_inline_secret(api_key_env) else api_key_env
            raise RuntimeError(f"CloudApiProvider 缺少 API Key，请设置 {safe_api_key_env}、LOOMSTEAD_API_KEY (兼容 AGENT_TOWN_API_KEY) 或 OPENAI_API_KEY。")

        base_url = str(profile.get("baseUrl") or "https://api.deepseek.com").rstrip("/")
        model = str(profile.get("model") or "deepseek-chat")
        timeout = int(profile.get("timeoutSeconds", 60))
        payload_data = {
            "model": model,
            "messages": messages,
            "temperature": float(profile.get("temperature", 0.8)),
        }
        if profile.get("maxTokens"):
            # OpenAI-compatible 接口常用 max_tokens 字段。
            payload_data["max_tokens"] = self._safe_max_tokens(profile, model)
        response_format = profile.get("responseFormat") or profile.get("response_format")
        if isinstance(response_format, dict) and response_format:
            payload_data["response_format"] = response_format
        elif profile.get("jsonMode"):
            payload_data["response_format"] = {"type": "json_object"}

        started = time.time()
        payload = json.dumps(payload_data, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            f"{base_url}/chat/completions",
            data=payload,
            headers={"content-type": "application/json", "authorization": f"Bearer {api_key}"},
            method="POST",
        )
        data = self._send_request(request, timeout=timeout)
        raw_text = str(data.get("choices", [{}])[0].get("message", {}).get("content", "") or "")
        latency_ms = int((time.time() - started) * 1000)
        usage_data = data.get("usage", {}) if isinstance(data.get("usage"), dict) else {}
        parsed = output_parser(raw_text) if output_parser else None
        return {
            "provider": self.name,
            "rawText": raw_text,
            "parsed": parsed,
            "usage": self._usage_payload(usage_data, profile=profile, model=model, latency_ms=latency_ms),
        }

    def _send_request(self, request: urllib.request.Request, *, timeout: int) -> dict[str, Any]:
        """发送 HTTP 请求并把供应商错误压成可记录摘要。"""
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - 本地开发工具按用户配置调用云端
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"CloudApiProvider HTTP {error.code}: {self._short_error_body(body)}") from error

    def _usage_payload(self, usage_data: dict[str, Any], *, profile: dict[str, Any], model: str, latency_ms: int) -> dict[str, Any]:
        """统一整理 tokens、延迟和估算成本，供 Debug 视图直接展示。"""
        prompt_tokens = self._int_usage(usage_data, "prompt_tokens")
        completion_tokens = self._int_usage(usage_data, "completion_tokens")
        total_tokens = self._int_usage(usage_data, "total_tokens") or prompt_tokens + completion_tokens
        cache_hit_tokens = self._int_usage(usage_data, "prompt_cache_hit_tokens")
        cache_miss_tokens = self._int_usage(usage_data, "prompt_cache_miss_tokens")
        if prompt_tokens and not cache_hit_tokens and not cache_miss_tokens:
            cache_miss_tokens = prompt_tokens

        cost_payload = self._estimate_cost(
            profile=profile,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cache_hit_tokens=cache_hit_tokens,
            cache_miss_tokens=cache_miss_tokens,
        )
        return {
            "tokens": total_tokens,
            "promptTokens": prompt_tokens,
            "completionTokens": completion_tokens,
            "cacheHitPromptTokens": cache_hit_tokens,
            "cacheMissPromptTokens": cache_miss_tokens,
            "cost": cost_payload["total"],
            "costInput": cost_payload["input"],
            "costOutput": cost_payload["output"],
            "costEstimated": cost_payload["available"],
            "currency": cost_payload["currency"],
            "pricing": cost_payload["pricing"],
            "latencyMs": latency_ms,
            "model": model,
            "profileName": profile.get("profileName"),
        }

    def _estimate_cost(
        self,
        *,
        profile: dict[str, Any],
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        cache_hit_tokens: int,
        cache_miss_tokens: int,
    ) -> dict[str, Any]:
        """按 profile 或内置 DeepSeek V4 Flash 价格估算本次调用成本。"""
        pricing = self._pricing_for_profile(profile, model)
        if not pricing:
            return {"available": False, "currency": None, "input": 0, "output": 0, "total": 0, "pricing": None}

        hit_rate = float(pricing.get("inputCacheHitPerMillionTokens", pricing.get("inputPerMillionTokens", 0)) or 0)
        miss_rate = float(pricing.get("inputCacheMissPerMillionTokens", pricing.get("inputPerMillionTokens", 0)) or 0)
        output_rate = float(pricing.get("outputPerMillionTokens", 0) or 0)
        input_cost = (cache_hit_tokens * hit_rate + cache_miss_tokens * miss_rate) / MILLION_TOKENS
        output_cost = completion_tokens * output_rate / MILLION_TOKENS
        return {
            "available": True,
            "currency": pricing.get("currency") or "USD",
            "input": round(input_cost, 8),
            "output": round(output_cost, 8),
            "total": round(input_cost + output_cost, 8),
            "pricing": pricing,
        }

    def _pricing_for_profile(self, profile: dict[str, Any], model: str) -> dict[str, Any] | None:
        """优先使用 profile 显式价格，缺省时识别当前 DeepSeek Flash 兼容模型。"""
        pricing = profile.get("pricing")
        if isinstance(pricing, dict) and pricing:
            return dict(pricing)
        return DEEPSEEK_PRICING_BY_MODEL.get(model)

    def _safe_max_tokens(self, profile: dict[str, Any], model: str) -> int:
        """限制 max_tokens 到供应商可接受范围，避免把上下文长度误填为输出长度。"""
        requested = int(profile.get("maxTokens") or 0)
        if requested <= 0:
            return requested
        limit = int(profile.get("maxOutputTokensLimit") or self._known_max_output_tokens(model) or requested)
        return min(requested, limit)

    def _known_max_output_tokens(self, model: str) -> int | None:
        """内置当前 DeepSeek V4 输出上限，模板仍可通过 maxOutputTokensLimit 覆盖。"""
        if model in {"deepseek-v4-flash", "deepseek-v4-pro", "deepseek-chat", "deepseek-reasoner"}:
            return 393_216
        return None

    def _int_usage(self, usage_data: dict[str, Any], key: str) -> int:
        """容错读取供应商 usage 数字字段。"""
        try:
            return int(usage_data.get(key, 0) or 0)
        except (TypeError, ValueError):
            return 0

    def _looks_like_inline_secret(self, value: Any) -> bool:
        """识别常见 API key 前缀，避免误填 apiKeyEnv 时真实调用失败。"""
        text = str(value or "")
        return text.startswith(("sk-", "sk_", "sk-proj-"))

    def _short_error_body(self, body: str, limit: int = 600) -> str:
        """压缩供应商错误正文，避免事件流塞入过长 HTML 或 JSON。"""
        normalized = " ".join(str(body or "").split())
        return normalized if len(normalized) <= limit else normalized[: limit - 1] + "…"
