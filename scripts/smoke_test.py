"""Python 后端 smoke test。"""

from pathlib import Path
from http.server import ThreadingHTTPServer
import json
import os
import sys
import tempfile
from threading import Thread
from types import MethodType
from urllib.parse import urlencode
from urllib.request import Request, urlopen

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

# Windows PowerShell 通过 npm 运行 Python 时可能出现输出编码漂移，统一用 UTF-8 输出。
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app.director import DirectorBeat, WorldDigest  # noqa: E402
from app.config.model_config import ModelConfigStore  # noqa: E402
from app.main import create_handler, create_town_app  # noqa: E402
from app.providers.context_builder import (  # noqa: E402
    build_player_dialogue_context,
    validate_gossip_propagation_payload,
)
from app.runtime.need_accumulator import NeedAccumulator  # noqa: E402
from app.skills import STARLIGHT_FESTIVAL_SHORTAGE_SKILL_ID  # noqa: E402

REQUIRED_DEBUG_FIELDS = {
    "providerMode",
    "profileName",
    "apiKeyConfigured",
    "messages",
    "rawText",
    "parsed",
    "usage",
    "latency",
    "fallbackReason",
}

REQUIRED_LLM_USAGE_FIELDS = {
    "tokens",
    "promptTokens",
    "completionTokens",
    "cost",
    "costEstimated",
    "latencyMs",
    "model",
    "profileName",
}

REQUIRED_CLIENT_CONTEXT_FIELDS = {
    "memoryEvidence",
    "relationshipEvidence",
    "playerProfile",
    "currentObjective",
    "availableInteractions",
}

REQUIRED_GAME_STATE_FIELDS = {
    "clock",
    "player",
    "playerAnchor",
    "locations",
    "anchors",
    "interactables",
    "npcPresence",
    "farmPlots",
    "npcs",
    "activeEvents",
    "completedEvents",
    "nightReflections",
    "npcSchedules",
    "lifeActionPlan",
    "recentEvents",
    "slice",
    "townStats",
}

REQUIRED_DEBUG_SNAPSHOT_FIELDS = {
    "clock",
    "providerMode",
    "director",
    "skills",
    "debugTurns",
    "memory",
    "playerProfile",
    "providerFallbacks",
    "phase2",
    "influenceChain",
}

REQUIRED_DEBUG_TURN_FIELDS = {
    "eventId",
    "eventType",
    "createdAt",
    "feature",
    "providerMode",
    "profileName",
    "latency",
    "summary",
    "debug",
}

REQUIRED_MEMORY_SEARCH_FIELDS = {"query", "agentId", "tags", "limit", "items"}
REQUIRED_MEMORY_ITEM_FIELDS = {"agentId", "agentName", "tick", "importance", "tags", "text", "match"}
REQUIRED_ACTION_FEEDBACK_FIELDS = {"title", "summary", "locationId", "anchorId", "resultType", "changedResources", "eventIds"}
REQUIRED_NPC_SCHEDULE_FIELDS = {
    "npcId",
    "day",
    "phase",
    "generatedAtTick",
    "locationId",
    "anchorId",
    "presenceSource",
    "activeLifeAction",
    "lifeActionCandidates",
    "rumorBeatCandidates",
    "relationshipBeatCandidates",
    "worldMutationPolicy",
}


def assert_no_inline_api_key(payload: object, label: str, path: str = "") -> None:
    """确认公开 API 响应没有返回真实 apiKey 字段。"""
    if isinstance(payload, dict):
        for key, value in payload.items():
            child_path = f"{path}.{key}" if path else str(key)
            if key == "apiKey":
                raise RuntimeError(f"{label} 泄漏 apiKey 字段：{child_path}")
            if isinstance(value, str) and value.startswith(("sk-", "sk_", "sk-proj-")):
                raise RuntimeError(f"{label} 泄漏疑似密钥字符串：{child_path}")
            assert_no_inline_api_key(value, label, child_path)
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            assert_no_inline_api_key(value, label, f"{path}[{index}]")
    elif isinstance(payload, str) and payload.startswith(("sk-", "sk_", "sk-proj-")):
        raise RuntimeError(f"{label} 泄漏疑似密钥字符串：{path}")


def assert_model_config_contract(payload: dict, label: str) -> None:
    """确认模型配置公开响应可用于 UI 展示且不泄漏密钥。"""
    for field in ("activeProvider", "defaultProfile", "profiles", "featureProfiles", "fallbackProfile", "validation"):
        if field not in payload:
            raise RuntimeError(f"{label} 缺少字段：{field}")
    if not isinstance(payload["profiles"], dict) or not payload["profiles"]:
        raise RuntimeError(f"{label}.profiles 应为非空对象")
    validation = payload["validation"]
    if not isinstance(validation, dict) or "ok" not in validation or "errors" not in validation or "warnings" not in validation:
        raise RuntimeError(f"{label}.validation 应包含 ok、errors、warnings")
    if not validation["ok"]:
        raise RuntimeError(f"{label}.validation 应通过：{validation['errors']}")
    assert_no_inline_api_key(payload, label)


def assert_feature_debug(state: dict, feature: str) -> dict:
    """确认指定 feature 生成了本轮 LLM 验证要求的 Debug 字段。"""
    events = state.get("recentEvents") or state.get("events") or []
    debug_events = [
        event
        for event in events
        if event["type"] == "debug.turn_recorded" and event["payload"].get("debug", {}).get("feature") == feature
    ]
    if not debug_events:
        raise RuntimeError(f"{feature} 应写入 debug.turn_recorded")
    debug = debug_events[-1]["payload"]["debug"]
    missing = sorted(REQUIRED_DEBUG_FIELDS - set(debug))
    if missing:
        raise RuntimeError(f"{feature} Debug 缺少字段：{missing}")
    if not isinstance(debug["messages"], list) or not debug["messages"]:
        raise RuntimeError(f"{feature} Debug messages 应为非空数组")
    if not isinstance(debug["parsed"], dict):
        raise RuntimeError(f"{feature} Debug parsed 应为对象")
    if not isinstance(debug["usage"], dict):
        raise RuntimeError(f"{feature} Debug usage 应为对象")
    return debug


def assert_gossip_propagation_contract(app) -> None:
    """确认 gossipEvidence 已提供最小传播闭环的调试契约。"""
    world = app.runtime.world
    npc = world["agents"]["kai"]
    context = build_player_dialogue_context(
        world,
        npc,
        {
            "type": "talk",
            "topic": "festival_debt_rumor",
            "message": "昨晚酒馆账单和星灯祭准备是不是又有新消息？",
        },
        app.runtime.event_store,
    )
    gossip = context.get("gossipEvidence")
    if not isinstance(gossip, dict):
        raise RuntimeError("gossipEvidence 应为对象")
    if not isinstance(gossip.get("selectionMeta"), dict):
        raise RuntimeError("gossipEvidence.selectionMeta 应为对象")
    if not isinstance(gossip.get("candidateDebugSummary"), list):
        raise RuntimeError("gossipEvidence.candidateDebugSummary 应为数组")
    contract = gossip.get("propagationRecordContract")
    if not isinstance(contract, dict):
        raise RuntimeError("gossipEvidence.propagationRecordContract 应为对象")
    for field in ("recordVersion", "requiredFields", "directionEnum", "forbiddenWorldStateFields", "validator"):
        if field not in contract:
            raise RuntimeError(f"gossipEvidence.propagationRecordContract 缺少字段：{field}")
    items = gossip.get("items")
    if not isinstance(items, list) or not items:
        raise RuntimeError("gossipEvidence.items 应为非空数组")
    first = items[0]
    if not isinstance(first.get("selectionReasons"), list) or not first["selectionReasons"]:
        raise RuntimeError("gossipEvidence.items[].selectionReasons 应提供选中理由")
    draft = first.get("propagationDraft")
    if not isinstance(draft, dict):
        raise RuntimeError("gossipEvidence.items[].propagationDraft 应为对象")
    for field in ("recordVersion", "hookId", "targetNpcIds", "direction", "allowedDirections"):
        if field not in draft:
            raise RuntimeError(f"gossipEvidence.items[].propagationDraft 缺少字段：{field}")
    if not isinstance(draft.get("targetNpcIds"), list):
        raise RuntimeError("gossipEvidence.items[].propagationDraft.targetNpcIds 应为数组")
    if draft["targetNpcIds"]:
        accepted = validate_gossip_propagation_payload(
            {
                "hookId": first["id"],
                "targetNpcIds": [draft["targetNpcIds"][0]],
                "direction": draft["direction"],
                "reason": "smoke 测试采样",
            },
            gossip,
        )
        if not accepted.get("accepted"):
            raise RuntimeError(f"gossip_propagation 合法样例被拒绝：{accepted.get('violations')}")
    rejected = validate_gossip_propagation_payload(
        {
            "hookId": "unknown_hook",
            "targetNpcIds": ["unknown_npc"],
            "direction": "amplify",
            "reason": "smoke 测试非法样例",
            "worldStatePatch": {"townStats": {"stability": 999}},
        },
        gossip,
    )
    if rejected.get("accepted"):
        raise RuntimeError("gossip_propagation 非法样例不应通过校验")


def assert_gossip_validation_record(record: dict, label: str, *, expected_accepted: bool) -> None:
    """确认运行时 gossip_propagation 校验记录结构稳定。"""
    if not isinstance(record, dict):
        raise RuntimeError(f"{label} gossipPropagationValidation 应为对象")
    for field in ("provided", "accepted", "violations", "normalized", "worldMutationApplied"):
        if field not in record:
            raise RuntimeError(f"{label} gossipPropagationValidation 缺少字段：{field}")
    if bool(record.get("accepted")) != expected_accepted:
        raise RuntimeError(f"{label} gossipPropagationValidation accepted 不符合预期：{record.get('accepted')}")
    if record.get("worldMutationApplied"):
        raise RuntimeError(f"{label} gossipPropagationValidation 不应声明世界状态变更")


def assert_client_context_fields(payload: dict, label: str) -> None:
    """确认 Godot 直显字段完整且具备基础可渲染结构。"""
    missing = sorted(REQUIRED_CLIENT_CONTEXT_FIELDS - set(payload))
    if missing:
        raise RuntimeError(f"{label} 缺少 Godot 直显字段：{missing}")
    if not isinstance(payload["memoryEvidence"], dict):
        raise RuntimeError(f"{label}.memoryEvidence 应为对象")
    if "ragHits" not in payload["memoryEvidence"]:
        raise RuntimeError(f"{label}.memoryEvidence 应包含 ragHits")
    relationship = payload["relationshipEvidence"]
    if not isinstance(relationship, dict) or not relationship.get("current"):
        raise RuntimeError(f"{label}.relationshipEvidence 应包含当前关系快照")
    if not payload["playerProfile"].get("styleSummary"):
        raise RuntimeError(f"{label}.playerProfile 应包含风格摘要")
    objective = payload["currentObjective"]
    if not isinstance(objective, dict) or not objective.get("id") or not objective.get("title"):
        raise RuntimeError(f"{label}.currentObjective 应包含 id 和 title")
    interactions = payload["availableInteractions"]
    if not isinstance(interactions, list) or not interactions:
        raise RuntimeError(f"{label}.availableInteractions 应为非空数组")
    if not all(isinstance(item, dict) and item.get("type") and isinstance(item.get("payload"), dict) for item in interactions):
        raise RuntimeError(f"{label}.availableInteractions 每项应包含 type 和 payload")


def assert_player_action_contract(response: dict, label: str) -> None:
    """确认 POST /api/player/action 根节点、result 和 state 都可直接取 Godot 直显字段。"""
    if not response.get("ok"):
        raise RuntimeError(f"{label} 动作应执行成功")
    assert_client_context_fields(response, f"{label} response")
    assert_client_context_fields(response["result"], f"{label} result")
    assert_game_state_contract(response["state"], f"{label} state")


