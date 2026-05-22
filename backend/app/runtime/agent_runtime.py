from __future__ import annotations

import json
import os
from typing import Any

from app.config.model_config import ModelConfigStore
from app.content.codex_loader import (
    NpcDeepCard,
    compute_relationship_stage,
    load_all_npc_deep_cards,
    match_gift_reaction_tier,
)
from app.director import DirectorBeat, DirectorQueueManager, DirectorValidator, SkillRouter, TensionDetector, WorldDigest
from app.events.event_store import EventStore
from app.memory.heuristic import HeuristicLibrary
from app.memory.memory_store import memory_summary_payload, rag_lite_search, remember, world_memory_summaries
from app.memory.observer import ResultObserver
from app.memory.relationship_edges import RelationshipEdgeStore
from app.memory.subjective_memory import SubjectiveMemoryStore
from app.providers.cloud_api_provider import CloudApiProvider
from app.providers.context_builder import (
    build_agent_context,
    build_event_reaction_context,
    build_event_reaction_messages,
    build_night_reflection_context,
    build_night_reflection_messages,
    build_player_dialogue_context,
    build_player_dialogue_messages,
    build_prompt_messages,
    validate_gossip_propagation_payload,
)
from app.providers.provider_support import FEATURE_DIALOGUE, FEATURE_EVENT_REACTION, FEATURE_NIGHT_REFLECTION, sanitize_profile_for_debug
from app.providers.response_parser import parse_feature_response
from app.providers.rule_based_provider import RuleBasedProvider
from app.runtime.action_executor import execute_action, maybe_population_event
from app.runtime.action_parser import parse_provider_output
from app.runtime.capability_registry import CapabilityRegistry
from app.runtime.motivation_engine import MotivationEngine
from app.runtime.trace_schema import TRACE_SCHEMA_VERSION, build_trace_envelope, trace_event_snapshot, with_trace_payload, world_time_payload
from app.skills import (
    STARLIGHT_FESTIVAL_SHORTAGE_SKILL_ID,
    EventChoiceOutcome,
    EventPlayerOption,
    EventSkillDebugField,
    EventSkillSchema,
    find_event_choice_outcome,
    find_event_option,
    get_event_skill,
    list_event_skills,
)
from app.world.seed_data import DAY1_EVENT_ID, DAY1_LOCATION_IDS, DAY1_NPC_IDS
from app.world.world_state import (
    action_budget_for_phase,
    advance_clock,
    advance_phase,
    adjust_relation,
    build_npc_presence,
    create_initial_world,
    default_anchor_for_location,
    get_relation,
    living_agents,
    public_game_world,
    public_world,
    sync_agents_from_presence,
    sync_farm_interactables,
)
from app.tools import ToolExecutor


CLIENT_CONTEXT_FIELDS = ("memoryEvidence", "relationshipEvidence", "playerProfile", "currentObjective", "availableInteractions")


class _SafeFormatDict(dict[str, Any]):
    """Skill 模板格式化上下文，缺字段时保留占位符方便 Debug。"""

    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


