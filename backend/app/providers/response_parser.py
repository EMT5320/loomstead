from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from app.providers.provider_support import FEATURE_AGENT_DECISION, FEATURE_DIALOGUE, FEATURE_EVENT_REACTION, FEATURE_NIGHT_REFLECTION


@dataclass(slots=True)
class ParsedResponse:
    """结构化解析结果，包含最终输出和兜底原因。"""

    parsed: dict[str, Any]
    fallback_reason: str | None


def parse_agent_decision_response(result: dict[str, Any]) -> ParsedResponse:
    """兼容旧决策流的解析入口。"""
    return parse_feature_response(result, FEATURE_AGENT_DECISION)


def parse_feature_response(result: dict[str, Any], feature: str) -> ParsedResponse:
    """按功能解析云端输出，优先 JSON，失败时回退自然语言。"""
    existing = result.get("parsed")
    if isinstance(existing, dict) and existing:
        normalized = _normalize_feature_fields(existing, feature)
        if _is_feature_payload_valid(normalized, feature):
            return ParsedResponse(parsed=normalized, fallback_reason=None)
        return ParsedResponse(parsed=_natural_language_fallback(result.get("rawText"), feature), fallback_reason="parsed_missing_required_fields")

    raw_text = str(result.get("rawText") or "").strip()
    candidate = _extract_json_object(raw_text)
    if isinstance(candidate, dict):
        normalized = _normalize_feature_fields(candidate, feature)
        if _is_feature_payload_valid(normalized, feature):
            return ParsedResponse(parsed=normalized, fallback_reason=None)
        return ParsedResponse(parsed=_natural_language_fallback(raw_text, feature), fallback_reason="json_missing_required_fields")
    return ParsedResponse(parsed=_natural_language_fallback(raw_text, feature), fallback_reason="natural_language_fallback")


def build_provider_debug_payload(
    *,
    provider_mode: str,
    profile_name: str | None,
    api_key_configured: bool,
    messages: list[dict[str, str]],
    raw_text: str,
    parsed: dict[str, Any],
    usage: dict[str, Any] | None,
    fallback_reason: str | None,
) -> dict[str, Any]:
    """构建统一 debug 字段，便于前后端按固定键展示。"""
    usage_payload = dict(usage or {})
    latency_ms = int(usage_payload.get("latencyMs", 0) or 0)
    return {
        "providerMode": provider_mode,
        "profileName": profile_name,
        "apiKeyConfigured": api_key_configured,
        "messages": messages,
        "rawText": raw_text,
        "parsed": parsed,
        "usage": usage_payload,
        "latency": {"ms": latency_ms},
        "fallbackReason": fallback_reason,
    }


def _extract_json_object(raw_text: str) -> dict[str, Any] | None:
    """从纯文本或 Markdown 代码块中提取首个 JSON 对象。"""
    if not raw_text:
        return None
    direct = _try_json_loads(raw_text)
    if isinstance(direct, dict):
        return direct

    fenced = _extract_fenced_block(raw_text)
    if fenced:
        fenced_json = _try_json_loads(fenced)
        if isinstance(fenced_json, dict):
            return fenced_json

    snippet = _find_balanced_braces(raw_text)
    if snippet:
        snippet_json = _try_json_loads(snippet)
        if isinstance(snippet_json, dict):
            return snippet_json
    return None


def _extract_fenced_block(raw_text: str) -> str:
    marker = "```"
    start = raw_text.find(marker)
    if start < 0:
        return ""
    end = raw_text.find(marker, start + len(marker))
    if end < 0:
        return ""
    block = raw_text[start + len(marker) : end].strip()
    if "\n" in block and block.split("\n", 1)[0].strip().lower() in {"json", "javascript", "js"}:
        return block.split("\n", 1)[1].strip()
    return block


def _find_balanced_braces(raw_text: str) -> str:
    start = raw_text.find("{")
    while start >= 0:
        depth = 0
        for index in range(start, len(raw_text)):
            char = raw_text[index]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return raw_text[start : index + 1]
        start = raw_text.find("{", start + 1)
    return ""