def assert_action_feedback_contract(result: dict, label: str, *, expected_result_type: str | None = None) -> dict:
    """确认锚点移动或场景动作返回统一 actionFeedback 契约。"""
    feedback = result.get("actionFeedback")
    if not isinstance(feedback, dict):
        raise RuntimeError(f"{label}.actionFeedback 应为对象")
    missing = sorted(REQUIRED_ACTION_FEEDBACK_FIELDS - set(feedback))
    if missing:
        raise RuntimeError(f"{label}.actionFeedback 缺少字段：{missing}")
    if expected_result_type and feedback.get("resultType") != expected_result_type:
        raise RuntimeError(f"{label}.actionFeedback.resultType 期望 {expected_result_type}，实际为 {feedback.get('resultType')}")
    if not isinstance(feedback["changedResources"], list):
        raise RuntimeError(f"{label}.actionFeedback.changedResources 应为数组")
    if not isinstance(feedback["eventIds"], list) or not feedback["eventIds"]:
        raise RuntimeError(f"{label}.actionFeedback.eventIds 应为非空数组")
    return feedback


def assert_npc_schedule_contract(state: dict, label: str) -> None:
    """确认运行时日程快照可直接作为后续玩法候选输入。"""
    schedules = state.get("npcSchedules")
    if not isinstance(schedules, list) or not schedules:
        raise RuntimeError(f"{label}.npcSchedules 应为非空数组")
    for index, schedule in enumerate(schedules):
        if not isinstance(schedule, dict):
            raise RuntimeError(f"{label}.npcSchedules[{index}] 应为对象")
        missing = sorted(REQUIRED_NPC_SCHEDULE_FIELDS - set(schedule))
        if missing:
            raise RuntimeError(f"{label}.npcSchedules[{index}] 缺少字段：{missing}")
        policy = schedule.get("worldMutationPolicy")
        if not isinstance(policy, dict) or policy.get("llmMayMutateWorld") is not False:
            raise RuntimeError(f"{label}.npcSchedules[{index}].worldMutationPolicy.llmMayMutateWorld 应为 false")
        life_candidates = schedule.get("lifeActionCandidates")
        if not isinstance(life_candidates, list) or not life_candidates:
            raise RuntimeError(f"{label}.npcSchedules[{index}].lifeActionCandidates 应为非空数组")
        active_action = schedule.get("activeLifeAction")
        if not isinstance(active_action, dict) or not active_action.get("id"):
            raise RuntimeError(f"{label}.npcSchedules[{index}].activeLifeAction 应包含 id")
        if not isinstance(active_action.get("spaceActionCandidates"), list):
            raise RuntimeError(f"{label}.npcSchedules[{index}].activeLifeAction.spaceActionCandidates 应为数组")
    plan = state.get("lifeActionPlan")
    if not isinstance(plan, dict):
        raise RuntimeError(f"{label}.lifeActionPlan 应为对象")
    for field in ("version", "day", "phase", "generatedAtTick", "selectedActions", "locationBuckets", "policy"):
        if field not in plan:
            raise RuntimeError(f"{label}.lifeActionPlan 缺少字段：{field}")
    if plan["version"] != "motivation_plan.v1":
        raise RuntimeError(f"{label}.lifeActionPlan.version 期望 motivation_plan.v1，实际为 {plan['version']}")
    if not isinstance(plan.get("selectedActions"), list) or not plan["selectedActions"]:
        raise RuntimeError(f"{label}.lifeActionPlan.selectedActions 应为非空数组")
    plan_policy = plan.get("policy")
    if not isinstance(plan_policy, dict) or plan_policy.get("llmMayMutateWorld") is not False:
        raise RuntimeError(f"{label}.lifeActionPlan.policy.llmMayMutateWorld 应为 false")


def assert_game_state_contract(state: dict, label: str) -> None:
    """确认 /api/world/state 保持 Godot 可消费的稳定状态切片。"""
    missing = sorted((REQUIRED_GAME_STATE_FIELDS | REQUIRED_CLIENT_CONTEXT_FIELDS) - set(state))
    if missing:
        raise RuntimeError(f"{label} 缺少状态字段：{missing}")
    assert_client_context_fields(state, label)
    for field in (
        "locations",
        "anchors",
        "interactables",
        "npcPresence",
        "farmPlots",
        "npcs",
        "activeEvents",
        "completedEvents",
        "nightReflections",
        "recentEvents",
    ):
        if not isinstance(state[field], list):
            raise RuntimeError(f"{label}.{field} 应为数组")
    for index, event in enumerate(state["recentEvents"]):
        compact_debug = event.get("payload", {}).get("debug")
        if isinstance(compact_debug, dict):
            assert_compact_debug_payload(compact_debug, f"{label}.recentEvents[{index}]")
    clock = state["clock"]
    if not clock.get("phase") or "actionBudget" not in clock:
        raise RuntimeError(f"{label}.clock 应包含 phase 和 actionBudget")
    if not isinstance(state["player"], dict) or not state["player"].get("locationId") or not state["player"].get("anchorId"):
        raise RuntimeError(f"{label}.player 应包含 locationId 和 anchorId")
    player_anchor = state.get("playerAnchor")
    if not isinstance(player_anchor, dict) or not player_anchor.get("id") or not player_anchor.get("locationId"):
        raise RuntimeError(f"{label}.playerAnchor 应包含 id 和 locationId")
    if player_anchor.get("id") != state["player"].get("anchorId"):
        raise RuntimeError(f"{label}.playerAnchor.id 应与 player.anchorId 一致")
    if not isinstance(state["player"].get("inventory"), list):
        raise RuntimeError(f"{label}.player.inventory 应为数组")
    if not isinstance(state["slice"], dict) or not state["slice"].get("npcIds") or not state["slice"].get("locationIds"):
        raise RuntimeError(f"{label}.slice 应包含 npcIds 和 locationIds")
    if state["slice"].get("scheduleSnapshotVersion") != "motivation_plan.v1":
        raise RuntimeError(f"{label}.slice.scheduleSnapshotVersion 应为 motivation_plan.v1")
    if not isinstance(state["slice"].get("supportedLifeActionWindows"), list):
        raise RuntimeError(f"{label}.slice.supportedLifeActionWindows 应为数组")
    supported_sources = set(state["slice"].get("supportedNpcPresenceSources", []))
    required_sources = {"habit", "director_spotlight", "event_skill", "relationship_pull"}
    if not required_sources.issubset(supported_sources):
        raise RuntimeError(f"{label}.slice 应声明支持 NPC Presence 来源：{required_sources}")
    if not state["anchors"] or not all(anchor.get("id") and anchor.get("locationId") and anchor.get("kind") for anchor in state["anchors"]):
        raise RuntimeError(f"{label}.anchors 应包含 id、locationId 和 kind")
    if not state["interactables"] or not all(item.get("id") and item.get("locationId") and item.get("anchorId") and isinstance(item.get("actions"), list) for item in state["interactables"]):
        raise RuntimeError(f"{label}.interactables 应包含 id、locationId、anchorId 和 actions")
    if not state["farmPlots"] or not all(plot.get("id") and plot.get("locationId") and plot.get("anchorId") and plot.get("stage") for plot in state["farmPlots"]):
        raise RuntimeError(f"{label}.farmPlots 应包含 id、locationId、anchorId 和 stage")
    if not state["npcPresence"]:
        raise RuntimeError(f"{label}.npcPresence 应为非空数组")
    for index, presence in enumerate(state["npcPresence"]):
        if not presence.get("agentId") or not presence.get("locationId") or not presence.get("anchorId"):
            raise RuntimeError(f"{label}.npcPresence[{index}] 应包含 agentId、locationId 和 anchorId")
        if not presence.get("source") or not presence.get("intent"):
            raise RuntimeError(f"{label}.npcPresence[{index}] 应包含 source 和 intent")
        if presence["source"] not in supported_sources:
            raise RuntimeError(f"{label}.npcPresence[{index}].source 未声明支持：{presence['source']}")
    active_event = next((event for event in state["activeEvents"] if event.get("id") == "starlight_festival_shortage"), None)
    if not active_event:
        raise RuntimeError(f"{label} 缺少星灯祭供应短缺事件")
    for field in ("skillId", "title", "summary", "choices", "assetHints", "debugFields"):
        if field not in active_event:
            raise RuntimeError(f"{label}.activeEvents 星灯祭事件缺少 {field}")
    if not all(isinstance(choice, dict) and choice.get("id") and choice.get("label") for choice in active_event["choices"]):
        raise RuntimeError(f"{label}.activeEvents 星灯祭 choices 应包含 id 和 label")
    assert_npc_schedule_contract(state, label)


def assert_memory_search_contract(payload: dict, label: str) -> None:
    """确认 /api/memory/search 返回 RAG-lite 可解释结构。"""
    missing = sorted(REQUIRED_MEMORY_SEARCH_FIELDS - set(payload))
    if missing:
        raise RuntimeError(f"{label} 缺少字段：{missing}")
    if not isinstance(payload["tags"], list):
        raise RuntimeError(f"{label}.tags 应为数组")
    if not isinstance(payload["items"], list):
        raise RuntimeError(f"{label}.items 应为数组")
    for index, item in enumerate(payload["items"]):
        missing_item = sorted(REQUIRED_MEMORY_ITEM_FIELDS - set(item))
        if missing_item:
            raise RuntimeError(f"{label}.items[{index}] 缺少字段：{missing_item}")
        match = item["match"]
        if not isinstance(match, dict) or "score" not in match or "terms" not in match or "tags" not in match:
            raise RuntimeError(f"{label}.items[{index}].match 应包含 score、terms 和 tags")


def assert_compact_debug_payload(debug: dict, label: str) -> None:
    """确认 Debug API 中的长文本已被压缩成预览字段。"""
    if "messageCount" not in debug or "rawTextLength" not in debug:
        raise RuntimeError(f"{label} Debug 应包含 messageCount 和 rawTextLength")
    if len(str(debug.get("rawText", ""))) > 240:
        raise RuntimeError(f"{label} rawText 预览过长")
    messages = debug.get("messages")
    if not isinstance(messages, list) or not messages:
        raise RuntimeError(f"{label} messages 应为预览数组")
    for index, message in enumerate(messages):
        if "content" in message:
            raise RuntimeError(f"{label}.messages[{index}] 不应返回完整 content")
        if "contentPreview" not in message or "contentLength" not in message:
            raise RuntimeError(f"{label}.messages[{index}] 应包含 contentPreview 和 contentLength")
        if len(str(message.get("contentPreview", ""))) > 320:
            raise RuntimeError(f"{label}.messages[{index}].contentPreview 预览过长")


def assert_compact_debug_turns(payload: dict, label: str) -> None:
    """确认 Debug turns 列表字段稳定，且长 Prompt 不进入列表响应。"""
    items = payload.get("items")
    if not isinstance(items, list) or not items:
        raise RuntimeError(f"{label}.items 应为非空数组")
    for index, item in enumerate(items):
        missing = sorted(REQUIRED_DEBUG_TURN_FIELDS - set(item))
        if missing:
            raise RuntimeError(f"{label}.items[{index}] 缺少字段：{missing}")
        assert_compact_debug_payload(item["debug"], f"{label}.items[{index}]")


def assert_motivation_profile_weight_contract() -> None:
    """确认 Runtime 读取 NPC 深度卡 motivationProfile.needs.<need>.weight。"""
    agent = {
        "id": "contract_npc",
        "status": {"energy": 50, "money": 50, "social": 50},
        "todayGoals": [],
        "deepCard": {
            "motivationProfile": {
                "needs": {"energy": {"weight": 2.0}},
                "personalityModifiers": {},
            }
        },
    }
    scores = NeedAccumulator().score({"activeFocus": {}, "agents": {"contract_npc": agent}}, agent, delta_minutes=0.0)
    energy = next((score for score in scores if score.need_id == "energy"), None)
    if energy is None or round(energy.weight, 4) != 2.0 or round(energy.urgency, 4) != 1.0:
        raise RuntimeError("NeedAccumulator 应读取 motivationProfile.needs.energy.weight")