class AgentRuntime:
    """后端核心运行时：时间、调度、Provider、行动、事件和 Debug 都由这里编排。"""

    def __init__(self, provider_mode: str | None = None, model_config_path: str | None = None) -> None:
        self.world = create_initial_world()
        self.world["clock"].setdefault("minute", 0)
        self.world["clock"].setdefault("_daySeconds", float((int(self.world["clock"].get("hour", 8)) - 8) * 3600))
        self.npc_deep_cards: dict[str, NpcDeepCard] = load_all_npc_deep_cards()
        self.event_store = EventStore()
        self.model_config = ModelConfigStore(model_config_path)
        self.rule_provider = RuleBasedProvider()
        self.cloud_provider = CloudApiProvider()
        self.capability_registry = CapabilityRegistry()
        self.motivation_engine = MotivationEngine(self.capability_registry)
        self.tool_executor = ToolExecutor(self.capability_registry.tool_registry)
        self.subjective_memory_store = SubjectiveMemoryStore()
        self.relationship_edge_store = RelationshipEdgeStore()
        self.heuristic_library = HeuristicLibrary()
        self.result_observer = ResultObserver()
        self.provider_mode_override = provider_mode
        self.provider_mode = self._resolve_runtime_provider_mode()
        self.event_skills = {skill.skill_id: skill for skill in list_event_skills()}
        self.tension_detector = TensionDetector()
        self.skill_router = SkillRouter()
        self.director_validator = DirectorValidator(
            allowed_skill_registry=list(self.event_skills),
            valid_target_agents=["player", *self.world["agents"].keys()],
        )
        self.director_queue = DirectorQueueManager(self.director_validator)
        self.world.setdefault("directorState", {"activatedEventSkills": [], "consumedBeatIds": []})
        self.event_store.append("system.ready", {"message": "Loomstead Python 运行时已启动。", "providerMode": self.provider_mode})

    def reload_model_config(self) -> dict[str, Any]:
        """热重载模型配置，避免每次调整 profile 后都重启开发服务器。"""
        model_config = self.model_config.reload()
        self.provider_mode = self._resolve_runtime_provider_mode()
        payload = {
            "providerMode": self.provider_mode,
            "activeProvider": model_config.get("activeProvider"),
            "defaultProfile": model_config.get("defaultProfile"),
            "localConfigLoaded": model_config.get("localConfigLoaded"),
            "validation": model_config.get("validation", {}),
        }
        event = self.event_store.append("model_config.reloaded", payload)
        return {"ok": True, "providerMode": self.provider_mode, "modelConfig": model_config, "event": event}

    def get_public_state(self) -> dict[str, Any]:
        state = public_world(self.world)
        state["events"] = self.event_store.list()
        state["snapshots"] = self.event_store.snapshots
        state["modelConfig"] = self.model_config.public_config()
        state["providerMode"] = self.provider_mode
        return state

    def get_game_state(self) -> dict[str, Any]:
        """输出游戏客户端状态，后续 Godot 只依赖这个契约。"""
        sync_farm_interactables(self.world)
        self.world["npcPresence"] = build_npc_presence(self.world)
        sync_agents_from_presence(self.world, self.world["npcPresence"])
        state = public_game_world(self.world, self.event_store.list())
        state["recentEvents"] = [self._debug_safe_event(event) for event in state.get("recentEvents", [])]
        state["activeEvents"] = self._skill_enriched_events(state.get("activeEvents", []))
        state["playerProfile"] = self._player_profile_payload()
        state["memoryEvidence"] = self._memory_evidence_payload()
        state["relationshipEvidence"] = self._relationship_evidence_payload()
        state["currentObjective"] = self._current_objective_payload()
        state["availableInteractions"] = self._available_interactions_payload()
        npc_schedules, motivation_plan = self._phase2_motivation_plan_snapshot()
        state["npcSchedules"] = npc_schedules
        state["lifeActionPlan"] = motivation_plan
        state.setdefault("slice", {})["scheduleSnapshotVersion"] = "motivation_plan.v1"
        return state

    def get_debug_snapshot(self, filters: dict[str, Any] | None = None) -> dict[str, Any]:
        """输出 Debug Console 查询用总览快照。"""
        filters = filters or {}
        return {
            "clock": dict(self.world["clock"]),
            "providerMode": self.provider_mode,
            "director": self.get_director_debug_snapshot(filters),
            "skills": self.get_skill_lifecycle_snapshot(filters),
            "debugTurns": self.get_debug_turns(filters),
            "memory": self.get_memory_debug(filters),
            "playerProfile": self._player_profile_payload(),
            "providerFallbacks": self._provider_fallback_debug(filters),
            "phase2": self.get_phase2_debug_snapshot(filters),
            "influenceChain": self.get_influence_chain_debug(filters),
        }

    def get_phase2_debug_snapshot(self, filters: dict[str, Any] | None = None) -> dict[str, Any]:
        filters = filters or {}
        npc_id = self._str_filter(filters, "agentId") or self._str_filter(filters, "agent_id")
        npc_ids = [npc_id] if npc_id else list(DAY1_NPC_IDS)
        world_tick = int(self.world.get("clock", {}).get("tick", 0)) if isinstance(self.world.get("clock"), dict) else 0
        return {
            "traceSchemaVersion": TRACE_SCHEMA_VERSION,
            "tools": self.capability_registry.tool_registry.to_debug_payload(),
            "needAccumulator": self.motivation_engine.need_accumulator.debug_snapshot(self.world, npc_ids=npc_ids, delta_minutes=20.0),
            "motivation": {"version": "motivation_engine.v0", "items": self._phase2_decisions(npc_ids[:6])},
            "toolRuntime": self._phase2_tool_runtime_snapshot(npc_ids),
            "subjectiveMemory": self.subjective_memory_store.debug_snapshot(agent_id=npc_id, limit=20),
            "relationshipEdges": self.relationship_edge_store.debug_snapshot(agent_id=npc_id, limit=30),
            "heuristics": self.heuristic_library.debug_snapshot(agent_id=npc_id, limit=20, world_tick=world_tick),
            "recentTraceEvents": self._phase2_recent_trace_events(filters),
        }

    def _phase2_motivation_plan_snapshot(self, npc_ids: list[str] | None = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        npc_ids = npc_ids or list(DAY1_NPC_IDS)
        clock = self.world.get("clock", {})
        schedules: list[dict[str, Any]] = []
        selected_actions: list[dict[str, Any]] = []
        for decision in self._phase2_decisions(npc_ids):
            planned = self.tool_executor.plan_action(self.world, decision)
            npc_id = str(planned.get("npcId") or "")
            agent = self.world.get("agents", {}).get(npc_id)
            if not npc_id or not isinstance(agent, dict):
                continue
            active_action = {
                "id": planned.get("toolId"),
                "toolId": planned.get("toolId"),
                "summary": planned.get("summary"),
                "timeWindow": "motivation_cycle",
                "primaryNeed": planned.get("primaryNeed"),
                "decision": decision.get("decision"),
                "spaceActionCandidates": [
                    {
                        "anchorId": planned.get("targetAnchorId"),
                        "locationId": planned.get("targetLocationId"),
                        "reason": "tool_target",
                    }
                ],
            }
            schedules.append(
                {
                    "npcId": npc_id,
                    "day": int(clock.get("day", 1)),
                    "phase": str(clock.get("phase") or "morning"),
                    "generatedAtTick": int(clock.get("tick", 0)),
                    "displayName": agent.get("name", npc_id),
                    "locationId": agent.get("locationId"),
                    "anchorId": agent.get("anchorId"),
                    "presenceSource": "motivation_engine",
                    "activeLifeAction": active_action,
                    "lifeActionCandidates": [active_action],
                    "rumorBeatCandidates": [],
                    "relationshipBeatCandidates": [],
                    "worldMutationPolicy": {"llmMayMutateWorld": False, "mutationPath": "ToolExecutor"},
                }
            )
            selected_actions.append(
                {
                    "npcId": npc_id,
                    "actionId": planned.get("toolId"),
                    "toolId": planned.get("toolId"),
                    "summary": planned.get("summary"),
                    "locationId": planned.get("targetLocationId"),
                    "anchorId": planned.get("targetAnchorId"),
                    "primaryNeed": planned.get("primaryNeed"),
                }
            )
        location_buckets: dict[str, list[str]] = {}
        for action in selected_actions:
            location_id = str(action.get("locationId") or "")
            location_buckets.setdefault(location_id, []).append(str(action.get("npcId") or ""))
        return schedules, {
            "version": "motivation_plan.v1",
            "day": int(clock.get("day", 1)),
            "phase": str(clock.get("phase") or "morning"),
            "generatedAtTick": int(clock.get("tick", 0)),
            "decisionSource": "MotivationEngine",
            "selectedActions": selected_actions,
            "locationBuckets": location_buckets,
            "policy": {"llmMayMutateWorld": False, "mutationPath": "ToolExecutor"},
            "legacyLifeActionExecutorActive": False,
        }

    def _phase2_decisions(self, npc_ids: list[str], delta_minutes: float = 20.0) -> list[dict[str, Any]]:
        decisions: list[dict[str, Any]] = []
        for npc_id in npc_ids:
            decisions.append(
                self.motivation_engine.evaluate_npc(
                    self.world,
                    npc_id,
                    delta_minutes=delta_minutes,
                    relationship_edges=[
                        edge.to_dict()
                        for edge in self.relationship_edge_store.list(agent_id=npc_id, limit=12)
                    ],
                    subjective_memory_records=self._phase2_subjective_memory_recall(npc_id),
                    heuristics=self._phase2_heuristic_recall(npc_id),
                )
            )
        return decisions

    def _phase2_subjective_memory_recall(self, npc_id: str, limit: int = 8) -> list[dict[str, Any]]:
        return [
            record.to_dict()
            for record in self.subjective_memory_store.recall(
                agent_id=npc_id,
                query="tool_result",
                limit=limit,
            )
        ]

    def _phase2_heuristic_recall(self, npc_id: str, limit: int = 8) -> list[dict[str, Any]]:
        world_tick = int(self.world.get("clock", {}).get("tick", 0)) if isinstance(self.world.get("clock"), dict) else 0
        return [
            item.to_dict(world_tick=world_tick)
            for item in self.heuristic_library.list(agent_id=npc_id, limit=limit)
        ]

    def _phase2_tool_runtime_snapshot(self, npc_ids: list[str]) -> dict[str, Any]:
        runtime_state = self.world.get("toolRuntime", {}) if isinstance(self.world.get("toolRuntime"), dict) else {}
        items = []
        for npc_id in npc_ids:
            state = runtime_state.get(npc_id)
            if not isinstance(state, dict):
                continue
            items.append(
                {
                    "npcId": npc_id,
                    "toolId": state.get("toolId"),
                    "phase": state.get("phase"),
                    "targetAnchorId": state.get("targetAnchorId"),
                    "targetLocationId": state.get("targetLocationId"),
                    "moveProgress": round(float(state.get("moveProgress", 0.0)), 3),
                    "elapsedSeconds": round(float(state.get("actionElapsedSeconds", 0.0)), 2),
                    "durationSeconds": round(float(state.get("actionDurationSeconds", 0.0)), 2),
                    "contributingSources": list(state.get("contributingSources") or []),
                }
            )
        return {"version": "tool_runtime.v1", "items": items}

    def _phase2_recent_trace_events(self, filters: dict[str, Any]) -> list[dict[str, Any]]:
        limit = self._int_filter(filters, "limit", 20)
        agent_id_filter = self._str_filter(filters, "agentId") or self._str_filter(filters, "agent_id")
        event_type_filter = self._str_filter(filters, "eventType") or self._str_filter(filters, "event_type")
        trace_types = {"tool.execution_completed", "tool.execution_failed", "memory.result_observed"}
        items: list[dict[str, Any]] = []
        for event in self.event_store.list():
            event_type = str(event.get("type") or "")
            if event_type_filter and event_type != event_type_filter:
                continue
            payload = event.get("payload", {}) if isinstance(event.get("payload"), dict) else {}
            if event_type not in trace_types and not payload.get("traceSchemaVersion"):
                continue
            snapshot = trace_event_snapshot(event)
            if agent_id_filter and str(snapshot.get("agentId") or "") != agent_id_filter and agent_id_filter not in snapshot.get("targetIds", []):
                continue
            items.append(snapshot)
        return items[-limit:]

    def get_director_debug_snapshot(self, filters: dict[str, Any] | None = None) -> dict[str, Any]:
        """输出 Director Digest、Beat 队列和生命周期事件。"""
        filters = filters or {}
        limit = self._int_filter(filters, "limit", 30)
        digest = WorldDigest.from_world(self.world)
        director_state = self.world.setdefault("directorState", {"activatedEventSkills": [], "consumedBeatIds": []})
        beat_events = [
            self._director_beat_event_payload(event)
            for event in self.event_store.list()
            if str(event.get("type", "")).startswith("director.")
        ]
        return {
            "digest": self._director_digest_payload(digest),
            "state": {
                "activatedEventSkills": list(director_state.get("activatedEventSkills", [])),
                "consumedBeatIds": list(director_state.get("consumedBeatIds", [])),
                "activeFocus": self.world.get("activeFocus"),
            },
            "queue": {
                "pendingCount": len(self.director_queue.pending),
                "pending": [beat.to_dict() for beat in self.director_queue.pending],
            },
            "lifecycle": beat_events[-limit:],
        }

    def get_skill_lifecycle_snapshot(self, filters: dict[str, Any] | None = None) -> dict[str, Any]:
        """输出 Event Skill 注册、激活、查看、结算与 Debug 生命周期。"""
        filters = filters or {}
        skill_filter = self._str_filter(filters, "skillId") or self._str_filter(filters, "skill_id")
        items = []
        for skill in list_event_skills():
            if skill_filter and skill.skill_id != skill_filter:
                continue
            items.append(self._event_skill_snapshot(skill))
        return {"skillId": skill_filter, "items": items}

    def get_debug_turns(self, filters: dict[str, Any] | None = None) -> dict[str, Any]:
        """按 feature / skillId 查询 Provider Debug 记录。"""
        filters = filters or {}
        feature = self._str_filter(filters, "feature")
        skill_id = self._str_filter(filters, "skillId") or self._str_filter(filters, "skill_id")
        limit = self._int_filter(filters, "limit", 20)
        turns: list[dict[str, Any]] = []
        for event in self.event_store.list():
            debug = event.get("payload", {}).get("debug")
            if not isinstance(debug, dict):
                continue
            if feature and debug.get("feature") != feature:
                continue
            if skill_id and not self._debug_matches_skill(debug, skill_id):
                continue
            turns.append(self._debug_turn_payload(event, debug))
        return {"feature": feature, "skillId": skill_id, "limit": limit, "items": turns[-limit:]}

    def get_memory_debug(self, filters: dict[str, Any] | None = None) -> dict[str, Any]:
        """输出 Memory Summary 和 RAG-lite 检索结果。"""
        filters = filters or {}
        agent_id = self._str_filter(filters, "agentId") or self._str_filter(filters, "agent_id")
        query = self._str_filter(filters, "q") or self._str_filter(filters, "query") or ""
        tags = self._str_filter(filters, "tags")
        limit = self._int_filter(filters, "limit", 8)
        return {
            "summaries": world_memory_summaries(self.world, agent_id=agent_id, limit=min(limit, 12)),
            "retrieval": rag_lite_search(self.world, query=query, agent_id=agent_id, tags=tags, limit=limit),
        }

    def get_influence_chain_debug(self, filters: dict[str, Any] | None = None) -> dict[str, Any]:
        """解释玩家动作如何影响记忆、关系、事件技能和模型兜底。"""
        filters = filters or {}
        skill_id = self._str_filter(filters, "skillId") or self._str_filter(filters, "skill_id")
        event_id = self._str_filter(filters, "eventId") or self._str_filter(filters, "event_id") or DAY1_EVENT_ID
        if not skill_id:
            try:
                skill_id = self._get_event_skill_for_event(event_id).skill_id
            except ValueError:
                skill_id = None
        memory_filters = dict(filters)
        memory_filters.setdefault("query", "星灯祭 玩家")
        if event_id:
            memory_filters.setdefault("tags", event_id)
        return {
            "filters": {"skillId": skill_id, "eventId": event_id, "agentId": self._str_filter(filters, "agentId") or self._str_filter(filters, "agent_id")},
            "playerProfile": self._player_profile_payload(),
            "memory": self.get_memory_debug(memory_filters),
            "relations": self._relationship_debug(filters),
            "skill": self.explain_event_skill({"skillId": skill_id}) if skill_id else None,
            "providerFallbacks": self._provider_fallback_debug(filters),
            "events": self._influence_event_debug(filters, skill_id=skill_id, event_id=event_id),
        }

    def _enrich_player_action_result(
        self,
        action_type: str,
        payload: dict[str, Any],
        result: dict[str, Any],
        state: dict[str, Any],
    ) -> dict[str, Any]:
        """补齐 Godot 可直接读取的玩家动作回执字段。"""
        enriched = dict(result)
        enriched["playerProfile"] = enriched.get("playerProfile") or state.get("playerProfile") or self._player_profile_payload()
        enriched["memoryEvidence"] = self._memory_evidence_payload(action_type=action_type, payload=payload, action_result=enriched)
        enriched["relationshipEvidence"] = self._relationship_evidence_payload(payload=payload, action_result=enriched)
        enriched["currentObjective"] = state.get("currentObjective") or self._current_objective_payload()
        enriched["availableInteractions"] = state.get("availableInteractions") or self._available_interactions_payload()
        return enriched

    def _memory_evidence_payload(
        self,
        *,
        action_type: str | None = None,
        payload: dict[str, Any] | None = None,
        action_result: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """整理 Godot 展示记忆证据需要的摘要、检索命中和本次写入。"""
        payload = payload or {}
        action_result = action_result or {}
        existing = action_result.get("memoryEvidence") if isinstance(action_result.get("memoryEvidence"), dict) else None
        target_id = str(payload.get("targetId") or "")
        target_id = target_id if target_id in self.world.get("agents", {}) else None
        query = self._memory_evidence_query(action_type, payload, action_result)

        if existing:
            evidence = dict(existing)
            evidence.setdefault("scope", "action")
            evidence.setdefault("targetId", target_id)
            evidence.setdefault("query", query)
        else:
            retrieval = rag_lite_search(self.world, query=query, agent_id=target_id, limit=5)
            if target_id:
                summary_key = "summary"
                summary_value: Any = memory_summary_payload(target_id, self.world["agents"][target_id], limit=8)
            else:
                summary_key = "summaries"
                visible_ids = {"player", *DAY1_NPC_IDS}
                summary_value = [
                    item
                    for item in world_memory_summaries(self.world, limit=4)["items"]
                    if item.get("agentId") in visible_ids
                ]
            evidence = {
                "scope": "target" if target_id else "world",
                "targetId": target_id,
                "query": retrieval.get("query", query),
                summary_key: summary_value,
                "ragHits": retrieval.get("items", []),
            }

        evidence["recentWrites"] = self._recent_memory_evidence_events()
        if action_result.get("memoryWrites"):
            evidence["writes"] = list(action_result.get("memoryWrites", []))
        if action_result.get("memoryEvidenceUsed"):
            evidence["used"] = action_result["memoryEvidenceUsed"]
        return evidence

    def _memory_evidence_query(self, action_type: str | None, payload: dict[str, Any], action_result: dict[str, Any]) -> str:
        """根据动作上下文选择轻量检索词，方便客户端解释命中来源。"""
        event_result = action_result.get("eventResult") if isinstance(action_result.get("eventResult"), dict) else {}
        if event_result.get("summary"):
            return str(event_result["summary"])
        inspect_payload = action_result.get("inspect") if isinstance(action_result.get("inspect"), dict) else {}
        if inspect_payload.get("summary"):
            return str(inspect_payload["summary"])
        topic = str(payload.get("topic") or "").strip()
        message = str(payload.get("message") or "").strip()
        if topic or message:
            return " ".join(part for part in (topic, message) if part)
        if action_type in {"attend_event", "inspect"} or self.world["player"].get("questFlags", {}).get(DAY1_EVENT_ID):
            return "星灯祭 玩家"
        return ""

    def _recent_memory_evidence_events(self, limit: int = 8) -> list[dict[str, Any]]:
        """从事件流提取最近记忆写入，避免 Godot 再解析完整 recentEvents。"""
        memory_types = {"npc.memory_created", "npc.night_reflection", "player.profile_updated"}
        items: list[dict[str, Any]] = []
        for event in self.event_store.list():
            if event.get("type") not in memory_types:
                continue
            payload = event.get("payload", {})
            items.append(
                {
                    "eventId": event.get("id"),
                    "eventType": event.get("type"),
                    "createdAt": event.get("createdAt"),
                    "agentId": payload.get("agentId"),
                    "agentName": payload.get("agentName"),
                    "text": payload.get("text"),
                    "tags": list(payload.get("tags", [])) if isinstance(payload.get("tags"), list) else [],
                    "skillId": payload.get("skillId"),
                    "sourceEventId": payload.get("eventId"),
                }
            )
        return items[-limit:]

    def _relationship_evidence_payload(
        self,
        *,
        payload: dict[str, Any] | None = None,
        action_result: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """整理玩家和首发 NPC 的关系快照、本次变化与近期变化。"""
        payload = payload or {}
        action_result = action_result or {}
        target_id = str(payload.get("targetId") or "")
        target_id = target_id if target_id in self.world.get("agents", {}) else None
        changes = list(action_result.get("relationshipDeltas", [])) if isinstance(action_result.get("relationshipDeltas"), list) else []
        focus_ids = {target_id} if target_id else {str(item.get("targetId")) for item in changes if isinstance(item, dict) and item.get("targetId")}

        current = []
        for npc_id in self._visible_npc_ids():
            agent = self.world["agents"][npc_id]
            current.append(
                {
                    "targetId": npc_id,
                    "targetName": agent.get("name", npc_id),
                    "focused": npc_id in focus_ids,
                    "relation": get_relation(self.world, "player", npc_id),
                }
            )

        return {
            "scope": "target" if target_id else "world",
            "targetId": target_id,
            "current": current,
            "changes": changes,
            "recentChanges": self._recent_relationship_events(),
        }

    def _recent_relationship_events(self, limit: int = 8) -> list[dict[str, Any]]:
        """从事件流提取关系变化，供客户端直接渲染变化列表。"""
        items: list[dict[str, Any]] = []
        for event in self.event_store.list():
            if event.get("type") != "relationship.changed":
                continue
            items.append({"eventId": event.get("id"), "createdAt": event.get("createdAt"), "payload": event.get("payload", {})})
        return items[-limit:]

    def _current_objective_payload(self) -> dict[str, Any]:
        """输出当前玩家目标，帮助 Godot 展示下一步引导。"""
        for event in self.world.get("activeEvents", []):
            if event.get("id") != DAY1_EVENT_ID:
                continue
            skill = self._get_event_skill_for_event(str(event.get("id")))
            if event.get("status") == "resolved":
                resolution = event.get("resolution", {}) if isinstance(event.get("resolution"), dict) else {}
                return {
                    "id": f"follow_up:{skill.event_id}",
                    "type": "follow_up",
                    "status": "active",
                    "title": "回访星灯祭后的居民",
                    "summary": resolution.get("summary") or "星灯祭供应短缺已经结算，可以继续观察居民记忆和关系变化。",
                    "eventId": skill.event_id,
                    "skillId": skill.skill_id,
                    "locationId": skill.trigger.location_id,
                    "targetNpcIds": [agent_id for agent_id in skill.participants if agent_id in self.world["agents"]],
                    "nextAction": {"type": "talk", "targetId": "kai", "locationId": skill.trigger.location_id, "topic": "starlight_follow_up"},
                }

            inspected = bool(self.world["player"].get("questFlags", {}).get(f"inspected_{skill.event_id}"))
            next_action = {"type": "attend_event", "eventId": skill.event_id, "choice": self._default_event_choice(skill), "locationId": skill.trigger.location_id}
            if not inspected:
                next_action = {"type": "inspect", "eventId": skill.event_id, "locationId": skill.trigger.location_id}
            return {
                "id": f"resolve:{skill.event_id}",
                "type": "event",
                "status": event.get("status", "available"),
                "title": skill.title,
                "summary": skill.brief,
                "eventId": skill.event_id,
                "skillId": skill.skill_id,
                "locationId": skill.trigger.location_id,
                "targetNpcIds": [agent_id for agent_id in skill.participants if agent_id in self.world["agents"]],
                "progress": {"inspected": inspected, "resolved": False},
                "nextAction": next_action,
            }

        first_npc = self._visible_npc_ids()[0] if self._visible_npc_ids() else None
        return {
            "id": "meet_townsfolk",
            "type": "social",
            "status": "active",
            "title": "认识小镇居民",
            "summary": "先和首发居民聊天，积累玩家风格、关系与记忆证据。",
            "targetNpcIds": self._visible_npc_ids(),
            "nextAction": {"type": "talk", "targetId": first_npc, "locationId": self.world["player"].get("locationId"), "topic": "first_meeting"} if first_npc else None,
        }

    def _available_interactions_payload(self) -> list[dict[str, Any]]:
        """列出 Godot 可直接渲染成按钮的后端动作。"""
        interactions: list[dict[str, Any]] = []
        player_location = self.world["player"].get("locationId")

        for location_id in DAY1_LOCATION_IDS:
            location = self.world["locations"].get(location_id)
            if not location:
                continue
            interactions.append(
                {
                    "id": f"move:{location_id}",
                    "type": "move",
                    "label": f"前往{location['name']}",
                    "enabled": location_id != player_location,
                    "reason": "already_here" if location_id == player_location else None,
                    "target": {"kind": "location", "id": location_id, "name": location["name"]},
                    "payload": {"type": "move", "locationId": location_id},
                }
            )
            for anchor in self.world.get("anchors", {}).values():
                if anchor.get("locationId") != location_id:
                    continue
                same_anchor = self.world["player"].get("anchorId") == anchor.get("id")
                interactions.append(
                    {
                        "id": f"move_to_anchor:{anchor['id']}",
                        "type": "move_to_anchor",
                        "label": f"移动到{location['name']}：{anchor['kind']}",
                        "enabled": not same_anchor and self._player_action_budget() > 0,
                        "reason": "already_here" if same_anchor else ("no_action_budget" if self._player_action_budget() <= 0 else None),
                        "target": {"kind": "anchor", "id": anchor["id"], "locationId": location_id, "screenPosition": anchor.get("screenPosition")},
                        "payload": {"type": "move_to_anchor", "locationId": location_id, "anchorId": anchor["id"]},
                    }
                )

        gift_items = [item for item in self.world["player"].get("inventory", []) if int(item.get("quantity", 0)) > 0 and "gift" in item.get("tags", [])]
        # 首版事件会用到 fresh_turnip，默认送礼优先选择不影响事件选项的物品。
        gift_items.sort(key=lambda item: (item.get("id") == "fresh_turnip", str(item.get("id", ""))))
        first_gift = gift_items[0] if gift_items else None
        for npc_id in self._visible_npc_ids():
            npc = self.world["agents"][npc_id]
            interactions.append(
                {
                    "id": f"talk:{npc_id}",
                    "type": "talk",
                    "label": f"和{npc['name']}聊天",
                    "enabled": bool(npc.get("alive", True)),
                    "target": {"kind": "npc", "id": npc_id, "name": npc["name"], "locationId": npc.get("locationId")},
                    "payload": {"type": "talk", "targetId": npc_id, "locationId": npc.get("locationId"), "topic": "first_meeting"},
                }
            )
            interactions.append(
                {
                    "id": f"give_gift:{npc_id}",
                    "type": "give_gift",
                    "label": f"送礼给{npc['name']}",
                    "enabled": bool(first_gift and npc.get("alive", True)),
                    "reason": None if first_gift else "no_gift_item",
                    "target": {"kind": "npc", "id": npc_id, "name": npc["name"], "locationId": npc.get("locationId")},
                    "payload": {"type": "give_gift", "targetId": npc_id, "locationId": npc.get("locationId"), "itemId": first_gift.get("id") if first_gift else None},
                    }
                )
        for plot in self.world.get("farmPlots", {}).values():
            farm_action = self._next_farm_action_for_plot(plot)
            if not farm_action:
                continue
            at_plot_anchor = self.world["player"].get("locationId") == plot.get("locationId") and self.world["player"].get("anchorId") == plot.get("anchorId")
            has_required_item = farm_action != "plant" or self._player_item_quantity(plot.get("seedItemId")) > 0
            enabled = at_plot_anchor and has_required_item and self._player_action_budget() > 0
            reason = None
            if not at_plot_anchor:
                reason = "not_near_plot"
            elif not has_required_item:
                reason = f"missing_item:{plot.get('seedItemId')}"
            elif self._player_action_budget() <= 0:
                reason = "no_action_budget"
            interactions.append(
                {
                    "id": f"farm_action:{plot['id']}:{farm_action}",
                    "type": "farm_action",
                    "label": self._farm_action_label(farm_action, str(plot["id"])),
                    "enabled": enabled,
                    "reason": reason,
                    "target": {"kind": "farm_plot", "id": plot["id"], "locationId": plot.get("locationId"), "anchorId": plot.get("anchorId")},
                    "payload": {
                        "type": "farm_action",
                        "locationId": plot.get("locationId"),
                        "interactableId": plot["id"],
                        "action": farm_action,
                        "itemId": plot.get("seedItemId") if farm_action == "plant" else None,
                    },
                }
            )
            interactions.append(
                {
                    "id": f"scene_action:{plot['id']}:{farm_action}",
                    "type": "scene_action",
                    "label": self._farm_action_label(farm_action, str(plot["id"])),
                    "enabled": enabled,
                    "reason": reason,
                    "target": {"kind": "farm_plot", "id": plot["id"], "locationId": plot.get("locationId"), "anchorId": plot.get("anchorId")},
                    "payload": {
                        "type": "scene_action",
                        "locationId": plot.get("locationId"),
                        "interactableId": plot["id"],
                        "action": farm_action,
                        "itemId": plot.get("seedItemId") if farm_action == "plant" else None,
                    },
                }
            )

        for interactable in self.world.get("interactables", {}).values():
            if str(interactable.get("kind") or "") == "farm_plot":
                continue
            actions = [str(action) for action in interactable.get("actions", []) if str(action)]
            if "inspect" not in actions:
                continue
            location_id = str(interactable.get("locationId") or "")
            anchor_id = str(interactable.get("anchorId") or "")
            at_anchor = self.world["player"].get("locationId") == location_id and self.world["player"].get("anchorId") == anchor_id
            interactions.append(
                {
                    "id": f"scene_action:{interactable['id']}:inspect",
                    "type": "scene_action",
                    "label": self._scene_action_label("inspect", interactable),
                    "enabled": at_anchor,
                    "reason": None if at_anchor else "not_near_anchor",
                    "target": {"kind": str(interactable.get("kind") or "interactable"), "id": interactable["id"], "locationId": location_id, "anchorId": anchor_id},
                    "payload": {
                        "type": "scene_action",
                        "locationId": location_id,
                        "interactableId": interactable["id"],
                        "action": "inspect",
                    },
                }
            )

        for event in self.world.get("activeEvents", []):
            if event.get("status") == "resolved":
                continue
            try:
                skill = self._get_event_skill_for_event(str(event.get("id") or ""))
            except ValueError:
                continue
            interactions.append(
                {
                    "id": f"inspect:{skill.event_id}",
                    "type": "inspect",
                    "label": f"查看事件：{skill.title}",
                    "enabled": True,
                    "target": {"kind": "event", "id": skill.event_id, "name": skill.title, "locationId": skill.trigger.location_id},
                    "payload": {"type": "inspect", "eventId": skill.event_id, "locationId": skill.trigger.location_id},
                }
            )
            for option in skill.player_options:
                has_required_item = option.requires_player_item_id is None or self._player_item_quantity(option.requires_player_item_id) > 0
                interactions.append(
                    {
                        "id": f"attend_event:{skill.event_id}:{option.option_id}",
                        "type": "attend_event",
                        "label": option.label,
                        "enabled": has_required_item,
                        "reason": None if has_required_item else f"missing_item:{option.requires_player_item_id}",
                        "target": {"kind": "event", "id": skill.event_id, "name": skill.title, "locationId": skill.trigger.location_id},
                        "payload": {"type": "attend_event", "eventId": skill.event_id, "choice": option.option_id, "locationId": skill.trigger.location_id},
                    }
                )
        interactions.append(
            {
                "id": "end_phase",
                "type": "end_phase",
                "label": "结束当前时段",
                "enabled": True,
                "target": {"kind": "clock", "phase": self.world["clock"].get("phase"), "day": self.world["clock"].get("day")},
                "payload": {"type": "end_phase"},
            }
        )
        return interactions

    def _visible_npc_ids(self) -> list[str]:
        """返回 Godot 首版切片内可见 NPC id。"""
        return [npc_id for npc_id in DAY1_NPC_IDS if npc_id in self.world.get("agents", {})]

    def _player_item_quantity(self, item_id: str | None) -> int:
        """读取玩家背包中指定物品数量，供交互按钮判定可用性。"""
        if not item_id:
            return 0
        for item in self.world["player"].get("inventory", []):
            if item.get("id") == item_id:
                return int(item.get("quantity", 0))
        return 0

    def _player_action_budget(self) -> int:
        """读取当前时段剩余玩家行动预算，缺失时按 phase 自动补齐。"""
        clock = self.world.setdefault("clock", {})
        if "actionBudget" not in clock:
            clock["actionBudget"] = action_budget_for_phase(str(clock.get("phase") or "morning"))
        return int(clock.get("actionBudget", 0))

    def _consume_player_action_budget(self, action_type: str) -> dict[str, int | str]:
        """消费一个玩家行动预算，预算不足时阻止地图玩法动作。"""
        before = self._player_action_budget()
        if before <= 0:
            raise ValueError(f"{action_type} 需要行动预算，请先结束当前时段")
        self.world["clock"]["actionBudget"] = before - 1
        return {"before": before, "after": before - 1, "actionType": action_type}

    def _assert_player_at_anchor(self, location_id: str, anchor_id: str) -> None:
        """校验玩家是否靠近目标锚点，保证 farm_action 真的来自地图交互。"""
        player = self.world["player"]
        if player.get("locationId") != location_id or player.get("anchorId") != anchor_id:
            raise ValueError(f"玩家需要先移动到锚点 {anchor_id} 才能交互")

    def _next_farm_action_for_plot(self, plot: dict[str, Any]) -> str | None:
        """根据田块阶段选择客户端下一步可展示的农场动作。"""
        stage = plot.get("stage")
        if stage == "empty":
            return "plant"
        if stage == "planted":
            return "water"
        if stage == "harvestable":
            return "harvest"
        return None

    def _farm_action_label(self, action: str, plot_id: str) -> str:
        """把农场动作转成 Godot 可直接显示的简短文案。"""
        labels = {"plant": "播种", "water": "浇水", "harvest": "收获"}
        return f"{labels.get(action, action)} {plot_id}"

    def _scene_action_label(self, action: str, interactable: dict[str, Any]) -> str:
        """把通用场景交互体转成客户端按钮文案。"""
        kind = str(interactable.get("kind") or "interactable")
        kind_labels = {
            "notice_board": "公告板",
            "event_marker": "事件点",
            "service_spot": "服务点",
            "interactable": "互动点",
        }
        action_labels = {"inspect": "查看", "attend_event": "参与"}
        return f"{action_labels.get(action, action)}{kind_labels.get(kind, kind)}"

    def explain_event_skill(self, filters: dict[str, Any] | None = None) -> dict[str, Any]:
        """解释单个 Event Skill 在 API / Debug Console 中如何被追踪。"""
        filters = filters or {}
        skill_id = self._str_filter(filters, "skillId") or self._str_filter(filters, "skill_id") or STARLIGHT_FESTIVAL_SHORTAGE_SKILL_ID
        skill = get_event_skill(skill_id)
        outcome_previews = []
        for option in skill.player_options:
            outcome = self._resolve_event_skill_outcome(skill, option, None)
            outcome_previews.append(
                {
                    "choice": option.option_id,
                    "choiceLabel": outcome["choiceLabel"],
                    "summary": outcome["summary"],
                    "consequenceTypes": outcome["consequenceTypes"],
                    "relationDeltas": outcome["relationDeltas"],
                    "memoryTemplateCount": len(outcome["memoryTemplates"]),
                    "reflectionSeedCount": len(outcome["reflectionSeeds"]),
                    "debugFields": outcome["debugFields"],
                }
            )
        return {
            "skill": self._event_skill_manifest_payload(skill),
            "actions": {
                "inspect": {
                    "api": "POST /api/player/action",
                    "payload": {"type": "inspect", "eventId": skill.event_id},
                    "debugFields": self._skill_debug_payload(skill, None, choice="inspect"),
                },
                "attend_event": {
                    "api": "POST /api/player/action",
                    "payloadExample": {"type": "attend_event", "eventId": skill.event_id, "choice": skill.player_options[0].option_id},
                    "outcomes": outcome_previews,
                },
                "event_reaction": {
                    "debugQuery": f"/api/debug/turns?feature=event_reaction&skillId={skill.skill_id}",
                    "latest": self.get_debug_turns({"feature": "event_reaction", "skillId": skill.skill_id, "limit": 1})["items"],
                },
                "night_reflection": {
                    "debugQuery": f"/api/debug/turns?feature=night_reflection&skillId={skill.skill_id}",
                    "latest": self.get_debug_turns({"feature": "night_reflection", "skillId": skill.skill_id, "limit": 1})["items"],
                },
            },
            "lifecycle": self._event_skill_lifecycle(skill),
            "memoryRetrieval": {
                "summaryEndpoint": "/api/memory/summary",
                "searchEndpoint": f"/api/memory/search?q={skill.event_id}&tags={skill.event_id}",
            },
        }

    def handle_player_action(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """处理玩家动作入口，所有结果都写入事件流和玩家行动历史。"""
        payload = payload or {}
        action_type = payload.get("type")
        if action_type == "move":
            result = self._handle_player_move(payload)
        elif action_type == "move_to_anchor":
            result = self._handle_player_move_to_anchor(payload)
        elif action_type == "scene_action":
            result = self._handle_player_scene_action(payload)
        elif action_type == "farm_action":
            result = self._handle_player_farm_action(payload)
        elif action_type == "end_phase":
            result = self._handle_player_end_phase(payload)
        elif action_type == "talk":
            result = self._handle_player_talk(payload)
        elif action_type == "give_gift":
            result = self._handle_player_gift(payload)
        elif action_type == "inspect":
            result = self._handle_player_inspect(payload)
        elif action_type == "attend_event":
            result = self._handle_player_attend_event(payload)
        else:
            raise ValueError(f"未知玩家动作：{action_type}")
        state = self.get_game_state()
        result = self._enrich_player_action_result(str(action_type), payload, result, state)
        response = {"ok": True, "result": result, "state": state}
        # 为 Godot 首版接入降低取值成本：动作回执根节点同步透出常用展示字段。
        for field in CLIENT_CONTEXT_FIELDS:
            response[field] = result[field]
        return response

    def step(self, actor_id: str = "developer") -> dict[str, Any]:
        if self.world["clock"].get("paused"):
            return {"skipped": True, "reason": "paused", "state": self.get_public_state()}
        self._run_director_v0()
        actors = self.pick_actors()
        decisions = []
        for agent in actors:
            context = build_agent_context(self.world, agent, self.event_store)
            messages = build_prompt_messages(context)
            profile = self.model_config.resolve_profile(agent_id=agent["id"], feature="agent_decision")
            result, fallback_reason = self._call_profile_provider(
                feature="agent_decision",
                agent=agent,
                context=context,
                messages=messages,
                profile=profile,
                rule_call=lambda: self.rule_provider.decide(context, messages),
            )
            parsed = parse_provider_output(result)
            executed = execute_action(self.world, agent, parsed, self.event_store)
            debug = self._build_provider_debug(
                feature="agent_decision",
                profile=profile,
                messages=messages,
                result=result,
                parsed=parsed,
                fallback_reason=fallback_reason,
                executed=executed["payload"],
            )
            agent.setdefault("decisionHistory", []).append(debug)
            agent["decisionHistory"] = agent["decisionHistory"][-10:]
            self.event_store.append("debug.decision", {"agentId": agent["id"], "agentName": agent["name"], "debug": debug})
            decisions.append(debug)
        maybe_population_event(self.world, self.event_store)
        advance_clock(self.world)
        self.event_store.add_snapshot(self.world)
        self.event_store.append("runtime.step", {"actorId": actor_id, "tick": self.world["clock"]["tick"], "day": self.world["clock"]["day"], "hour": self.world["clock"]["hour"], "actors": [agent["id"] for agent in actors]})
        return {"decisions": decisions, "state": self.get_public_state()}

    def tick(self, delta_seconds: float, speed: float = 1.0) -> dict[str, Any]:
        """按游戏时间推进 NPC 行动并输出最小事件/差异快照。"""
        if self.world["clock"].get("paused"):
            return {"clock": self._tick_clock_payload(), "events": [], "agents": [], "skipped": True, "reason": "paused"}

        game_seconds = max(0.0, float(delta_seconds)) * max(0.0, float(speed))
        self._advance_clock_by_game_seconds(game_seconds)
        if not isinstance(self.world.get("npcPresence"), list) or not self.world["npcPresence"]:
            self.world["npcPresence"] = build_npc_presence(self.world)
            sync_agents_from_presence(self.world, self.world["npcPresence"])

        tick_events: list[dict[str, Any]] = []
        decisions = self._record_phase2_decision_events(
            self._phase2_decisions(list(DAY1_NPC_IDS), delta_minutes=20.0),
            tick_events=tick_events,
        )
        execution = self.tool_executor.tick(
            world=self.world,
            decisions=decisions,
            delta_seconds=game_seconds,
        )

        completion_event_ids: dict[tuple[str, str], str] = {}
        for payload in execution.get("events", []):
            event_type = str(payload.get("type") or "")
            if not event_type:
                continue
            stored = self.event_store.append(event_type, {key: value for key, value in payload.items() if key != "type"})
            tick_events.append(stored)
            if event_type == "npc.action_completed":
                completion_event_ids[(str(payload.get("npcId") or ""), str(payload.get("toolId") or payload.get("actionId") or ""))] = str(stored.get("id") or "")

        for completion in execution.get("completedActions", []):
            source_event_id = completion_event_ids.get((str(completion.get("npcId") or ""), str(completion.get("toolId") or completion.get("actionId") or "")))
            completion_event = self.tool_executor.apply_completion(world=self.world, completion=completion, event_store=self.event_store, source_event_id=source_event_id)
            tick_events.append(completion_event)
            observation = self.result_observer.distribute(
                world=self.world,
                event=completion_event,
                subjective_memory=self.subjective_memory_store,
                relationship_edges=self.relationship_edge_store,
                heuristic_library=self.heuristic_library,
            )
            # 主观记忆与关系边也进入 EventStore，保证 Eval / Debug 能从同一条事件流回放因果。
            tick_events.append(self.event_store.append("memory.result_observed", observation))

        self._run_director_v0()
        self.event_store.add_snapshot(self.world)
        self.event_store.append(
            "runtime.tick",
            {
                "deltaSeconds": round(game_seconds, 3),
                "speed": round(max(0.0, float(speed)), 3),
                "tick": self.world["clock"]["tick"],
                "phase": self.world["clock"]["phase"],
                "npcEventCount": len(tick_events),
                "agentDiffCount": len(execution.get("agents", [])),
            },
        )
        return {
            "clock": self._tick_clock_payload(),
            "events": [self._debug_safe_event(event) for event in tick_events],
            "agents": execution.get("agents", []),
        }

    def _record_phase2_decision_events(self, decisions: list[dict[str, Any]], *, tick_events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """把 MotivationEngine 决策写入 EventStore，并把 trace ref 传给后续 ToolExecutor。"""
        enriched_decisions: list[dict[str, Any]] = []
        for decision in decisions:
            if not isinstance(decision, dict) or not isinstance(decision.get("decision"), dict):
                enriched_decisions.append(decision)
                continue
            payload = self._phase2_decision_trace_payload(decision)
            event = self.event_store.append(
                "motivation.decision_made",
                with_trace_payload(
                    payload,
                    build_trace_envelope(
                        event_type="motivation.decision_made",
                        summary=str(payload.get("summary") or "NPC 决策已生成"),
                        world_time=world_time_payload(self.world),
                        agent_id=str(decision.get("npcId") or ""),
                        target_ids=self._phase2_decision_target_ids(decision),
                    ),
                ),
            )
            tick_events.append(event)
            enriched = dict(decision)
            decision_payload = dict(decision.get("decision") or {})
            trace_payload = event.get("payload", {}) if isinstance(event.get("payload"), dict) else {}
            trace_ref = {
                "type": "motivation_decision_trace",
                "eventId": event.get("id"),
                "traceId": trace_payload.get("traceId"),
                "spanId": trace_payload.get("spanId"),
                "selectedToolId": decision_payload.get("selectedToolId"),
            }
            decision_payload["contributingSources"] = [
                *[dict(item) for item in decision_payload.get("contributingSources", []) if isinstance(item, dict)],
                trace_ref,
            ]
            decision_payload["decisionTraceRef"] = trace_ref
            enriched["decision"] = decision_payload
            enriched["decisionTraceEventId"] = event.get("id")
            enriched_decisions.append(enriched)
        return enriched_decisions

    def _phase2_decision_trace_payload(self, decision: dict[str, Any]) -> dict[str, Any]:
        decision_payload = decision.get("decision", {}) if isinstance(decision.get("decision"), dict) else {}
        primary_need = decision.get("primaryNeed", {}) if isinstance(decision.get("primaryNeed"), dict) else {}
        selected_tool_id = str(decision_payload.get("selectedToolId") or "")
        npc_name = str(decision.get("npcName") or decision.get("npcId") or "NPC")
        need_id = str(primary_need.get("needId") or decision_payload.get("needId") or "unknown_need")
        capabilities = decision.get("capabilities", []) if isinstance(decision.get("capabilities"), list) else []
        capability_filters = decision.get("capabilityFilters", {}) if isinstance(decision.get("capabilityFilters"), dict) else {}
        subjective_memory_recall = decision.get("subjectiveMemoryRecall", {}) if isinstance(decision.get("subjectiveMemoryRecall"), dict) else {}
        heuristic_recall = decision.get("heuristicRecall", {}) if isinstance(decision.get("heuristicRecall"), dict) else {}
        return {
            "npcId": decision.get("npcId"),
            "npcName": decision.get("npcName"),
            "primaryNeed": dict(primary_need),
            "needs": [dict(item) for item in decision.get("needs", [])[:6] if isinstance(item, dict)],
            "capabilityCount": len(capabilities),
            "capabilities": [self._phase2_capability_ref(item) for item in capabilities[:12] if isinstance(item, dict)],
            "capabilityFilters": self._phase2_capability_filter_ref(capability_filters),
            "subjectiveMemoryRecall": self._phase2_subjective_memory_recall_ref(subjective_memory_recall),
            "heuristicRecall": self._phase2_heuristic_recall_ref(heuristic_recall),
            "selectedToolId": selected_tool_id,
            "candidateScores": [dict(item) for item in decision_payload.get("candidateScores", []) if isinstance(item, dict)],
            "relationshipEdgeRefs": [dict(item) for item in decision_payload.get("relationshipEdgeRefs", []) if isinstance(item, dict)],
            "subjectiveMemoryRefs": [dict(item) for item in decision_payload.get("subjectiveMemoryRefs", []) if isinstance(item, dict)],
            "heuristicRefs": [dict(item) for item in decision_payload.get("heuristicRefs", []) if isinstance(item, dict)],
            "contributingSources": [dict(item) for item in decision_payload.get("contributingSources", []) if isinstance(item, dict)],
            "decisionReason": decision_payload.get("reason"),
            "summary": f"{npc_name} 因 {need_id} 选择 {selected_tool_id or 'no_tool'}。",
        }

    def _phase2_capability_ref(self, capability: dict[str, Any]) -> dict[str, Any]:
        return {
            "toolId": capability.get("toolId"),
            "tier": capability.get("tier"),
            "durationSeconds": capability.get("durationSeconds"),
            "observerVisibility": capability.get("observerVisibility"),
        }

    def _phase2_capability_filter_ref(self, capability_filters: dict[str, Any]) -> dict[str, Any]:
        layers = capability_filters.get("layers", []) if isinstance(capability_filters.get("layers"), list) else []
        return {
            "version": capability_filters.get("version"),
            "allowedToolIds": list(capability_filters.get("allowedToolIds", [])) if isinstance(capability_filters.get("allowedToolIds"), list) else [],
            "layers": [
                {
                    "layer": layer.get("layer"),
                    "inputCount": layer.get("inputCount"),
                    "allowedCount": layer.get("allowedCount"),
                    "rejectedCount": layer.get("rejectedCount"),
                    "decisions": [dict(item) for item in layer.get("decisions", [])[:8] if isinstance(item, dict)],
                }
                for layer in layers
                if isinstance(layer, dict)
            ],
            "rejectedTools": [
                dict(item)
                for item in capability_filters.get("rejectedTools", [])[:12]
                if isinstance(item, dict)
            ] if isinstance(capability_filters.get("rejectedTools"), list) else [],
        }

    def _phase2_subjective_memory_recall_ref(self, recall: dict[str, Any]) -> dict[str, Any]:
        return {
            "version": recall.get("version"),
            "query": recall.get("query"),
            "count": recall.get("count"),
            "recordIds": list(recall.get("recordIds", []))[:8] if isinstance(recall.get("recordIds"), list) else [],
            "sourceEventIds": list(recall.get("sourceEventIds", []))[:8] if isinstance(recall.get("sourceEventIds"), list) else [],
        }

    def _phase2_heuristic_recall_ref(self, recall: dict[str, Any]) -> dict[str, Any]:
        return {
            "version": recall.get("version"),
            "worldTick": recall.get("worldTick"),
            "count": recall.get("count"),
            "activeCount": recall.get("activeCount"),
            "heuristicIds": list(recall.get("heuristicIds", []))[:8] if isinstance(recall.get("heuristicIds"), list) else [],
            "sourceEventIds": list(recall.get("sourceEventIds", []))[:8] if isinstance(recall.get("sourceEventIds"), list) else [],
        }

    def _phase2_decision_target_ids(self, decision: dict[str, Any]) -> list[str]:
        decision_payload = decision.get("decision", {}) if isinstance(decision.get("decision"), dict) else {}
        target_ids: list[str] = []
        for edge in decision_payload.get("relationshipEdgeRefs", []):
            if not isinstance(edge, dict):
                continue
            for key in ("sourceAgentId", "targetAgentId"):
                value = str(edge.get(key) or "")
                if value and value != str(decision.get("npcId") or "") and value not in target_ids:
                    target_ids.append(value)
        return target_ids

    def _advance_clock_by_game_seconds(self, delta_seconds: float) -> None:
        """只基于游戏时间推进时钟，避免任何墙钟依赖。"""
        clock = self.world["clock"]
        previous_phase = str(clock.get("phase") or "morning")
        day = int(clock.get("day", 1))
        day_seconds = float(clock.get("_daySeconds", (int(clock.get("hour", 8)) - 8) * 3600 + int(clock.get("minute", 0)) * 60))
        day_seconds += max(0.0, delta_seconds)
        day_span_seconds = 14 * 3600.0
        while day_seconds >= day_span_seconds:
            day += 1
            day_seconds -= day_span_seconds
        hour = 8 + int(day_seconds // 3600)
        minute = int((day_seconds % 3600) // 60)
        next_phase = "night" if hour >= 21 else ("evening" if hour >= 18 else ("afternoon" if hour >= 14 else ("noon" if hour >= 12 else "morning")))

        clock["day"] = day
        clock["hour"] = hour
        clock["minute"] = minute
        clock["_daySeconds"] = day_seconds
        clock["tick"] = int(clock.get("tick", 0)) + 1
        clock["phase"] = next_phase
        if next_phase != previous_phase:
            clock["actionBudget"] = action_budget_for_phase(next_phase)

    def _tick_clock_payload(self) -> dict[str, Any]:
        """输出 /api/world/tick 的紧凑时钟结构。"""
        clock = self.world.get("clock", {})
        return {
            "day": int(clock.get("day", 1)),
            "hour": int(clock.get("hour", 8)),
            "minute": int(clock.get("minute", 0)),
            "phase": str(clock.get("phase") or "morning"),
            "tick": int(clock.get("tick", 0)),
        }


    def pick_actors(self) -> list[dict[str, Any]]:
        agents = living_agents(self.world)
        count = min(3, len(agents))
        start = self.world["clock"]["tick"] % len(agents)
        return [agents[(start + index) % len(agents)] for index in range(count)]

    def _run_director_v0(self) -> None:
        """运行规则版 Director v0，并把摘要、Beat 和队列结果写入 Debug 事件流。"""
        digest = WorldDigest.from_world(self.world)
        self.event_store.append("director.digest_created", self._director_digest_payload(digest))

        skill = get_event_skill(STARLIGHT_FESTIVAL_SHORTAGE_SKILL_ID)
        if self._should_activate_event_skill(skill):
            beat = self._create_activate_event_skill_beat(digest, skill)
            self.event_store.append("director.beat_created", beat.to_dict())
            validation = self.director_validator.validate(beat, current_world_version=digest.world_version)
            self.event_store.append(
                "director.beat_validated",
                {"beatId": beat.beatId, "ok": validation.ok, "errors": list(validation.errors), "beat": beat.to_dict()},
            )
            if validation.ok:
                enqueue_result = self.director_queue.enqueue(beat, current_world_version=digest.world_version)
                if enqueue_result.discarded:
                    self.event_store.append("director.beat_discarded", enqueue_result.discarded.to_event_payload())
            else:
                self.event_store.append(
                    "director.beat_discarded",
                    {"beatId": beat.beatId, "reason": "validation_failed", "detail": "; ".join(validation.errors), "beat": beat.to_dict()},
                )

        self._consume_director_queue(digest)

    def _consume_director_queue(self, digest: WorldDigest | None = None) -> None:
        """消费 Director 队列，并记录已消费或丢弃的 Beat。"""
        digest = digest or WorldDigest.from_world(self.world)
        consume_result = self.director_queue.consume(digest)
        for beat in consume_result.ready:
            active_focus = self._apply_director_beat(beat)
            self.event_store.append("director.beat_consumed", {"beat": beat.to_dict(), "activeFocus": active_focus})
        for discarded in consume_result.discarded:
            self.event_store.append("director.beat_discarded", discarded.to_event_payload())

    def _director_digest_payload(self, digest: WorldDigest) -> dict[str, Any]:
        """把 WorldDigest 转成 EventStore 友好的调试载荷。"""
        return {
            "worldVersion": digest.world_version,
            "tick": digest.tick,
            "livingAgentIds": list(digest.living_agent_ids),
            "activeEventCount": digest.active_event_count,
            "avgStress": digest.avg_stress,
        }

    def _director_beat_event_payload(self, event: dict[str, Any]) -> dict[str, Any]:
        """把 Director 事件压缩成可读生命周期条目。"""
        payload = event.get("payload", {})
        beat = payload.get("beat") if isinstance(payload.get("beat"), dict) else payload
        beat_payload = beat.get("payload", {}) if isinstance(beat.get("payload"), dict) else {}
        return {
            "eventId": event.get("id"),
            "eventType": event.get("type"),
            "createdAt": event.get("createdAt"),
            "beatId": beat.get("beatId") or payload.get("beatId"),
            "beatType": beat.get("beatType") or payload.get("beatType"),
            "skillId": beat_payload.get("skillId") or payload.get("skillId"),
            "eventSkillEventId": beat_payload.get("eventId") or payload.get("eventId"),
            "ok": payload.get("ok"),
            "reason": payload.get("reason"),
            "detail": payload.get("detail") or payload.get("errors"),
            "beat": beat if isinstance(beat, dict) else {},
        }

    def _player_profile_payload(self) -> dict[str, Any]:
        """输出轻量玩家风格摘要，给 NPC Prompt 和 Debug API 共用。"""
        player = self.world.setdefault("player", {})
        profile = player.setdefault(
            "profile",
            {
                "styleSummary": "刚搬来晨露农场，正在通过聊天、送礼和事件选择形成小镇印象。",
                "signals": {"talk": 0, "gift": 0, "festivalChoice": 0, "help": 0, "mediate": 0, "observe": 0, "support": 0},
                "evidence": [],
            },
        )
        return {
            "playerId": player.get("id", "player"),
            "playerName": player.get("name", "新来的农场主"),
            "styleSummary": str(profile.get("styleSummary", "")),
            "signals": dict(profile.get("signals", {})) if isinstance(profile.get("signals"), dict) else {},
            "evidence": list(profile.get("evidence", []))[-8:] if isinstance(profile.get("evidence"), list) else [],
        }

    def _provider_fallback_debug(self, filters: dict[str, Any]) -> dict[str, Any]:
        """汇总显式模型兜底事件和 Debug 记录里的兜底原因。"""
        feature = self._str_filter(filters, "feature")
        limit = self._int_filter(filters, "limit", 20)
        items: list[dict[str, Any]] = []
        for event in self.event_store.list():
            event_type = str(event.get("type", ""))
            payload = event.get("payload", {})
            if event_type == "provider.fallback":
                if feature and payload.get("feature") != feature:
                    continue
                items.append(
                    {
                        "eventId": event.get("id"),
                        "eventType": event_type,
                        "createdAt": event.get("createdAt"),
                        "feature": payload.get("feature"),
                        "agentId": payload.get("agentId"),
                        "profileName": payload.get("profileName"),
                        "fallbackProfile": payload.get("fallbackProfile"),
                        "reason": payload.get("error"),
                    }
                )
                continue
            debug = payload.get("debug")
            if isinstance(debug, dict) and debug.get("fallbackReason"):
                if feature and debug.get("feature") != feature:
                    continue
                items.append(
                    {
                        "eventId": event.get("id"),
                        "eventType": event_type,
                        "createdAt": event.get("createdAt"),
                        "feature": debug.get("feature"),
                        "agentId": payload.get("agentId"),
                        "profileName": debug.get("profileName"),
                        "fallbackProfile": self.model_config.fallback_profile().get("profileName"),
                        "reason": debug.get("fallbackReason"),
                    }
                )
        return {"limit": limit, "items": items[-limit:]}

    def _relationship_debug(self, filters: dict[str, Any]) -> dict[str, Any]:
        """解释当前关系数值和本轮关系变化事件。"""
        agent_id = self._str_filter(filters, "agentId") or self._str_filter(filters, "targetId") or self._str_filter(filters, "agent_id")
        limit = self._int_filter(filters, "limit", 20)
        current = []
        for target_id, target in self.world.get("agents", {}).items():
            if agent_id and target_id != agent_id:
                continue
            current.append({"targetId": target_id, "targetName": target.get("name", target_id), "relation": get_relation(self.world, "player", target_id)})

        events = []
        for event in self.event_store.list():
            if event.get("type") != "relationship.changed":
                continue
            payload = event.get("payload", {})
            if agent_id and payload.get("targetId") != agent_id and payload.get("sourceId") != agent_id:
                continue
            events.append({"eventId": event.get("id"), "createdAt": event.get("createdAt"), "payload": payload})
        return {"current": current, "events": events[-limit:]}

    def _influence_event_debug(self, filters: dict[str, Any], *, skill_id: str | None, event_id: str | None) -> dict[str, Any]:
        """筛出首日影响链相关事件，供 Debug Console 一屏解释。"""
        limit = self._int_filter(filters, "limit", 30)
        agent_id = self._str_filter(filters, "agentId") or self._str_filter(filters, "targetId") or self._str_filter(filters, "agent_id")
        items = [
            {
                "eventId": event.get("id"),
                "eventType": event.get("type"),
                "createdAt": event.get("createdAt"),
                "summary": self._short_debug_text(self._event_debug_summary(event), 240),
                "payload": self._debug_safe_event_payload(event.get("payload", {})),
            }
            for event in self.event_store.list()
            if self._event_matches_influence_filters(event, agent_id=agent_id, skill_id=skill_id, event_id=event_id)
        ]
        return {"limit": limit, "items": items[-limit:]}

    def _event_matches_influence_filters(
        self,
        event: dict[str, Any],
        *,
        agent_id: str | None,
        skill_id: str | None,
        event_id: str | None,
    ) -> bool:
        """判断事件是否属于玩家首日影响链。"""
        event_type = str(event.get("type", ""))
        payload = event.get("payload", {})
        debug = payload.get("debug") if isinstance(payload, dict) else None
        tracked_types = {
            "player.talked",
            "player.gift_given",
            "player.event_choice",
            "player.profile_updated",
            "relationship.changed",
            "npc.memory_created",
            "npc.night_reflection",
            "npc.dialogue",
            "gossip.propagation_validated",
            "town.event_resolved",
            "debug.turn_recorded",
            "provider.fallback",
        }
        if event_type not in tracked_types:
            return False
        if agent_id and agent_id not in {payload.get("agentId"), payload.get("targetId"), payload.get("sourceId")}:
            if not (isinstance(debug, dict) and debug.get("actorId") == agent_id):
                return False
        if skill_id:
            payload_skill_id = payload.get("skillId") or (debug.get("skillId") if isinstance(debug, dict) else None)
            if payload_skill_id != skill_id and not (isinstance(debug, dict) and self._debug_matches_skill(debug, skill_id)):
                if event_type not in {"player.talked", "player.gift_given", "player.profile_updated", "relationship.changed", "npc.dialogue", "debug.turn_recorded"}:
                    return False
        if event_id:
            payload_event_id = payload.get("eventId") or (debug.get("eventId") if isinstance(debug, dict) else None)
            if payload_event_id and payload_event_id != event_id:
                return False
        return True

    def _event_debug_summary(self, event: dict[str, Any]) -> str:
        """从事件载荷中提取适合 Debug 列表显示的一句话。"""
        payload = event.get("payload", {})
        debug = payload.get("debug") if isinstance(payload, dict) else None
        if isinstance(debug, dict):
            return self._debug_summary(debug)
        for key in ("summary", "speech", "text", "message"):
            if payload.get(key):
                return str(payload[key])
        if payload.get("item"):
            return f"送出 {payload['item'].get('name', payload['item'].get('id', '礼物'))}"
        if payload.get("delta"):
            return f"关系变化 {payload['delta']}"
        return str(event.get("type", ""))

    def _event_skill_manifest_payload(self, skill: EventSkillSchema) -> dict[str, Any]:
        """把 Skill manifest 转为 Debug 友好的只读结构。"""
        return {
            "skillId": skill.skill_id,
            "eventId": skill.event_id,
            "title": skill.title,
            "brief": skill.brief,
            "trigger": {
                "phase": skill.trigger.phase,
                "locationId": skill.trigger.location_id,
                "requiredStatus": skill.trigger.required_status,
                "requiredActiveEventId": skill.trigger.required_active_event_id,
            },
            "participants": list(skill.participants),
            "playerOptions": self._skill_choice_payloads(skill),
            "assetHints": self._skill_asset_hint_payloads(skill),
            "debugFields": self._skill_debug_field_templates(skill.debug_fields),
        }

    def _event_skill_snapshot(self, skill: EventSkillSchema) -> dict[str, Any]:
        """生成单个 Skill 的当前状态与生命周期快照。"""
        active_event = next((event for event in self.world.get("activeEvents", []) if event.get("id") == skill.event_id), None)
        completed_event = next((event for event in self.world.get("completedEvents", []) if event.get("id") == skill.event_id), None)
        director_state = self.world.setdefault("directorState", {"activatedEventSkills": [], "consumedBeatIds": []})
        status = "registered"
        if active_event:
            status = str(active_event.get("status") or "available")
        if skill.skill_id in director_state.get("activatedEventSkills", []):
            status = "activated"
        if completed_event or (active_event and active_event.get("status") == "resolved"):
            status = "resolved"
        return {
            **self._event_skill_manifest_payload(skill),
            "status": status,
            "activeEvent": active_event,
            "completedEvent": completed_event,
            "lifecycle": self._event_skill_lifecycle(skill),
        }

    def _event_skill_lifecycle(self, skill: EventSkillSchema) -> list[dict[str, Any]]:
        """收集 Skill 从注册到结算的 Debug 可解释阶段。"""
        lifecycle: list[dict[str, Any]] = [
            {"stage": "registered", "source": "skill_registry", "skillId": skill.skill_id, "eventId": skill.event_id}
        ]
        for event in self.world.get("activeEvents", []):
            if event.get("id") == skill.event_id:
                lifecycle.append(
                    {
                        "stage": "available",
                        "source": "world.activeEvents",
                        "eventId": event.get("id"),
                        "status": event.get("status"),
                        "locationId": event.get("locationId"),
                    }
                )

        for event in self.event_store.list():
            event_type = str(event.get("type", ""))
            payload = event.get("payload", {})
            stage = self._skill_event_stage(skill, event_type, payload)
            if not stage:
                continue
            lifecycle.append(
                {
                    "stage": stage,
                    "source": event_type,
                    "eventStoreId": event.get("id"),
                    "createdAt": event.get("createdAt"),
                    "summary": payload.get("summary") or payload.get("debug", {}).get("feature"),
                    "payload": self._debug_safe_event_payload(payload),
                }
            )
        return lifecycle

    def _skill_event_stage(self, skill: EventSkillSchema, event_type: str, payload: dict[str, Any]) -> str | None:
        """识别某条事件是否属于指定 Skill 生命周期。"""
        if event_type.startswith("director."):
            beat = payload.get("beat") if isinstance(payload.get("beat"), dict) else payload
            beat_payload = beat.get("payload", {}) if isinstance(beat.get("payload"), dict) else {}
            if beat_payload.get("skillId") == skill.skill_id:
                return event_type.replace("director.beat_", "director_beat_").replace("director.", "director_")

        if payload.get("skillId") == skill.skill_id:
            mapping = {
                "player.inspected": "inspect",
                "player.event_choice": "attend_event",
                "town.event_resolved": "resolved",
                "npc.memory_created": "memory_write",
                "npc.night_reflection": "night_reflection_write",
            }
            return mapping.get(event_type, event_type)

        debug = payload.get("debug")
        if isinstance(debug, dict) and self._debug_matches_skill(debug, skill.skill_id):
            feature = str(debug.get("feature") or "debug")
            return f"{feature}_debug"
        return None

    def _debug_turn_payload(self, event: dict[str, Any], debug: dict[str, Any]) -> dict[str, Any]:
        """压缩 Provider Debug 记录，避免 Debug API 直接暴露整段 Prompt。"""
        return {
            "eventId": event.get("id"),
            "eventType": event.get("type"),
            "createdAt": event.get("createdAt"),
            "agentId": event.get("payload", {}).get("agentId"),
            "agentName": event.get("payload", {}).get("agentName"),
            "feature": debug.get("feature"),
            "skillId": debug.get("skillId"),
            "providerMode": debug.get("providerMode"),
            "provider": debug.get("provider"),
            "profileName": debug.get("profileName"),
            "fallbackReason": debug.get("fallbackReason"),
            "latency": debug.get("latency"),
            "summary": self._short_debug_text(self._debug_summary(debug), 240),
            "debug": self._compact_debug_payload(debug),
        }

    def _debug_safe_event_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        """裁剪事件 payload 内的 Debug 长字段，供 Debug Console 列表稳定消费。"""
        safe_payload = dict(payload) if isinstance(payload, dict) else {}
        debug = safe_payload.get("debug")
        if isinstance(debug, dict):
            safe_payload["debug"] = self._compact_debug_payload(debug)
        return safe_payload

    def _debug_safe_event(self, event: dict[str, Any]) -> dict[str, Any]:
        """裁剪单条事件内的 Debug 长字段，供 Godot recentEvents 安全消费。"""
        safe_event = dict(event) if isinstance(event, dict) else {}
        payload = safe_event.get("payload")
        if isinstance(payload, dict):
            safe_event["payload"] = self._debug_safe_event_payload(payload)
        return safe_event

    def _compact_debug_payload(self, debug: dict[str, Any]) -> dict[str, Any]:
        """保留 Debug 关键诊断字段，同时把 Prompt、rawText 和嵌套文本压成预览。"""
        compact_keys = (
            "tick",
            "feature",
            "provider",
            "providerMode",
            "profileName",
            "apiKeyConfigured",
            "profile",
            "usage",
            "latency",
            "fallbackReason",
            "executed",
            "parsed",
            "skillId",
            "eventId",
            "choice",
            "skillDebugFields",
            "playerProfile",
            "memoryEvidence",
            "memoryEvidenceUsed",
            "gossipPropagationValidation",
        )
        compact = {key: self._compact_debug_value(debug[key]) for key in compact_keys if key in debug}

        messages = debug.get("messages")
        if isinstance(messages, list):
            compact["messageCount"] = len(messages)
            compact["messages"] = [self._compact_debug_message(message) for message in messages[:3] if isinstance(message, dict)]

        raw_text = str(debug.get("rawText", ""))
        compact["rawText"] = self._short_debug_text(raw_text, 240)
        compact["rawTextLength"] = len(raw_text)
        return compact

    def _compact_debug_message(self, message: dict[str, Any]) -> dict[str, Any]:
        """把单条 Provider message 转成长度可控的预览结构。"""
        content = str(message.get("content", ""))
        return {
            "role": message.get("role"),
            "contentPreview": self._short_debug_text(content, 320),
            "contentLength": len(content),
        }

    def _compact_debug_value(self, value: Any, *, text_limit: int = 180, item_limit: int = 6) -> Any:
        """递归裁剪 Debug 值，保留结构形状和可读摘要。"""
        if isinstance(value, str):
            return self._short_debug_text(value, text_limit)
        if value is None or isinstance(value, (bool, int, float)):
            return value
        if isinstance(value, list):
            compact_items = [self._compact_debug_value(item, text_limit=text_limit, item_limit=item_limit) for item in value[:item_limit]]
            if len(value) > item_limit:
                compact_items.append({"truncatedCount": len(value) - item_limit})
            return compact_items
        if isinstance(value, dict):
            return {str(key): self._compact_debug_value(item, text_limit=text_limit, item_limit=item_limit) for key, item in value.items()}
        return self._short_debug_text(str(value), text_limit)

    def _debug_summary(self, debug: dict[str, Any]) -> str:
        """从 executed / parsed 中提取一行可读摘要。"""
        executed = debug.get("executed") if isinstance(debug.get("executed"), dict) else {}
        if executed.get("speech"):
            return str(executed["speech"])
        if executed.get("dialogue"):
            return " / ".join(str(item.get("text", "")) for item in executed["dialogue"][:2] if isinstance(item, dict))
        if executed.get("reflections"):
            return " / ".join(str(item.get("text", "")) for item in executed["reflections"][:2] if isinstance(item, dict))
        parsed = debug.get("parsed") if isinstance(debug.get("parsed"), dict) else {}
        return str(parsed.get("speech") or parsed.get("memory_to_save") or debug.get("feature") or "")

    def _debug_matches_skill(self, debug: dict[str, Any], skill_id: str) -> bool:
        """检查 Debug 记录是否指向某个 Skill。"""
        if debug.get("skillId") == skill_id:
            return True
        fields = debug.get("skillDebugFields")
        if isinstance(fields, list):
            return any(isinstance(field, dict) and field.get("id") == "skillId" and field.get("value") == skill_id for field in fields)
        return False

    def _str_filter(self, filters: dict[str, Any], key: str) -> str | None:
        """读取查询参数中的字符串值。"""
        value = filters.get(key)
        if isinstance(value, list):
            value = value[-1] if value else None
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _int_filter(self, filters: dict[str, Any], key: str, default: int) -> int:
        """读取查询参数中的正整数值，并限制 Debug 返回量。"""
        text = self._str_filter(filters, key)
        if text is None:
            return default
        try:
            return max(1, min(int(text), 100))
        except ValueError:
            return default

    def _should_activate_event_skill(self, skill: EventSkillSchema) -> bool:
        """检测事件技能候选，避免同一个事件技能重复激活。"""
        director_state = self.world.setdefault("directorState", {"activatedEventSkills": [], "consumedBeatIds": []})
        if skill.skill_id in director_state.setdefault("activatedEventSkills", []):
            return False
        trigger = skill.trigger
        required_event_id = trigger.required_active_event_id or skill.event_id
        for event in self.world.get("activeEvents", []):
            if event.get("id") != required_event_id:
                continue
            if event.get("status") != trigger.required_status:
                continue
            if event.get("locationId") != trigger.location_id:
                continue
            if event.get("phase") != trigger.phase:
                continue
            return True
        return False

    def _create_activate_event_skill_beat(self, digest: WorldDigest, skill: EventSkillSchema) -> DirectorBeat:
        """把事件技能候选转为 activate_event_skill Beat。"""
        tension = self.tension_detector.detect(digest)
        target_agents = [agent_id for agent_id in skill.participants if agent_id != "player" and agent_id in self.world["agents"]]
        allowed_skills = [skill.skill_id]
        routed_skills = self.skill_router.route(tension, target_agents, candidate_skills=allowed_skills)
        if not routed_skills:
            routed_skills = allowed_skills
        return DirectorBeat(
            beatType="activate_event_skill",
            worldVersion=digest.world_version,
            validFromTick=digest.tick,
            expiresAtTick=digest.tick + 2,
            targetAgents=target_agents,
            allowedSkills=routed_skills,
            payload={
                "skillId": skill.skill_id,
                "eventId": skill.event_id,
                "title": skill.title,
                "brief": skill.brief,
                "trigger": {
                    "phase": skill.trigger.phase,
                    "locationId": skill.trigger.location_id,
                    "requiredStatus": skill.trigger.required_status,
                    "requiredActiveEventId": skill.trigger.required_active_event_id,
                },
                "playerOptions": [
                    {
                        "id": option.option_id,
                        "label": option.label,
                        "brief": option.brief,
                        "requiresPlayerItemId": option.requires_player_item_id,
                        "consequenceTypes": [consequence.consequence_type for consequence in option.consequences],
                    }
                    for option in skill.player_options
                ],
                "assetHints": [
                    {"id": hint.hint_id, "type": hint.asset_type, "brief": hint.brief, "tags": list(hint.tags)}
                    for hint in skill.asset_hints
                ],
                "debugFields": self._skill_debug_field_templates(skill.debug_fields),
                "tension": {"level": tension.level, "score": tension.score, "evidence": tension.evidence},
            },
        )

    def _apply_director_beat(self, beat: DirectorBeat) -> dict[str, Any]:
        """把已消费 Beat 写入世界的轻量 Director 状态，供后续层读取。"""
        director_state = self.world.setdefault("directorState", {"activatedEventSkills": [], "consumedBeatIds": []})
        director_state.setdefault("consumedBeatIds", []).append(beat.beatId)
        payload = dict(beat.payload)
        skill_id = str(payload.get("skillId") or "")
        if skill_id:
            activated = director_state.setdefault("activatedEventSkills", [])
            if skill_id not in activated:
                activated.append(skill_id)
        active_focus = {
            "type": beat.beatType,
            "beatId": beat.beatId,
            "skillId": skill_id,
            "eventId": payload.get("eventId"),
            "eventLocationId": (payload.get("trigger") or {}).get("locationId") if isinstance(payload.get("trigger"), dict) else None,
            "brief": payload.get("brief"),
            "targetAgents": list(beat.targetAgents),
            "validFromTick": beat.validFromTick,
            "expiresAtTick": beat.expiresAtTick,
        }
        self.world["activeFocus"] = active_focus
        return active_focus

    def _handle_player_move(self, payload: dict[str, Any]) -> dict[str, Any]:
        """移动玩家位置，为 Godot 地图切换保留统一事件记录。"""
        location_id = str(payload.get("locationId") or "")
        if location_id not in self.world["locations"]:
            raise ValueError(f"未知地点：{location_id}")
        player = self.world["player"]
        previous_location = player["locationId"]
        previous_anchor = player.get("anchorId")
        anchor_id = default_anchor_for_location(self.world, location_id)
        player["locationId"] = location_id
        if anchor_id:
            player["anchorId"] = anchor_id
        event = self.event_store.append(
            "player.moved",
            {
                "playerId": player["id"],
                "fromLocationId": previous_location,
                "fromAnchorId": previous_anchor,
                "toLocationId": location_id,
                "toAnchorId": anchor_id,
                "summary": f"{player['name']} 前往 {self.world['locations'][location_id]['name']}。",
            },
        )
        self._record_player_history("move", payload, [event["id"]])
        return {"dialogue": [], "relationshipDeltas": [], "memoryWrites": [], "eventIds": [event["id"]]}

    def _handle_player_move_to_anchor(self, payload: dict[str, Any]) -> dict[str, Any]:
        """把玩家移动到地图锚点，是 Godot 地图主循环的最小合法移动动作。"""
        anchor_id = str(payload.get("anchorId") or "")
        anchor = self.world.get("anchors", {}).get(anchor_id)
        if not anchor:
            raise ValueError(f"未知锚点：{anchor_id}")
        location_id = str(payload.get("locationId") or anchor.get("locationId") or "")
        if location_id != anchor.get("locationId") or location_id not in self.world["locations"]:
            raise ValueError(f"锚点与地点不匹配：{anchor_id} / {location_id}")
        budget = self._consume_player_action_budget("move_to_anchor")
        player = self.world["player"]
        previous = {"locationId": player.get("locationId"), "anchorId": player.get("anchorId")}
        player["locationId"] = location_id
        player["anchorId"] = anchor_id
        event = self.event_store.append(
            "player.move_to_anchor",
            {
                "playerId": player["id"],
                "from": previous,
                "to": {"locationId": location_id, "anchorId": anchor_id},
                "actionBudget": budget,
                "summary": f"{player['name']} 移动到 {self.world['locations'][location_id]['name']} 的 {anchor_id}。",
            },
        )
        self._record_player_history("move_to_anchor", payload, [event["id"]])
        action_feedback = self._build_action_feedback(
            title="移动到场景锚点",
            summary=str(event["payload"]["summary"]),
            location_id=location_id,
            anchor_id=anchor_id,
            result_type="anchor_moved",
            changed_resources=[
                {
                    "resourceType": "player_position",
                    "resourceId": "player",
                    "before": previous,
                    "after": {"locationId": location_id, "anchorId": anchor_id},
                },
                {
                    "resourceType": "action_budget",
                    "resourceId": "clock.actionBudget",
                    "before": budget["before"],
                    "after": budget["after"],
                    "delta": int(budget["after"]) - int(budget["before"]),
                },
            ],
            event_ids=[event["id"]],
        )
        return {
            "dialogue": [{"speakerId": "system", "speakerName": "旁白", "text": event["payload"]["summary"]}],
            "relationshipDeltas": [],
            "memoryWrites": [],
            "movement": event["payload"],
            "actionFeedback": action_feedback,
            "eventIds": [event["id"]],
        }

    def _handle_player_farm_action(self, payload: dict[str, Any]) -> dict[str, Any]:
        """执行播种、浇水、收获的最小农场闭环。"""
        plot_id = str(payload.get("interactableId") or payload.get("farmPlotId") or "")
        plot = self.world.get("farmPlots", {}).get(plot_id)
        if not plot:
            raise ValueError(f"未知田块：{plot_id}")
        action = str(payload.get("action") or "")
        if action not in {"plant", "water", "harvest"}:
            raise ValueError(f"未知农场动作：{action}")
        self._assert_player_at_anchor(str(plot.get("locationId")), str(plot.get("anchorId")))
        budget = self._consume_player_action_budget("farm_action")
        stage_before = str(plot.get("stage") or "")
        inventory_before: dict[str, int] = {
            str(item.get("id")): int(item.get("quantity", 0))
            for item in self.world["player"].get("inventory", [])
            if item.get("id")
        }
        event_payload: dict[str, Any] = {"playerId": "player", "farmPlotId": plot_id, "action": action, "actionBudget": budget}

        if action == "plant":
            if plot.get("stage") != "empty":
                raise ValueError(f"田块不可播种，当前阶段：{plot.get('stage')}")
            seed_id = str(payload.get("itemId") or plot.get("seedItemId") or "")
            seed_item = self._take_player_item(seed_id)
            plot["cropId"] = "starlight_turnip"
            plot["stage"] = "planted"
            plot["plantedAt"] = {"day": self.world["clock"].get("day"), "phase": self.world["clock"].get("phase")}
            event_payload.update({"item": seed_item, "summary": "你把星灯芜菁种子种进了第一块田。"})
        elif action == "water":
            if plot.get("stage") != "planted":
                raise ValueError(f"田块不可浇水，当前阶段：{plot.get('stage')}")
            plot["stage"] = "watered"
            plot["wateredAt"] = {"day": self.world["clock"].get("day"), "phase": self.world["clock"].get("phase")}
            event_payload["summary"] = "你给星灯芜菁浇了水，结束时段后就能确认成熟情况。"
        else:
            if plot.get("stage") != "harvestable":
                raise ValueError(f"田块不可收获，当前阶段：{plot.get('stage')}")
            output_item = dict(plot.get("outputItem") or {"id": "fresh_turnip", "name": "新鲜芜菁", "tags": ["crop", "gift"]})
            self._add_player_item(output_item)
            plot["cropId"] = None
            plot["stage"] = "empty"
            plot.pop("plantedAt", None)
            plot.pop("wateredAt", None)
            event_payload.update({"item": output_item, "summary": f"你收获了{output_item.get('name', output_item.get('id'))}，作物已进入背包。"})

        sync_farm_interactables(self.world)
        event_payload["farmPlot"] = dict(plot)
        event_payload["inventory"] = self.world["player"].get("inventory", [])
        event = self.event_store.append("player.farm_action", event_payload)
        self._record_player_history("farm_action", payload, [event["id"]])
        changed_resources = [
            {
                "resourceType": "farm_plot",
                "resourceId": plot_id,
                "before": {"stage": stage_before},
                "after": {"stage": plot.get("stage"), "cropId": plot.get("cropId")},
            },
            {
                "resourceType": "action_budget",
                "resourceId": "clock.actionBudget",
                "before": budget["before"],
                "after": budget["after"],
                "delta": int(budget["after"]) - int(budget["before"]),
            },
        ]
        inventory_delta = self._inventory_quantity_delta(inventory_before)
        if inventory_delta:
            changed_resources.append(
                {
                    "resourceType": "inventory",
                    "resourceId": "player.inventory",
                    "delta": inventory_delta,
                }
            )
        action_feedback = self._build_action_feedback(
            title=f"执行场景动作：{action}",
            summary=str(event_payload["summary"]),
            location_id=str(plot.get("locationId") or self.world["player"].get("locationId") or ""),
            anchor_id=str(plot.get("anchorId") or self.world["player"].get("anchorId") or ""),
            result_type="scene_action_applied",
            changed_resources=changed_resources,
            event_ids=[event["id"]],
        )
        return {
            "dialogue": [{"speakerId": "system", "speakerName": "旁白", "text": event_payload["summary"]}],
            "relationshipDeltas": [],
            "memoryWrites": [],
            "farmAction": event_payload,
            "actionFeedback": action_feedback,
            "eventIds": [event["id"]],
        }

    def _handle_player_scene_action(self, payload: dict[str, Any]) -> dict[str, Any]:
        """执行锚点附近的场景动作，统一走 interactable 契约。"""
        interactable_id = str(payload.get("interactableId") or "")
        interactable = self.world.get("interactables", {}).get(interactable_id)
        if not interactable:
            raise ValueError(f"未知场景交互体：{interactable_id}")
        action = str(payload.get("action") or "")
        supported_actions = {
            str(item)
            for item in interactable.get("actions", [])
            if str(item)
        }
        if action not in supported_actions:
            raise ValueError(f"交互体 {interactable_id} 不支持动作：{action}")
        location_id = str(interactable.get("locationId") or "")
        anchor_id = str(interactable.get("anchorId") or "")
        self._assert_player_at_anchor(location_id, anchor_id)
        kind = str(interactable.get("kind") or "")

        if kind == "farm_plot":
            farm_payload = {
                "type": "farm_action",
                "locationId": location_id,
                "interactableId": interactable_id,
                "action": action,
                "itemId": payload.get("itemId"),
            }
            result = self._handle_player_farm_action(farm_payload)
        elif action == "inspect":
            state = interactable.get("state") if isinstance(interactable.get("state"), dict) else {}
            inspect_payload = {"type": "inspect", "locationId": location_id}
            event_id = str(payload.get("eventId") or state.get("eventId") or "")
            if event_id:
                inspect_payload["eventId"] = event_id
            result = self._handle_player_inspect(inspect_payload)
        elif action == "attend_event":
            state = interactable.get("state") if isinstance(interactable.get("state"), dict) else {}
            event_id = str(payload.get("eventId") or state.get("eventId") or "")
            if not event_id:
                raise ValueError(f"交互体 {interactable_id} 缺少 eventId，无法执行 attend_event")
            attend_payload = {"type": "attend_event", "eventId": event_id}
            if payload.get("choice"):
                attend_payload["choice"] = payload["choice"]
            result = self._handle_player_attend_event(attend_payload)
        else:
            raise ValueError(f"交互体 {interactable_id} 暂不支持 scene_action:{action}")

        scene_action = {
            "interactableId": interactable_id,
            "kind": kind,
            "action": action,
            "locationId": location_id,
            "anchorId": anchor_id,
        }
        result["sceneAction"] = scene_action
        if not isinstance(result.get("actionFeedback"), dict):
            summary = scene_action["action"]
            if isinstance(result.get("inspect"), dict):
                summary = str(result["inspect"].get("summary") or summary)
            elif isinstance(result.get("eventResult"), dict):
                summary = str(result["eventResult"].get("summary") or summary)
            result["actionFeedback"] = self._build_action_feedback(
                title=f"执行场景动作：{action}",
                summary=summary,
                location_id=location_id,
                anchor_id=anchor_id,
                result_type="scene_action_applied",
                changed_resources=[],
                event_ids=[str(event_id) for event_id in result.get("eventIds", [])],
            )
        return result

    def _inventory_quantity_delta(self, before: dict[str, int]) -> list[dict[str, Any]]:
        """计算玩家背包数量变化，供 actionFeedback 追踪资源变化。"""
        after: dict[str, int] = {
            str(item.get("id")): int(item.get("quantity", 0))
            for item in self.world["player"].get("inventory", [])
            if item.get("id")
        }
        item_ids = sorted(set(before) | set(after))
        deltas: list[dict[str, Any]] = []
        for item_id in item_ids:
            quantity_before = int(before.get(item_id, 0))
            quantity_after = int(after.get(item_id, 0))
            if quantity_before == quantity_after:
                continue
            deltas.append(
                {
                    "itemId": item_id,
                    "before": quantity_before,
                    "after": quantity_after,
                    "delta": quantity_after - quantity_before,
                }
            )
        return deltas

    def _build_action_feedback(
        self,
        *,
        title: str,
        summary: str,
        location_id: str,
        anchor_id: str,
        result_type: str,
        changed_resources: list[dict[str, Any]],
        event_ids: list[str],
    ) -> dict[str, Any]:
        """统一构造场景动作反馈契约，供客户端直接渲染行动回执。"""
        return {
            "title": title,
            "summary": summary,
            "locationId": location_id,
            "anchorId": anchor_id,
            "resultType": result_type,
            "changedResources": changed_resources,
            "eventIds": [str(event_id) for event_id in event_ids],
        }

    def _handle_player_end_phase(self, payload: dict[str, Any]) -> dict[str, Any]:
        """结束当前时段，推进 phase 并刷新该时段的行动预算。"""
        transition = advance_phase(self.world)
        event = self.event_store.append(
            "clock.phase_ended",
            {
                "playerId": "player",
                "transition": transition,
                "clock": dict(self.world["clock"]),
                "summary": f"时段从 {transition['fromPhase']} 推进到 {transition['toPhase']}，行动预算刷新为 {transition['actionBudget']}。",
            },
        )
        self._record_player_history("end_phase", payload, [event["id"]])
        return {
            "dialogue": [{"speakerId": "system", "speakerName": "旁白", "text": event["payload"]["summary"]}],
            "relationshipDeltas": [],
            "memoryWrites": [],
            "clockTransition": transition,
            "eventIds": [event["id"]],
        }

    def _handle_player_talk(self, payload: dict[str, Any]) -> dict[str, Any]:
        """处理玩家主动聊天，并让目标 NPC 生成可追踪回复。"""
        target = self._get_target_agent(payload)
        player = self.world["player"]
        self._sync_player_location(payload)
        self._mark_known_npc(target["id"])

        message = str(payload.get("message") or "你好，我刚搬到小镇。")
        topic = str(payload.get("topic") or "free_talk")
        player_event = self.event_store.append(
            "player.talked",
            {"playerId": player["id"], "targetId": target["id"], "targetName": target["name"], "topic": topic, "message": message},
        )
        profile_payload, profile_event = self._update_player_profile(
            "talk",
            f"主动和 {target['name']} 聊起 {topic}。",
            tags=["player_profile_memory", "dialogue", topic],
        )

        before_relation = get_relation(self.world, "player", target["id"])
        adjust_relation(self.world, "player", target["id"], {"affection": 2, "trust": 1, "conflict": -1})
        after_relation = get_relation(self.world, "player", target["id"])
        relationship_payload = {
            "sourceId": "player",
            "targetId": target["id"],
            "targetName": target["name"],
            "delta": self._relation_diff(before_relation, after_relation),
            "after": after_relation,
        }
        relation_event = self.event_store.append("relationship.changed", relationship_payload)

        context = build_player_dialogue_context(self.world, target, payload, self.event_store)
        context["playerProfile"] = self._player_profile_payload()
        context["memoryEvidence"] = self._dialogue_memory_evidence(target, payload)
        messages = build_player_dialogue_messages(context)
        provider_result, profile, fallback_reason = self._decide_player_dialogue(target, payload, context, messages)
        parsed, fallback_reason = self._parse_structured_provider_result(
            provider_result,
            FEATURE_DIALOGUE,
            fallback_reason=fallback_reason,
        )
        speech = str(parsed.get("speech") or provider_result.get("rawText") or f"{target['name']}向你点点头。")
        memory_text = str(parsed.get("memory_to_save") or f"我和新来的农场主聊了 {topic}。")
        memory_evidence = context["memoryEvidence"]
        memory_evidence_used = parsed.get("memory_evidence_used")
        gossip_validation = self._validate_dialogue_gossip_propagation(parsed=parsed, context=context, target=target, topic=topic)
        gossip_event = None
        if gossip_validation is not None:
            gossip_event = self.event_store.append("gossip.propagation_validated", gossip_validation)

        remember(target, memory_text, tick=self.world["clock"]["tick"], importance=0.68, tags=["player_talk", topic])
        memory_payload = {"agentId": target["id"], "agentName": target["name"], "text": memory_text, "tags": ["player_talk", topic]}
        memory_event = self.event_store.append("npc.memory_created", memory_payload)
        dialogue_event = self.event_store.append(
            "npc.dialogue",
            {"agentId": target["id"], "agentName": target["name"], "targetId": "player", "speech": speech, "topic": topic},
        )

        debug = self._build_provider_debug(
            feature="dialogue",
            profile=profile,
            messages=messages,
            result=provider_result,
            parsed=parsed,
            fallback_reason=fallback_reason,
            executed={"speech": speech},
            extra={
                "turnId": dialogue_event["id"],
                "actorId": target["id"],
                "memoryWrites": [memory_payload],
                "relationshipDeltas": [relationship_payload],
                "playerProfile": self._player_profile_payload(),
                "memoryEvidence": memory_evidence,
                "memoryEvidenceUsed": memory_evidence_used,
                "gossipPropagationValidation": gossip_validation,
            },
        )
        target.setdefault("decisionHistory", []).append(debug)
        target["decisionHistory"] = target["decisionHistory"][-10:]
        debug_event = self.event_store.append("debug.turn_recorded", {"agentId": target["id"], "agentName": target["name"], "debug": debug})

        event_ids = [player_event["id"], profile_event["id"], relation_event["id"], memory_event["id"], dialogue_event["id"], debug_event["id"]]
        if gossip_event is not None:
            event_ids.insert(-1, gossip_event["id"])
        self._record_player_history("talk", payload, event_ids)
        return {
            "dialogue": [{"speakerId": target["id"], "speakerName": target["name"], "text": speech}],
            "relationshipDeltas": [relationship_payload],
            "memoryWrites": [profile_payload, memory_payload],
            "playerProfile": self._player_profile_payload(),
            "memoryEvidence": memory_evidence,
            "memoryEvidenceUsed": memory_evidence_used,
            "gossipPropagationValidation": gossip_validation,
            "relationshipStage": self._relationship_stage_payload(target["id"], before_relation, after_relation),
            "eventIds": event_ids,
        }

    def _handle_player_gift(self, payload: dict[str, Any]) -> dict[str, Any]:
        """处理首版送礼动作：基础 delta 之上叠加深度卡 giftReactions 修正。"""
        target = self._get_target_agent(payload)
        item_id = str(payload.get("itemId") or "")
        item = self._take_player_item(item_id)
        gift_delta = {"affection": 4, "trust": 2, "conflict": -1}
        tier_name = "neutral"
        deep_card = self.npc_deep_cards.get(target["id"])
        fallback_pool: tuple[str, ...] = ()
        if deep_card is not None:
            tier_name, tier = match_gift_reaction_tier(deep_card, item)
            for key, value in tier.delta_modifier.items():
                if key in gift_delta:
                    gift_delta[key] = gift_delta[key] + int(value)
                else:
                    gift_delta[key] = int(value)
            fallback_pool = tier.fallback_speech_pool
        before_relation = get_relation(self.world, "player", target["id"])
        adjust_relation(self.world, "player", target["id"], gift_delta)
        after_relation = get_relation(self.world, "player", target["id"])
        relationship_payload = {
            "sourceId": "player",
            "targetId": target["id"],
            "targetName": target["name"],
            "delta": self._relation_diff(before_relation, after_relation),
            "after": after_relation,
        }
        gift_event = self.event_store.append(
            "player.gift_given",
            {"playerId": "player", "targetId": target["id"], "item": item, "reactionTier": tier_name},
        )
        profile_payload, profile_event = self._update_player_profile(
            "gift",
            f"把 {item['name']} 送给 {target['name']}，表现出愿意用实际物品照顾居民。",
            tags=["player_profile_memory", "gift", item_id, target["id"]],
        )
        relation_event = self.event_store.append("relationship.changed", relationship_payload)
        memory_text = self._compose_gift_memory_text(target["name"], item["name"], tier_name)
        memory_tags = ["player_gift", item_id, f"gift_tier:{tier_name}"]
        remember(target, memory_text, tick=self.world["clock"]["tick"], importance=0.72, tags=memory_tags)
        memory_payload = {"agentId": target["id"], "agentName": target["name"], "text": memory_text, "tags": memory_tags}
        memory_event = self.event_store.append("npc.memory_created", memory_payload)
        speech_text = self._pick_gift_speech(target["name"], item["name"], tier_name, fallback_pool)
        dialogue_event = self.event_store.append(
            "npc.dialogue",
            {"agentId": target["id"], "agentName": target["name"], "targetId": "player", "speech": speech_text, "topic": "gift", "reactionTier": tier_name},
        )
        event_ids = [gift_event["id"], profile_event["id"], relation_event["id"], memory_event["id"], dialogue_event["id"]]
        self._mark_known_npc(target["id"])
        self._record_player_history("give_gift", payload, event_ids)
        return {
            "dialogue": [{"speakerId": target["id"], "speakerName": target["name"], "text": speech_text}],
            "relationshipDeltas": [relationship_payload],
            "memoryWrites": [profile_payload, memory_payload],
            "playerProfile": self._player_profile_payload(),
            "relationshipStage": self._relationship_stage_payload(target["id"], before_relation, after_relation),
            "giftReaction": {"tier": tier_name, "itemId": item_id},
            "eventIds": event_ids,
        }

    def _compose_gift_memory_text(self, target_name: str, item_name: str, tier_name: str) -> str:
        """根据反应档生成 NPC 主观记忆文本，保留 LLM 在线时再覆盖的空间。"""
        templates = {
            "loved": f"新来的农场主送来{item_name}，正中我的喜好，今天心里暖了好久。",
            "liked": f"新来的农场主送给我{item_name}，这份心意我会记着。",
            "neutral": f"新来的农场主送给我{item_name}，虽然不是最爱，但收下时也很客气。",
            "disliked": f"新来的农场主送来{item_name}，我有点不知道该怎么收，气氛一下子有点尴尬。",
        }
        return templates.get(tier_name, templates["neutral"])

    def _pick_gift_speech(
        self,
        target_name: str,
        item_name: str,
        tier_name: str,
        fallback_pool: tuple[str, ...],
    ) -> str:
        """优先使用深度卡 fallbackSpeechPool；缺失时回退到通用礼貌句。"""
        if fallback_pool:
            tick = int(self.world.get("clock", {}).get("tick", 0))
            return fallback_pool[tick % len(fallback_pool)]
        return f"谢谢你送来的{item_name}，我会记住这份心意。"

    def _relationship_stage_payload(
        self,
        npc_id: str,
        before_relation: dict[str, Any],
        after_relation: dict[str, Any],
    ) -> dict[str, Any] | None:
        """计算玩家与该 NPC 当前阶段及变化方向，缺失深度卡时返回 None。"""
        card = self.npc_deep_cards.get(npc_id)
        if card is None:
            return None
        before = compute_relationship_stage(card, before_relation)
        after = compute_relationship_stage(card, after_relation)
        order = [stage.stage for stage in card.relationship_stages]
        try:
            transition = "up" if order.index(after["stage"]) > order.index(before["stage"]) else (
                "down" if order.index(after["stage"]) < order.index(before["stage"]) else "same"
            )
        except ValueError:
            transition = "same"
        return {
            "targetId": npc_id,
            "stage": after["stage"],
            "label": after["label"],
            "previousStage": before["stage"],
            "transition": transition,
            "unlocks": after["unlocks"],
        }

    def _handle_player_inspect(self, payload: dict[str, Any]) -> dict[str, Any]:
        """查看地点或事件提示，给 Godot 地图层提供轻量调查动作。"""
        event_id = str(payload.get("eventId") or "")
        location_id = str(payload.get("locationId") or self.world["player"].get("locationId") or "")
        if event_id:
            event = self._get_active_event(event_id)
            skill = self._get_event_skill_for_event(event["id"])
            inspect_payload = {
                "subjectType": "event",
                "subjectId": event["id"],
                "skillId": skill.skill_id,
                "title": skill.title,
                "summary": skill.brief,
                "locationId": skill.trigger.location_id,
                "status": event["status"],
                "participants": list(skill.participants),
                "choices": self._skill_choice_payloads(skill),
                "assetHints": self._skill_asset_hint_payloads(skill),
                "debugFields": self._skill_debug_payload(skill, None, choice="inspect"),
            }
        else:
            if location_id not in self.world["locations"]:
                raise ValueError(f"未知地点：{location_id}")
            location = self.world["locations"][location_id]
            nearby = [agent for agent in living_agents(self.world) if agent.get("locationId") == location_id]
            inspect_payload = {
                "subjectType": "location",
                "subjectId": location_id,
                "title": location["name"],
                "summary": location["description"],
                "nearbyNpcs": [{"id": agent["id"], "name": agent["name"], "job": agent["job"]} for agent in nearby],
            }

        event = self.event_store.append("player.inspected", {"playerId": "player", **inspect_payload})
        self.world["player"].setdefault("questFlags", {})[f"inspected_{inspect_payload['subjectId']}"] = True
        self._record_player_history("inspect", payload, [event["id"]])
        return {
            "dialogue": [{"speakerId": "system", "speakerName": "旁白", "text": inspect_payload["summary"]}],
            "relationshipDeltas": [],
            "memoryWrites": [],
            "inspect": inspect_payload,
            "eventIds": [event["id"]],
        }

    def _handle_player_attend_event(self, payload: dict[str, Any]) -> dict[str, Any]:
        """处理 Event Skill 事件选择，并写入关系、记忆和夜间反思种子。"""
        event_id = str(payload.get("eventId") or DAY1_EVENT_ID)
        event = self._get_active_event(event_id)
        skill = self._get_event_skill_for_event(event_id)
        choice = str(payload.get("choice") or self._default_event_choice(skill))
        try:
            option = find_event_option(skill.skill_id, choice)
        except KeyError as error:
            raise ValueError(str(error)) from error
        if event.get("status") == "resolved":
            raise ValueError(f"事件已结算：{event_id}")
        if option.requires_player_item_id:
            donated_item = self._take_player_item(option.requires_player_item_id)
        else:
            donated_item = None

        self.world["player"]["locationId"] = event["locationId"]
        outcome = self._resolve_event_skill_outcome(skill, option, donated_item)
        choice_event = self.event_store.append(
            "player.event_choice",
            {
                "playerId": "player",
                "eventId": event_id,
                "skillId": skill.skill_id,
                "choice": choice,
                "choiceLabel": outcome["choiceLabel"],
                "summary": outcome["summary"],
                "consequenceTypes": outcome["consequenceTypes"],
            },
        )
        profile_payload, profile_event = self._update_player_profile(
            "festivalChoice",
            outcome["profileEvidence"],
            tags=["player_profile_memory", "festival", skill.event_id, choice],
            choice=choice,
            style_signal=outcome.get("styleSignal"),
        )

        relationship_events: list[dict[str, Any]] = []
        relationship_payloads: list[dict[str, Any]] = []
        for target_id, delta in outcome["relationDeltas"].items():
            if target_id in self.world["agents"]:
                payload_delta = self._apply_player_relation_delta(target_id, delta)
                relationship_payloads.append(payload_delta)
                relationship_events.append(self.event_store.append("relationship.changed", payload_delta))

        memory_payloads, memory_events = self._write_event_skill_memories(skill, choice, outcome)
        dialogue_payloads, dialogue_events = self._write_event_skill_dialogue(event, skill, choice, outcome)
        reflection_payloads, reflection_events = self._write_event_skill_reflections(event, skill, choice, outcome)
        outcome_record = self._event_outcome_record(skill, outcome, choice=choice)

        event["status"] = "resolved"
        event["resolution"] = {
            "skillId": skill.skill_id,
            "choice": choice,
            "summary": outcome["summary"],
            "resolvedTick": self.world["clock"]["tick"],
            "outcomeRecord": outcome_record,
        }
        self.world.setdefault("completedEvents", []).append(dict(event))
        self.world["player"].setdefault("questFlags", {})[skill.event_id] = f"resolved_{choice}"
        resolved_event = self.event_store.append(
            "town.event_resolved",
            {
                "eventId": event_id,
                "skillId": skill.skill_id,
                "choice": choice,
                "summary": outcome["summary"],
                "outcomeRecord": outcome_record,
            },
        )

        event_ids = (
            [choice_event["id"], profile_event["id"]]
            + [item["id"] for item in relationship_events]
            + [item["id"] for item in memory_events]
            + [item["id"] for item in dialogue_events]
            + [item["id"] for item in reflection_events]
            + [resolved_event["id"]]
        )
        self._record_player_history("attend_event", payload, event_ids)
        return {
            "dialogue": dialogue_payloads,
            "relationshipDeltas": relationship_payloads,
            "memoryWrites": [profile_payload] + memory_payloads + reflection_payloads,
            "eventResult": outcome_record,
            "eventIds": event_ids,
            "playerProfile": self._player_profile_payload(),
        }

    def _update_player_profile(
        self,
        signal: str,
        evidence_summary: str,
        *,
        tags: list[str],
        choice: str | None = None,
        style_signal: str | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """更新轻量玩家风格摘要，并把摘要写入玩家记忆与事件流。"""
        player = self.world["player"]
        profile = self._player_profile_payload()
        raw_profile = player.setdefault("profile", {})
        signals = raw_profile.setdefault("signals", profile.get("signals", {}))
        signals[signal] = int(signals.get(signal, 0)) + 1
        if signal == "gift":
            signals["help"] = int(signals.get("help", 0)) + 1
        resolved_style_signal = style_signal.strip() if isinstance(style_signal, str) else ""
        if not resolved_style_signal and choice:
            resolved_style_signal = self._choice_style_signal_from_choice(choice)
        if resolved_style_signal:
            signals[resolved_style_signal] = int(signals.get(resolved_style_signal, 0)) + 1

        evidence = raw_profile.setdefault("evidence", [])
        evidence.append({"tick": self.world["clock"]["tick"], "type": signal, "summary": evidence_summary, "tags": list(tags)})
        raw_profile["evidence"] = evidence[-12:]
        raw_profile["styleSummary"] = self._compose_player_style_summary(signals)

        memory_text = f"玩家风格摘要：{raw_profile['styleSummary']} 最新依据：{evidence_summary}"
        remember(player, memory_text, tick=self.world["clock"]["tick"], importance=0.74, tags=tags)
        memory_payload = {
            "agentId": player.get("id", "player"),
            "agentName": player.get("name", "玩家"),
            "text": memory_text,
            "tags": tags,
            "profile": self._player_profile_payload(),
        }
        event = self.event_store.append("player.profile_updated", memory_payload)
        return memory_payload, event

    def _compose_player_style_summary(self, signals: dict[str, Any]) -> str:
        """把玩家行为计数压缩成 NPC 可引用的一句话风格摘要。"""
        parts: list[str] = []
        if int(signals.get("talk", 0)) > 0:
            parts.append("愿意主动认识居民")
        if int(signals.get("gift", 0)) > 0:
            parts.append("会用礼物表达善意")
        if int(signals.get("mediate", 0)) > 0:
            parts.append("遇到冲突时倾向调解")
        if int(signals.get("help", 0)) > 0 and int(signals.get("mediate", 0)) == 0:
            parts.append("遇到困难时倾向直接帮忙")
        if int(signals.get("support", 0)) > 0:
            parts.append("会在关键争执里明确站队")
        if int(signals.get("observe", 0)) > 0:
            parts.append("面对复杂局势会先观察")
        if not parts:
            parts.append("刚搬来晨露农场，风格仍在形成")
        return "；".join(parts) + "。"

    def _choice_style_signal_from_choice(self, choice: str) -> str:
        """给旧数据兼容保留的选项到风格信号映射。"""
        return {
            "mediate": "mediate",
            "support_kai": "support",
            "support_bram": "support",
            "observe": "observe",
            "donate_crop": "help",
        }.get(choice, "help")

    def _choice_style_signal_from_option(self, option: EventPlayerOption) -> str:
        """从选项后果类型推断玩家风格信号，降低 Runtime 对固定选项 id 的依赖。"""
        consequence_types = {str(consequence.consequence_type) for consequence in option.consequences}
        if "mediate" in consequence_types:
            return "mediate"
        if "support" in consequence_types or "stability" in consequence_types:
            return "support"
        if "observe" in consequence_types:
            return "observe"
        return "help"

    def _dialogue_memory_evidence(self, target: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        """为玩家二次对话准备 Memory Summary 与 RAG-lite 证据。"""
        topic = str(payload.get("topic") or "")
        message = str(payload.get("message") or "")
        query = " ".join(part for part in (topic, message) if part).strip()
        if not query and self.world["player"].get("questFlags", {}).get(DAY1_EVENT_ID):
            query = "星灯祭 玩家"
        summary = memory_summary_payload(target["id"], target, limit=8)
        retrieval = rag_lite_search(self.world, query=query, agent_id=target["id"], limit=5)
        if not retrieval["items"] and self.world["player"].get("questFlags", {}).get(DAY1_EVENT_ID):
            query = "星灯祭"
            retrieval = rag_lite_search(self.world, query=query, agent_id=target["id"], limit=5)
        return {"query": query, "summary": summary, "ragHits": retrieval["items"]}

    def _get_active_event(self, event_id: str) -> dict[str, Any]:
        """按 id 读取当前可交互事件。"""
        for event in self.world.get("activeEvents", []):
            if event.get("id") == event_id:
                return event
        raise ValueError(f"未知事件：{event_id}")

    def _get_event_skill_for_event(self, event_id: str) -> EventSkillSchema:
        """按事件 id 查找对应 Skill，避免 Runtime 写死具体事件表。"""
        for skill in self.event_skills.values():
            if skill.event_id == event_id:
                return skill
        raise ValueError(f"事件缺少可用 Skill 定义：{event_id}")

    def _default_event_choice(self, skill: EventSkillSchema) -> str:
        """选择一个无需额外物品的默认事件选项。"""
        for option in skill.player_options:
            if not option.requires_player_item_id:
                return option.option_id
        if skill.player_options:
            return skill.player_options[0].option_id
        raise ValueError(f"事件技能缺少玩家选项：{skill.skill_id}")

    def _resolve_event_skill_outcome(
        self,
        skill: EventSkillSchema,
        option: EventPlayerOption,
        donated_item: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """把 Skill 选项结算定义解析为 Runtime 可执行的 JSON 结构。"""
        try:
            outcome_def = find_event_choice_outcome(skill.skill_id, option.option_id)
        except KeyError as error:
            raise ValueError(str(error)) from error
        item_name = donated_item["name"] if donated_item else "农场作物"
        consequence_types = [str(consequence.consequence_type) for consequence in option.consequences]

        base_context = {
            "skillId": skill.skill_id,
            "eventId": skill.event_id,
            "choice": option.option_id,
            "optionId": option.option_id,
            "itemName": item_name,
            "consequenceTypes": ",".join(consequence_types),
        }
        choice_label = self._format_skill_text(outcome_def.choice_label_template, base_context)
        summary_context = dict(base_context, choiceLabel=choice_label)
        summary = self._format_skill_text(outcome_def.summary_template, summary_context)
        style_signal_template = outcome_def.player_style_signal.strip() if isinstance(outcome_def.player_style_signal, str) else ""
        style_signal = style_signal_template or self._choice_style_signal_from_option(option)
        style_label_template = outcome_def.player_style_label.strip() if isinstance(outcome_def.player_style_label, str) else ""
        if style_label_template:
            style_label = self._format_skill_text(
                style_label_template,
                dict(summary_context, summary=summary, styleSignal=style_signal),
            )
        else:
            style_label = "愿意参与小镇事务的人"
        profile_evidence_template = (
            outcome_def.profile_evidence_template.strip() if isinstance(outcome_def.profile_evidence_template, str) else ""
        )
        if profile_evidence_template:
            profile_evidence = self._format_skill_text(
                profile_evidence_template,
                dict(summary_context, summary=summary, styleLabel=style_label, styleSignal=style_signal),
            )
        else:
            profile_evidence = f"在事件“{skill.title}”中选择“{choice_label}”，小镇会把玩家记为{style_label}。"
        reaction_memory_template = (
            outcome_def.reaction_memory_template.strip() if isinstance(outcome_def.reaction_memory_template, str) else ""
        )
        if reaction_memory_template:
            fallback_memory = self._format_skill_text(
                reaction_memory_template,
                dict(summary_context, summary=summary, styleLabel=style_label, styleSignal=style_signal),
            )
        else:
            fallback_memory = f"事件结算：{summary}"
        context = dict(
            summary_context,
            summary=summary,
            styleSignal=style_signal,
            styleLabel=style_label,
            profileEvidence=profile_evidence,
            fallbackMemory=fallback_memory,
            memoryTemplateCount=len(outcome_def.memory_templates),
            reflectionSeedCount=len(outcome_def.reflection_seeds),
        )

        relation_delta_defs = outcome_def.relation_deltas or self._option_relation_deltas(option)
        relation_deltas = {
            delta.participant_id: {"affection": delta.affection, "trust": delta.trust, "conflict": delta.conflict}
            for delta in relation_delta_defs
        }
        memory_templates = [
            {
                "agentId": template.agent_id,
                "text": self._format_skill_text(template.text_template, context),
                "importance": template.importance,
                "tags": self._skill_tags(template.tags, skill.event_id, option.option_id),
            }
            for template in outcome_def.memory_templates
        ]
        fallback_dialogue = self._skill_fallback_dialogue_payloads(skill, outcome_def, context)
        reflection_seeds = [
            {
                "agentId": seed.agent_id,
                "text": self._format_skill_text(seed.text_template, context),
                "tags": self._skill_tags(seed.tags, skill.event_id, option.option_id),
            }
            for seed in outcome_def.reflection_seeds
        ]

        return {
            "skillId": skill.skill_id,
            "eventId": skill.event_id,
            "choice": option.option_id,
            "choiceLabel": choice_label,
            "summary": summary,
            "styleSignal": style_signal,
            "styleLabel": style_label,
            "profileEvidence": profile_evidence,
            "fallbackMemory": fallback_memory,
            "consequenceTypes": consequence_types,
            "relationDeltas": relation_deltas,
            "memoryTemplates": memory_templates,
            "fallbackDialogue": fallback_dialogue,
            "reflectionSeeds": reflection_seeds,
            "reflectionTags": self._skill_tags(("night_reflection",), skill.event_id, option.option_id),
            "debugFieldDefinitions": outcome_def.debug_fields,
            "debugFields": self._skill_debug_payload(
                skill,
                None,
                choice=option.option_id,
                context=context,
                extra_fields=outcome_def.debug_fields,
            ),
        }

    def _event_outcome_record(
        self,
        skill: EventSkillSchema,
        outcome: dict[str, Any],
        *,
        choice: str,
    ) -> dict[str, Any]:
        """生成事件结算记录契约，供 API 返回、事件流和 completedEvents 复用。"""
        memory_templates = outcome.get("memoryTemplates", [])
        reflection_seeds = outcome.get("reflectionSeeds", [])
        relation_deltas = outcome.get("relationDeltas", {})
        return {
            "recordVersion": skill.outcome_record_version,
            "eventId": skill.event_id,
            "skillId": skill.skill_id,
            "choice": choice,
            "choiceLabel": outcome.get("choiceLabel"),
            "summary": outcome.get("summary"),
            "consequenceTypes": list(outcome.get("consequenceTypes", [])),
            "styleSignal": outcome.get("styleSignal", ""),
            "styleLabel": outcome.get("styleLabel", ""),
            "profileEvidence": outcome.get("profileEvidence", ""),
            "fallbackMemory": outcome.get("fallbackMemory", ""),
            "memoryTemplateCount": len(memory_templates) if isinstance(memory_templates, list) else 0,
            "reflectionSeedCount": len(reflection_seeds) if isinstance(reflection_seeds, list) else 0,
            "relationDeltaCount": len(relation_deltas) if isinstance(relation_deltas, dict) else 0,
            "debugFields": self._skill_debug_payload(skill, outcome, choice=choice),
        }

    def _skill_fallback_dialogue_payloads(
        self,
        skill: EventSkillSchema,
        outcome_def: EventChoiceOutcome,
        context: dict[str, Any],
    ) -> list[dict[str, str]]:
        """按 Skill 默认模板 + 选项模板生成离线事件反应台词。"""
        template_map: dict[str, str] = {
            line.agent_id: line.speech_template
            for line in skill.fallback_dialogue_templates
            if line.agent_id and line.speech_template
        }
        for line in outcome_def.fallback_dialogue:
            if line.agent_id and line.speech_template:
                template_map[line.agent_id] = line.speech_template

        ordered_agent_ids: list[str] = [
            agent_id for agent_id in skill.participants if agent_id != "player" and agent_id in template_map
        ]
        for agent_id in template_map:
            if agent_id not in ordered_agent_ids:
                ordered_agent_ids.append(agent_id)

        return [
            {
                "agentId": agent_id,
                "speech": self._format_skill_text(template_map[agent_id], context),
            }
            for agent_id in ordered_agent_ids
        ]

    def _skill_choice_payloads(self, skill: EventSkillSchema) -> list[dict[str, Any]]:
        """把 Skill 选项转换为客户端 inspect 可直接展示的结构。"""
        return [
            {
                "id": option.option_id,
                "label": option.label,
                "brief": option.brief,
                "requiresPlayerItemId": option.requires_player_item_id,
                "consequences": [
                    {
                        "type": consequence.consequence_type,
                        "brief": consequence.brief,
                        "deltas": [
                            {
                                "participantId": delta.participant_id,
                                "affection": delta.affection,
                                "trust": delta.trust,
                                "conflict": delta.conflict,
                            }
                            for delta in consequence.deltas
                        ],
                    }
                    for consequence in option.consequences
                ],
            }
            for option in skill.player_options
        ]

    def _skill_enriched_events(self, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """把公开事件叠加 Skill 数据，减少客户端依赖种子表细节。"""
        enriched: list[dict[str, Any]] = []
        for event in events:
            item = dict(event)
            try:
                skill = self._get_event_skill_for_event(str(event.get("id") or ""))
            except ValueError:
                enriched.append(item)
                continue
            item.update(
                {
                    "skillId": skill.skill_id,
                    "title": skill.title,
                    "summary": skill.brief,
                    "participants": list(skill.participants),
                    "choices": self._skill_choice_payloads(skill),
                    "assetHints": self._skill_asset_hint_payloads(skill),
                    "debugFields": self._skill_debug_payload(skill, None, choice="public_state"),
                }
            )
            enriched.append(item)
        return enriched

    def _skill_asset_hint_payloads(self, skill: EventSkillSchema) -> list[dict[str, Any]]:
        """把 Skill 资源提示转换为 Debug 和客户端可消费的字典。"""
        return [{"id": hint.hint_id, "type": hint.asset_type, "brief": hint.brief, "tags": list(hint.tags)} for hint in skill.asset_hints]

    def _skill_debug_field_templates(self, fields: tuple[EventSkillDebugField, ...]) -> list[dict[str, str]]:
        """输出 Skill 声明的 Debug 字段模板，供 Director payload 展示。"""
        return [{"id": field.field_id, "label": field.label, "valueTemplate": field.value_template} for field in fields]

    def _skill_debug_payload(
        self,
        skill: EventSkillSchema,
        outcome: dict[str, Any] | None,
        *,
        choice: str,
        context: dict[str, Any] | None = None,
        extra_fields: tuple[EventSkillDebugField, ...] = (),
    ) -> list[dict[str, str]]:
        """按 Skill 声明生成 Debug 字段值。"""
        field_context = {
            "skillId": skill.skill_id,
            "eventId": skill.event_id,
            "choice": choice,
            "choiceLabel": outcome.get("choiceLabel") if outcome else "",
            "summary": outcome.get("summary") if outcome else skill.brief,
            "styleSignal": outcome.get("styleSignal") if outcome else "",
            "styleLabel": outcome.get("styleLabel") if outcome else "",
            "profileEvidence": outcome.get("profileEvidence") if outcome else "",
            "fallbackMemory": outcome.get("fallbackMemory") if outcome else "",
            "consequenceTypes": ",".join(outcome.get("consequenceTypes", [])) if outcome else "",
            "memoryTemplateCount": len(outcome.get("memoryTemplates", [])) if outcome else 0,
            "reflectionSeedCount": len(outcome.get("reflectionSeeds", [])) if outcome else 0,
        }
        if context:
            field_context.update(context)

        fields = list(skill.debug_fields)
        fields.extend(extra_fields)
        if outcome and isinstance(outcome.get("debugFieldDefinitions"), tuple):
            fields.extend(outcome["debugFieldDefinitions"])

        return [
            {
                "id": field.field_id,
                "label": field.label,
                "value": self._format_skill_text(field.value_template, field_context),
            }
            for field in fields
        ]

    def _option_relation_deltas(self, option: EventPlayerOption) -> tuple[Any, ...]:
        """从选项后果中提取关系变化，作为缺省结算表。"""
        deltas: list[Any] = []
        for consequence in option.consequences:
            deltas.extend(consequence.deltas)
        return tuple(deltas)

    def _skill_tags(self, tags: Any, event_id: str, choice: str) -> list[str]:
        """统一整理 Skill 标签，补上事件 id 和选项 id。"""
        if isinstance(tags, str):
            tags = (tags,)
        normalized = [str(tag) for tag in tags or [] if str(tag)]
        for tag in (event_id, choice):
            if tag and tag not in normalized:
                normalized.append(tag)
        return normalized

    def _format_skill_text(self, template: str, context: dict[str, Any]) -> str:
        """用 Skill 上下文填充文案模板。"""
        return template.format_map(_SafeFormatDict(context))

    def _apply_player_relation_delta(self, target_id: str, delta: dict[str, int | str]) -> dict[str, Any]:
        """调整玩家与 NPC 的关系并返回 Debug 友好的差值记录。"""
        target = self.world["agents"][target_id]
        before_relation = get_relation(self.world, "player", target_id)
        adjust_relation(self.world, "player", target_id, delta)
        after_relation = get_relation(self.world, "player", target_id)
        return {
            "sourceId": "player",
            "targetId": target_id,
            "targetName": target["name"],
            "delta": self._relation_diff(before_relation, after_relation),
            "after": after_relation,
        }

    def _write_event_skill_memories(
        self,
        skill: EventSkillSchema,
        choice: str,
        outcome: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """根据 Skill 记忆模板写入参与者的即时主观记忆。"""
        payloads: list[dict[str, Any]] = []
        events: list[dict[str, Any]] = []
        for template in outcome["memoryTemplates"]:
            agent_id = str(template["agentId"])
            if agent_id not in self.world["agents"]:
                continue
            agent = self.world["agents"][agent_id]
            memory_text = str(template["text"])
            tags = self._skill_tags(template.get("tags", ()), skill.event_id, choice)
            remember(agent, memory_text, tick=self.world["clock"]["tick"], importance=float(template.get("importance", 0.8)), tags=tags)
            payload = {
                "agentId": agent_id,
                "agentName": agent["name"],
                "skillId": skill.skill_id,
                "eventId": skill.event_id,
                "text": memory_text,
                "tags": tags,
            }
            payloads.append(payload)
            events.append(self.event_store.append("npc.memory_created", payload))
        return payloads, events

    def _write_event_skill_dialogue(
        self,
        event: dict[str, Any],
        skill: EventSkillSchema,
        choice: str,
        outcome: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """按 event_reaction profile 生成事件结算时玩家能看到的关键 NPC 台词。"""
        context = build_event_reaction_context(self.world, event, outcome, choice, self.event_store)
        context["playerProfile"] = self._player_profile_payload()
        context["memoryRetrieval"] = rag_lite_search(self.world, query=outcome["summary"], tags=skill.event_id, limit=5)
        messages = build_event_reaction_messages(context)
        profile = self._structured_feature_profile(self.model_config.resolve_profile(feature=FEATURE_EVENT_REACTION), FEATURE_EVENT_REACTION)
        rule_result = self._rule_event_reaction(outcome)
        provider_result, fallback_reason = self._call_profile_provider(
            feature=FEATURE_EVENT_REACTION,
            agent=None,
            context=context,
            messages=messages,
            profile=profile,
            rule_call=lambda: rule_result,
        )
        parsed, fallback_reason = self._parse_structured_provider_result(
            provider_result,
            FEATURE_EVENT_REACTION,
            fallback_reason=fallback_reason,
            fallback=rule_result["parsed"],
        )
        payloads = self._normalise_dialogue_payloads(parsed, rule_result["parsed"]["dialogue"])
        if not any(item.get("speakerId") == "system" and item.get("text") == outcome["summary"] for item in payloads):
            payloads.append({"speakerId": "system", "speakerName": "旁白", "text": outcome["summary"]})

        events: list[dict[str, Any]] = []
        for payload in payloads:
            agent_id = payload.get("speakerId")
            if agent_id in self.world["agents"]:
                agent = self.world["agents"][str(agent_id)]
                events.append(
                    self.event_store.append(
                        "npc.dialogue",
                        {"agentId": agent_id, "agentName": agent["name"], "targetId": "player", "speech": payload["text"], "topic": skill.event_id},
                    )
                )

        debug = self._build_provider_debug(
            feature=FEATURE_EVENT_REACTION,
            profile=profile,
            messages=messages,
            result=provider_result,
            parsed=parsed,
            fallback_reason=fallback_reason,
            executed={"dialogue": payloads},
            extra={
                "eventId": event.get("id"),
                "skillId": skill.skill_id,
                "choice": choice,
                "skillDebugFields": self._skill_debug_payload(skill, outcome, choice=choice),
                "playerProfile": self._player_profile_payload(),
                "memoryEvidence": context["memoryRetrieval"],
            },
        )
        events.append(self.event_store.append("debug.turn_recorded", {"agentId": "system", "agentName": event.get("title", "事件"), "debug": debug}))
        return payloads, events

    def _write_event_skill_reflections(
        self,
        event: dict[str, Any],
        skill: EventSkillSchema,
        choice: str,
        outcome: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """按 night_reflection profile 生成夜间反思摘要，失败时保留 Skill 规则种子。"""
        context = build_night_reflection_context(self.world, event, outcome, choice, self.event_store)
        context["playerProfile"] = self._player_profile_payload()
        context["memoryRetrieval"] = self._merge_night_reflection_memory_evidence(
            rag_lite_search(self.world, query=outcome["summary"], tags=skill.event_id, limit=5),
            context.get("monologueEvidence"),
        )
        messages = build_night_reflection_messages(context)
        profile = self._structured_feature_profile(self.model_config.resolve_profile(feature=FEATURE_NIGHT_REFLECTION), FEATURE_NIGHT_REFLECTION)
        rule_result = self._rule_night_reflection(outcome, monologue_evidence=context.get("monologueEvidence"))
        provider_result, fallback_reason = self._call_profile_provider(
            feature=FEATURE_NIGHT_REFLECTION,
            agent=None,
            context=context,
            messages=messages,
            profile=profile,
            rule_call=lambda: rule_result,
        )
        parsed, fallback_reason = self._parse_structured_provider_result(
            provider_result,
            FEATURE_NIGHT_REFLECTION,
            fallback_reason=fallback_reason,
            fallback=rule_result["parsed"],
        )
        payloads = self._normalise_reflection_payloads(parsed, rule_result["parsed"]["reflections"], outcome["reflectionTags"])

        events: list[dict[str, Any]] = []
        for payload in payloads:
            payload["skillId"] = skill.skill_id
            payload["eventId"] = skill.event_id
            agent = self.world["agents"][payload["agentId"]]
            remember(agent, payload["text"], tick=self.world["clock"]["tick"], importance=0.86, tags=payload["tags"])
            self.world.setdefault("nightReflections", []).append(payload)
            events.append(self.event_store.append("npc.night_reflection", payload))

        debug = self._build_provider_debug(
            feature=FEATURE_NIGHT_REFLECTION,
            profile=profile,
            messages=messages,
            result=provider_result,
            parsed=parsed,
            fallback_reason=fallback_reason,
            executed={"reflections": payloads},
            extra={
                "eventId": event.get("id"),
                "skillId": skill.skill_id,
                "choice": choice,
                "skillDebugFields": self._skill_debug_payload(skill, outcome, choice=choice),
                "playerProfile": self._player_profile_payload(),
                "memoryEvidence": context["memoryRetrieval"],
                "monologueEvidence": self._compact_monologue_evidence(context.get("monologueEvidence")),
            },
        )
        events.append(self.event_store.append("debug.turn_recorded", {"agentId": "system", "agentName": event.get("title", "事件"), "debug": debug}))
        return payloads, events

    def _decide_player_dialogue(self, target: dict[str, Any], payload: dict[str, Any], context: dict[str, Any], messages: list[dict[str, str]]) -> tuple[dict[str, Any], dict[str, Any], str | None]:
        """按 dialogue profile 生成玩家对话回复，失败时退回规则回复。"""
        profile = self._structured_feature_profile(self.model_config.resolve_profile(agent_id=target["id"], feature=FEATURE_DIALOGUE), FEATURE_DIALOGUE)
        provider_result, fallback_reason = self._call_profile_provider(
            feature=FEATURE_DIALOGUE,
            agent=target,
            context=context,
            messages=messages,
            profile=profile,
            rule_call=lambda: self._rule_player_dialogue(target, payload, context),
        )
        return provider_result, profile, fallback_reason

    def _call_profile_provider(
        self,
        *,
        feature: str,
        agent: dict[str, Any] | None,
        context: dict[str, Any],
        messages: list[dict[str, str]],
        profile: dict[str, Any],
        rule_call: Any,
    ) -> tuple[dict[str, Any], str | None]:
        """统一按 profile 调用云端或规则 Provider，并记录云端失败原因。"""
        provider_mode = self._effective_provider_mode(profile)
        if provider_mode == "cloud" and profile.get("provider") == "cloud":
            try:
                return self.cloud_provider.decide(context, messages, profile), None
            except Exception as error:
                fallback_profile = self.model_config.fallback_profile()
                fallback_reason = self._safe_error_message(error, profile=profile)
                self.event_store.append(
                    "provider.fallback",
                    {
                        "agentId": agent.get("id") if agent else None,
                        "agentName": agent.get("name") if agent else None,
                        "feature": feature,
                        "providerMode": provider_mode,
                        "profileName": profile.get("profileName"),
                        "error": fallback_reason,
                        "fallbackProfile": fallback_profile.get("profileName"),
                    },
                )
                return rule_call(), fallback_reason
        if provider_mode == "cloud" and profile.get("provider") != "cloud":
            return rule_call(), "profile_provider_rule"
        return rule_call(), None

    def _structured_feature_profile(self, profile: dict[str, Any], feature: str) -> dict[str, Any]:
        """给结构化功能补齐 JSON response_format，提升真实 LLM smoke 的可解析率。"""
        call_profile = dict(profile)
        if feature in {FEATURE_DIALOGUE, FEATURE_EVENT_REACTION, FEATURE_NIGHT_REFLECTION} and call_profile.get("provider") == "cloud":
            call_profile.setdefault("responseFormat", {"type": "json_object"})
        return call_profile

    def _parse_structured_provider_result(
        self,
        result: dict[str, Any],
        feature: str,
        *,
        fallback_reason: str | None,
        fallback: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], str | None]:
        """解析结构化功能输出，并把解析兜底原因合并进 Debug。"""
        parsed_response = parse_feature_response(result, feature)
        parsed = parse_provider_output({"rawText": result.get("rawText", ""), "parsed": parsed_response.parsed}, fallback=fallback)
        return parsed, self._combine_fallback_reasons(fallback_reason, parsed_response.fallback_reason)

    def _combine_fallback_reasons(self, *reasons: str | None) -> str | None:
        """把 provider 兜底和解析兜底合并成一条可搜索字符串。"""
        normalized = [reason for reason in reasons if reason]
        if not normalized:
            return None
        return "|".join(normalized)

    def _rule_event_reaction(self, outcome: dict[str, Any]) -> dict[str, Any]:
        """生成离线可用的事件反应 JSON，供 event_reaction fallback 使用。"""
        dialogue = [{"agentId": item["agentId"], "speech": item["speech"]} for item in outcome["fallbackDialogue"]]
        response = {"dialogue": dialogue, "memory_to_save": str(outcome.get("fallbackMemory") or f"事件结算：{outcome['summary']}")}
        return {"provider": "RuleEventReactionProvider", "rawText": json.dumps(response, ensure_ascii=False), "parsed": response, "usage": {"tokens": 0, "cost": 0, "latencyMs": 1}}

    def _rule_night_reflection(
        self,
        outcome: dict[str, Any],
        *,
        monologue_evidence: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """生成离线可用的夜间反思 JSON，供 night_reflection fallback 使用。"""
        monologue_lookup = self._night_reflection_monologue_lookup(monologue_evidence)
        reflections: list[dict[str, Any]] = []
        for seed in outcome["reflectionSeeds"]:
            agent_id = str(seed.get("agentId", ""))
            text = str(seed.get("text", "")).strip()
            if not text:
                continue
            monologue_text = monologue_lookup.get(agent_id)
            if monologue_text:
                text = f"{text} 我心里还反复想着：{monologue_text}"
            reflections.append({"agentId": agent_id, "text": text, "tags": list(seed.get("tags", []))})
        response = {"reflections": reflections or outcome["reflectionSeeds"]}
        return {"provider": "RuleNightReflectionProvider", "rawText": json.dumps(response, ensure_ascii=False), "parsed": response, "usage": {"tokens": 0, "cost": 0, "latencyMs": 1}}

    def _merge_night_reflection_memory_evidence(
        self,
        retrieval: dict[str, Any],
        monologue_evidence: Any,
    ) -> dict[str, Any]:
        """把深度卡独白种子合并进夜间反思 RAG 上下文，供模型或 fallback 引用。"""
        merged = dict(retrieval)
        items = list(retrieval.get("items", [])) if isinstance(retrieval.get("items"), list) else []
        monologue_items = monologue_evidence if isinstance(monologue_evidence, list) else []
        for entry in monologue_items:
            if not isinstance(entry, dict):
                continue
            agent_id = str(entry.get("agentId") or "")
            agent_name = str(entry.get("agentName") or agent_id or "NPC")
            for seed in entry.get("seeds", [])[:1]:
                if not isinstance(seed, dict):
                    continue
                text = str(seed.get("text") or "").strip()
                if not text:
                    continue
                tags = [str(tag) for tag in seed.get("contextTags", [])]
                items.append(
                    {
                        "agentId": agent_id,
                        "agentName": agent_name,
                        "tick": self.world["clock"]["tick"],
                        "importance": 0.55,
                        "tags": ["monologue_seed", *tags],
                        "text": self._short_debug_text(text, limit=72),
                        "source": "npc_monologue_seed",
                        "seedId": seed.get("id"),
                        "match": {"score": 5.5, "terms": [], "tags": tags},
                    }
                )
        merged["items"] = items[: max(int(merged.get("limit", 5)) + len(monologue_items), 8)]
        merged["monologueSeeds"] = self._compact_monologue_evidence(monologue_items)
        return merged

    def _night_reflection_monologue_lookup(self, monologue_evidence: list[dict[str, Any]] | None) -> dict[str, str]:
        """抽取每个 NPC 的首条独白文本，供 night_reflection fallback 拼接。"""
        lookup: dict[str, str] = {}
        for entry in monologue_evidence or []:
            if not isinstance(entry, dict):
                continue
            agent_id = str(entry.get("agentId") or "")
            if not agent_id:
                continue
            for seed in entry.get("seeds", []):
                if not isinstance(seed, dict):
                    continue
                text = str(seed.get("text") or "").strip()
                if text:
                    lookup[agent_id] = self._short_debug_text(text, limit=72)
                    break
        return lookup

    def _compact_monologue_evidence(self, monologue_evidence: Any) -> list[dict[str, Any]]:
        """压缩独白证据，避免 Debug 里出现过长文本。"""
        compact: list[dict[str, Any]] = []
        items = monologue_evidence if isinstance(monologue_evidence, list) else []
        for entry in items:
            if not isinstance(entry, dict):
                continue
            seeds: list[dict[str, Any]] = []
            for seed in entry.get("seeds", [])[:2]:
                if not isinstance(seed, dict):
                    continue
                text = str(seed.get("text") or "").strip()
                if not text:
                    continue
                seeds.append(
                    {
                        "id": str(seed.get("id") or ""),
                        "contextTags": [str(tag) for tag in seed.get("contextTags", [])],
                        "text": self._short_debug_text(text, limit=72),
                    }
                )
            compact.append(
                {
                    "agentId": str(entry.get("agentId") or ""),
                    "agentName": str(entry.get("agentName") or ""),
                    "seeds": seeds,
                }
            )
        return compact

    def _normalise_dialogue_payloads(self, parsed: dict[str, Any], fallback_dialogue: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """把模型输出统一整理成前端可消费的 dialogue payload。"""
        if parsed.get("naturalLanguageFallback") and parsed.get("speech"):
            items = [{"agentId": "system", "speech": parsed["speech"]}]
        else:
            items = parsed.get("dialogue")
        if isinstance(items, str):
            items = [{"agentId": "system", "speech": items}]
        if not isinstance(items, list) or not items:
            speech = parsed.get("speech")
            items = [{"agentId": "system", "speech": speech}] if speech else fallback_dialogue

        payloads: list[dict[str, Any]] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            speaker_id = str(item.get("agentId") or item.get("speakerId") or "system")
            text = str(item.get("speech") or item.get("text") or "").strip()
            if not text:
                continue
            if speaker_id in self.world["agents"]:
                speaker_name = self.world["agents"][speaker_id]["name"]
            else:
                speaker_id = "system"
                speaker_name = str(item.get("speakerName") or "旁白")
            payloads.append({"speakerId": speaker_id, "speakerName": speaker_name, "text": text})
        if payloads:
            return payloads
        return self._normalise_dialogue_payloads({"dialogue": fallback_dialogue}, [])

    def _normalise_reflection_payloads(
        self,
        parsed: dict[str, Any],
        fallback_reflections: list[dict[str, Any]],
        fallback_tags: list[str],
    ) -> list[dict[str, Any]]:
        """把模型输出统一整理成 nightReflections 与记忆系统可写入的 payload。"""
        if parsed.get("naturalLanguageFallback") and parsed.get("speech"):
            items = [{"agentId": fallback_reflections[0]["agentId"], "text": parsed["speech"]}]
        else:
            items = parsed.get("reflections")
        if isinstance(items, str):
            items = [{"agentId": fallback_reflections[0]["agentId"], "text": items}]
        if not isinstance(items, list) or not items:
            speech = parsed.get("speech")
            items = [{"agentId": fallback_reflections[0]["agentId"], "text": speech}] if speech else fallback_reflections

        payloads: list[dict[str, Any]] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            agent_id = str(item.get("agentId") or "")
            text = str(item.get("text") or item.get("reflection") or item.get("speech") or "").strip()
            if agent_id not in self.world["agents"] or not text:
                continue
            agent = self.world["agents"][agent_id]
            tags = self._skill_tags(item.get("tags", fallback_tags), "", "")
            payloads.append({"agentId": agent_id, "agentName": agent["name"], "text": text, "tags": tags})
        if payloads:
            return payloads
        return self._normalise_reflection_payloads({"reflections": fallback_reflections}, fallback_reflections, fallback_tags)

    def _build_provider_debug(
        self,
        *,
        feature: str,
        profile: dict[str, Any],
        messages: list[dict[str, str]],
        result: dict[str, Any],
        parsed: dict[str, Any],
        fallback_reason: str | None,
        executed: dict[str, Any] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """构建三类 LLM 验证共用的 Debug 记录，字段保持扁平可查。"""
        debug_profile = self._debug_profile(profile)
        usage = result.get("usage", {}) if isinstance(result.get("usage"), dict) else {}
        debug = {
            "tick": self.world["clock"]["tick"],
            "feature": feature,
            "provider": result.get("provider"),
            "providerMode": self._effective_provider_mode(profile),
            "profileName": debug_profile.get("profileName"),
            "apiKeyConfigured": bool(debug_profile.get("apiKeyConfigured")),
            "profile": debug_profile,
            "messages": messages,
            "rawText": result.get("rawText", ""),
            "parsed": parsed,
            "executed": executed or {},
            "usage": usage,
            "latency": usage.get("latencyMs", result.get("latencyMs")),
            "fallbackReason": fallback_reason,
        }
        if extra:
            debug.update(extra)
        return debug

    def _effective_provider_mode(self, profile: dict[str, Any]) -> str:
        """解析当前调用实际采用的 Provider 模式。"""
        return self.provider_mode if self.provider_mode != "auto" else str(profile.get("provider", "rule"))

    def _resolve_runtime_provider_mode(self) -> str:
        """统一解析全局 Provider 模式，显式测试覆盖优先于配置文件。"""
        return self.provider_mode_override or self.model_config.active_provider()

    def _safe_error_message(self, error: Exception, *, profile: dict[str, Any] | None = None) -> str:
        """保留错误摘要，避免把请求头或密钥写入事件流。"""
        message = str(error)
        for env_name in ("OPENAI_API_KEY", "DEEPSEEK_API_KEY", "AGENT_TOWN_API_KEY"):
            secret = os.getenv(env_name)
            if secret:
                message = message.replace(secret, "[REDACTED_SECRET]")
        profile = profile or {}
        for value in (profile.get("apiKey"), profile.get("apiKeyEnv")):
            text = str(value or "")
            if text.startswith(("sk-", "sk_", "sk-proj-")):
                message = message.replace(text, "[REDACTED_SECRET]")
        return message

    def _select_dialogue_memory_evidence(self, memory_evidence: dict[str, Any]) -> dict[str, Any] | None:
        """优先选择 RAG-lite 命中，其次选择 Memory Summary 中的星灯祭记忆。"""
        hits = memory_evidence.get("ragHits") if isinstance(memory_evidence.get("ragHits"), list) else []
        for hit in hits:
            tags = [str(tag) for tag in hit.get("tags", [])]
            if "starlight_festival_shortage" in tags or "night_reflection" in tags or "player_gift" in tags:
                return {"source": "rag_lite", "text": hit.get("text", ""), "tags": tags, "score": hit.get("match", {}).get("score")}
        summary = memory_evidence.get("summary") if isinstance(memory_evidence.get("summary"), dict) else {}
        summary_text = str(summary.get("summary", ""))
        if "星灯祭" in summary_text:
            return {"source": "memory_summary", "text": summary_text, "tags": ["memory_summary"], "score": None}
        return None

    def _validate_dialogue_gossip_propagation(
        self,
        *,
        parsed: dict[str, Any],
        context: dict[str, Any],
        target: dict[str, Any],
        topic: str,
    ) -> dict[str, Any] | None:
        """校验对话返回中的 gossip_propagation，并写入仅记录用途的调试结构。"""
        gossip_evidence = context.get("gossipEvidence") if isinstance(context.get("gossipEvidence"), dict) else {}
        items = gossip_evidence.get("items") if isinstance(gossip_evidence.get("items"), list) else []
        payload = parsed.get("gossip_propagation")
        if payload is None and not items:
            return None

        contract = gossip_evidence.get("propagationRecordContract") if isinstance(gossip_evidence.get("propagationRecordContract"), dict) else {}
        if payload is None:
            validation = {"accepted": False, "violations": ["payload_missing"], "normalized": {}}
        else:
            validation = validate_gossip_propagation_payload(payload, gossip_evidence)

        normalized = validation.get("normalized") if isinstance(validation.get("normalized"), dict) else {}
        accepted = bool(validation.get("accepted"))
        return {
            "agentId": target.get("id"),
            "agentName": target.get("name"),
            "topic": topic,
            "provided": payload is not None,
            "accepted": accepted,
            "violations": list(validation.get("violations", [])),
            "normalized": normalized,
            "hookId": normalized.get("hookId"),
            "direction": normalized.get("direction"),
            "targetNpcIds": list(normalized.get("targetNpcIds", [])) if isinstance(normalized.get("targetNpcIds"), list) else [],
            "recordVersion": contract.get("recordVersion"),
            "validator": contract.get("validator"),
            "worldMutationApplied": False,
            "summary": "gossip_propagation accepted" if accepted else "gossip_propagation rejected",
        }

    def _build_rule_dialogue_gossip_propagation(self, context: dict[str, Any]) -> dict[str, Any] | None:
        """规则对话模式下生成一条可被后端校验的 gossip_propagation 样例。"""
        gossip_evidence = context.get("gossipEvidence") if isinstance(context.get("gossipEvidence"), dict) else {}
        items = gossip_evidence.get("items") if isinstance(gossip_evidence.get("items"), list) else []
        if not items:
            return None
        first = items[0] if isinstance(items[0], dict) else {}
        hook_id = str(first.get("id") or "").strip()
        draft = first.get("propagationDraft") if isinstance(first.get("propagationDraft"), dict) else {}
        target_ids = [str(item).strip() for item in draft.get("targetNpcIds", []) if str(item).strip()]
        if not hook_id or not target_ids:
            return None
        direction = str(draft.get("direction") or "seed").strip() or "seed"
        return {
            "hookId": hook_id,
            "targetNpcIds": [target_ids[0]],
            "direction": direction,
            "reason": "我先记下这条传闻，再观察后续走向。",
        }

    def _short_debug_text(self, text: str, limit: int = 80) -> str:
        """压缩 Debug 和规则台词里的证据文本，避免单句过长。"""
        normalized = " ".join(str(text).split())
        return normalized if len(normalized) <= limit else normalized[: limit - 1] + "…"

    def _rule_player_dialogue(self, target: dict[str, Any], payload: dict[str, Any], context: dict[str, Any] | None = None) -> dict[str, Any]:
        """生成离线可用的 NPC 回复，方便没有云端密钥时继续开发游戏流程。"""
        context = context or {}
        topic = str(payload.get("topic") or "free_talk")
        message = str(payload.get("message") or "你好，我刚搬到小镇。")
        memory_evidence = context.get("memoryEvidence") if isinstance(context.get("memoryEvidence"), dict) else {}
        evidence_used = self._select_dialogue_memory_evidence(memory_evidence)
        player_profile = context.get("playerProfile") if isinstance(context.get("playerProfile"), dict) else self._player_profile_payload()
        if evidence_used:
            reference = self._short_debug_text(str(evidence_used.get("text", "")), 64)
            profile_hint = self._short_debug_text(str(player_profile.get("styleSummary", "")), 36)
            speech = f"我还记得这件事：{reference} 你给我的印象是{profile_hint}"
        elif "医生" in target["job"]:
            speech = "欢迎来到小镇。刚搬家别太劳累，如果农场生活让你不适应，可以来白桦诊所找我。"
        elif "酒馆" in target["job"] or target["id"] == "kai":
            speech = "新来的农场主？太好了，月猫酒馆今晚也许会有新故事。等你有空，来听我弹一曲吧。"
        elif "农夫" in target["job"] or "农场主" in target["job"]:
            speech = "晨露农场终于有人打理了。只要你踏实干活，小镇会慢慢接纳你。"
        elif "店主" in target["job"]:
            speech = "欢迎你，农场主。需要种子、食材或生活用品时，可以来星露杂货铺找我。"
        else:
            speech = f"欢迎来到 Loomstead。我听见你说“{message}”，之后我们可以慢慢熟悉。"
        response = {
            "speech": speech,
            "action": "talkTo",
            "args": {"npc": "player", "topic": topic, "message": speech},
            "memory_to_save": f"新来的农场主和我聊了 {topic}，他说：{message[:60]}",
        }
        if evidence_used:
            response["memory_evidence_used"] = evidence_used
        gossip_propagation = self._build_rule_dialogue_gossip_propagation(context)
        if gossip_propagation:
            response["gossip_propagation"] = gossip_propagation
        return {"provider": "RuleDialogueProvider", "rawText": json.dumps(response, ensure_ascii=False), "parsed": response, "usage": {"tokens": 0, "cost": 0, "latencyMs": 1}}

    def _sync_player_location(self, payload: dict[str, Any]) -> None:
        """根据客户端上报地点同步玩家位置，减少 Godot 首版接入时的状态阻塞。"""
        location_id = payload.get("locationId")
        if location_id and location_id in self.world["locations"]:
            self.world["player"]["locationId"] = str(location_id)
            anchor_id = payload.get("anchorId") or default_anchor_for_location(self.world, str(location_id))
            if anchor_id and anchor_id in self.world.get("anchors", {}):
                self.world["player"]["anchorId"] = str(anchor_id)

    def _get_target_agent(self, payload: dict[str, Any]) -> dict[str, Any]:
        """读取玩家动作目标 NPC。"""
        target_id = str(payload.get("targetId") or "")
        target = self.world["agents"].get(target_id)
        if not target or not target.get("alive", True):
            raise ValueError(f"未知或不可交互 NPC：{target_id}")
        return target

    def _mark_known_npc(self, npc_id: str) -> None:
        """记录玩家已经认识的 NPC，供任务和对话分支使用。"""
        known = self.world["player"].setdefault("knownNpcs", [])
        if npc_id not in known:
            known.append(npc_id)

    def _record_player_history(self, action_type: str, payload: dict[str, Any], event_ids: list[str]) -> None:
        """记录玩家行动历史，后续可直接扩展为存档或任务条件。"""
        history = self.world["player"].setdefault("actionHistory", [])
        history.append({"tick": self.world["clock"]["tick"], "type": action_type, "payload": dict(payload), "eventIds": event_ids})
        self.world["player"]["actionHistory"] = history[-40:]

    def _take_player_item(self, item_id: str) -> dict[str, Any]:
        """从玩家背包扣除一个物品。"""
        if not item_id:
            raise ValueError("玩家动作缺少 itemId")
        inventory = self.world["player"].setdefault("inventory", [])
        for item in inventory:
            if item.get("id") == item_id and int(item.get("quantity", 0)) > 0:
                item["quantity"] = int(item["quantity"]) - 1
                return {"id": item["id"], "name": item.get("name", item["id"])}
        raise ValueError(f"玩家背包中没有可用物品：{item_id}")

    def _add_player_item(self, item: dict[str, Any], quantity: int = 1) -> None:
        """向玩家背包加入物品；同 id 物品叠加数量。"""
        inventory = self.world["player"].setdefault("inventory", [])
        item_id = str(item.get("id") or "")
        if not item_id:
            raise ValueError("新增背包物品缺少 id")
        for existing in inventory:
            if existing.get("id") == item_id:
                existing["quantity"] = int(existing.get("quantity", 0)) + quantity
                return
        inventory.append(
            {
                "id": item_id,
                "name": item.get("name", item_id),
                "quantity": quantity,
                "tags": list(item.get("tags", [])) if isinstance(item.get("tags"), list) else [],
            }
        )

    def _relation_diff(self, before: dict[str, Any], after: dict[str, Any]) -> dict[str, int]:
        """计算关系数值变化，便于 Debug Console 展示。"""
        return {
            "affection": int(after.get("affection", 0)) - int(before.get("affection", 0)),
            "trust": int(after.get("trust", 0)) - int(before.get("trust", 0)),
            "conflict": int(after.get("conflict", 0)) - int(before.get("conflict", 0)),
        }

    def _debug_profile(self, profile: dict[str, Any]) -> dict[str, Any]:
        """Debug 展示模型配置时隐藏实际密钥。"""
        return sanitize_profile_for_debug(profile)
