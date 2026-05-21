from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.memory.memory_store import remember
from app.tools.registry import ToolRegistry
from app.world.seed_data import DAY1_LOCATION_IDS, DAY1_NPC_IDS
from app.world.world_state import adjust_relation, clamp, sync_farm_interactables


DEFAULT_TOOL_DURATION_SECONDS = 180.0
ACTION_TICK_INTERVAL_SECONDS = 30.0
MOVE_SPEED_PER_SECOND = 0.08
LOCATION_STAGE_OFFSETS = {"farm": 0.0, "plaza": 1.0, "tavern": 2.0, "shop": 1.0, "clinic": 1.0, "home-north": 3.0}
VISIBLE_LOCATION_IDS = set(DAY1_LOCATION_IDS)

TOOL_TARGET_ANCHORS = {
    "life.move_to": "plaza_gate",
    "life.rest": "farm_house_door",
    "life.eat_food": "tavern_door",
    "farm.water_crop": "farm_field",
    "shop.open_shop": "market_stall",
    "cook.prepare_meal": "tavern_stage",
    "craft.repair_stall": "plaza_fountain",
    "social.chat_with": "plaza_fountain",
    "social.give_gift": "plaza_fountain",
    "strategic.spread_rumor": "plaza_fountain",
}

TOOL_SUMMARIES = {
    "life.move_to": "前往新的小镇锚点。",
    "life.rest": "找个安静角落恢复精力。",
    "life.eat_food": "补充一点食物，稳定当天状态。",
    "farm.water_crop": "照看农田，让作物进入可成长状态。",
    "shop.open_shop": "整理摊位并维持小镇交易。",
    "cook.prepare_meal": "准备简单餐食支撑节日前夜。",
    "craft.repair_stall": "修补公共摊架，降低节日前的混乱。",
    "social.chat_with": "主动找附近居民聊聊近况。",
    "social.give_gift": "把合适的小礼物交给关系对象。",
    "strategic.spread_rumor": "谨慎传播一条已经校验过的传闻。",
}