def assert_phase2_decision_budget_routing() -> dict:
    """确认 LLM eligible 工具会经过决策预算路由，并在耗尽时降级为规则路径。"""
    budget_app = create_town_app(provider_mode="rule")
    runtime = budget_app.runtime
    runtime.get_game_state()
    world = runtime.world
    npc_id = "kai"
    agent = world["agents"][npc_id]
    agent["status"].update({"energy": 100, "money": 100, "social": 0})
    agent["todayGoals"] = []
    agent["locationId"] = "plaza"
    agent["anchorId"] = "plaza_fountain"
    for presence in world.get("npcPresence", []):
        if presence.get("agentId") == npc_id:
            presence["locationId"] = "plaza"
            presence["anchorId"] = "plaza_fountain"
    runtime.decision_budget.exhaust(world, npc_id, "social_strategic_layer")

    decision = runtime.motivation_engine.evaluate_npc(world, npc_id, delta_minutes=0.0)
    capability_filters = decision.get("capabilityFilters", {})
    budget_layer = next((layer for layer in capability_filters.get("layers", []) if isinstance(layer, dict) and layer.get("layer") == "decision_budget"), None)
    if not isinstance(budget_layer, dict):
        raise RuntimeError("CapabilityRegistry 应输出 decision_budget 路由层")
    fallback_decisions = [
        item
        for item in budget_layer.get("decisions", [])
        if isinstance(item, dict) and item.get("metadata", {}).get("route") == "rule_fallback"
    ]
    if not fallback_decisions:
        raise RuntimeError("预算耗尽时，LLM eligible 工具应标记 rule_fallback")
    selected_score = next(
        (
            item
            for item in decision.get("decision", {}).get("candidateScores", [])
            if isinstance(item, dict) and item.get("toolId") == decision.get("decision", {}).get("selectedToolId")
        ),
        {},
    )
    if selected_score.get("decisionBudgetRoute") != "rule_fallback":
        raise RuntimeError("Arbitration candidateScores 应展开选中工具的预算路由")

    planned = runtime.tool_executor.plan_action(world, decision)
    if planned.get("decisionBudget", {}).get("route") != "rule_fallback":
        raise RuntimeError("ToolExecutor plan_action 应携带 decisionBudget.route")
    execution = runtime.tool_executor.tick(world=world, decisions=[decision], delta_seconds=1.0)
    fallback_event = next((event for event in execution.get("events", []) if event.get("type") == "budget.decision_fallback"), None)
    if not isinstance(fallback_event, dict) or fallback_event.get("reason") != "llm_budget_exhausted_rule_fallback":
        raise RuntimeError("工具开始执行时应写入 budget.decision_fallback 事件")
    debug_budget = runtime.decision_budget.debug_snapshot(world, npc_ids=[npc_id])
    remaining = debug_budget["items"][0]["remaining"].get("social_strategic_layer")
    if remaining != 0:
        raise RuntimeError("rule_fallback 不应继续消耗已耗尽预算")
    return {
        "route": planned["decisionBudget"].get("route"),
        "event": fallback_event.get("type"),
        "remaining": remaining,
    }


def assert_phase2_observer_visibility_scope() -> dict:
    """确认 ResultObserver 会按 private、participants_only 和 all_in_location 分发主观记忆。"""
    observer_app = create_town_app(provider_mode="rule")
    runtime = observer_app.runtime
    runtime.get_game_state()
    world = runtime.world

    def place_npc(npc_id: str, location_id: str, anchor_id: str) -> None:
        agent = world["agents"].get(npc_id)
        if isinstance(agent, dict):
            agent["locationId"] = location_id
            agent["anchorId"] = anchor_id
        for presence in world.get("npcPresence", []):
            if isinstance(presence, dict) and presence.get("agentId") == npc_id:
                presence["locationId"] = location_id
                presence["anchorId"] = anchor_id

    for npc_id in list(world.get("agents", {}).keys()):
        if npc_id in {"kai", "mira", "bram"}:
            place_npc(str(npc_id), "plaza", "plaza_fountain")
        else:
            place_npc(str(npc_id), "tavern", "tavern_stage")

    def store_tool_event(label: str, payload: dict) -> dict:
        event_payload = {
            "npcId": "kai",
            "summary": f"smoke {label}",
            "targetAnchorId": "plaza_fountain",
            "targetLocationId": "plaza",
            "traceSchemaVersion": "phase2.trace.v1",
            "traceId": f"trace_smoke_observer_{label}",
            **payload,
        }
        return runtime.event_store.append("tool.execution_completed", event_payload)

    def assert_observation(label: str, observation: dict, expected_observers: list[str], expected_visibility: str) -> dict:
        payload = observation.get("payload", {})
        expected = sorted(expected_observers)
        actual = sorted(str(item) for item in payload.get("observers", []))
        if actual != expected:
            raise RuntimeError(f"{label} 观察者分发应为 {expected}，实际为 {actual}")
        if payload.get("observerVisibility") != expected_visibility:
            raise RuntimeError(f"{label} observerVisibility 应为 {expected_visibility}")
        if int(payload.get("observerCount") or 0) != len(expected):
            raise RuntimeError(f"{label} observerCount 应为 {len(expected)}")
        memory_agents = sorted(str(item.get("agentId") or "") for item in payload.get("memories", []) if isinstance(item, dict))
        if memory_agents != expected:
            raise RuntimeError(f"{label} 主观记忆写入对象应为 {expected}，实际为 {memory_agents}")
        scope = payload.get("observerScope")
        if not isinstance(scope, dict) or scope.get("version") != "observer_scope.v1":
            raise RuntimeError(f"{label} 应输出 observer_scope.v1")
        if sorted(scope.get("observerIds", [])) != expected:
            raise RuntimeError(f"{label} observerScope.observerIds 应与 observers 一致")
        return scope

    private_event = store_tool_event(
        "private",
        {
            "toolId": "life.rest",
            "observerVisibility": "private",
            "input": {"targetNpcId": "mira"},
        },
    )
    private_observation = _record_tool_result_observation(runtime, private_event)
    private_scope = assert_observation("private", private_observation, ["kai"], "private")
    if "mira" not in private_scope.get("excludedObserverIds", []):
        raise RuntimeError("private 可见性应排除同场明确 targetNpcId")

    participant_event = store_tool_event(
        "participants",
        {
            "toolId": "social.chat_with",
            "observerVisibility": "participants_only",
            "input": {"targetNpcId": "mira"},
        },
    )
    participant_observation = _record_tool_result_observation(runtime, participant_event)
    participant_scope = assert_observation("participants_only", participant_observation, ["kai", "mira"], "participants_only")
    if "bram" not in participant_scope.get("excludedObserverIds", []):
        raise RuntimeError("participants_only 应排除同地点但未参与的旁观者")

    location_event = store_tool_event(
        "location",
        {
            "toolId": "shop.open_shop",
            "observerVisibility": "all_in_location",
            "input": {},
        },
    )
    location_observation = _record_tool_result_observation(runtime, location_event)
    location_scope = assert_observation("all_in_location", location_observation, ["kai", "mira", "bram"], "all_in_location")
    if sorted(location_scope.get("locationObserverIds", [])) != ["bram", "kai", "mira"]:
        raise RuntimeError("all_in_location 应枚举同地点 NPC 旁观者")

    debug = observer_app.debug_phase2({"eventType": "memory.result_observed", "limit": "20"})
    participant_trace = next(
        (
            item
            for item in debug.get("recentTraceEvents", [])
            if item.get("sourceEventId") == participant_event.get("id")
        ),
        None,
    )
    if not isinstance(participant_trace, dict):
        raise RuntimeError("/api/debug.phase2 应返回 participants_only 的 memory.result_observed trace")
    participant_details = participant_trace.get("details", {})
    if participant_details.get("observerVisibility") != "participants_only" or int(participant_details.get("observerCount") or 0) != 2:
        raise RuntimeError("memory.result_observed trace details 应展开 observerVisibility 和 observerCount")
    trace_scope = participant_details.get("observerScope")
    if not isinstance(trace_scope, dict) or "bram" not in trace_scope.get("excludedObserverIds", []):
        raise RuntimeError("memory.result_observed trace details 应展开 observerScope.excludedObserverIds")

    return {
        "private": len(private_observation["payload"]["observers"]),
        "participants": len(participant_observation["payload"]["observers"]),
        "location": len(location_observation["payload"]["observers"]),
    }


def assert_debug_snapshot_contract(payload: dict, label: str) -> None:
    """确认 /api/debug 总览结构稳定，并复用压缩后的 Debug turn 契约。"""
    missing = sorted(REQUIRED_DEBUG_SNAPSHOT_FIELDS - set(payload))
    if missing:
        raise RuntimeError(f"{label} 缺少字段：{missing}")
    if not payload.get("skills", {}).get("items"):
        raise RuntimeError(f"{label}.skills 应返回 Skill 快照")
    phase2 = payload.get("phase2")
    if not isinstance(phase2, dict):
        raise RuntimeError(f"{label}.phase2 应返回 Phase 2 调试快照")
    if phase2.get("traceSchemaVersion") != "phase2.trace.v1":
        raise RuntimeError(f"{label}.phase2.traceSchemaVersion 应为 phase2.trace.v1")
    tools = phase2.get("tools")
    if not isinstance(tools, dict) or int(tools.get("count") or 0) < 8:
        raise RuntimeError(f"{label}.phase2.tools 应返回至少 8 个 ToolDefinition")
    decision_budget = phase2.get("decisionBudget")
    if not isinstance(decision_budget, dict) or decision_budget.get("version") != "decision_budget.v1":
        raise RuntimeError(f"{label}.phase2.decisionBudget 应返回 decision_budget.v1")
    motivation = phase2.get("motivation")
    if not isinstance(motivation, dict) or motivation.get("version") != "motivation_engine.v0" or not motivation.get("items"):
        raise RuntimeError(f"{label}.phase2.motivation 应返回 MotivationEngine 快照")
    first_decision = motivation["items"][0].get("decision", {})
    if not first_decision.get("contributingSources"):
        raise RuntimeError(f"{label}.phase2.motivation.decision 应包含 contributingSources")
    if not isinstance(first_decision.get("subjectiveMemoryRefs"), list):
        raise RuntimeError(f"{label}.phase2.motivation.decision 应包含 subjectiveMemoryRefs 数组")
    if not isinstance(first_decision.get("heuristicRefs"), list):
        raise RuntimeError(f"{label}.phase2.motivation.decision 应包含 heuristicRefs 数组")
    recall_debug = motivation["items"][0].get("subjectiveMemoryRecall")
    if not isinstance(recall_debug, dict) or recall_debug.get("version") != "subjective_memory_recall.v1":
        raise RuntimeError(f"{label}.phase2.motivation 应包含 subjective_memory_recall.v1")
    heuristic_recall = motivation["items"][0].get("heuristicRecall")
    if not isinstance(heuristic_recall, dict) or heuristic_recall.get("version") != "heuristic_recall.v1":
        raise RuntimeError(f"{label}.phase2.motivation 应包含 heuristic_recall.v1")
    if not all("subjectiveMemoryBonus" in item and "subjectiveMemoryRefCount" in item and "heuristicBonus" in item and "heuristicRefCount" in item and "decisionBudgetRoute" in item for item in first_decision.get("candidateScores", []) if isinstance(item, dict)):
        raise RuntimeError(f"{label}.phase2.motivation.candidateScores 应包含主观记忆、启发式和预算路由评分字段")
    capability_filters = motivation["items"][0].get("capabilityFilters")
    if not isinstance(capability_filters, dict) or capability_filters.get("version") != "capability_resolution.v1":
        raise RuntimeError(f"{label}.phase2.motivation 应包含 capability_resolution.v1")
    layer_names = {str(layer.get("layer")) for layer in capability_filters.get("layers", []) if isinstance(layer, dict)}
    required_layers = {"need_relevance", "preconditions", "npc_profile", "event_scope", "decision_budget"}
    if not required_layers.issubset(layer_names):
        raise RuntimeError(f"{label}.phase2.motivation.capabilityFilters 缺少过滤层：{required_layers - layer_names}")
    if not capability_filters.get("allowedToolIds"):
        raise RuntimeError(f"{label}.phase2.motivation.capabilityFilters 应包含 allowedToolIds")
    need_layer = next((layer for layer in capability_filters.get("layers", []) if isinstance(layer, dict) and layer.get("layer") == "need_relevance"), {})
    if int(need_layer.get("rejectedCount") or 0) <= 0:
        raise RuntimeError(f"{label}.phase2.motivation.capabilityFilters.need_relevance 应记录被过滤工具")
    tool_runtime = phase2.get("toolRuntime")
    if not isinstance(tool_runtime, dict) or tool_runtime.get("version") != "tool_runtime.v1" or not tool_runtime.get("items"):
        raise RuntimeError(f"{label}.phase2.toolRuntime 应返回 ToolExecutor 运行态")
    subjective_memory = phase2.get("subjectiveMemory")
    if not isinstance(subjective_memory, dict) or subjective_memory.get("version") != "subjective_memory_store.v0":
        raise RuntimeError(f"{label}.phase2.subjectiveMemory 应返回 subjective_memory_store.v0")
    heuristics = phase2.get("heuristics")
    if not isinstance(heuristics, dict) or heuristics.get("version") != "heuristic_library.v0":
        raise RuntimeError(f"{label}.phase2.heuristics 应返回 heuristic_library.v0")
    trace_events = phase2.get("recentTraceEvents")
    if not isinstance(trace_events, list) or not trace_events:
        raise RuntimeError(f"{label}.phase2.recentTraceEvents 应返回 Phase 2 trace")
    decision_trace = next((item for item in trace_events if item.get("eventType") == "motivation.decision_made"), None)
    if not isinstance(decision_trace, dict):
        raise RuntimeError(f"{label}.phase2.recentTraceEvents 应包含 motivation.decision_made")
    decision_details = decision_trace.get("details")
    if not isinstance(decision_details, dict) or not decision_details.get("selectedToolId") or not isinstance(decision_details.get("candidateScores"), list):
        raise RuntimeError(f"{label}.phase2.recentTraceEvents.decision.details 应包含 selectedToolId 和 candidateScores")
    if not isinstance(decision_details.get("subjectiveMemoryRefs"), list) or not isinstance(decision_details.get("subjectiveMemoryRecall"), dict):
        raise RuntimeError(f"{label}.phase2.recentTraceEvents.decision.details 应包含主观记忆召回字段")
    if not isinstance(decision_details.get("heuristicRefs"), list) or not isinstance(decision_details.get("heuristicRecall"), dict):
        raise RuntimeError(f"{label}.phase2.recentTraceEvents.decision.details 应包含启发式召回字段")
    detail_filters = decision_details.get("capabilityFilters")
    if not isinstance(detail_filters, dict) or {str(layer.get("layer")) for layer in detail_filters.get("layers", []) if isinstance(layer, dict)} != required_layers:
        raise RuntimeError(f"{label}.phase2.recentTraceEvents.decision.details 应包含五层 capabilityFilters")
    assert_compact_debug_turns(payload["debugTurns"], f"{label}.debugTurns")