def _try_json_loads(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _normalize_feature_fields(payload: dict[str, Any], feature: str) -> dict[str, Any]:
    payload = _unwrap_feature_payload(payload)
    if feature == FEATURE_DIALOGUE:
        if "memory" in payload and "memory_to_save" not in payload:
            payload = dict(payload)
            payload["memory_to_save"] = payload.get("memory")
        if "memoryToSave" in payload and "memory_to_save" not in payload:
            payload = dict(payload)
            payload["memory_to_save"] = payload.get("memoryToSave")
        if "speech" not in payload:
            speech = _first_speech_from_lines(payload.get("dialogue")) or _first_speech_from_lines(payload.get("lines"))
            if speech:
                payload = dict(payload)
                payload["speech"] = speech
        if payload.get("speech") and "memory_to_save" not in payload:
            # 云端模型有时会返回 event_reaction 形态的 dialogue/lines；这里保留结构化结果，
            # 并用已解析台词生成一条可保存的主观记忆，避免真实 smoke 被误判为自然语言兜底。
            payload = dict(payload)
            payload["memory_to_save"] = f"我和玩家聊到：{str(payload.get('speech'))[:80]}"
    if feature == FEATURE_EVENT_REACTION:
        if "lines" in payload and "dialogue" not in payload:
            payload = dict(payload)
            payload["dialogue"] = payload.get("lines")
    if feature == FEATURE_NIGHT_REFLECTION:
        if "nightReflection" in payload and "reflections" not in payload:
            payload = dict(payload)
            payload["reflections"] = payload.get("nightReflection")
        if "reflection" in payload and "reflections" not in payload:
            payload = dict(payload)
            payload["reflections"] = [{"agentId": payload.get("agentId") or "unknown", "text": payload.get("reflection")}]
    return payload


def _unwrap_feature_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """兼容模型把结构化结果包在 response/result/output 下的情况。"""
    for key in ("response", "result", "output"):
        nested = payload.get(key)
        if isinstance(nested, dict):
            return nested
    return payload


def _first_speech_from_lines(value: Any) -> str:
    """从 dialogue/lines 风格数组里提取第一条可展示台词。"""
    if not isinstance(value, list):
        return ""
    for item in value:
        if not isinstance(item, dict):
            continue
        speech = item.get("speech") or item.get("text") or item.get("line")
        if speech:
            return str(speech)
    return ""


def _is_feature_payload_valid(payload: dict[str, Any], feature: str) -> bool:
    if feature == FEATURE_EVENT_REACTION:
        dialogue = payload.get("dialogue")
        return isinstance(dialogue, list) and any(isinstance(item, dict) and item.get("agentId") and item.get("speech") for item in dialogue)
    if feature == FEATURE_NIGHT_REFLECTION:
        reflections = payload.get("reflections")
        return isinstance(reflections, list) and any(isinstance(item, dict) and item.get("agentId") and item.get("text") for item in reflections)
    required_fields = _required_fields(feature)
    return all(bool(payload.get(field)) for field in required_fields)


def _required_fields(feature: str) -> tuple[str, ...]:
    if feature == FEATURE_DIALOGUE:
        return ("speech", "memory_to_save")
    if feature == FEATURE_EVENT_REACTION:
        return ("dialogue",)
    if feature == FEATURE_NIGHT_REFLECTION:
        return ("reflections",)
    if feature == FEATURE_AGENT_DECISION:
        return ("speech", "action")
    return ("speech",)


def _natural_language_fallback(raw_text: str | None, feature: str) -> dict[str, Any]:
    text = str(raw_text or "").strip()
    if feature == FEATURE_DIALOGUE:
        speech = text or "我在想怎么回应你，让我们慢慢熟悉彼此。"
        return {"speech": speech, "memory_to_save": f"我和玩家聊到了：{speech[:80]}"}
    if feature == FEATURE_EVENT_REACTION:
        reaction = text or "这件事让我紧张，我们得先稳住局面。"
        return {"dialogue": [{"agentId": "unknown", "speech": reaction}]}
    if feature == FEATURE_NIGHT_REFLECTION:
        reflection = text or "今晚的信息很多，我决定先整理情绪和线索。"
        return {"reflections": [{"agentId": "unknown", "text": reflection}]}
    if feature == FEATURE_AGENT_DECISION:
        speech = text or "沉默片刻，继续观察小镇。"
        return {"speech": speech, "action": "remember", "args": {}, "memory_to_save": speech[:120]}
    return {"speech": text or "沉默片刻。"}
