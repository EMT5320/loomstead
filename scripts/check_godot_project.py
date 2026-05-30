"""检查 Godot 客户端骨架是否满足当前数据契约要求。"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GODOT_ROOT = ROOT / "clients" / "godot"


def read(path: Path) -> str:
    """按 UTF-8 读取项目文件。"""
    return path.read_text(encoding="utf-8")


required_files = [
    GODOT_ROOT / "project.godot",
    GODOT_ROOT / "README.md",
    GODOT_ROOT / "scenes" / "main.tscn",
    GODOT_ROOT / "scenes" / "world_main.tscn",
    GODOT_ROOT / "scripts" / "asset_registry.gd",
    GODOT_ROOT / "scripts" / "main.gd",
    GODOT_ROOT / "scripts" / "api_client.gd",
    GODOT_ROOT / "scripts" / "world_sync.gd",
    GODOT_ROOT / "scripts" / "core" / "world_clock.gd",
    GODOT_ROOT / "scripts" / "core" / "event_bus.gd",
    GODOT_ROOT / "scripts" / "world" / "npc_controller.gd",
    GODOT_ROOT / "scripts" / "world" / "player_controller.gd",
    GODOT_ROOT / "scripts" / "world" / "town_map.gd",
    GODOT_ROOT / "scripts" / "ui" / "hud.gd",
    GODOT_ROOT / "scripts" / "ui" / "vn_panel.gd",
    GODOT_ROOT / "scripts" / "ui" / "observer_panel.gd",
    GODOT_ROOT / "scripts" / "ui" / "showcase_panel.gd",
]

for file_path in required_files:
    if not file_path.exists():
        raise RuntimeError(f"Godot 客户端缺少必要文件：{file_path}")

project = read(GODOT_ROOT / "project.godot")
scene = read(GODOT_ROOT / "scenes" / "main.tscn")
world_main_scene = read(GODOT_ROOT / "scenes" / "world_main.tscn")
asset_registry = read(GODOT_ROOT / "scripts" / "asset_registry.gd")
api_client = read(GODOT_ROOT / "scripts" / "api_client.gd")
main_script = read(GODOT_ROOT / "scripts" / "main.gd")
world_sync = read(GODOT_ROOT / "scripts" / "world_sync.gd")
world_clock = read(GODOT_ROOT / "scripts" / "core" / "world_clock.gd")
event_bus = read(GODOT_ROOT / "scripts" / "core" / "event_bus.gd")
npc_controller = read(GODOT_ROOT / "scripts" / "world" / "npc_controller.gd")
player_controller = read(GODOT_ROOT / "scripts" / "world" / "player_controller.gd")
town_map = read(GODOT_ROOT / "scripts" / "world" / "town_map.gd")
hud = read(GODOT_ROOT / "scripts" / "ui" / "hud.gd")
vn_panel = read(GODOT_ROOT / "scripts" / "ui" / "vn_panel.gd")
observer_panel = read(GODOT_ROOT / "scripts" / "ui" / "observer_panel.gd")
showcase_panel = read(GODOT_ROOT / "scripts" / "ui" / "showcase_panel.gd")

checks = {
    "project main scene": 'run/main_scene="res://scenes/world_main.tscn"' in project,
    "legacy main scene kept": 'path="res://scripts/main.gd"' in scene,
    "scene script": 'path="res://scripts/main.gd"' in scene,
    "world main scene script": 'path="res://scripts/world/town_map.gd"' in world_main_scene,
    "world main scene hud": 'path="res://scripts/ui/hud.gd"' in world_main_scene,
    "world state endpoint": '"/api/world/state"' in api_client,
    "showcase starlight endpoint": '"/api/showcase/starlight"' in api_client and "func get_showcase_starlight" in api_client,
    "player action endpoint": '"/api/player/action"' in api_client,
    "world tick endpoint": '"/api/world/tick"' in api_client and "func tick(" in api_client,
    "api class": "class_name ApiClient" in api_client,
    "project autoload world clock": 'WorldClockService="*res://scripts/core/world_clock.gd"' in project,
    "project autoload event bus": 'EventBusService="*res://scripts/core/event_bus.gd"' in project,
    "world clock class": "class_name WorldClock" in world_clock,
    "world clock signals": "signal tick_requested" in world_clock and "signal tick_received" in world_clock,
    "world clock tick request": "_api_client.tick(" in world_clock and "func set_paused" in world_clock and "func set_speed" in world_clock,
    "world clock speed contract": "tick_interval_seconds * speed" not in world_clock,
    "event bus class": "class_name EventBus" in event_bus,
    "event bus tick consume": "_on_world_clock_tick_received" in event_bus and "tick_events_received.emit" in event_bus,
    "event bus npc dispatch": "signal npc_motion_event" in event_bus and "signal npc_action_event" in event_bus,
    "event bus eventstore payload flatten": "_normalize_event_payload" in event_bus and 'event_payload.get("payload", {})' in event_bus,
    "npc controller class": "class_name NpcController" in npc_controller,
    "npc controller state machine": "enum NpcState" in npc_controller and "IDLE" in npc_controller and "WALKING" in npc_controller and "PERFORMING" in npc_controller,
    "npc controller anchor lerp": "configure_anchor_graph" in npc_controller and "lerp(" in npc_controller and "ActionLabel" in npc_controller,
    "npc controller authoritative move": "后端当前直接下发起点和终点" in npc_controller and "Path?" not in npc_controller,
    "npc controller sprite appearance": "Sprite2D" in npc_controller and "configure_appearance" in npc_controller and "FallbackBody" in npc_controller,
    "npc controller idle bobbing": "_update_idle_bobbing" in npc_controller and "GroundShadow" in npc_controller,
    "player controller class": "class_name PlayerController" in player_controller,
    "player controller local movement": "Input.is_key_pressed" in player_controller and "interaction_origin" in player_controller and "set_world_bounds" in player_controller,
    "vn panel class": "class_name WorldVnPanel" in vn_panel,
    "vn panel backend status": "show_busy" in vn_panel and "show_dialogue" in vn_panel and "show_hint" in vn_panel,
    "town map class": "class_name TownMap" in town_map,
    "town map stage visuals": "STAGE_ORDER" in town_map and "_build_stage_visuals" in town_map and "get_location_background" in town_map,
    "town map route readability": "_update_route_line" in town_map and "Line2D" in town_map and "WorldEventLabel" in town_map,
    "town map world pulse panel": "WorldPulsePanel" in town_map and "_request_initial_world_snapshot" in town_map and "_refresh_world_pulse_panel" in town_map,
    "town map schedule snapshot": "npcSchedules" in town_map and "activeLifeAction" in town_map and "spaceActionCandidates" in town_map,
    "town map npc status pulse": "_update_npc_status_from_event" in town_map and "_update_npc_statuses_from_agents" in town_map and "PULSE_PANEL_MAX_LINES" in town_map,
    "town map remote event beacon": "RemoteEventCompass" in town_map and "_sync_event_beacons" in town_map and "_ensure_event_beacon" in town_map,
    "town map event anchor mapping": "EVENT_ANCHORS" in town_map and "DEFAULT_EVENT_ANCHORS" in town_map and "get_interaction_marker(\"event\")" in town_map,
    "town map player loop": "PlayerControllerScript" in town_map and "_spawn_player" in town_map and "_update_nearest_npc_hint" in town_map,
    "town map backend talk": "_submit_talk" in town_map and "post_player_action" in town_map and "world_map_greeting" in town_map,
    "town map observer selected tool": "selectedToolId" in town_map,
    "town map observer effective heuristic": "effectiveConfidence" in town_map,
    "town map vn panel": "VnPanelScript" in town_map and "show_dialogue" in town_map and "show_busy" in town_map,
    "town map observer panel": "ObserverPanelScript" in town_map and "get_phase2_debug" in town_map and "_build_phase2_observer_summary" in town_map,
    "town map showcase panel": "ShowcasePanelScript" in town_map and "_build_showcase_panel" in town_map and "_request_showcase_payload" in town_map,
    "town map showcase keys": "KEY_F1" in town_map and "_toggle_showcase_panel" in town_map and "_on_showcase_deep_dive_requested" in town_map,
    "town map camera follow": "Camera2D" in town_map and "make_current" in town_map,
    "town map npc wiring": "_ensure_npc_controller" in town_map and "_on_npc_motion_event" in town_map,
    "town map backend ids": "farm_house_door" in town_map and "tavern_stage" in town_map and "DEMO_SPAWN_ANCHORS" in town_map and "npc_kai" not in town_map,
    "hud class": "class_name WorldHud" in hud,
    "hud clock speed controls": "_on_pause_pressed" in hud and "_on_speed_pressed" in hud and "_on_tick_clock_updated" in hud,
    "observer panel class": "class_name ObserverPanel" in observer_panel,
    "observer panel phase2 sections": "subjectiveMemory" in observer_panel and "relationshipEdges" in observer_panel and "heuristics" in observer_panel,
    "observer panel recent trace": "recentTraceEvents" in observer_panel and "_summarize_phase2_recent_trace" in town_map,
    "observer panel trace copy empty state": "暂无 trace 可复制" in observer_panel and "当前过滤器暂无 trace，等待下一次 Phase 2 Debug 刷新" in observer_panel,
    "observer panel phase2 error hint": "Phase 2 Debug 同步失败：可点击 Retry 重新拉取，trace 区将自动恢复。" in observer_panel and "trace details 暂不可用：Phase 2 Debug 同步失败，请先点击 Retry 重试。" in observer_panel,
    "observer panel trace filter": "traceFilter" in observer_panel and "recentTraceEventGroups" in town_map and "_phase2_trace_filter_matches" in town_map,
    "observer panel trace drilldown": "Copy trace" in observer_panel and "_on_trace_copy_pressed" in observer_panel and "recentTraceDetailGroups" in town_map and "_phase2_trace_detail_text" in town_map,
    # 任务 7.3（R4.4）：trace 裁剪上限 50 条 + 共享纯逻辑 + 裁剪后 reverse 为 newest→oldest。
    "observer panel trace clip limit": "TRACE_RECENT_LIMIT := 50" in town_map and "_clip_and_sort_trace_entries" in town_map and "clipped.reverse()" in town_map,
    # 任务 8.3（R4.6）：Prev/Next 同帧导航守卫 + 同帧 Next 优先（基线索引 + 帧号守卫 + Engine.get_process_frames）。
    "observer panel same-frame next priority": "_apply_trace_navigation" in observer_panel and "_last_trace_nav_frame" in observer_panel and "_trace_nav_baseline_index" in observer_panel and "_trace_nav_next_applied" in observer_panel and "Engine.get_process_frames()" in observer_panel,
    # 任务 8.5（R4.7）：Copy trace 反馈时长常量 ≥2 秒。
    "observer panel copy feedback duration": "TRACE_COPY_FEEDBACK_SECONDS := 2.0" in observer_panel,
    # 任务 9.4（R4.1/R4.3/R4.8/R4.9）：身份四字段 + loading 文案（SECTION_LOADING_TEXT + 四 section loading 渲染）+ placeholder（SECTION_EMPTY_TEXT）+ 同步失败语义指示。
    "observer panel loading vs placeholder states": "_identity_id_label" in observer_panel and "_identity_name_label" in observer_panel and "_identity_location_label" in observer_panel and "_identity_anchor_label" in observer_panel and "SECTION_LOADING_TEXT" in observer_panel and "_render_loading_motivation" in observer_panel and "_render_loading_memory" in observer_panel and "_render_loading_relationships" in observer_panel and "_render_loading_heuristics" in observer_panel and "SECTION_EMPTY_TEXT" in observer_panel and "同步失败" in observer_panel and "show_phase2_error" in observer_panel,
    "showcase panel class": "class_name ShowcasePanel" in showcase_panel and "extends CanvasLayer" in showcase_panel,
    "showcase panel default visible": "set_panel_visible(true)" in showcase_panel and "func toggle_panel_visible" in showcase_panel,
    "showcase panel required cards": "goalCard" in showcase_panel and "directorCard" in showcase_panel and "eventSkillCard" in showcase_panel and "npcDecisionCard" in showcase_panel and "traceEvidenceCard" in showcase_panel,
    "showcase panel deep dive": "signal deep_dive_requested" in showcase_panel and "Deep dive" in showcase_panel and "_trace_focus_from_strip" in showcase_panel,
    "showcase panel backend fallback": "show_backend_error" in showcase_panel and "Backend error" in showcase_panel,
    "asset registry class": "class_name AssetRegistry" in asset_registry,
    "asset registry backgrounds": "farm_day_anime.png" in asset_registry and "tavern_evening_anime.png" in asset_registry,
    "asset registry portraits": "npc_orren_neutral.png" in asset_registry and "player_farmer_neutral.png" in asset_registry,
    "asset registry map sprites": "npc_orren_map_idle.png" in asset_registry and "player_farmer_map_idle.png" in asset_registry,
    "asset registry interaction markers": "interaction_marker_talk.png" in asset_registry and "interaction_marker_event.png" in asset_registry,
    "world sync class": "class_name WorldSync" in world_sync,
    "world sync interactions": "get_available_interactions" in world_sync and "find_event_choice_interaction" in world_sync,
    "main asset registry": "AssetRegistryScript" in main_script,
    "main background texture": "background_rect" in main_script,
    "main map character layer": "map_character_layer" in main_script and "_render_map_characters" in main_script,
    "main local move feedback": "player_local_target" in main_script and "_tick_local_player_motion" in main_script,
    "main continuous input move": "Input.get_vector" in main_script and "PLAYER_LOCAL_KEY_STEP" not in main_script,
    "main proximity feedback": "_update_map_proximity_feedback" in main_script and "MapMoveHint" in main_script,
    "main wasd input move": "_ensure_local_input_actions" in main_script and "_read_local_move_axis" in main_script and "move_left" in main_script and "move_down" in main_script,
    "main direct map click target": "_on_map_character_layer_gui_input" in main_script and "gui_input.connect" in main_script,
    "main ui click-through": "mouse_filter = Control.MOUSE_FILTER_IGNORE" in main_script and "Control.FOCUS_NONE" in main_script,
    "main single proximity target": "nearest_npc_actor" in main_script and "nearest_event_marker" in main_script,
    "main proximity anchor/interactable target": "current_near_anchor_id" in main_script and "current_near_interactable_id" in main_script and "_rebuild_map_context_candidates" in main_script,
    "main map context panel": "MapContextActions" in main_script and "map_context_candidates" in main_script and "_refresh_map_context_panel" in main_script,
    "main map context hotkeys": "KEY_E" in main_script and "KEY_SPACE" in main_script and "KEY_TAB" in main_script and "KEY_Q" in main_script and "_trigger_current_map_context_action" in main_script,
    "main separated player spawn": "_player_spawn_for_location" in main_script and "_scene_stage_center" in main_script,
    "main scene slot anchors": "MAP_NPC_SLOT_RATIOS" in main_script and "_scene_npc_anchor" in main_script and "_scene_anchor_from_ratio" in main_script,
    "main compact interact radius": "PLAYER_LOCAL_INTERACT_RADIUS := 86.0" in main_script,
    "main proximity hysteresis": "PLAYER_LOCAL_INTERACT_EXIT_MARGIN" in main_script and "current_near_npc_id" in main_script and "current_near_event_id" in main_script,
    "main movement debug overlay": "MAP_MOVEMENT_DEBUG_ENABLED := false" in main_script and "MapMovementDebug" in main_script and "_update_map_debug_label" in main_script,
    "main movement debug notes": "last_location_debug" in main_script and "_push_map_debug_note" in main_script and "last_proximity_debug" in main_script,
    "main stable player actor reference": "player_actor_node" in main_script and "_get_player_actor_node" in main_script and "str(child.get_meta(\"agentId\", \"\")) == \"player\"" in main_script,
    "main immediate map child removal": "node.remove_child(child)" in main_script and "旧名字占位" in main_script,
    "main clamped click target": "target_was_clamped" in main_script and "bounds.has_point(world_point)" not in main_script,
    "main wider dynamic map bounds": "viewport_size.x * 0.10" in main_script and "side_margin" in main_script,
    "main safe player spawn": "MAP_PLAYER_SPAWN_RATIO := Vector2(0.50, 0.66)" in main_script,
    "main clear near focus on location change": "current_near_npc_id = \"\"" in main_script and "selected_location_id != previous_location_id" in main_script,
    "main authoritative location switch": "selected_location_id = location_id" not in main_script and "previous_player = world_sync.get_player()" in main_script,
    "main npc sprite remains clickable": "sprite_button.disabled = false" in main_script,
    "main no npc selection location drift": "selected_location_id = str(npc.get(\"locationId\"" not in main_script,
    "main no npc center cluster": "MAP_CLUSTER_OFFSETS" not in main_script and "_cluster_offset" not in main_script,
    "main current-scene actor filter": "npc_location != selected_location_id" in main_script and "event_location != selected_location_id" in main_script,
    "main wider walk area": "_clamp_point_to_walk_area" in main_script and "PLAYER_LOCAL_ZONE_RADIUS" not in main_script,
    "main click target marker": "PlayerMoveTarget" in main_script,
    "main no sprite halo background": '"Halo"' not in main_script,
    "main backend interactions": "give_gift" in main_script and "find_interaction" in main_script,
    "main scene anchor contract": "anchorId" in main_script and "_on_move_to_anchor_pressed" in main_script and "_render_scene_actions" in main_script,
    "main portrait texture": "portrait_rect" in main_script,
    "main refresh": "_refresh_world" in main_script,
}

failed = [name for name, ok in checks.items() if not ok]
if failed:
    raise RuntimeError(f"Godot 客户端骨架检查失败：{', '.join(failed)}")

required_assets = [
    GODOT_ROOT / "assets" / "locations" / "farm_day_anime.png",
    GODOT_ROOT / "assets" / "locations" / "plaza_day_anime.png",
    GODOT_ROOT / "assets" / "locations" / "tavern_evening_anime.png",
    GODOT_ROOT / "assets" / "characters" / "player_farmer_neutral.png",
    GODOT_ROOT / "assets" / "characters" / "npc_mira_neutral.png",
    GODOT_ROOT / "assets" / "characters" / "npc_tomas_neutral.png",
    GODOT_ROOT / "assets" / "characters" / "npc_orren_neutral.png",
    GODOT_ROOT / "assets" / "characters" / "npc_lena_neutral.png",
    GODOT_ROOT / "assets" / "characters" / "npc_kai_neutral.png",
    GODOT_ROOT / "assets" / "characters" / "npc_bram_neutral.png",
    GODOT_ROOT / "assets" / "sprites" / "player_farmer_map_idle.png",
    GODOT_ROOT / "assets" / "sprites" / "npc_mira_map_idle.png",
    GODOT_ROOT / "assets" / "sprites" / "npc_tomas_map_idle.png",
    GODOT_ROOT / "assets" / "sprites" / "npc_orren_map_idle.png",
    GODOT_ROOT / "assets" / "sprites" / "npc_lena_map_idle.png",
    GODOT_ROOT / "assets" / "sprites" / "npc_kai_map_idle.png",
    GODOT_ROOT / "assets" / "sprites" / "npc_bram_map_idle.png",
    GODOT_ROOT / "assets" / "sprites" / "interaction_marker_talk.png",
    GODOT_ROOT / "assets" / "sprites" / "interaction_marker_gift.png",
    GODOT_ROOT / "assets" / "sprites" / "interaction_marker_event.png",
]
missing_assets = [str(path.relative_to(GODOT_ROOT)) for path in required_assets if not path.exists()]
if missing_assets:
    raise RuntimeError(f"Godot 客户端缺少首批视觉资产：{', '.join(missing_assets)}")

missing_imports = [
    str(path.with_name(path.name + ".import").relative_to(GODOT_ROOT))
    for path in required_assets
    if not path.with_name(path.name + ".import").exists()
]
if missing_imports:
    raise RuntimeError(f"Godot 客户端缺少首批视觉资产导入元数据：{', '.join(missing_imports)}")

print("[godot-check] ok", {"files": len(required_files)})