def _record_tool_result_observation(runtime, event: dict) -> dict:
    """把工具结果分发为主观记忆、关系边和启发式，并写回 EventStore。"""
    observation = runtime.result_observer.distribute(
        world=runtime.world,
        event=event,
        subjective_memory=runtime.subjective_memory_store,
        relationship_edges=runtime.relationship_edge_store,
        heuristic_library=runtime.heuristic_library,
    )
    return runtime.event_store.append("memory.result_observed", observation)


def _store_raw_tool_event(runtime, raw_event: dict) -> dict:
    """把 ToolExecutor 原始事件落入 EventStore，复用运行时 tick 的存储形态。"""
    event_type = str(raw_event.get("type") or "")
    if not event_type:
        raise RuntimeError("ToolExecutor 原始事件缺少 type")
    return runtime.event_store.append(event_type, {key: value for key, value in raw_event.items() if key != "type"})


def assert_phase2_failure_and_interrupt_trace() -> dict:
    """确认 Phase 2 失败与中断路径会进入 trace、主观记忆和启发式链路。"""
    failure_app = create_town_app(provider_mode="rule")
    failure_runtime = failure_app.runtime
    failure_runtime.get_game_state()
    decision_event = failure_runtime.event_store.append(
        "motivation.decision_made",
        {
            "npcId": "kai",
            "selectedToolId": "social.chat_with",
            "traceSchemaVersion": "phase2.trace.v1",
            "eventType": "motivation.decision_made",
            "traceId": "trace_smoke_failure_decision",
        },
    )
    failed_event = failure_runtime.tool_executor.apply_completion(
        world=failure_runtime.world,
        event_store=failure_runtime.event_store,
        source_event_id=str(decision_event["id"]),
        completion={
            "npcId": "kai",
            "toolId": "social.chat_with",
            "actionId": "social.chat_with",
            "summary": "smoke 注入目标不可用的社交动作。",
            "targetAnchorId": "plaza_fountain",
            "targetLocationId": "plaza",
            "input": {"targetNpcId": "missing_npc"},
            "contributingSources": [
                {
                    "type": "motivation_decision_trace",
                    "eventId": decision_event["id"],
                    "traceId": "trace_smoke_failure_decision",
                }
            ],
        },
    )
    if failed_event.get("type") != "tool.execution_failed":
        raise RuntimeError("Phase 2 失败 smoke 应产生 tool.execution_failed")
    failed_payload = failed_event.get("payload", {})
    if failed_payload.get("reason") != "target_unavailable":
        raise RuntimeError(f"Phase 2 失败 reason 应为 target_unavailable，实际为 {failed_payload.get('reason')}")
    if failed_payload.get("traceSchemaVersion") != "phase2.trace.v1":
        raise RuntimeError("tool.execution_failed 应携带 phase2.trace.v1")
    if str(decision_event["id"]) not in failed_payload.get("sourceEventIds", []):
        raise RuntimeError("tool.execution_failed 应追溯 sourceEventIds")
    failed_observation = _record_tool_result_observation(failure_runtime, failed_event)
    failed_heuristic = failed_observation.get("payload", {}).get("heuristic", {})
    if failed_heuristic.get("triggerPattern") != "avoid_failed_tool:social.chat_with":
        raise RuntimeError("tool.execution_failed 应沉淀 avoid_failed_tool 启发式")
    failure_debug = failure_app.debug_phase2({"eventType": "tool.execution_failed", "agentId": "kai", "limit": "10"})
    failure_trace = next((item for item in failure_debug.get("recentTraceEvents", []) if item.get("eventType") == "tool.execution_failed"), None)
    if not isinstance(failure_trace, dict):
        raise RuntimeError("/api/debug.phase2 应返回 tool.execution_failed trace")
    failure_details = failure_trace.get("details", {})
    if failure_details.get("reason") != "target_unavailable" or failure_details.get("toolId") != "social.chat_with":
        raise RuntimeError("tool.execution_failed trace details 应展开 toolId 和 reason")

    schema_failed_event = failure_runtime.tool_executor.apply_completion(
        world=failure_runtime.world,
        event_store=failure_runtime.event_store,
        source_event_id=str(decision_event["id"]),
        completion={
            "npcId": "kai",
            "toolId": "strategic.spread_rumor",
            "actionId": "strategic.spread_rumor",
            "summary": "smoke 注入缺少 hookId 的传闻动作。",
            "targetAnchorId": "plaza_fountain",
            "targetLocationId": "plaza",
            "input": {},
            "contributingSources": [
                {
                    "type": "motivation_decision_trace",
                    "eventId": decision_event["id"],
                    "traceId": "trace_smoke_schema_decision",
                }
            ],
        },
    )
    schema_payload = schema_failed_event.get("payload", {})
    if schema_payload.get("reason") != "missing_required_input:hookId":
        raise RuntimeError(f"Tool input schema 应拒绝缺少 hookId 的 spread_rumor，实际为 {schema_payload.get('reason')}")
    if not isinstance(schema_payload.get("violationDetails"), dict) or schema_payload["violationDetails"].get("field") != "hookId":
        raise RuntimeError("tool.execution_failed 应记录 input schema violationDetails.field")

    non_object_failed_event = failure_runtime.tool_executor.apply_completion(
        world=failure_runtime.world,
        event_store=failure_runtime.event_store,
        source_event_id=str(decision_event["id"]),
        completion={
            "npcId": "mira",
            "toolId": "shop.open_shop",
            "actionId": "shop.open_shop",
            "summary": "smoke 注入非 object 输入的开店动作。",
            "targetAnchorId": "market_stall",
            "targetLocationId": "market",
            "input": ["invalid"],
            "contributingSources": [
                {
                    "type": "motivation_decision_trace",
                    "eventId": decision_event["id"],
                    "traceId": "trace_smoke_non_object_input",
                }
            ],
        },
    )
    non_object_payload = non_object_failed_event.get("payload", {})
    if non_object_payload.get("reason") != "input_not_object":
        raise RuntimeError(f"Tool input schema 应拒绝非 object 输入，实际为 {non_object_payload.get('reason')}")

    precondition_failed_event = failure_runtime.tool_executor.apply_completion(
        world=failure_runtime.world,
        event_store=failure_runtime.event_store,
        source_event_id=str(decision_event["id"]),
        completion={
            "npcId": "bram",
            "toolId": "farm.water_crop",
            "actionId": "farm.water_crop",
            "summary": "smoke 注入不存在田块的浇水动作。",
            "targetAnchorId": "farm_field",
            "targetLocationId": "farm",
            "input": {"farmPlotId": "missing_plot"},
            "contributingSources": [
                {
                    "type": "motivation_decision_trace",
                    "eventId": decision_event["id"],
                    "traceId": "trace_smoke_precondition_decision",
                }
            ],
        },
    )
    precondition_payload = precondition_failed_event.get("payload", {})
    if precondition_payload.get("reason") != "farm_plot_unavailable":
        raise RuntimeError(f"Tool precondition 应拒绝不存在的 farmPlotId，实际为 {precondition_payload.get('reason')}")

    interrupt_app = create_town_app(provider_mode="rule")
    interrupt_runtime = interrupt_app.runtime
    interrupt_runtime.get_game_state()
    first_decision = {
        "npcId": "kai",
        "primaryNeed": {"needId": "money", "urgency": 0.4},
        "decision": {
            "selectedToolId": "shop.open_shop",
            "contributingSources": [
                {"type": "motivation_decision_trace", "eventId": "evt_smoke_interrupt_1", "traceId": "trace_smoke_interrupt_1"}
            ],
        },
    }
    second_decision = {
        "npcId": "kai",
        "primaryNeed": {"needId": "affiliation", "urgency": 0.95},
        "decision": {
            "selectedToolId": "strategic.spread_rumor",
            "contributingSources": [
                {"type": "motivation_decision_trace", "eventId": "evt_smoke_interrupt_2", "traceId": "trace_smoke_interrupt_2"}
            ],
        },
    }
    interrupt_runtime.tool_executor.tick(world=interrupt_runtime.world, decisions=[first_decision], delta_seconds=1.0)
    interruption = interrupt_runtime.tool_executor.tick(
        world=interrupt_runtime.world,
        decisions=[second_decision],
        delta_seconds=1.0,
    )
    interrupted_raw = next((event for event in interruption.get("events", []) if event.get("type") == "tool.execution_interrupted"), None)
    if not isinstance(interrupted_raw, dict):
        raise RuntimeError("高优先级需求应中断正在执行的 shop.open_shop")
    interrupted_event = _store_raw_tool_event(interrupt_runtime, interrupted_raw)
    interrupted_payload = interrupted_event.get("payload", {})
    if interrupted_payload.get("traceSchemaVersion") != "phase2.trace.v1":
        raise RuntimeError("tool.execution_interrupted 应携带 phase2.trace.v1")
    if interrupted_payload.get("replacementToolId") != "strategic.spread_rumor":
        raise RuntimeError("tool.execution_interrupted 应记录 replacementToolId")
    if float(interrupted_payload.get("interruptUrgency") or 0.0) < 0.9:
        raise RuntimeError("tool.execution_interrupted 应记录高优先级 urgency")
    interrupted_observation = _record_tool_result_observation(interrupt_runtime, interrupted_event)
    interrupted_heuristic = interrupted_observation.get("payload", {}).get("heuristic", {})
    if interrupted_heuristic.get("triggerPattern") != "avoid_interrupted_tool:shop.open_shop":
        raise RuntimeError("tool.execution_interrupted 应沉淀 avoid_interrupted_tool 启发式")
    interrupt_debug = interrupt_app.debug_phase2({"eventType": "tool.execution_interrupted", "agentId": "kai", "limit": "10"})
    interrupt_trace = next((item for item in interrupt_debug.get("recentTraceEvents", []) if item.get("eventType") == "tool.execution_interrupted"), None)
    if not isinstance(interrupt_trace, dict):
        raise RuntimeError("/api/debug.phase2 应返回 tool.execution_interrupted trace")
    interrupt_details = interrupt_trace.get("details", {})
    if interrupt_details.get("interruptedToolId") != "shop.open_shop":
        raise RuntimeError("tool.execution_interrupted trace details 应展开 interruptedToolId")
    if interrupt_details.get("replacementToolId") != "strategic.spread_rumor":
        raise RuntimeError("tool.execution_interrupted trace details 应展开 replacementToolId")
    return {
        "failedReason": failed_payload.get("reason"),
        "schemaReason": schema_payload.get("reason"),
        "nonObjectReason": non_object_payload.get("reason"),
        "preconditionReason": precondition_payload.get("reason"),
        "interruptedTool": interrupted_payload.get("interruptedToolId"),
        "replacementTool": interrupted_payload.get("replacementToolId"),
    }