class ToolExecutor:
    """Phase 2 工具执行器：按 ToolDefinition 推进持续动作、位移和权威副作用。"""

    def __init__(self, tool_registry: ToolRegistry | None = None) -> None:
        self.tool_registry = tool_registry or ToolRegistry()

    def tick(self, *, world: dict[str, Any], decisions: list[dict[str, Any]], delta_seconds: float) -> dict[str, Any]:
        if delta_seconds <= 0:
            return {"events": [], "agents": [], "completedActions": []}
        runtime_state = world.setdefault("toolRuntime", {})
        presence_index = self._presence_index(world)
        events: list[dict[str, Any]] = []
        agent_diffs: list[dict[str, Any]] = []
        completed_actions: list[dict[str, Any]] = []

        for decision in decisions:
            selected = self.plan_action(world, decision)
            npc_id = str(selected.get("npcId") or "")
            agent = world.get("agents", {}).get(npc_id)
            presence = presence_index.get(npc_id)
            target_anchor_id = str(selected.get("targetAnchorId") or "")
            target_location_id = str(selected.get("targetLocationId") or "")
            if not npc_id or not isinstance(agent, dict) or not isinstance(presence, dict) or not target_anchor_id or not target_location_id:
                continue
            if target_anchor_id not in world.get("anchors", {}):
                continue

            state = runtime_state.setdefault(npc_id, {})
            self._reset_state_if_needed(
                state=state,
                selected=selected,
                current_anchor_id=str(presence.get("anchorId") or ""),
                target_anchor_id=target_anchor_id,
                target_location_id=target_location_id,
            )
            before = self._agent_snapshot(agent, presence, state)
            if state.get("phase") == "moving":
                self._advance_move(world=world, presence=presence, agent=agent, selected=selected, state=state, delta_seconds=delta_seconds, events=events)
            if state.get("phase") == "performing":
                self._advance_action(selected=selected, state=state, delta_seconds=delta_seconds, events=events, completed_actions=completed_actions)
            after = self._agent_snapshot(agent, presence, state)
            if after != before:
                agent_diffs.append(after)

        return {"events": events, "agents": agent_diffs, "completedActions": completed_actions}

    def plan_action(self, world: dict[str, Any], decision: dict[str, Any]) -> dict[str, Any]:
        npc_id = str(decision.get("npcId") or "")
        selected_tool_id = str(decision.get("decision", {}).get("selectedToolId") or "")
        tool = self.tool_registry.get(selected_tool_id)
        if not npc_id or tool is None:
            return {}
        target_anchor_id = self._target_anchor_for_tool(world, npc_id, selected_tool_id, decision)
        target_anchor = world.get("anchors", {}).get(target_anchor_id, {})
        target_location_id = str(target_anchor.get("locationId") or "") if isinstance(target_anchor, dict) else ""
        tool_input = self._default_tool_input(world, npc_id, selected_tool_id, decision)
        return {
            "npcId": npc_id,
            "toolId": selected_tool_id,
            "actionId": selected_tool_id,
            "summary": TOOL_SUMMARIES.get(selected_tool_id, f"执行 {selected_tool_id}。"),
            "targetAnchorId": target_anchor_id,
            "targetLocationId": target_location_id,
            "input": tool_input,
            "durationSeconds": float(tool.duration_seconds or DEFAULT_TOOL_DURATION_SECONDS),
            "observerVisibility": tool.observer_visibility,
            "primaryNeed": decision.get("primaryNeed", {}),
            "contributingSources": list(decision.get("decision", {}).get("contributingSources") or []),
        }

    def apply_completion(self, *, world: dict[str, Any], completion: dict[str, Any], event_store: Any, source_event_id: str | None = None) -> dict[str, Any]:
        npc_id = str(completion.get("npcId") or "")
        tool_id = str(completion.get("toolId") or completion.get("actionId") or "")
        agent = world.get("agents", {}).get(npc_id)
        tool = self.tool_registry.get(tool_id)
        if not isinstance(agent, dict) or tool is None:
            return event_store.append("tool.execution_failed", {"npcId": npc_id, "toolId": tool_id, "reason": "missing_agent_or_tool", "sourceEventIds": self._source_ids(source_event_id)})

        snapshot = self._transaction_snapshot(world, agent)
        try:
            effect_summary = self._apply_tool_effect(world, agent, completion)
        except Exception as exc:  # noqa: BLE001 - 事务边界需要把未知失败转成事件。
            self._rollback_transaction(world, agent, snapshot)
            return event_store.append(
                "tool.execution_failed",
                {
                    "npcId": npc_id,
                    "npcName": agent.get("name", npc_id),
                    "toolId": tool_id,
                    "reason": str(exc),
                    "sourceEventIds": self._source_ids(source_event_id),
                    "traceRefs": list(completion.get("contributingSources") or []),
                },
            )

        return event_store.append(
            "tool.execution_completed",
            {
                "npcId": npc_id,
                "npcName": agent.get("name", npc_id),
                "toolId": tool_id,
                "summary": effect_summary,
                "worldEffects": [effect.__dict__ for effect in tool.world_effects],
                "sourceEventIds": self._source_ids(source_event_id),
                "traceRefs": list(completion.get("contributingSources") or []),
            },
        )

    def _reset_state_if_needed(self, *, state: dict[str, Any], selected: dict[str, Any], current_anchor_id: str, target_anchor_id: str, target_location_id: str) -> None:
        tool_id = str(selected.get("toolId") or "")
        changed = state.get("toolId") != tool_id or state.get("targetAnchorId") != target_anchor_id or state.get("targetLocationId") != target_location_id
        if not changed:
            return
        state.clear()
        state.update(
            {
                "toolId": tool_id,
                "actionId": tool_id,
                "targetAnchorId": target_anchor_id,
                "targetLocationId": target_location_id,
                "summary": str(selected.get("summary") or ""),
                "phase": "performing" if current_anchor_id == target_anchor_id else "moving",
                "moveProgress": 0.0,
                "moveStarted": False,
                "actionStarted": False,
                "actionElapsedSeconds": 0.0,
                "actionDurationSeconds": float(selected.get("durationSeconds") or DEFAULT_TOOL_DURATION_SECONDS),
                "actionTickAccumulator": 0.0,
                "input": deepcopy(selected.get("input") or {}),
                "contributingSources": deepcopy(selected.get("contributingSources") or []),
            }
        )

    def _advance_move(self, *, world: dict[str, Any], presence: dict[str, Any], agent: dict[str, Any], selected: dict[str, Any], state: dict[str, Any], delta_seconds: float, events: list[dict[str, Any]]) -> None:
        source_anchor_id = str(presence.get("anchorId") or "")
        source_location_id = str(presence.get("locationId") or "")
        target_anchor_id = str(state.get("targetAnchorId") or "")
        target_location_id = str(state.get("targetLocationId") or "")
        if not state.get("moveStarted"):
            state["moveStarted"] = True
            events.append(
                {
                    "type": "npc.move_started",
                    "npcId": str(selected.get("npcId") or ""),
                    "actionId": str(state.get("actionId") or ""),
                    "toolId": str(state.get("toolId") or ""),
                    "fromAnchorId": source_anchor_id,
                    "fromLocationId": source_location_id,
                    "toAnchorId": target_anchor_id,
                    "toLocationId": target_location_id,
                    "from": self._anchor_ref(world, source_anchor_id),
                    "to": self._anchor_ref(world, target_anchor_id),
                    "source": "motivation_engine",
                }
            )

        source_anchor = world.get("anchors", {}).get(source_anchor_id)
        target_anchor = world.get("anchors", {}).get(target_anchor_id)
        if not isinstance(source_anchor, dict) or not isinstance(target_anchor, dict):
            return
        distance = self._anchor_distance(source_anchor, target_anchor)
        progress_delta = 1.0 if distance <= 0.0001 else (delta_seconds * MOVE_SPEED_PER_SECOND) / distance
        new_progress = min(1.0, float(state.get("moveProgress", 0.0)) + progress_delta)
        state["moveProgress"] = new_progress
        events.append(
            {
                "type": "npc.move_progress",
                "npcId": str(selected.get("npcId") or ""),
                "actionId": str(state.get("actionId") or ""),
                "toolId": str(state.get("toolId") or ""),
                "fromAnchorId": source_anchor_id,
                "fromLocationId": source_location_id,
                "toAnchorId": target_anchor_id,
                "toLocationId": target_location_id,
                "progress": round(new_progress, 3),
            }
        )
        if new_progress < 1.0:
            return
        presence["anchorId"] = target_anchor_id
        presence["locationId"] = target_location_id
        presence["intent"] = str(selected.get("summary") or "") or str(agent.get("currentIntent") or "")
        agent["anchorId"] = presence["anchorId"]
        agent["locationId"] = presence["locationId"]
        agent["currentIntent"] = presence["intent"]
        state["phase"] = "performing"
        events.append({"type": "npc.arrived", "npcId": str(selected.get("npcId") or ""), "actionId": str(state.get("actionId") or ""), "toolId": str(state.get("toolId") or ""), "anchorId": target_anchor_id, "locationId": target_location_id})

    def _advance_action(self, *, selected: dict[str, Any], state: dict[str, Any], delta_seconds: float, events: list[dict[str, Any]], completed_actions: list[dict[str, Any]]) -> None:
        npc_id = str(selected.get("npcId") or "")
        tool_id = str(state.get("toolId") or selected.get("toolId") or "")
        duration = float(state.get("actionDurationSeconds") or DEFAULT_TOOL_DURATION_SECONDS)
        if not state.get("actionStarted"):
            state["actionStarted"] = True
            events.append(
                {
                    "type": "npc.action_started",
                    "npcId": npc_id,
                    "actionId": tool_id,
                    "toolId": tool_id,
                    "durationSeconds": duration,
                    "summary": str(state.get("summary") or ""),
                    "source": "motivation_engine",
                    "contributingSources": deepcopy(state.get("contributingSources") or []),
                }
            )
        elapsed = min(duration, float(state.get("actionElapsedSeconds", 0.0)) + delta_seconds)
        state["actionElapsedSeconds"] = elapsed
        state["actionTickAccumulator"] = float(state.get("actionTickAccumulator", 0.0)) + delta_seconds
        if elapsed < duration and state["actionTickAccumulator"] >= ACTION_TICK_INTERVAL_SECONDS:
            state["actionTickAccumulator"] = 0.0
            events.append({"type": "npc.action_tick", "npcId": npc_id, "actionId": tool_id, "toolId": tool_id, "elapsedSeconds": round(elapsed, 2), "progress": round(elapsed / duration, 3)})
        if elapsed < duration:
            return
        events.append({"type": "npc.action_completed", "npcId": npc_id, "actionId": tool_id, "toolId": tool_id, "durationSeconds": duration, "source": "motivation_engine"})
        completed_actions.append(
            {
                "npcId": npc_id,
                "toolId": tool_id,
                "actionId": tool_id,
                "summary": str(state.get("summary") or ""),
                "targetAnchorId": str(state.get("targetAnchorId") or ""),
                "targetLocationId": str(state.get("targetLocationId") or ""),
                "input": deepcopy(state.get("input") or {}),
                "contributingSources": deepcopy(state.get("contributingSources") or []),
            }
        )
        state["actionStarted"] = False
        state["actionElapsedSeconds"] = 0.0
        state["actionTickAccumulator"] = 0.0

    def _apply_tool_effect(self, world: dict[str, Any], agent: dict[str, Any], completion: dict[str, Any]) -> str:
        tool_id = str(completion.get("toolId") or "")
        tool_input = completion.get("input") if isinstance(completion.get("input"), dict) else {}
        if tool_id == "life.rest":
            agent["status"]["energy"] = clamp(agent["status"].get("energy", 50) + 18)
            agent["status"]["stress"] = clamp(agent["status"].get("stress", 0) - 8)
            return f"{agent['name']} 通过休息恢复了精力。"
        if tool_id == "life.eat_food":
            agent["status"]["energy"] = clamp(agent["status"].get("energy", 50) + 8)
            agent["status"]["mood"] = clamp(agent["status"].get("mood", 50) + 3)
            return f"{agent['name']} 补充食物后状态稳定了一些。"
        if tool_id == "life.move_to":
            agent["status"]["energy"] = clamp(agent["status"].get("energy", 50) - 2)
            return f"{agent['name']} 完成了一次自主移动。"
        if tool_id == "farm.water_crop":
            plot_id = str(tool_input.get("farmPlotId") or self._first_farm_plot_id(world) or "")
            plot = world.get("farmPlots", {}).get(plot_id)
            if isinstance(plot, dict):
                plot["stage"] = "watered"
                sync_farm_interactables(world)
            agent["status"]["energy"] = clamp(agent["status"].get("energy", 50) - 6)
            return f"{agent['name']} 浇灌了 {plot_id or '农田'}。"
        if tool_id == "shop.open_shop":
            agent["status"]["money"] = clamp(agent["status"].get("money", 0) + 7, 0, 999)
            agent["status"]["energy"] = clamp(agent["status"].get("energy", 50) - 8)
            world["townStats"]["economy"] = clamp(world["townStats"].get("economy", 50) + 1)
            return f"{agent['name']} 维持了摊位交易。"
        if tool_id == "cook.prepare_meal":
            agent["status"]["energy"] = clamp(agent["status"].get("energy", 50) - 5)
            world["townStats"]["harmony"] = clamp(world["townStats"].get("harmony", 50) + 1)
            return f"{agent['name']} 准备了节日前的简单餐食。"
        if tool_id == "craft.repair_stall":
            agent["status"]["energy"] = clamp(agent["status"].get("energy", 50) - 10)
            world["townStats"]["harmony"] = clamp(world["townStats"].get("harmony", 50) + 1)
            return f"{agent['name']} 修好了公共摊架的一处松动。"
        if tool_id in {"social.chat_with", "social.give_gift"}:
            target_id = str(tool_input.get("targetNpcId") or self._default_social_target(world, str(agent.get("id") or "")) or "")
            target = world.get("agents", {}).get(target_id)
            if isinstance(target, dict):
                relation_delta = {"affection": 3, "trust": 1} if tool_id == "social.give_gift" else {"affection": 2, "trust": 1, "conflict": -1}
                adjust_relation(world, str(agent["id"]), target_id, relation_delta)
                agent["status"]["social"] = clamp(agent["status"].get("social", 50) + 8)
                target["status"]["social"] = clamp(target["status"].get("social", 50) + 4)
                return f"{agent['name']} 与 {target['name']} 完成了一次社交互动。"
            return f"{agent['name']} 尝试社交，但目标暂不可用。"
        if tool_id == "strategic.spread_rumor":
            remember(agent, str(tool_input.get("hookId") or "传播了一条传闻"), tick=world["clock"].get("tick", 0), importance=0.55, tags=["rumor", "tool"])
            return f"{agent['name']} 记录并传播了一条受限传闻。"
        remember(agent, f"执行工具 {tool_id}", tick=world["clock"].get("tick", 0), importance=0.4, tags=["tool"])
        return f"{agent['name']} 执行了 {tool_id}。"

    def _default_tool_input(self, world: dict[str, Any], npc_id: str, tool_id: str, decision: dict[str, Any]) -> dict[str, Any]:
        if tool_id == "farm.water_crop":
            return {"farmPlotId": self._first_farm_plot_id(world)}
        if tool_id in {"social.chat_with", "social.give_gift"}:
            return {"targetNpcId": self._default_social_target(world, npc_id)}
        if tool_id == "strategic.spread_rumor":
            return {"hookId": "phase2_rule_rumor"}
        if tool_id == "life.move_to":
            return {"anchorId": self._target_anchor_for_tool(world, npc_id, tool_id, decision)}
        return {}

    def _target_anchor_for_tool(self, world: dict[str, Any], npc_id: str, tool_id: str, decision: dict[str, Any]) -> str:
        if tool_id in {"social.chat_with", "social.give_gift"}:
            target_id = self._default_social_target(world, npc_id)
            target = world.get("agents", {}).get(target_id or "")
            target_anchor = str(target.get("anchorId") or "") if isinstance(target, dict) else ""
            if self._is_visible_anchor(world, target_anchor):
                return target_anchor
        if tool_id == "life.move_to":
            anchor_id = str(decision.get("input", {}).get("anchorId") or "") if isinstance(decision.get("input"), dict) else ""
            if self._is_visible_anchor(world, anchor_id):
                return anchor_id
        configured = TOOL_TARGET_ANCHORS.get(tool_id, "plaza_fountain")
        if self._is_visible_anchor(world, configured):
            return configured
        agent = world.get("agents", {}).get(npc_id)
        current_anchor = str(agent.get("anchorId") or "") if isinstance(agent, dict) else ""
        return current_anchor if current_anchor in world.get("anchors", {}) else "plaza_fountain"

    def _default_social_target(self, world: dict[str, Any], npc_id: str) -> str | None:
        agent = world.get("agents", {}).get(npc_id)
        location_id = str(agent.get("locationId") or "") if isinstance(agent, dict) else ""
        for candidate_id in DAY1_NPC_IDS:
            if candidate_id == npc_id:
                continue
            candidate = world.get("agents", {}).get(candidate_id)
            if isinstance(candidate, dict) and str(candidate.get("locationId") or "") == location_id:
                return candidate_id
        return next((candidate_id for candidate_id in DAY1_NPC_IDS if candidate_id != npc_id), None)

    def _first_farm_plot_id(self, world: dict[str, Any]) -> str | None:
        return next(iter(world.get("farmPlots", {}).keys()), None)

    def _presence_index(self, world: dict[str, Any]) -> dict[str, dict[str, Any]]:
        index: dict[str, dict[str, Any]] = {}
        for presence in world.get("npcPresence", []):
            if isinstance(presence, dict) and presence.get("agentId"):
                index[str(presence["agentId"])] = presence
        return index

    def _anchor_ref(self, world: dict[str, Any], anchor_id: str) -> dict[str, Any]:
        anchor = world.get("anchors", {}).get(anchor_id)
        if not isinstance(anchor, dict):
            return {"anchorId": anchor_id, "locationId": "", "screenPosition": {"x": 0.0, "y": 0.0}}
        return {"anchorId": anchor_id, "locationId": str(anchor.get("locationId") or ""), "screenPosition": deepcopy(anchor.get("screenPosition") or {"x": 0.0, "y": 0.0})}

    def _is_visible_anchor(self, world: dict[str, Any], anchor_id: str) -> bool:
        anchor = world.get("anchors", {}).get(anchor_id)
        return isinstance(anchor, dict) and str(anchor.get("locationId") or "") in VISIBLE_LOCATION_IDS

    def _anchor_distance(self, source_anchor: dict[str, Any], target_anchor: dict[str, Any]) -> float:
        source_pos = source_anchor.get("screenPosition") if isinstance(source_anchor.get("screenPosition"), dict) else {}
        target_pos = target_anchor.get("screenPosition") if isinstance(target_anchor.get("screenPosition"), dict) else {}
        source_offset = LOCATION_STAGE_OFFSETS.get(str(source_anchor.get("locationId") or ""), 0.0)
        target_offset = LOCATION_STAGE_OFFSETS.get(str(target_anchor.get("locationId") or ""), source_offset)
        source_x = source_offset + float(source_pos.get("x", 0.0))
        source_y = float(source_pos.get("y", 0.0))
        target_x = target_offset + float(target_pos.get("x", 0.0))
        target_y = float(target_pos.get("y", 0.0))
        return ((source_x - target_x) ** 2 + (source_y - target_y) ** 2) ** 0.5

    def _agent_snapshot(self, agent: dict[str, Any], presence: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
        return {
            "npcId": str(agent.get("id") or ""),
            "locationId": str(presence.get("locationId") or agent.get("locationId") or ""),
            "anchorId": str(presence.get("anchorId") or agent.get("anchorId") or ""),
            "lifeAction": {
                "actionId": str(state.get("actionId") or ""),
                "phase": str(state.get("phase") or ""),
                "moveProgress": round(float(state.get("moveProgress", 0.0)), 3),
                "elapsedSeconds": round(float(state.get("actionElapsedSeconds", 0.0)), 2),
                "durationSeconds": round(float(state.get("actionDurationSeconds", 0.0)), 2),
            },
            "toolDecision": {
                "toolId": str(state.get("toolId") or ""),
                "source": "motivation_engine",
            },
        }

    def _transaction_snapshot(self, world: dict[str, Any], agent: dict[str, Any]) -> dict[str, Any]:
        return {
            "agentStatus": deepcopy(agent.get("status", {})),
            "agentMemories": deepcopy(agent.get("memories", [])),
            "townStats": deepcopy(world.get("townStats", {})),
            "relations": deepcopy(world.get("relations", {})),
            "farmPlots": deepcopy(world.get("farmPlots", {})),
            "interactables": deepcopy(world.get("interactables", {})),
        }

    def _rollback_transaction(self, world: dict[str, Any], agent: dict[str, Any], snapshot: dict[str, Any]) -> None:
        agent["status"] = deepcopy(snapshot.get("agentStatus", {}))
        agent["memories"] = deepcopy(snapshot.get("agentMemories", []))
        world["townStats"] = deepcopy(snapshot.get("townStats", {}))
        world["relations"] = deepcopy(snapshot.get("relations", {}))
        world["farmPlots"] = deepcopy(snapshot.get("farmPlots", {}))
        world["interactables"] = deepcopy(snapshot.get("interactables", {}))

    def _source_ids(self, source_event_id: str | None) -> list[str]:
        return [source_event_id] if source_event_id else []