def has_real_llm_config() -> bool:
    """检测是否存在可用于真实 LLM smoke 的本地配置入口。"""
    if (PROJECT_ROOT / "config" / "models.local.json").exists() or any(
        os.getenv(name) for name in ("DEEPSEEK_API_KEY", "OPENAI_API_KEY", "AGENT_TOWN_API_KEY")
    ):
        return True
    try:
        public_config = ModelConfigStore().public_config()
    except Exception:
        return False
    profiles = public_config.get("profiles", {})
    if not isinstance(profiles, dict):
        return False
    return any(isinstance(profile, dict) and profile.get("provider") == "cloud" and profile.get("apiKeyConfigured") for profile in profiles.values())


def assert_real_cloud_debug(debug: dict, feature: str) -> None:
    """确认真实 LLM smoke 没有走规则兜底，并且 usage 已带成本与延迟字段。"""
    if debug.get("providerMode") != "cloud":
        raise RuntimeError(f"{feature} LLM smoke 应运行在 cloud providerMode，实际为 {debug.get('providerMode')}")
    if debug.get("provider") != "CloudApiProvider":
        raise RuntimeError(f"{feature} LLM smoke 应调用 CloudApiProvider，实际为 {debug.get('provider')}")
    if not debug.get("apiKeyConfigured"):
        raise RuntimeError(f"{feature} LLM smoke 应检测到 apiKeyConfigured=true")
    if debug.get("fallbackReason"):
        raise RuntimeError(f"{feature} LLM smoke 不应触发 fallbackReason：{debug.get('fallbackReason')}")
    usage = debug.get("usage")
    if not isinstance(usage, dict):
        raise RuntimeError(f"{feature} LLM smoke usage 应为对象")
    missing = sorted(REQUIRED_LLM_USAGE_FIELDS - set(usage))
    if missing:
        raise RuntimeError(f"{feature} LLM smoke usage 缺少字段：{missing}")
    if int(usage.get("latencyMs") or 0) <= 0:
        raise RuntimeError(f"{feature} LLM smoke latencyMs 应大于 0")
    if int(usage.get("tokens") or 0) <= 0:
        raise RuntimeError(f"{feature} LLM smoke tokens 应大于 0")
    if not debug.get("rawText"):
        raise RuntimeError(f"{feature} LLM smoke rawText 应非空")


def enable_real_llm_smoke() -> bool:
    """是否执行真实 LLM smoke；默认跳过，避免常规检查消耗真实模型额度。"""
    if require_real_llm_smoke():
        return True
    return str(os.getenv("AGENT_TOWN_ENABLE_REAL_LLM_SMOKE") or "").lower() in {"1", "true", "yes"}


def require_real_llm_smoke() -> bool:
    """是否要求真实 LLM smoke 必须成功，供本地带网络的强验收使用。"""
    return str(os.getenv("AGENT_TOWN_REQUIRE_REAL_LLM_SMOKE") or "").lower() in {"1", "true", "yes"}


def real_cloud_check_error(debug: dict, feature: str) -> str | None:
    """返回真实云端 smoke 校验错误；通过时返回 None，便于普通检查降级为提示。"""
    try:
        assert_real_cloud_debug(debug, feature)
    except RuntimeError as error:
        return str(error)
    return None


def llm_debug_summary(debug: dict) -> dict:
    """输出不含 Prompt 正文和 rawText 全文的 LLM smoke 摘要。"""
    usage = debug.get("usage", {}) if isinstance(debug.get("usage"), dict) else {}
    return {
        "providerMode": debug.get("providerMode"),
        "provider": debug.get("provider"),
        "profileName": debug.get("profileName"),
        "apiKeyConfigured": debug.get("apiKeyConfigured"),
        "model": usage.get("model"),
        "tokens": usage.get("tokens"),
        "latencyMs": usage.get("latencyMs"),
        "cost": usage.get("cost"),
        "currency": usage.get("currency"),
        "costEstimated": usage.get("costEstimated"),
        "fallbackReason": debug.get("fallbackReason"),
        "rawTextLength": len(str(debug.get("rawText", ""))),
        "messageCount": len(debug.get("messages", [])) if isinstance(debug.get("messages"), list) else 0,
    }


def assert_http_debug_endpoints(api_app) -> dict:
    """启动临时 HTTP 服务，确认 Debug / Memory 查询接口能走真实路由。"""
    server = ThreadingHTTPServer(("127.0.0.1", 0), create_handler(api_app, PROJECT_ROOT))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()

    def fetch(path: str, query: dict[str, str] | None = None) -> dict:
        suffix = f"?{urlencode(query)}" if query else ""
        with urlopen(f"http://127.0.0.1:{server.server_port}{path}{suffix}", timeout=5) as response:  # noqa: S310 - 本地 smoke 服务
            return json.loads(response.read().decode("utf-8"))

    def post(path: str, payload: dict) -> dict:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = Request(
            f"http://127.0.0.1:{server.server_port}{path}",
            data=data,
            headers={"content-type": "application/json; charset=utf-8"},
            method="POST",
        )
        with urlopen(request, timeout=5) as response:  # noqa: S310 - 本地 smoke 服务
            return json.loads(response.read().decode("utf-8"))

    try:
        model_config = fetch("/api/model-config")
        model_reload = post("/api/model-config/reload", {})
        world_state = fetch("/api/world/state")
        world_tick = post("/api/world/tick", {"deltaSeconds": 5.0, "speed": 1.0})
        http_action = post("/api/player/action", {"type": "talk", "targetId": "mira", "locationId": "plaza", "topic": "http_contract", "message": "请确认后端动作契约。"})
        debug = fetch("/api/debug", {"skillId": STARLIGHT_FESTIVAL_SHORTAGE_SKILL_ID, "limit": "20"})
        world_tick_completed = post("/api/world/tick", {"deltaSeconds": 3600.0, "speed": 1.0})
        phase2_after_completion = fetch("/api/debug.phase2", {"limit": "40"})
        skill = fetch("/api/debug/skill", {"skillId": STARLIGHT_FESTIVAL_SHORTAGE_SKILL_ID})
        memory = fetch("/api/memory/search", {"query": "玩家", "tags": "night_reflection", "limit": "5"})
        influence = fetch("/api/debug/influence", {"skillId": STARLIGHT_FESTIVAL_SHORTAGE_SKILL_ID, "agentId": "kai", "query": "星灯祭", "limit": "30"})
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    assert_model_config_contract(model_config, "HTTP /api/model-config")
    if not model_reload.get("ok"):
        raise RuntimeError("HTTP /api/model-config/reload 应返回 ok=true")
    assert_model_config_contract(model_reload["modelConfig"], "HTTP /api/model-config/reload")
    assert_game_state_contract(world_state, "HTTP /api/world/state")
    for field in ("clock", "events", "agents"):
        if field not in world_tick:
            raise RuntimeError(f"HTTP /api/world/tick 缺少字段：{field}")
    clock = world_tick["clock"]
    if not isinstance(clock, dict) or any(field not in clock for field in ("day", "hour", "minute", "phase")):
        raise RuntimeError("HTTP /api/world/tick.clock 应包含 day/hour/minute/phase")
    if not isinstance(world_tick["events"], list):
        raise RuntimeError("HTTP /api/world/tick.events 应为数组")
    if not isinstance(world_tick["agents"], list):
        raise RuntimeError("HTTP /api/world/tick.agents 应为数组")
    if not any(event.get("type") == "motivation.decision_made" for event in world_tick["events"]):
        raise RuntimeError("HTTP /api/world/tick.events 应包含 motivation.decision_made trace")
    if not any(str(event.get("type", "")).startswith("npc.") for event in world_tick["events"]):
        raise RuntimeError("HTTP /api/world/tick.events 应至少包含一个 npc.* 事件")
    move_payloads = [
        event.get("payload", {})
        for event in world_tick["events"]
        if str(event.get("type", "")).startswith("npc.move") and isinstance(event.get("payload"), dict)
    ]
    if not any(payload.get("npcId") and payload.get("fromAnchorId") and payload.get("toAnchorId") for payload in move_payloads):
        raise RuntimeError("HTTP /api/world/tick 的移动事件应透出 npcId/fromAnchorId/toAnchorId")
    completed_events = [event for event in world_tick_completed.get("events", []) if event.get("type") == "tool.execution_completed"]
    if not completed_events:
        raise RuntimeError("长 tick 应产生 tool.execution_completed")
    if not any(
        any(isinstance(ref, dict) and ref.get("type") == "motivation_decision_trace" for ref in event.get("payload", {}).get("traceRefs", []))
        for event in completed_events
    ):
        raise RuntimeError("tool.execution_completed 应携带 motivation_decision_trace 引用")
    completion_event_ids = {str(event.get("id") or "") for event in completed_events}
    observed_events = [event for event in world_tick_completed.get("events", []) if event.get("type") == "memory.result_observed"]
    if not any(event.get("payload", {}).get("sourceEventId") in completion_event_ids and event.get("payload", {}).get("memories") for event in observed_events):
        raise RuntimeError("memory.result_observed 应追溯到 tool.execution_completed 并写入主观记忆")
    subjective_memory_after = phase2_after_completion.get("subjectiveMemory", {})
    if not isinstance(subjective_memory_after, dict) or int(subjective_memory_after.get("count") or 0) <= 0:
        raise RuntimeError("/api/debug.phase2 应在工具完成后返回主观记忆")
    motivation_after = phase2_after_completion.get("motivation", {})
    motivation_items = motivation_after.get("items", []) if isinstance(motivation_after, dict) else []
    if not any(int(item.get("subjectiveMemoryRecall", {}).get("count") or 0) > 0 for item in motivation_items if isinstance(item, dict)):
        raise RuntimeError("/api/debug.phase2.motivation 应召回已写入的主观记忆")
    if not any(
        any(int(score.get("subjectiveMemoryRefCount") or 0) > 0 for score in item.get("decision", {}).get("candidateScores", []) if isinstance(score, dict))
        for item in motivation_items
        if isinstance(item, dict)
    ):
        raise RuntimeError("/api/debug.phase2.motivation 应把主观记忆证据用于候选评分")
    heuristics_after = phase2_after_completion.get("heuristics", {})
    if not isinstance(heuristics_after, dict) or int(heuristics_after.get("count") or 0) <= 0:
        raise RuntimeError("/api/debug.phase2 应在工具完成后返回启发式记忆")
    if not any(int(item.get("heuristicRecall", {}).get("activeCount") or 0) > 0 for item in motivation_items if isinstance(item, dict)):
        raise RuntimeError("/api/debug.phase2.motivation 应召回启发式记忆")
    if not any(
        any(int(score.get("heuristicRefCount") or 0) > 0 for score in item.get("decision", {}).get("candidateScores", []) if isinstance(score, dict))
        for item in motivation_items
        if isinstance(item, dict)
    ):
        raise RuntimeError("/api/debug.phase2.motivation 应把启发式证据用于候选评分")
    completed_debug_trace = next((item for item in phase2_after_completion.get("recentTraceEvents", []) if item.get("eventType") == "tool.execution_completed"), None)
    if not isinstance(completed_debug_trace, dict) or not completed_debug_trace.get("details", {}).get("traceRefs"):
        raise RuntimeError("/api/debug.phase2 应展开 tool.execution_completed.traceRefs")
    memory_debug_trace = next((item for item in phase2_after_completion.get("recentTraceEvents", []) if item.get("eventType") == "memory.result_observed"), None)
    if not isinstance(memory_debug_trace, dict) or int(memory_debug_trace.get("details", {}).get("memoryCount") or 0) <= 0:
        raise RuntimeError("/api/debug.phase2 应展开 memory.result_observed.memoryCount")
    assert_player_action_contract(http_action, "HTTP /api/player/action")
    assert_debug_snapshot_contract(debug, "/api/debug")
    if "attend_event" not in skill.get("actions", {}):
        raise RuntimeError("/api/debug/skill 应解释 attend_event")
    assert_memory_search_contract(memory, "/api/memory/search")
    if not memory["items"]:
        raise RuntimeError("/api/memory/search 应返回 RAG-lite 命中")
    if not influence.get("memory", {}).get("retrieval", {}).get("items"):
        raise RuntimeError("/api/debug/influence 应解释相关 RAG-lite 记忆")
    if not influence.get("relations", {}).get("events"):
        raise RuntimeError("/api/debug/influence 应解释关系变化")
    if not influence.get("skill", {}).get("actions", {}).get("attend_event"):
        raise RuntimeError("/api/debug/influence 应解释事件 Skill")
    if not influence.get("playerProfile", {}).get("styleSummary"):
        raise RuntimeError("/api/debug/influence 应返回玩家风格摘要")
    for index, item in enumerate(influence["events"]["items"]):
        compact_debug = item.get("payload", {}).get("debug")
        if isinstance(compact_debug, dict):
            assert_compact_debug_payload(compact_debug, f"/api/debug/influence.events[{index}]")
    return {"debugSkills": len(debug["skills"]["items"]), "memoryHits": len(memory["items"]), "influenceEvents": len(influence["events"]["items"])}


def assert_provider_fallback_debug() -> dict:
    """用临时无密钥配置强制云端转规则兜底，并确认 Debug API 可解释。"""
    previous_env = {name: os.environ.get(name) for name in ("AGENT_TOWN_MODEL_CONFIG", "OPENAI_API_KEY", "AGENT_TOWN_NEVER_SET_API_KEY")}
    with tempfile.TemporaryDirectory(prefix="agent-town-fallback-") as tmp_dir:
        config_path = Path(tmp_dir) / "models.json"
        config_path.write_text(
            json.dumps(
                {
                    "activeProvider": "cloud",
                    "defaultProfile": "no_key_cloud",
                    "profiles": {
                        "no_key_cloud": {
                            "provider": "cloud",
                            "baseUrl": "https://example.invalid",
                            "apiKeyEnv": "AGENT_TOWN_NEVER_SET_API_KEY",
                            "model": "debug-no-key",
                            "timeoutSeconds": 1,
                        },
                        "rule_fallback": {"provider": "rule"},
                    },
                    "featureProfiles": {"dialogue": "no_key_cloud"},
                    "fallbackProfile": "rule_fallback",
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        os.environ["AGENT_TOWN_MODEL_CONFIG"] = str(config_path)
        os.environ.pop("OPENAI_API_KEY", None)
        os.environ.pop("AGENT_TOWN_NEVER_SET_API_KEY", None)
        try:
            fallback_app = create_town_app(provider_mode="cloud")
            fallback_talk = fallback_app.player_action({"type": "talk", "targetId": "mira", "locationId": "plaza", "topic": "fallback_check", "message": "测试无密钥兜底。"})
            fallback_debug = assert_feature_debug(fallback_app.get_public_state(), "dialogue")
            if not fallback_debug.get("fallbackReason"):
                raise RuntimeError("cloud 无密钥时 dialogue Debug 应记录 fallbackReason")
            fallback_items = fallback_app.debug_influence({"feature": "dialogue"})["providerFallbacks"]["items"]
            if not fallback_items:
                raise RuntimeError("Debug influence 应能解释模型兜底")
            return {"fallbackReason": fallback_debug["fallbackReason"], "fallbackItems": len(fallback_items)}
        finally:
            for name, value in previous_env.items():
                if value is None:
                    os.environ.pop(name, None)
                else:
                    os.environ[name] = value


app = create_town_app(provider_mode="rule")
initial = app.get_public_state()
if len(initial["agents"]) != 10:
    raise RuntimeError(f"期望 10 个初始 Agent，实际得到 {len(initial['agents'])}")
if initial.get("playerAnchor", {}).get("id") != initial.get("player", {}).get("anchorId"):
    raise RuntimeError("公开状态应暴露与 player.anchorId 一致的 playerAnchor")
assert_gossip_propagation_contract(app)

game_state = app.get_game_state()
assert_game_state_contract(game_state, "/api/world/state")
if game_state["player"]["locationId"] != "farm":
    raise RuntimeError("玩家初始位置应为 farm")
if game_state["player"]["anchorId"] != "farm_house_door":
    raise RuntimeError("玩家初始锚点应为 farm_house_door")
if game_state["clock"]["phase"] != "morning" or game_state["clock"]["actionBudget"] <= 0:
    raise RuntimeError("游戏状态应返回 clock.phase 和正数 actionBudget")
if not any(item["id"] == "starlight_turnip_seed" and item["quantity"] >= 1 for item in game_state["player"]["inventory"]):
    raise RuntimeError("玩家初始背包应包含可播种的星灯芜菁种子")
if len(game_state["npcs"]) != 6:
    raise RuntimeError(f"游戏状态应只暴露首发 6 个 NPC，实际得到 {len(game_state['npcs'])}")
if {location["id"] for location in game_state["locations"]} != {"farm", "plaza", "tavern"}:
    raise RuntimeError("游戏状态应只暴露首版 3 个地点")
if not any(location["id"] == "farm" for location in game_state["locations"]):
    raise RuntimeError("游戏状态缺少玩家农场地点")
if not any(anchor["id"] == "farm_field" for anchor in game_state["anchors"]):
    raise RuntimeError("游戏状态缺少农场田地锚点")
presence_sources = {presence["source"] for presence in game_state["npcPresence"]}
for expected_source in ("habit", "event_skill", "relationship_pull"):
    if expected_source not in presence_sources:
        raise RuntimeError(f"初始 npcPresence 应覆盖来源：{expected_source}")
if not any(plot["id"] == "farm_plot_01" and plot["stage"] == "empty" for plot in game_state["farmPlots"]):
    raise RuntimeError("游戏状态缺少空置 farm_plot_01")
if not any(event["id"] == "starlight_festival_shortage" for event in game_state["activeEvents"]):
    raise RuntimeError("游戏状态缺少星灯祭供应短缺事件")
deep_card_kai = next((npc.get("deepCard") for npc in game_state["npcs"] if npc.get("id") == "kai"), None)
if not isinstance(deep_card_kai, dict) or len(deep_card_kai.get("relationshipStages", [])) < 4:
    raise RuntimeError("游戏状态应挂载 Kai NPC 深度卡和关系阶段")
if not deep_card_kai.get("giftReactions", {}).get("loved", {}).get("fallbackSpeechPool"):
    raise RuntimeError("Kai NPC 深度卡应提供送礼 fallback 台词池")
starlight_event = next(event for event in game_state["activeEvents"] if event["id"] == "starlight_festival_shortage")
if starlight_event.get("skillId") != STARLIGHT_FESTIVAL_SHORTAGE_SKILL_ID:
    raise RuntimeError("游戏状态中的星灯祭事件应叠加 Event Skill 数据")
if not all(choice.get("brief") and choice.get("consequences") for choice in starlight_event.get("choices", [])):
    raise RuntimeError("游戏状态中的事件选项应由 Skill 提供 brief 和 consequences")
asset_hint_ids = {str(item.get("id")) for item in starlight_event.get("assetHints", []) if isinstance(item, dict)}
for required_hint in ("starlight_shortage_scene", "starlight_shortage_ui_card", "starlight_shortage_choice_icons"):
    if required_hint not in asset_hint_ids:
        raise RuntimeError(f"游戏状态中的事件资源提示缺少 {required_hint}")
interaction_types = {item.get("type") for item in game_state["availableInteractions"]}
for required_interaction in ("move", "move_to_anchor", "scene_action", "farm_action", "end_phase", "talk", "give_gift", "inspect", "attend_event"):
    if required_interaction not in interaction_types:
        raise RuntimeError(f"/api/world/state availableInteractions 缺少 {required_interaction}")

anchor_move = app.player_action({"type": "move_to_anchor", "locationId": "farm", "anchorId": "farm_field"})
assert_player_action_contract(anchor_move, "move_to_anchor")
anchor_feedback = assert_action_feedback_contract(anchor_move["result"], "move_to_anchor", expected_result_type="anchor_moved")
if anchor_move["state"]["player"]["anchorId"] != "farm_field":
    raise RuntimeError("move_to_anchor 后玩家锚点应同步为 farm_field")
if anchor_move["state"]["clock"]["actionBudget"] != game_state["clock"]["actionBudget"] - 1:
    raise RuntimeError("move_to_anchor 应消耗 1 点行动预算")
if anchor_feedback.get("anchorId") != "farm_field":
    raise RuntimeError("move_to_anchor.actionFeedback.anchorId 应为 farm_field")

plant = app.player_action(
    {"type": "scene_action", "locationId": "farm", "interactableId": "farm_plot_01", "action": "plant", "itemId": "starlight_turnip_seed"}
)
assert_player_action_contract(plant, "scene_action plant")
assert_action_feedback_contract(plant["result"], "scene_action plant", expected_result_type="scene_action_applied")
if not any(plot["id"] == "farm_plot_01" and plot["stage"] == "planted" for plot in plant["state"]["farmPlots"]):
    raise RuntimeError("plant 后 farm_plot_01 应进入 planted 阶段")

water = app.player_action({"type": "scene_action", "locationId": "farm", "interactableId": "farm_plot_01", "action": "water"})
assert_player_action_contract(water, "scene_action water")
assert_action_feedback_contract(water["result"], "scene_action water", expected_result_type="scene_action_applied")
if not any(plot["id"] == "farm_plot_01" and plot["stage"] == "watered" for plot in water["state"]["farmPlots"]):
    raise RuntimeError("water 后 farm_plot_01 应进入 watered 阶段")
if water["state"]["clock"]["actionBudget"] != 0:
    raise RuntimeError("连续移动、播种、浇水后行动预算应耗尽")

phase_end = app.player_action({"type": "end_phase"})
assert_player_action_contract(phase_end, "end_phase")
if phase_end["state"]["clock"]["phase"] != "noon" or phase_end["state"]["clock"]["actionBudget"] <= 0:
    raise RuntimeError("end_phase 应推进到 noon 并刷新行动预算")
if "farm_plot_01" not in phase_end["result"]["clockTransition"]["maturedFarmPlotIds"]:
    raise RuntimeError("end_phase 应把已浇水田块推进到可收获")

harvest = app.player_action({"type": "scene_action", "locationId": "farm", "interactableId": "farm_plot_01", "action": "harvest"})
assert_player_action_contract(harvest, "scene_action harvest")
assert_action_feedback_contract(harvest["result"], "scene_action harvest", expected_result_type="scene_action_applied")
if not any(plot["id"] == "farm_plot_01" and plot["stage"] == "empty" for plot in harvest["state"]["farmPlots"]):
    raise RuntimeError("harvest 后 farm_plot_01 应回到 empty 阶段")
if not any(item["id"] == "fresh_turnip" and item["quantity"] >= 2 for item in harvest["state"]["player"]["inventory"]):
    raise RuntimeError("harvest 后玩家背包应接收作物")

director_app = create_town_app(provider_mode="rule")
director_step = director_app.step_simulation({"actorId": "director-smoke"})
director_events = director_step["state"]["events"]
for event_type in (
    "director.digest_created",
    "director.beat_created",
    "director.beat_validated",
    "director.beat_consumed",
):
    if not any(event["type"] == event_type for event in director_events):
        raise RuntimeError(f"Director v0 应写入 {event_type}")
consumed = next(event for event in director_events if event["type"] == "director.beat_consumed")
if consumed["payload"]["beat"]["beatType"] != "activate_event_skill":
    raise RuntimeError("Director Beat 类型应为 activate_event_skill")
if consumed["payload"]["beat"]["payload"]["skillId"] != STARLIGHT_FESTIVAL_SHORTAGE_SKILL_ID:
    raise RuntimeError("Director Beat 应激活星灯祭供应短缺 Event Skill")
director_game_state = director_app.get_game_state()
if not any(presence["source"] == "director_spotlight" for presence in director_game_state["npcPresence"]):
    raise RuntimeError("Director Beat 消费后 npcPresence 应包含 director_spotlight 来源")

current_digest = WorldDigest.from_world(director_app.runtime.world)
expired_beat = DirectorBeat(
    worldVersion=current_digest.world_version,
    validFromTick=0,
    expiresAtTick=0,
    targetAgents=["kai"],
    allowedSkills=[STARLIGHT_FESTIVAL_SHORTAGE_SKILL_ID],
)
director_app.runtime.director_queue.enqueue(expired_beat)
director_app.runtime._consume_director_queue(current_digest)
if not any(event["type"] == "director.beat_discarded" and event["payload"].get("reason") == "expired" for event in director_app.get_public_state()["events"]):
    raise RuntimeError("Director 队列应丢弃过期 Beat")

mismatch_beat = DirectorBeat(
    worldVersion=current_digest.world_version + 1,
    validFromTick=current_digest.tick,
    expiresAtTick=current_digest.tick + 2,
    targetAgents=["kai"],
    allowedSkills=[STARLIGHT_FESTIVAL_SHORTAGE_SKILL_ID],
)
director_app.runtime.director_queue.enqueue(mismatch_beat)
director_app.runtime._consume_director_queue(current_digest)
if not any(event["type"] == "director.beat_discarded" and event["payload"].get("reason") == "world_version_mismatch" for event in director_app.get_public_state()["events"]):
    raise RuntimeError("Director 队列应丢弃世界版本不匹配 Beat")

move = app.player_action({"type": "move", "locationId": "plaza"})
assert_player_action_contract(move, "move")
if move["state"]["player"]["locationId"] != "plaza":
    raise RuntimeError("玩家移动后 state 应同步位置")

talk = app.player_action({"type": "talk", "targetId": "orren", "locationId": "plaza", "topic": "first_meeting", "message": "你好，我刚搬到晨露农场。"})
assert_player_action_contract(talk, "talk")
if "orren" not in talk["state"]["player"]["knownNpcs"]:
    raise RuntimeError("玩家对话后应记录已认识 NPC")
if not talk["result"]["dialogue"]:
    raise RuntimeError("玩家对话后应返回 NPC 回复")
if not any(event["type"] == "debug.turn_recorded" for event in talk["state"]["recentEvents"]):
    raise RuntimeError("玩家对话后应写入 Debug 决策记录")
dialogue_debug = assert_feature_debug(app.get_public_state(), "dialogue")
dialogue_prompt = "\n".join(str(message.get("content", "")) for message in dialogue_debug["messages"])
if "voiceStyle" not in dialogue_prompt or "speechQuirks" not in dialogue_prompt:
    raise RuntimeError("对话 Prompt 应包含 NPC 深度卡 voiceStyle 和 speechQuirks")
if "gossipEvidence" not in dialogue_prompt:
    raise RuntimeError("对话 Prompt 应包含 gossipEvidence，便于谣言传播原型提供上下文素材")
if "propagationRecordContract" not in dialogue_prompt or "selectionReasons" not in dialogue_prompt:
    raise RuntimeError("对话 Prompt 应包含谣言传播契约与选中理由，便于最小传播闭环调试")
if "gossip_propagation" not in dialogue_prompt:
    raise RuntimeError("对话 Prompt 应声明 gossip_propagation 输出字段")
if not talk["result"].get("playerProfile", {}).get("styleSummary"):
    raise RuntimeError("玩家对话后应更新 Player Profile")
if not talk["result"].get("relationshipStage", {}).get("stage"):
    raise RuntimeError("玩家对话后应返回 relationshipStage")

gossip_accept = app.player_action(
    {
        "type": "talk",
        "targetId": "kai",
        "locationId": "tavern",
        "topic": "festival_debt_rumor",
        "message": "昨晚酒馆账单和星灯祭准备是不是又有新消息？",
    }
)
assert_player_action_contract(gossip_accept, "gossip_accept")
accepted_record = gossip_accept["result"].get("gossipPropagationValidation")
assert_gossip_validation_record(accepted_record, "gossip_accept", expected_accepted=True)
if not accepted_record.get("provided"):
    raise RuntimeError("gossip_accept 应记录 provided=true")
accepted_event = next((event for event in reversed(gossip_accept["state"]["recentEvents"]) if event["type"] == "gossip.propagation_validated"), None)
if not accepted_event:
    raise RuntimeError("gossip_accept 应写入 gossip.propagation_validated 事件")
if not accepted_event.get("payload", {}).get("accepted"):
    raise RuntimeError("gossip_accept 事件应标记 accepted=true")
accepted_debug = assert_feature_debug(app.get_public_state(), "dialogue")
assert_gossip_validation_record(accepted_debug.get("gossipPropagationValidation"), "gossip_accept debug", expected_accepted=True)

gossip_reject_app = create_town_app(provider_mode="rule")
original_decide_player_dialogue = gossip_reject_app.runtime._decide_player_dialogue


def _inject_rejected_gossip(self, target, payload, context, messages):
    provider_result, profile, fallback_reason = original_decide_player_dialogue(target, payload, context, messages)
    parsed = dict(provider_result.get("parsed", {}))
    parsed["gossip_propagation"] = {
        "hookId": "unknown_hook",
        "targetNpcIds": ["unknown_npc"],
        "direction": "amplify",
        "reason": "smoke 注入非法 gossip",
        "worldStatePatch": {"townStats": {"stability": 999}},
    }
    mutated = dict(provider_result)
    mutated["provider"] = "SmokeInjectedDialogueProvider"
    mutated["parsed"] = parsed
    mutated["rawText"] = json.dumps(parsed, ensure_ascii=False)
    return mutated, profile, fallback_reason


gossip_reject_app.runtime._decide_player_dialogue = MethodType(_inject_rejected_gossip, gossip_reject_app.runtime)
gossip_reject = gossip_reject_app.player_action(
    {
        "type": "talk",
        "targetId": "kai",
        "locationId": "tavern",
        "topic": "festival_debt_rumor",
        "message": "昨晚酒馆账单和星灯祭准备是不是又有新消息？",
    }
)
assert_player_action_contract(gossip_reject, "gossip_reject")
rejected_record = gossip_reject["result"].get("gossipPropagationValidation")
assert_gossip_validation_record(rejected_record, "gossip_reject", expected_accepted=False)
if not any("forbidden_state_fields" in str(item) for item in rejected_record.get("violations", [])):
    raise RuntimeError("gossip_reject 应记录 forbidden_state_fields 违规")
rejected_event = next((event for event in reversed(gossip_reject["state"]["recentEvents"]) if event["type"] == "gossip.propagation_validated"), None)
if not rejected_event:
    raise RuntimeError("gossip_reject 应写入 gossip.propagation_validated 事件")
if rejected_event.get("payload", {}).get("accepted"):
    raise RuntimeError("gossip_reject 事件应标记 accepted=false")
rejected_debug = assert_feature_debug(gossip_reject_app.get_public_state(), "dialogue")
assert_gossip_validation_record(rejected_debug.get("gossipPropagationValidation"), "gossip_reject debug", expected_accepted=False)

gift = app.player_action({"type": "give_gift", "targetId": "kai", "locationId": "tavern", "itemId": "farm_flower"})
assert_player_action_contract(gift, "give_gift")
if not gift["result"]["relationshipDeltas"]:
    raise RuntimeError("送礼后应产生关系变化")
if not any("player_gift" in item.get("tags", []) for item in gift["result"]["memoryWrites"]):
    raise RuntimeError("送礼后应写入 NPC 礼物记忆")
if "礼物" not in gift["result"].get("playerProfile", {}).get("styleSummary", ""):
    raise RuntimeError("送礼后 Player Profile 应体现礼物风格")
gift_reaction = gift["result"].get("giftReaction", {})
if gift_reaction.get("tier") not in {"loved", "liked", "neutral", "disliked"}:
    raise RuntimeError("送礼后应返回 NPC 深度卡匹配出的 giftReaction.tier")
if not gift["result"].get("relationshipStage", {}).get("label"):
    raise RuntimeError("送礼后应返回 relationshipStage.label")

inspect = app.player_action({"type": "inspect", "eventId": "starlight_festival_shortage"})
assert_player_action_contract(inspect, "inspect")
if not inspect["result"]["inspect"]["choices"]:
    raise RuntimeError("事件查看应返回可选项")
if inspect["result"]["inspect"].get("skillId") != STARLIGHT_FESTIVAL_SHORTAGE_SKILL_ID:
    raise RuntimeError("事件查看结果应包含 Skill ID")
if not inspect["result"]["inspect"].get("debugFields"):
    raise RuntimeError("事件查看结果应包含 Skill Debug 字段")
inspect_asset_hints = inspect["result"]["inspect"].get("assetHints", [])
if not inspect_asset_hints or not all(
    isinstance(item, dict) and item.get("id") and item.get("type") and item.get("brief") and isinstance(item.get("tags"), list)
    for item in inspect_asset_hints
):
    raise RuntimeError("事件查看结果应返回结构完整的 Skill assetHints")

event_result = app.player_action({"type": "attend_event", "eventId": "starlight_festival_shortage", "choice": "donate_crop"})
assert_player_action_contract(event_result, "attend_event")
if event_result["result"]["eventResult"]["choice"] != "donate_crop":
    raise RuntimeError("星灯祭事件结算选项异常")
if event_result["result"]["eventResult"].get("skillId") != STARLIGHT_FESTIVAL_SHORTAGE_SKILL_ID:
    raise RuntimeError("星灯祭事件结算应返回 Skill ID")
if not event_result["result"]["eventResult"].get("debugFields"):
    raise RuntimeError("星灯祭事件结算应返回 Skill Debug 字段")
if event_result["result"]["eventResult"].get("recordVersion") != "event_skill_outcome.v1":
    raise RuntimeError("星灯祭事件结算应返回通用 outcome recordVersion")
if event_result["result"]["eventResult"].get("memoryTemplateCount", 0) <= 0:
    raise RuntimeError("星灯祭事件结算应返回 memoryTemplateCount")
if event_result["result"]["eventResult"].get("reflectionSeedCount", 0) <= 0:
    raise RuntimeError("星灯祭事件结算应返回 reflectionSeedCount")
event_result_debug_fields = {
    str(item.get("id")): str(item.get("value"))
    for item in event_result["result"]["eventResult"].get("debugFields", [])
    if isinstance(item, dict) and item.get("id")
}
for field_id in ("styleSignal", "profileEvidence", "fallbackMemory"):
    if field_id not in event_result_debug_fields:
        raise RuntimeError(f"星灯祭事件结算 Debug 字段应包含 {field_id}")
if event_result_debug_fields["styleSignal"] != "help":
    raise RuntimeError("星灯祭 donate_crop 结算应透出 Skill 声明的 styleSignal=help")
if not all(item.get("skillId") == STARLIGHT_FESTIVAL_SHORTAGE_SKILL_ID for item in event_result["result"]["memoryWrites"] if item.get("agentId") != "player"):
    raise RuntimeError("星灯祭记忆写入应记录来源 Skill")
if "直接帮忙" not in event_result["result"].get("playerProfile", {}).get("styleSummary", "") and "实际" not in event_result["result"].get("playerProfile", {}).get("styleSummary", ""):
    raise RuntimeError("星灯祭选择后 Player Profile 应体现选择风格")
if not event_result["state"]["nightReflections"]:
    raise RuntimeError("星灯祭事件后应生成夜间反思摘要")
if not any(event["type"] == "town.event_resolved" for event in event_result["state"]["recentEvents"]):
    raise RuntimeError("星灯祭事件后应写入事件结算记录")
resolved_event = next(
    (event for event in event_result["state"]["recentEvents"] if event["type"] == "town.event_resolved"),
    None,
)
if not resolved_event:
    raise RuntimeError("星灯祭事件后应返回 town.event_resolved 事件")
resolved_outcome_record = resolved_event.get("payload", {}).get("outcomeRecord", {})
if resolved_outcome_record.get("recordVersion") != "event_skill_outcome.v1":
    raise RuntimeError("town.event_resolved 应附带通用 outcomeRecord")
if resolved_outcome_record.get("choice") != "donate_crop":
    raise RuntimeError("town.event_resolved.outcomeRecord 应记录本次选项")
completed_starlight = next(
    (event for event in event_result["state"].get("completedEvents", []) if event.get("id") == "starlight_festival_shortage"),
    None,
)
if not completed_starlight:
    raise RuntimeError("事件结算后 completedEvents 应包含星灯祭事件")
completed_outcome_record = completed_starlight.get("resolution", {}).get("outcomeRecord", {})
if completed_outcome_record.get("recordVersion") != "event_skill_outcome.v1":
    raise RuntimeError("completedEvents.resolution 应附带通用 outcomeRecord")
event_reaction_debug = assert_feature_debug(app.get_public_state(), "event_reaction")
night_reflection_debug = assert_feature_debug(app.get_public_state(), "night_reflection")
if event_reaction_debug.get("skillId") != STARLIGHT_FESTIVAL_SHORTAGE_SKILL_ID or not event_reaction_debug.get("skillDebugFields"):
    raise RuntimeError("event_reaction Debug 应记录 Skill 字段")
if night_reflection_debug.get("skillId") != STARLIGHT_FESTIVAL_SHORTAGE_SKILL_ID or not night_reflection_debug.get("skillDebugFields"):
    raise RuntimeError("night_reflection Debug 应记录 Skill 字段")
night_reflection_memory = night_reflection_debug.get("memoryEvidence", {})
if not isinstance(night_reflection_memory, dict):
    raise RuntimeError("night_reflection Debug 应输出 memoryEvidence 对象")
monologue_candidates = night_reflection_memory.get("monologueSeeds")
if not isinstance(monologue_candidates, list) or not monologue_candidates:
    raise RuntimeError("night_reflection memoryEvidence 应包含 monologueSeeds 素材")
if not any(
    isinstance(item, dict) and item.get("source") == "npc_monologue_seed"
    for item in night_reflection_memory.get("items", [])
):
    raise RuntimeError("night_reflection memoryEvidence.items 应包含来自 npc_monologue_seed 的 compact evidence")
if night_reflection_debug.get("provider") == "RuleNightReflectionProvider":
    if not any("我心里还反复想着：" in str(item.get("text", "")) for item in event_result["state"]["nightReflections"]):
        raise RuntimeError("规则夜间反思 fallback 应拼接独白素材提示语")
event_reaction_memory = str(event_reaction_debug.get("parsed", {}).get("memory_to_save") or "")
if event_reaction_debug.get("provider") == "RuleEventReactionProvider" and event_reaction_memory != event_result_debug_fields["fallbackMemory"]:
    raise RuntimeError("event_reaction fallback 记忆文案应来自 Event Skill 结算模板")
if event_reaction_debug.get("provider") == "RuleEventReactionProvider":
    fallback_dialogue_ids = {
        str(item.get("agentId"))
        for item in event_reaction_debug.get("parsed", {}).get("dialogue", [])
        if isinstance(item, dict) and item.get("agentId")
    }
    for required_agent in ("mira", "lena", "orren", "tomas"):
        if required_agent not in fallback_dialogue_ids:
            raise RuntimeError(f"event_reaction fallback 台词应包含 Skill 模板角色：{required_agent}")

follow_up = app.player_action({"type": "talk", "targetId": "kai", "locationId": "tavern", "topic": "starlight_follow_up", "message": "昨晚星灯祭之后，你怎么看我的选择？"})
assert_player_action_contract(follow_up, "follow_up")
follow_up_text = follow_up["result"]["dialogue"][0]["text"]
if "记得" not in follow_up_text and "星灯祭" not in follow_up_text:
    raise RuntimeError("第二次对话应引用既有记忆或星灯祭上下文")
if not follow_up["result"].get("memoryEvidenceUsed"):
    raise RuntimeError("第二次对话结果应直出已使用的记忆证据，方便 Godot 展示 NPC 记忆影响")
if follow_up["result"]["memoryEvidenceUsed"].get("source") not in {"rag_lite", "memory_summary"}:
    raise RuntimeError("第二次对话结果应标明记忆证据来源")
if not follow_up["result"].get("memoryEvidence", {}).get("ragHits"):
    raise RuntimeError("第二次对话结果应直出 RAG-lite 候选命中")
follow_up_debug = assert_feature_debug(app.get_public_state(), "dialogue")
if not follow_up_debug.get("memoryEvidenceUsed"):
    raise RuntimeError("第二次对话 Debug 应记录实际使用的记忆证据")
if follow_up_debug["memoryEvidenceUsed"].get("source") not in {"rag_lite", "memory_summary"}:
    raise RuntimeError("第二次对话应引用 Memory Summary 或 RAG-lite 命中")
if not follow_up_debug.get("memoryEvidence", {}).get("ragHits"):
    raise RuntimeError("第二次对话 Debug 应保留 RAG-lite 候选命中")

skill_debug = app.debug_skill_explain({"skillId": STARLIGHT_FESTIVAL_SHORTAGE_SKILL_ID})
for action_name in ("inspect", "attend_event", "event_reaction", "night_reflection"):
    if action_name not in skill_debug["actions"]:
        raise RuntimeError(f"Skill 解释接口应覆盖 {action_name}")
mediate_preview = next(
    (item for item in skill_debug["actions"]["attend_event"]["outcomes"] if item.get("choice") == "mediate"),
    None,
)
if not mediate_preview:
    raise RuntimeError("Skill 解释接口应包含 mediate 结算预览")
mediate_debug_fields = {
    str(item.get("id")): str(item.get("value"))
    for item in mediate_preview.get("debugFields", [])
    if isinstance(item, dict) and item.get("id")
}
if mediate_debug_fields.get("styleSignal") != "mediate":
    raise RuntimeError("Skill 解释接口应返回 registry 声明的 mediate styleSignal")
skill_lifecycle_stages = {item["stage"] for item in app.debug_skills({"skillId": STARLIGHT_FESTIVAL_SHORTAGE_SKILL_ID})["items"][0]["lifecycle"]}
for required_stage in ("registered", "inspect", "attend_event", "event_reaction_debug", "night_reflection_debug"):
    if required_stage not in skill_lifecycle_stages:
        raise RuntimeError(f"Skill 生命周期快照缺少阶段：{required_stage}")

debug_turns = app.debug_turns({"feature": "event_reaction", "skillId": STARLIGHT_FESTIVAL_SHORTAGE_SKILL_ID, "limit": "5"})
if not debug_turns["items"] or not debug_turns["items"][-1]["summary"]:
    raise RuntimeError("Debug turns 查询应能解释 event_reaction")
assert_compact_debug_turns(debug_turns, "app.debug_turns")
memory_summary = app.memory_summary({"agentId": "kai", "limit": "4"})
if not memory_summary["items"] or "星灯祭" not in memory_summary["items"][0]["summary"]:
    raise RuntimeError("Memory Summary 应包含星灯祭记忆")
memory_search = app.memory_search({"query": "玩家", "tags": "night_reflection", "limit": "5"})
assert_memory_search_contract(memory_search, "app.memory_search")
if not memory_search["items"]:
    raise RuntimeError("RAG-lite 检索应能召回 night_reflection 记忆")
http_debug_summary = assert_http_debug_endpoints(app)
fallback_summary = assert_provider_fallback_debug()
assert_motivation_profile_weight_contract()
phase2_budget_summary = assert_phase2_decision_budget_routing()
phase2_observer_summary = assert_phase2_observer_visibility_scope()
phase2_failure_interrupt_summary = assert_phase2_failure_and_interrupt_trace()

tick_before_step = app.get_public_state()["clock"]["tick"]
step = app.step_simulation({"actorId": "smoke-test"})
state = step["state"]
if state["clock"]["tick"] != tick_before_step + 1:
    raise RuntimeError(f"期望 tick={tick_before_step + 1}，实际得到 {state['clock']['tick']}")
if len(state["events"]) < 3:
    raise RuntimeError("推进一轮后事件数量异常")

print(
    "[python-smoke] ok",
    {
        "agents": len(state["agents"]),
        "events": len(state["events"]),
        "tick": state["clock"]["tick"],
        "dialogueProfile": dialogue_debug["profileName"],
        "eventReactionProfile": event_reaction_debug["profileName"],
        "nightReflectionProfile": night_reflection_debug["profileName"],
        "followUpEvidence": follow_up_debug["memoryEvidenceUsed"]["source"],
        "gossipAccepted": accepted_record["accepted"],
        "gossipRejectedViolations": len(rejected_record.get("violations", [])),
        "debugSkills": http_debug_summary["debugSkills"],
        "memoryHits": http_debug_summary["memoryHits"],
        "influenceEvents": http_debug_summary["influenceEvents"],
        "fallbackItems": fallback_summary["fallbackItems"],
        "phase2Budget": phase2_budget_summary,
        "phase2Observers": phase2_observer_summary,
        "phase2FailureInterrupt": phase2_failure_interrupt_summary,
    },
)

if enable_real_llm_smoke():
    if not has_real_llm_config():
        raise RuntimeError("真实 LLM smoke 已启用，但未检测到 config/models.local.json 或 API key 环境变量。")
    llm_app = create_town_app(provider_mode="cloud")
    llm_talk = llm_app.player_action({"type": "talk", "targetId": "mira", "locationId": "plaza", "topic": "llm_smoke", "message": "能和我聊聊今晚的小镇吗？"})
    llm_dialogue_debug = assert_feature_debug(llm_app.get_public_state(), "dialogue")
    dialogue_error = real_cloud_check_error(llm_dialogue_debug, "dialogue")
    if dialogue_error:
        if require_real_llm_smoke():
            raise RuntimeError(dialogue_error)
        print(
            "[llm-smoke] fallback",
            {
                "reason": dialogue_error,
                "dialogue": llm_debug_summary(llm_dialogue_debug),
                "strictHint": "设置 AGENT_TOWN_REQUIRE_REAL_LLM_SMOKE=1 可要求真实云端 smoke 必须通过",
            },
        )
    else:
        llm_event = llm_app.player_action({"type": "attend_event", "eventId": "starlight_festival_shortage", "choice": "mediate"})
        llm_event_reaction_debug = assert_feature_debug(llm_app.get_public_state(), "event_reaction")
        llm_night_reflection_debug = assert_feature_debug(llm_app.get_public_state(), "night_reflection")
        event_error = real_cloud_check_error(llm_event_reaction_debug, "event_reaction")
        reflection_error = real_cloud_check_error(llm_night_reflection_debug, "night_reflection")
        strict_error = event_error or reflection_error
        if strict_error and require_real_llm_smoke():
            raise RuntimeError(strict_error)
        if strict_error:
            print(
                "[llm-smoke] fallback",
                {
                    "eventReactionError": event_error,
                    "nightReflectionError": reflection_error,
                    "dialogue": llm_debug_summary(llm_dialogue_debug),
                    "eventReaction": llm_debug_summary(llm_event_reaction_debug),
                    "nightReflection": llm_debug_summary(llm_night_reflection_debug),
                    "strictHint": "设置 AGENT_TOWN_REQUIRE_REAL_LLM_SMOKE=1 可要求真实云端 smoke 必须通过",
                },
            )
        else:
            print(
                "[llm-smoke]",
                {
                    "dialogue": llm_debug_summary(llm_dialogue_debug),
                    "eventReaction": llm_debug_summary(llm_event_reaction_debug),
                    "nightReflection": llm_debug_summary(llm_night_reflection_debug),
                    "dialoguePreview": llm_talk["result"]["dialogue"][0]["text"][:80],
                    "eventChoice": llm_event["result"]["eventResult"]["choice"],
                    "eventDialogueCount": len(llm_event["result"]["dialogue"]),
                    "nightReflectionCount": len(llm_event["state"]["nightReflections"]),
                },
            )
else:
    print("[llm-smoke] skipped: 默认跳过真实 LLM smoke；需要验收云端链路时运行 npm.cmd run llm:smoke。")
