class_name TownMap
extends Node2D

const ApiClientScript := preload("res://scripts/api_client.gd")
const AssetRegistryScript := preload("res://scripts/asset_registry.gd")
const PlayerControllerScript := preload("res://scripts/world/player_controller.gd")
const VnPanelScript := preload("res://scripts/ui/vn_panel.gd")
const ObserverPanelScript := preload("res://scripts/ui/observer_panel.gd")

const STAGE_WIDTH := 640.0
const STAGE_HEIGHT := 1080.0
const PLAYER_INTERACT_RADIUS := 128.0
const OBSERVER_NPC_CLICK_RADIUS := 72.0
const OBSERVER_PHASE2_CACHE_MSEC := 12000
const OBSERVER_PHASE2_REQUEST_INTERVAL_MSEC := 800
const OBSERVER_TRACE_HIGHLIGHT_MSEC := 2600
const ROUTE_LINE_VISIBLE_MSEC := 2200
const PULSE_PANEL_MAX_LINES := 6
const STAGE_ORDER := ["farm", "plaza", "tavern"]
const EVENT_ANCHORS := {
	"starlight_festival_shortage": "tavern_stage",
}
const DEFAULT_EVENT_ANCHORS := {
	"farm": "farm_house_door",
	"plaza": "plaza_fountain",
	"tavern": "tavern_stage",
}
const STAGE_NAMES := {
	"farm": "Farm 农场",
	"plaza": "Plaza 广场",
	"tavern": "Tavern 酒馆",
}
const STAGE_ANCHORS := {
	"farm": {
		"farm_house_door": Vector2(0.26, 0.68),
		"farm_field": Vector2(0.58, 0.72),
	},
	"plaza": {
		"plaza_gate": Vector2(0.18, 0.76),
		"plaza_fountain": Vector2(0.54, 0.62),
		"market_stall": Vector2(0.72, 0.58),
	},
	"tavern": {
		"tavern_door": Vector2(0.22, 0.74),
		"tavern_stage": Vector2(0.62, 0.56),
	},
}
const DEMO_SPAWN_ANCHORS := {
	"mira": "market_stall",
	"tomas": "plaza_fountain",
	"orren": "plaza_fountain",
	"lena": "plaza_fountain",
	"kai": "tavern_stage",
	"bram": "farm_field",
}
const NPC_CROWD_OFFSETS := {
	"mira": Vector2(-22.0, 12.0),
	"tomas": Vector2(-36.0, 10.0),
	"orren": Vector2(0.0, -8.0),
	"lena": Vector2(34.0, 12.0),
	"kai": Vector2(-18.0, 8.0),
	"bram": Vector2(20.0, 10.0),
}
const NPC_DISPLAY_NAMES := {
	"mira": "Mira 米娅",
	"tomas": "Tomas 托玛",
	"orren": "Orren 奥蕾娅",
	"lena": "Lena 莉娜",
	"kai": "Kai 凯娅",
	"bram": "Bram 布兰娜",
}
const NPC_COLORS := {
	"mira": Color(1.0, 0.76, 0.88, 1.0),
	"tomas": Color(0.70, 0.90, 1.0, 1.0),
	"orren": Color(0.86, 0.78, 1.0, 1.0),
	"lena": Color(0.82, 1.0, 0.74, 1.0),
	"kai": Color(1.0, 0.90, 0.62, 1.0),
	"bram": Color(1.0, 0.72, 0.55, 1.0),
}

@onready var stage_layer: Node2D = $StageLayer
@onready var npc_layer: Node2D = $NpcLayer
@onready var debug_layer: Node2D = $DebugLayer

var _api_client: ApiClient
var _asset_registry: AssetRegistry
var _stage_origins: Dictionary = {}
var _anchor_positions: Dictionary = {}
var _anchor_graph: Dictionary = {}
var _npc_nodes: Dictionary = {}
var _route_lines: Dictionary = {}
var _route_line_expire_msec: Dictionary = {}
var _event_label: Label
var _pulse_layer: CanvasLayer
var _pulse_clock_label: Label
var _pulse_event_label: Label
var _pulse_schedule_label: Label
var _event_compass_label: Label
var _player_controller
var _camera: Camera2D
var _vn_panel
var _observer_panel
var _nearest_npc_id := ""
var _selected_observer_npc_id := ""
var _observer_phase2_cache: Dictionary = {}
var _observer_phase2_request_msec: Dictionary = {}
var _observer_phase2_in_flight: Dictionary = {}
var _talk_in_flight := false
var _snapshot_in_flight := false
var _latest_clock: Dictionary = {}
var _npc_plans: Dictionary = {}
var _npc_statuses: Dictionary = {}
var _active_event_summaries: Array[String] = []
var _active_event_records: Dictionary = {}
var _event_beacons: Dictionary = {}


func _ready() -> void:
	# 默认入口必须直接使用现有美术资源，纯色块只作为资源缺失 fallback。
	stage_layer.z_index = 0
	debug_layer.z_index = 5
	npc_layer.z_index = 10
	_api_client = ApiClientScript.new()
	_api_client.name = "WorldInteractionApiClient"
	add_child(_api_client)
	_asset_registry = AssetRegistryScript.new()
	_asset_registry.name = "WorldAssetRegistry"
	add_child(_asset_registry)
	_build_stage_visuals()
	_build_anchor_graph()
	_build_event_label()
	_build_world_pulse_panel()
	_spawn_demo_npcs()
	_spawn_player()
	_build_camera()
	_build_vn_panel()
	_build_observer_panel()
	_connect_event_bus()
	_connect_world_clock()
	call_deferred("_request_initial_world_snapshot")
	set_process(true)


func _process(_delta: float) -> void:
	_update_camera_target()
	_update_nearest_npc_hint()
	_expire_route_lines()
	_update_event_beacons()
	_refresh_event_compass()
	_refresh_selected_observer_npc()


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey:
		var key_event := event as InputEventKey
		if key_event.pressed and not key_event.echo:
			if key_event.keycode == KEY_TAB:
				_toggle_observer_panel()
				get_viewport().set_input_as_handled()
				return
			if key_event.keycode == KEY_E and _nearest_npc_id != "":
				_select_observer_npc(_nearest_npc_id)
				_submit_talk(_nearest_npc_id)
				get_viewport().set_input_as_handled()
				return
	if event is InputEventMouseButton:
		var mouse_event := event as InputEventMouseButton
		if mouse_event.pressed and mouse_event.button_index == MOUSE_BUTTON_LEFT:
			if _select_observer_npc_by_mouse():
				get_viewport().set_input_as_handled()


func _build_stage_visuals() -> void:
	for i in range(STAGE_ORDER.size()):
		var stage_id := str(STAGE_ORDER[i])
		var origin := Vector2(float(i) * STAGE_WIDTH, 0.0)
		_stage_origins[stage_id] = origin
		_build_stage_background(stage_id, origin)
		_build_stage_title(stage_id, origin)


func _build_stage_background(stage_id: String, origin: Vector2) -> void:
	var texture := _asset_registry.get_location_background(stage_id)
	if texture != null:
		var sprite := Sprite2D.new()
		sprite.name = "Stage_%s_Background" % stage_id
		sprite.texture = texture
		sprite.centered = false
		sprite.position = origin
		var texture_size := texture.get_size()
		if texture_size.x > 0.0 and texture_size.y > 0.0:
			sprite.scale = Vector2(STAGE_WIDTH / texture_size.x, STAGE_HEIGHT / texture_size.y)
		stage_layer.add_child(sprite)
	else:
		var tile := ColorRect.new()
		tile.name = "Stage_%s_Fallback" % stage_id
		tile.position = origin
		tile.size = Vector2(STAGE_WIDTH, STAGE_HEIGHT)
		tile.color = _stage_color(stage_id)
		stage_layer.add_child(tile)

	var veil := ColorRect.new()
	veil.name = "Stage_%s_ReadabilityVeil" % stage_id
	veil.position = origin
	veil.size = Vector2(STAGE_WIDTH, STAGE_HEIGHT)
	veil.color = Color(0.0, 0.0, 0.0, 0.10)
	veil.mouse_filter = Control.MOUSE_FILTER_IGNORE
	stage_layer.add_child(veil)


func _build_stage_title(stage_id: String, origin: Vector2) -> void:
	var title := Label.new()
	title.name = "Title_%s" % stage_id
	title.text = "%s / %s" % [str(STAGE_NAMES.get(stage_id, stage_id)), stage_id]
	title.position = origin + Vector2(18.0, 18.0)
	title.add_theme_font_size_override("font_size", 24)
	title.add_theme_color_override("font_color", Color(1.0, 1.0, 1.0, 1.0))
	title.add_theme_color_override("font_shadow_color", Color(0.0, 0.0, 0.0, 0.75))
	title.add_theme_constant_override("shadow_offset_x", 2)
	title.add_theme_constant_override("shadow_offset_y", 2)
	stage_layer.add_child(title)


func _build_anchor_graph() -> void:
	for stage_item in STAGE_ORDER:
		var stage_id := str(stage_item)
		var origin: Vector2 = _stage_origins.get(stage_id, Vector2.ZERO)
		var stage_anchors: Dictionary = STAGE_ANCHORS.get(stage_id, {})
		for anchor_key in stage_anchors.keys():
			var anchor_id := str(anchor_key)
			var ratio := stage_anchors[anchor_id] as Vector2
			var anchor_position := origin + Vector2(ratio.x * STAGE_WIDTH, ratio.y * STAGE_HEIGHT)
			_anchor_positions[anchor_id] = anchor_position
			_build_anchor_marker(anchor_id, anchor_position)

	for stage_item in STAGE_ORDER:
		var stage_id := str(stage_item)
		var stage_anchor_ids: Array = _anchor_ids_for_stage(stage_id)
		for anchor_key in stage_anchor_ids:
			var anchor_id := str(anchor_key)
			var linked_ids: Array = []
			for other_anchor_key in stage_anchor_ids:
				var other_anchor_id := str(other_anchor_key)
				if other_anchor_id != anchor_id:
					linked_ids.append(other_anchor_id)
			_anchor_graph[anchor_id] = linked_ids

	# 阶段 1 先显式连通跨场景 anchor，让 NPC 迁徙路径可读。
	_anchor_graph["farm_house_door"].append("plaza_gate")
	_anchor_graph["plaza_gate"].append("farm_house_door")
	_anchor_graph["market_stall"].append("tavern_door")
	_anchor_graph["tavern_door"].append("market_stall")


func _build_anchor_marker(anchor_id: String, anchor_position: Vector2) -> void:
	var marker := Node2D.new()
	marker.name = "Anchor_%s" % anchor_id
	marker.position = anchor_position

	var dot := ColorRect.new()
	dot.name = "Dot"
	dot.position = Vector2(-5.0, -5.0)
	dot.size = Vector2(10.0, 10.0)
	dot.color = Color(1.0, 0.92, 0.28, 0.92)
	dot.mouse_filter = Control.MOUSE_FILTER_IGNORE
	marker.add_child(dot)

	var label := Label.new()
	label.name = "Label"
	label.text = anchor_id.replace("_", " ")
	label.position = Vector2(10.0, -12.0)
	label.add_theme_font_size_override("font_size", 12)
	label.add_theme_color_override("font_color", Color(1.0, 0.96, 0.65, 0.92))
	label.add_theme_color_override("font_shadow_color", Color(0.0, 0.0, 0.0, 0.85))
	label.add_theme_constant_override("shadow_offset_x", 1)
	label.add_theme_constant_override("shadow_offset_y", 1)
	marker.add_child(label)

	debug_layer.add_child(marker)


func _build_event_label() -> void:
	_event_label = Label.new()
	_event_label.name = "WorldEventLabel"
	_event_label.position = Vector2(18.0, STAGE_HEIGHT - 96.0)
	_event_label.size = Vector2(900.0, 56.0)
	_event_label.text = "Waiting for /api/world/tick ..."
	_event_label.add_theme_font_size_override("font_size", 18)
	_event_label.add_theme_color_override("font_color", Color(1.0, 1.0, 1.0, 0.95))
	_event_label.add_theme_color_override("font_shadow_color", Color(0.0, 0.0, 0.0, 0.85))
	_event_label.add_theme_constant_override("shadow_offset_x", 2)
	_event_label.add_theme_constant_override("shadow_offset_y", 2)
	debug_layer.add_child(_event_label)


func _build_world_pulse_panel() -> void:
	# 世界动态面板把后端日程快照转成玩家可读提示，避免只看调试路径线。
	_pulse_layer = CanvasLayer.new()
	_pulse_layer.name = "WorldPulseLayer"
	_pulse_layer.layer = 12
	add_child(_pulse_layer)

	var panel := PanelContainer.new()
	panel.name = "WorldPulsePanel"
	panel.anchor_left = 1.0
	panel.anchor_top = 0.0
	panel.anchor_right = 1.0
	panel.anchor_bottom = 0.0
	panel.offset_left = -440.0
	panel.offset_top = 72.0
	panel.offset_right = -18.0
	panel.offset_bottom = 322.0
	panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
	panel.add_theme_stylebox_override("panel", _make_pulse_panel_style())
	_pulse_layer.add_child(panel)
	_build_event_compass_label()

	var margin := MarginContainer.new()
	margin.mouse_filter = Control.MOUSE_FILTER_IGNORE
	margin.add_theme_constant_override("margin_left", 16)
	margin.add_theme_constant_override("margin_right", 16)
	margin.add_theme_constant_override("margin_top", 12)
	margin.add_theme_constant_override("margin_bottom", 12)
	panel.add_child(margin)

	var column := VBoxContainer.new()
	column.mouse_filter = Control.MOUSE_FILTER_IGNORE
	column.add_theme_constant_override("separation", 7)
	margin.add_child(column)

	var title := _make_pulse_label("WorldPulseTitle", "World Pulse / 小镇动态", 18, Color(1.0, 0.88, 0.52, 1.0))
	column.add_child(title)

	_pulse_clock_label = _make_pulse_label("WorldPulseClock", "Clock: waiting for tick", 14, Color(0.82, 0.94, 1.0, 0.95))
	column.add_child(_pulse_clock_label)

	_pulse_event_label = _make_pulse_label("WorldPulseEvent", "Event: loading world state ...", 14, Color(1.0, 0.82, 0.68, 0.95))
	_pulse_event_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	column.add_child(_pulse_event_label)

	_pulse_schedule_label = _make_pulse_label("WorldPulseSchedule", "NPC Plans: loading ...", 13, Color(0.93, 1.0, 0.90, 0.95))
	_pulse_schedule_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_pulse_schedule_label.size_flags_vertical = Control.SIZE_EXPAND_FILL
	column.add_child(_pulse_schedule_label)
	_refresh_world_pulse_panel()


func _build_event_compass_label() -> void:
	_event_compass_label = Label.new()
	_event_compass_label.name = "RemoteEventCompass"
	_event_compass_label.position = Vector2(520.0, 64.0)
	_event_compass_label.size = Vector2(760.0, 34.0)
	_event_compass_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_event_compass_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_event_compass_label.visible = false
	_event_compass_label.add_theme_font_size_override("font_size", 18)
	_event_compass_label.add_theme_color_override("font_color", Color(1.0, 0.78, 0.38, 0.96))
	_event_compass_label.add_theme_color_override("font_shadow_color", Color(0.0, 0.0, 0.0, 0.90))
	_event_compass_label.add_theme_constant_override("shadow_offset_x", 2)
	_event_compass_label.add_theme_constant_override("shadow_offset_y", 2)
	_pulse_layer.add_child(_event_compass_label)


func _make_pulse_label(label_name: String, text: String, font_size: int, font_color: Color) -> Label:
	var label := Label.new()
	label.name = label_name
	label.text = text
	label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	label.add_theme_font_size_override("font_size", font_size)
	label.add_theme_color_override("font_color", font_color)
	label.add_theme_color_override("font_shadow_color", Color(0.0, 0.0, 0.0, 0.88))
	label.add_theme_constant_override("shadow_offset_x", 1)
	label.add_theme_constant_override("shadow_offset_y", 1)
	return label


func _make_pulse_panel_style() -> StyleBoxFlat:
	var style := StyleBoxFlat.new()
	style.bg_color = Color(0.04, 0.07, 0.08, 0.72)
	style.border_color = Color(0.78, 0.95, 0.78, 0.70)
	style.set_border_width_all(1)
	style.set_corner_radius_all(14)
	style.shadow_color = Color(0.0, 0.0, 0.0, 0.28)
	style.shadow_size = 5
	return style


func _spawn_demo_npcs() -> void:
	for npc_key in DEMO_SPAWN_ANCHORS.keys():
		var npc_id := str(npc_key)
		var node := _ensure_npc_controller(npc_id)
		node.set_anchor_position(str(DEMO_SPAWN_ANCHORS[npc_id]))


func _spawn_player() -> void:
	_player_controller = PlayerControllerScript.new()
	_player_controller.name = "PlayerController"
	npc_layer.add_child(_player_controller)
	_player_controller.set_world_bounds(_player_world_bounds())
	var spawn_point = _anchor_positions.get("plaza_gate", Vector2(STAGE_WIDTH + STAGE_WIDTH * 0.35, STAGE_HEIGHT * 0.76))
	if spawn_point is Vector2:
		_player_controller.set_spawn_position(spawn_point)
	_player_controller.configure_appearance("Player", _asset_registry.get_map_sprite("player"))


func _build_camera() -> void:
	_camera = Camera2D.new()
	_camera.name = "PlayerCamera"
	_camera.position_smoothing_enabled = true
	_camera.position_smoothing_speed = 8.0
	_camera.limit_left = 0
	_camera.limit_top = 0
	_camera.limit_right = int(STAGE_WIDTH * float(STAGE_ORDER.size()))
	_camera.limit_bottom = int(STAGE_HEIGHT)
	add_child(_camera)
	_update_camera_target()
	_camera.make_current()


func _build_vn_panel() -> void:
	_vn_panel = VnPanelScript.new()
	_vn_panel.name = "WorldVnPanel"
	add_child(_vn_panel)


func _build_observer_panel() -> void:
	_observer_panel = ObserverPanelScript.new()
	_observer_panel.name = "ObserverPanel"
	add_child(_observer_panel)
	# ObserverPanel 只发出 UI 意图，世界节点负责真实 NPC 高亮和重新拉取。
	if not _observer_panel.highlight_npcs_requested.is_connected(_on_observer_panel_highlight_npcs_requested):
		_observer_panel.highlight_npcs_requested.connect(_on_observer_panel_highlight_npcs_requested)
	if not _observer_panel.retry_requested.is_connected(_on_observer_panel_retry_requested):
		_observer_panel.retry_requested.connect(_on_observer_panel_retry_requested)


func _on_observer_panel_highlight_npcs_requested(npc_ids) -> void:
	var highlighted: Array[String] = []
	for id_value in _normalize_observer_npc_ids(npc_ids):
		var npc_id := str(id_value)
		var controller := _npc_nodes.get(npc_id, null) as NpcController
		if controller == null:
			continue
		controller.flash_observer_highlight(OBSERVER_TRACE_HIGHLIGHT_MSEC)
		highlighted.append(npc_id)
	if highlighted.is_empty():
		return
	_event_label.text = "Observer trace highlight: %s" % ", ".join(highlighted)


func _on_observer_panel_retry_requested(npc_id: String) -> void:
	var trimmed_id := npc_id.strip_edges()
	if trimmed_id == "":
		return
	if bool(_observer_phase2_in_flight.get(trimmed_id, false)):
		return
	# 人工点击重试需要绕过短间隔节流和旧缓存，确保错误态能立即恢复。
	_observer_phase2_cache.erase(trimmed_id)
	_observer_phase2_request_msec.erase(trimmed_id)
	_request_phase2_debug_for_observer(trimmed_id)


func _normalize_observer_npc_ids(value) -> Array[String]:
	var ids: Array[String] = []
	if value is Array:
		var values := value as Array
		for item in values:
			var npc_id := str(item).strip_edges()
			if npc_id != "" and not ids.has(npc_id):
				ids.append(npc_id)
		return ids
	var single_id := str(value).strip_edges()
	if single_id != "":
		ids.append(single_id)
	return ids


func _toggle_observer_panel() -> void:
	if _observer_panel == null:
		return
	var visible_now: bool = bool(_observer_panel.toggle_panel_visible())
	if not visible_now:
		return
	if _selected_observer_npc_id == "":
		_observer_panel.show_empty_selection()
		return
	_refresh_observer_panel_for(_selected_observer_npc_id)


func _select_observer_npc_by_mouse() -> bool:
	var clicked_point := get_global_mouse_position()
	var selected_id := ""
	var selected_distance := OBSERVER_NPC_CLICK_RADIUS
	for npc_key in _npc_nodes.keys():
		var npc_id := str(npc_key)
		var controller := _npc_nodes.get(npc_id, null) as NpcController
		if controller == null:
			continue
		var distance := clicked_point.distance_to(controller.global_position)
		if distance > selected_distance:
			continue
		selected_distance = distance
		selected_id = npc_id
	if selected_id == "":
		return false
	_select_observer_npc(selected_id)
	return true


func _select_observer_npc(npc_id: String) -> void:
	_selected_observer_npc_id = npc_id
	if _observer_panel != null:
		_observer_panel.set_panel_visible(true)
	_refresh_observer_panel_for(npc_id)


func _refresh_observer_panel_for(npc_id: String) -> void:
	if _observer_panel == null:
		return
	var controller := _npc_nodes.get(npc_id, null) as NpcController
	var location_id := ""
	if controller != null:
		location_id = _stage_id_for_position(controller.global_position)
	var plan_data = _npc_plans.get(npc_id, {})
	if plan_data is Dictionary:
		var plan_dict := plan_data as Dictionary
		var plan_location := str(plan_dict.get("locationId", ""))
		if plan_location != "":
			location_id = plan_location
	var npc_payload := {
		"npcId": npc_id,
		"name": str(NPC_DISPLAY_NAMES.get(npc_id, npc_id)),
		"location": location_id,
		"anchor": _observer_anchor_for(controller, plan_data),
	}
	_observer_panel.set_selected_npc(npc_payload)
	_apply_cached_phase2_debug(npc_id)
	_request_phase2_debug_for_observer(npc_id)


func _observer_anchor_for(controller: NpcController, plan_data) -> String:
	if controller != null:
		if controller.current_anchor_id != "":
			return controller.current_anchor_id
		if controller.target_anchor_id != "":
			return controller.target_anchor_id
	if plan_data is Dictionary:
		return str((plan_data as Dictionary).get("targetAnchor", ""))
	return ""


func _refresh_selected_observer_npc() -> void:
	if _selected_observer_npc_id == "":
		return
	if _observer_panel == null or not bool(_observer_panel.is_panel_visible()):
		return
	_refresh_observer_panel_for(_selected_observer_npc_id)


func _apply_cached_phase2_debug(npc_id: String) -> void:
	if _observer_panel == null:
		return
	var cached = _observer_phase2_cache.get(npc_id, null)
	if not (cached is Dictionary):
		return
	var cached_dict := cached as Dictionary
	var fetched_at := int(cached_dict.get("fetchedAtMsec", 0))
	if fetched_at <= 0:
		return
	if Time.get_ticks_msec() - fetched_at > OBSERVER_PHASE2_CACHE_MSEC:
		_observer_phase2_cache.erase(npc_id)
		return
	var summary = cached_dict.get("summary", {})
	if summary is Dictionary:
		_observer_panel.set_phase2_debug_summary(summary)


func _request_phase2_debug_for_observer(npc_id: String) -> void:
	if _observer_panel == null or _api_client == null:
		return
	if npc_id == "":
		return
	if bool(_observer_phase2_in_flight.get(npc_id, false)):
		return
	var now_msec := Time.get_ticks_msec()
	var last_request_msec := int(_observer_phase2_request_msec.get(npc_id, 0))
	if now_msec - last_request_msec < OBSERVER_PHASE2_REQUEST_INTERVAL_MSEC:
		return
	var cached = _observer_phase2_cache.get(npc_id, null)
	if cached is Dictionary:
		var cached_dict := cached as Dictionary
		var fetched_at := int(cached_dict.get("fetchedAtMsec", 0))
		if fetched_at > 0 and now_msec - fetched_at <= OBSERVER_PHASE2_CACHE_MSEC:
			return
	_observer_phase2_request_msec[npc_id] = now_msec
	_observer_phase2_in_flight[npc_id] = true
	if _selected_observer_npc_id == npc_id and bool(_observer_panel.is_panel_visible()):
		_observer_panel.show_phase2_loading()
	call_deferred("_fetch_phase2_debug_for_observer", npc_id)


func _fetch_phase2_debug_for_observer(npc_id: String) -> void:
	await _fetch_phase2_debug_for_observer_async(npc_id)


func _fetch_phase2_debug_for_observer_async(npc_id: String) -> void:
	var response := await _api_client.get_phase2_debug(npc_id)
	_observer_phase2_in_flight.erase(npc_id)
	if not bool(response.get("ok", false)):
		if _selected_observer_npc_id == npc_id and _observer_panel != null and bool(_observer_panel.is_panel_visible()):
			_observer_panel.show_phase2_error(str(response.get("error", "unknown error")))
		return
	var payload = response.get("data", {})
	if not (payload is Dictionary):
		if _selected_observer_npc_id == npc_id and _observer_panel != null and bool(_observer_panel.is_panel_visible()):
			_observer_panel.show_phase2_error("phase2 调试响应格式错误")
		return
	var summary := _build_phase2_observer_summary(payload as Dictionary)
	_observer_phase2_cache[npc_id] = {
		"fetchedAtMsec": Time.get_ticks_msec(),
		"summary": summary,
	}
	if _selected_observer_npc_id == npc_id and _observer_panel != null and bool(_observer_panel.is_panel_visible()):
		_observer_panel.set_phase2_debug_summary(summary)


func _build_phase2_observer_summary(payload: Dictionary) -> Dictionary:
	return {
		"motivation": _summarize_phase2_motivation(payload.get("motivation", {})),
		"subjectiveMemory": _summarize_phase2_subjective_memory(payload.get("subjectiveMemory", {})),
		"relationshipEdges": _summarize_phase2_relationship_edges(payload.get("relationshipEdges", {})),
		"heuristics": _summarize_phase2_heuristics(payload.get("heuristics", {})),
		"recentTraceEvents": _summarize_phase2_recent_trace(payload.get("recentTraceEvents", [])),
		"recentTraceEventGroups": _build_phase2_trace_filter_summaries(payload.get("recentTraceEvents", [])),
		"recentTraceEventRows": _build_phase2_trace_event_groups(payload.get("recentTraceEvents", [])),
		"recentTraceDetailGroups": _build_phase2_trace_detail_groups(payload.get("recentTraceEvents", [])),
		"recentTraceCopyDetailGroups": _build_phase2_trace_copy_detail_groups(payload.get("recentTraceEvents", [])),
		"recentTraceDetails": _summarize_phase2_trace_details(payload.get("recentTraceEvents", [])),
	}


func _summarize_phase2_motivation(section) -> String:
	var items := _phase2_items(section)
	if items.is_empty():
		return "暂无 motivation：后端没有返回该 NPC 的决策记录，等待下一次世界 tick。"
	var focus = items[0]
	if not (focus is Dictionary):
		return "motivation 数据不可读"
	var focus_dict := focus as Dictionary
	var primary_need = focus_dict.get("primaryNeed", {})
	var need_id := str(primary_need.get("needId", "unknown")) if primary_need is Dictionary else "unknown"
	var urgency := float(primary_need.get("urgency", 0.0)) if primary_need is Dictionary else 0.0
	var decision = focus_dict.get("decision", {})
	var tool_id := str(decision.get("selectedToolId", decision.get("toolId", ""))) if decision is Dictionary else ""
	if tool_id == "":
		tool_id = str(decision.get("reason", "pending")) if decision is Dictionary else "pending"
	return "need=%s(%.2f) / decision=%s" % [need_id, urgency, tool_id]


func _summarize_phase2_subjective_memory(section) -> String:
	var items := _phase2_items(section)
	if items.is_empty():
		return "暂无 subjectiveMemory：该 NPC 尚未写入主观记忆。"
	var latest = items[items.size() - 1]
	if not (latest is Dictionary):
		return "subjective memory 数据不可读"
	var latest_dict := latest as Dictionary
	var text := str(latest_dict.get("text", ""))
	var valence := float(latest_dict.get("emotionalValence", 0.0))
	return "%d 条，最新 valence=%.2f：%s" % [items.size(), valence, _truncate_text(text, 44)]


func _summarize_phase2_relationship_edges(section) -> String:
	var items := _phase2_items(section)
	if items.is_empty():
		return "暂无 relationshipEdges：该 NPC 暂无可解释关系边。"
	var strongest: Dictionary = {}
	var strongest_strength := -1.0
	for item in items:
		if not (item is Dictionary):
			continue
		var entry := item as Dictionary
		var strength: float = absf(float(entry.get("strength", 0.0)))
		if strength > strongest_strength:
			strongest_strength = strength
			strongest = entry
	if strongest.is_empty():
		return "%d 条，暂无可读 edge" % items.size()
	return "%d 条，最强 %s %.2f (%s→%s)" % [
		items.size(),
		str(strongest.get("edgeType", "edge")),
		float(strongest.get("strength", 0.0)),
		str(strongest.get("sourceAgentId", "?")),
		str(strongest.get("targetAgentId", "?")),
	]


func _summarize_phase2_heuristics(section) -> String:
	var items := _phase2_items(section)
	if items.is_empty():
		return "暂无 heuristics：该 NPC 暂无启发式学习记录。"
	var top = items[0]
	if not (top is Dictionary):
		return "heuristic 数据不可读"
	var top_dict := top as Dictionary
	return "%d 条，top=%s (%.2f)" % [
		items.size(),
		str(top_dict.get("triggerPattern", top_dict.get("heuristicId", "unknown"))),
		float(top_dict.get("effectiveConfidence", top_dict.get("confidence", 0.0))),
	]


func _summarize_phase2_recent_trace(section) -> String:
	return _summarize_phase2_recent_trace_for_filter(section, "all")


func _build_phase2_trace_filter_summaries(section) -> Dictionary:
	return {
		"all": _summarize_phase2_recent_trace_for_filter(section, "all"),
		"decision": _summarize_phase2_recent_trace_for_filter(section, "decision"),
		"tool": _summarize_phase2_recent_trace_for_filter(section, "tool"),
		"interrupt": _summarize_phase2_recent_trace_for_filter(section, "interrupt"),
		"memory": _summarize_phase2_recent_trace_for_filter(section, "memory"),
	}


func _build_phase2_trace_event_groups(section) -> Dictionary:
	# 面板点击需要原始 trace envelope；这里只裁剪到可见的最近 4 条。
	return {
		"all": _phase2_trace_events_for_filter(section, "all"),
		"decision": _phase2_trace_events_for_filter(section, "decision"),
		"tool": _phase2_trace_events_for_filter(section, "tool"),
		"interrupt": _phase2_trace_events_for_filter(section, "interrupt"),
		"memory": _phase2_trace_events_for_filter(section, "memory"),
	}


func _build_phase2_trace_detail_groups(section) -> Dictionary:
	return {
		"all": _phase2_trace_details_for_filter(section, "all"),
		"decision": _phase2_trace_details_for_filter(section, "decision"),
		"tool": _phase2_trace_details_for_filter(section, "tool"),
		"interrupt": _phase2_trace_details_for_filter(section, "interrupt"),
		"memory": _phase2_trace_details_for_filter(section, "memory"),
	}


func _build_phase2_trace_copy_detail_groups(section) -> Dictionary:
	return {
		"all": _phase2_trace_details_for_filter(section, "all", true),
		"decision": _phase2_trace_details_for_filter(section, "decision", true),
		"tool": _phase2_trace_details_for_filter(section, "tool", true),
		"interrupt": _phase2_trace_details_for_filter(section, "interrupt", true),
		"memory": _phase2_trace_details_for_filter(section, "memory", true),
	}


func _phase2_trace_events_for_filter(section, filter_id: String) -> Array:
	var items := _phase2_items(section)
	var rows: Array = []
	if items.is_empty():
		return rows
	var filtered_items: Array = []
	for item in items:
		if not (item is Dictionary):
			continue
		var entry := item as Dictionary
		var event_type := str(entry.get("eventType", entry.get("type", "trace")))
		if _phase2_trace_filter_matches(event_type, filter_id):
			filtered_items.append(entry)
	var start_index = max(0, filtered_items.size() - 4)
	for index in range(start_index, filtered_items.size()):
		var entry := filtered_items[index] as Dictionary
		rows.append(entry.duplicate(true))
	return rows


func _summarize_phase2_recent_trace_for_filter(section, filter_id: String) -> String:
	var items := _phase2_items(section)
	if items.is_empty():
		return "暂无 recentTraceEvents：该 NPC 尚未产生可解释 trace。"
	var filtered_items: Array = []
	for item in items:
		if not (item is Dictionary):
			continue
		var entry := item as Dictionary
		var event_type := str(entry.get("eventType", entry.get("type", "trace")))
		if _phase2_trace_filter_matches(event_type, filter_id):
			filtered_items.append(entry)
	if filtered_items.is_empty():
		return "暂无 %s trace：当前筛选器没有匹配记录。" % filter_id
	var lines: Array[String] = []
	var start_index = max(0, filtered_items.size() - 4)
	for index in range(start_index, filtered_items.size()):
		var entry := filtered_items[index] as Dictionary
		var event_type := str(entry.get("eventType", entry.get("type", "trace")))
		var summary := str(entry.get("summary", ""))
		var world_time = entry.get("worldTime", {})
		var tick_text := "t?"
		if world_time is Dictionary:
			tick_text = "t%d" % int((world_time as Dictionary).get("tick", -1))
		var detail_hint := _phase2_trace_detail_hint(entry.get("details", {}))
		lines.append("%s %s%s · %s" % [
			tick_text,
			_pretty_trace_type(event_type),
			detail_hint,
			_truncate_text(summary, 58),
		])
	if lines.is_empty():
		return "recent trace 数据不可读"
	return "\n".join(lines)


func _phase2_trace_details_for_filter(section, filter_id: String, full_detail: bool = false) -> Array[String]:
	var items := _phase2_items(section)
	var details: Array[String] = []
	if items.is_empty():
		return details
	var filtered_items: Array = []
	for item in items:
		if not (item is Dictionary):
			continue
		var entry := item as Dictionary
		var event_type := str(entry.get("eventType", entry.get("type", "trace")))
		if _phase2_trace_filter_matches(event_type, filter_id):
			filtered_items.append(entry)
	var start_index = max(0, filtered_items.size() - 4)
	for index in range(start_index, filtered_items.size()):
		var entry := filtered_items[index] as Dictionary
		details.append(_phase2_trace_detail_text(entry, full_detail))
	return details


func _summarize_phase2_trace_details(section) -> String:
	var items := _phase2_items(section)
	if items.is_empty():
		return "暂无 traceDetails：先等待 trace 产生，再查看明细。"
	var latest = items[items.size() - 1]
	if not (latest is Dictionary):
		return "trace detail 数据不可读"
	var entry := latest as Dictionary
	return _phase2_trace_detail_text(entry)


func _phase2_trace_detail_text(entry: Dictionary, full_detail: bool = false) -> String:
	# 面板展示保留摘要；Copy trace 使用完整 details，避免人工验收时拿到省略文本。
	var event_type := str(entry.get("eventType", entry.get("type", "trace")))
	var trace_id := str(entry.get("traceId", entry.get("id", "")))
	var span_id := str(entry.get("spanId", ""))
	var summary := str(entry.get("summary", ""))
	var world_time = entry.get("worldTime", {})
	var tick_text := "?"
	if world_time is Dictionary:
		tick_text = str((world_time as Dictionary).get("tick", "?"))
	var details = entry.get("details", {})
	var detail_text := "{}"
	if details is Dictionary:
		detail_text = JSON.stringify(details)
	if not full_detail:
		summary = _truncate_text(summary, 64)
		detail_text = _truncate_text(detail_text, 144)
	return "tick=%s type=%s trace=%s span=%s summary=%s details=%s" % [
		tick_text,
		_pretty_trace_type(event_type),
		trace_id if trace_id != "" else "-",
		span_id if span_id != "" else "-",
		summary,
		detail_text,
	]


func _phase2_trace_filter_matches(event_type: String, filter_id: String) -> bool:
	match filter_id:
		"all":
			return true
		"decision":
			return event_type == "motivation.decision_made"
		"tool":
			return event_type == "tool.execution_completed" or event_type == "tool.execution_failed"
		"interrupt":
			return event_type == "tool.execution_interrupted"
		"memory":
			return event_type == "memory.result_observed"
		_:
			return true


func _phase2_trace_detail_hint(details) -> String:
	if not (details is Dictionary):
		return ""
	var detail_dict := details as Dictionary
	var tool_id := str(detail_dict.get("selectedToolId", detail_dict.get("toolId", "")))
	if tool_id != "":
		return " [%s]" % _short_action_label(tool_id)
	var reason := str(detail_dict.get("reason", detail_dict.get("decisionReason", "")))
	if reason != "":
		return " [%s]" % _truncate_text(reason, 22)
	return ""


func _pretty_trace_type(event_type: String) -> String:
	match event_type:
		"motivation.decision_made":
			return "decision"
		"tool.execution_completed":
			return "tool done"
		"tool.execution_failed":
			return "tool fail"
		"tool.execution_interrupted":
			return "interrupt"
		"memory.result_observed":
			return "observed"
		_:
			return event_type


func _phase2_items(section) -> Array:
	if section is Array:
		return section
	if section is Dictionary:
		var items = (section as Dictionary).get("items", [])
		if items is Array:
			return items
	return []


func _connect_event_bus() -> void:
	var event_bus := _get_event_bus()
	if event_bus == null:
		return
	if not event_bus.tick_clock_updated.is_connected(_on_tick_clock_updated):
		event_bus.tick_clock_updated.connect(_on_tick_clock_updated)
	if not event_bus.tick_agents_updated.is_connected(_on_tick_agents_updated):
		event_bus.tick_agents_updated.connect(_on_tick_agents_updated)
	if not event_bus.npc_motion_event.is_connected(_on_npc_motion_event):
		event_bus.npc_motion_event.connect(_on_npc_motion_event)
	if not event_bus.npc_action_event.is_connected(_on_npc_action_event):
		event_bus.npc_action_event.connect(_on_npc_action_event)


func _connect_world_clock() -> void:
	var world_clock := _get_world_clock()
	if world_clock == null:
		return
	if not world_clock.tick_received.is_connected(_on_tick_received):
		world_clock.tick_received.connect(_on_tick_received)
	if not world_clock.tick_failed.is_connected(_on_tick_failed):
		world_clock.tick_failed.connect(_on_tick_failed)


func _request_initial_world_snapshot() -> void:
	if _snapshot_in_flight:
		return
	_snapshot_in_flight = true
	var response := await _api_client.get_world_state()
	_snapshot_in_flight = false
	if not bool(response.get("ok", false)):
		if _pulse_event_label != null:
			_pulse_event_label.text = "Event: state load failed - %s" % str(response.get("error", "unknown"))
		return
	var data = response.get("data", {})
	if data is Dictionary:
		_apply_world_state_snapshot(data)


func _apply_world_state_snapshot(snapshot: Dictionary) -> void:
	var clock = snapshot.get("clock", {})
	if clock is Dictionary:
		_latest_clock = clock.duplicate(true)

	_active_event_summaries.clear()
	_active_event_records.clear()
	var active_events = snapshot.get("activeEvents", [])
	if active_events is Array:
		for event in active_events:
			if not (event is Dictionary):
				continue
			var title := str(event.get("title", event.get("id", "event")))
			var phase := str(event.get("phase", ""))
			var location_id := str(event.get("locationId", ""))
			_active_event_summaries.append("%s @ %s %s" % [title, _pretty_location(location_id), phase])
			var event_id := str(event.get("id", ""))
			if event_id != "":
				_active_event_records[event_id] = {
					"id": event_id,
					"title": title,
					"locationId": location_id,
					"phase": phase,
					"anchorId": _event_anchor_for(event),
				}
	_sync_event_beacons()

	_update_npc_plans(snapshot.get("npcSchedules", []))
	_refresh_world_pulse_panel()
	_refresh_event_compass()


func _update_npc_plans(raw_schedules) -> void:
	_npc_plans.clear()
	if not (raw_schedules is Array):
		return
	for item in raw_schedules:
		if not (item is Dictionary):
			continue
		var npc_id := str(item.get("npcId", ""))
		if npc_id == "":
			continue
		var active = item.get("activeLifeAction", {})
		if not (active is Dictionary):
			continue
		var target_anchor := _target_anchor_from_schedule(item, active)
		_npc_plans[npc_id] = {
			"actionId": str(active.get("id", "")),
			"summary": str(active.get("summary", "")),
			"timeWindow": str(active.get("timeWindow", "")),
			"targetAnchor": target_anchor,
			"locationId": str(item.get("locationId", "")),
			"presenceSource": str(item.get("presenceSource", "")),
			"intentLabel": _format_npc_intent_label(active, target_anchor),
		}
		_apply_npc_intent_status(npc_id)
	for npc_key in _npc_nodes.keys():
		_apply_npc_intent_status(str(npc_key))


func _target_anchor_from_schedule(schedule: Dictionary, active_action: Dictionary) -> String:
	var current_anchor := str(schedule.get("anchorId", ""))
	var candidates = active_action.get("spaceActionCandidates", [])
	if not (candidates is Array):
		return current_anchor
	for candidate in candidates:
		if not (candidate is Dictionary):
			continue
		var anchor_id := str(candidate.get("anchorId", ""))
		if anchor_id != "" and anchor_id != current_anchor:
			return anchor_id
	for candidate in candidates:
		if candidate is Dictionary and str(candidate.get("anchorId", "")) != "":
			return str(candidate.get("anchorId", ""))
	return current_anchor


func _format_npc_intent_label(active_action: Dictionary, target_anchor: String) -> String:
	var primary_need = active_action.get("primaryNeed", {})
	var need_id := ""
	var urgency := 0.0
	if primary_need is Dictionary:
		need_id = str((primary_need as Dictionary).get("needId", ""))
		urgency = float((primary_need as Dictionary).get("urgency", 0.0))
	var decision = active_action.get("decision", {})
	var action_id := str(active_action.get("toolId", active_action.get("id", "")))
	if decision is Dictionary:
		var selected_tool := str((decision as Dictionary).get("selectedToolId", ""))
		if selected_tool != "":
			action_id = selected_tool
	var need_text := _need_label(need_id)
	var action_text := _short_action_label(action_id)
	var target_text := _pretty_anchor(target_anchor)
	if urgency > 0.0:
		return "意图：%s %.2f · %s → %s" % [need_text, urgency, action_text, target_text]
	return "意图：%s · %s → %s" % [need_text, action_text, target_text]


func _apply_npc_intent_status(npc_id: String) -> void:
	var controller := _npc_nodes.get(npc_id, null) as NpcController
	if controller == null:
		return
	var plan = _npc_plans.get(npc_id, {})
	if plan is Dictionary:
		controller.set_intent_status(str((plan as Dictionary).get("intentLabel", "")))
		return
	controller.set_intent_status("")


func _apply_npc_action_status(npc_id: String, status: String) -> void:
	var controller := _npc_nodes.get(npc_id, null) as NpcController
	if controller == null:
		return
	controller.set_action_status(status)


func _on_tick_clock_updated(clock: Dictionary) -> void:
	var old_phase := str(_latest_clock.get("phase", ""))
	_latest_clock = clock.duplicate(true)
	var next_phase := str(_latest_clock.get("phase", ""))
	if old_phase != "" and next_phase != "" and old_phase != next_phase:
		call_deferred("_request_initial_world_snapshot")
	_refresh_world_pulse_panel()


func _on_tick_agents_updated(agents: Array) -> void:
	_update_npc_statuses_from_agents(agents)
	_refresh_world_pulse_panel()


func _on_npc_motion_event(npc_id: String, event_type: String, event_payload: Dictionary) -> void:
	var node := _ensure_npc_controller(npc_id)
	node.apply_tick_event(event_payload)
	_update_npc_status_from_event(npc_id, event_type, event_payload)
	_update_route_line(npc_id, event_type, event_payload)
	_update_event_label(npc_id, event_type, event_payload)
	_refresh_world_pulse_panel()


func _on_npc_action_event(npc_id: String, event_type: String, event_payload: Dictionary) -> void:
	var node := _ensure_npc_controller(npc_id)
	node.apply_tick_event(event_payload)
	_update_npc_status_from_event(npc_id, event_type, event_payload)
	_update_event_label(npc_id, event_type, event_payload)
	_refresh_world_pulse_panel()


func _on_tick_received(payload: Dictionary) -> void:
	var clock = payload.get("clock", {})
	if clock is Dictionary:
		_on_tick_clock_updated(clock)

	var agents = payload.get("agents", [])
	if agents is Array:
		_update_npc_statuses_from_agents(agents)

	var events = payload.get("events", [])
	if _event_label != null and events is Array and events.is_empty():
		_event_label.text = "Tick received: no NPC motion event yet."
	_refresh_world_pulse_panel()


func _on_tick_failed(error_message: String) -> void:
	if _event_label == null:
		return
	_event_label.text = "Tick failed: %s" % error_message
	if _pulse_event_label != null:
		_pulse_event_label.text = "Event: tick failed - %s" % error_message


func _ensure_npc_controller(npc_id: String) -> NpcController:
	if _npc_nodes.has(npc_id):
		return _npc_nodes[npc_id] as NpcController

	var controller := NpcController.new()
	controller.name = "Npc_%s" % npc_id
	controller.npc_id = npc_id
	controller.configure_anchor_graph(_anchor_graph, _anchor_positions)
	controller.configure_appearance(
		str(NPC_DISPLAY_NAMES.get(npc_id, npc_id)),
		_asset_registry.get_map_sprite(npc_id),
		NPC_COLORS.get(npc_id, Color(1.0, 1.0, 1.0, 1.0))
	)
	var crowd_offset: Vector2 = NPC_CROWD_OFFSETS.get(npc_id, Vector2.ZERO)
	controller.set_crowd_offset(crowd_offset)
	npc_layer.add_child(controller)
	_npc_nodes[npc_id] = controller
	_apply_npc_intent_status(npc_id)
	return controller


func _update_route_line(npc_id: String, event_type: String, event_payload: Dictionary) -> void:
	var line := _ensure_route_line(npc_id)
	if event_type == "npc.arrived":
		line.visible = false
		_route_line_expire_msec.erase(npc_id)
		return

	var from_anchor := str(event_payload.get("fromAnchorId", ""))
	var to_anchor := str(event_payload.get("toAnchorId", ""))
	var from_point = _anchor_positions.get(from_anchor, null)
	var to_point = _anchor_positions.get(to_anchor, null)
	if from_point is Vector2 and to_point is Vector2:
		line.visible = true
		line.default_color = _route_debug_color(npc_id)
		line.points = PackedVector2Array([from_point, to_point])
		_route_line_expire_msec[npc_id] = Time.get_ticks_msec() + ROUTE_LINE_VISIBLE_MSEC


func _ensure_route_line(npc_id: String) -> Line2D:
	if _route_lines.has(npc_id):
		return _route_lines[npc_id] as Line2D

	var line := Line2D.new()
	line.name = "Route_%s" % npc_id
	line.width = 2.0
	line.default_color = _route_debug_color(npc_id)
	line.joint_mode = Line2D.LINE_JOINT_ROUND
	line.begin_cap_mode = Line2D.LINE_CAP_ROUND
	line.end_cap_mode = Line2D.LINE_CAP_ROUND
	line.z_index = 1
	line.visible = false
	debug_layer.add_child(line)
	_route_lines[npc_id] = line
	return line


func _route_debug_color(npc_id: String) -> Color:
	# 路线只做开发期运动说明，降低透明度，避免压过角色和背景。
	var route_color: Color = NPC_COLORS.get(npc_id, Color(0.8, 0.9, 1.0, 1.0))
	route_color.a = 0.42
	return route_color


func _expire_route_lines() -> void:
	var now := Time.get_ticks_msec()
	for npc_key in _route_line_expire_msec.keys():
		var npc_id := str(npc_key)
		var expires_at := int(_route_line_expire_msec[npc_id])
		if now < expires_at:
			continue
		var line = _route_lines.get(npc_id, null)
		if line is Line2D:
			line.visible = false
		_route_line_expire_msec.erase(npc_id)


func _update_npc_statuses_from_agents(agents: Array) -> void:
	for item in agents:
		if not (item is Dictionary):
			continue
		var npc_id := str(item.get("npcId", ""))
		if npc_id == "":
			continue
		var life_action = item.get("lifeAction", {})
		if not (life_action is Dictionary):
			continue
		var phase := str(life_action.get("phase", ""))
		var action_id := str(life_action.get("actionId", ""))
		var status := ""
		if phase == "moving":
			var progress := float(life_action.get("moveProgress", 0.0))
			status = "移动中 %.0f%% · %s" % [progress * 100.0, _short_action_label(action_id)]
		elif phase == "performing":
			var elapsed := float(life_action.get("elapsedSeconds", 0.0))
			var duration := maxf(1.0, float(life_action.get("durationSeconds", 1.0)))
			status = "行动中 %.0f%% · %s" % [elapsed / duration * 100.0, _short_action_label(action_id)]
		if status != "":
			_npc_statuses[npc_id] = status
			_apply_npc_action_status(npc_id, status)


func _update_npc_status_from_event(npc_id: String, event_type: String, event_payload: Dictionary) -> void:
	if event_type == "npc.move_started":
		_npc_statuses[npc_id] = "出发 → %s" % _pretty_anchor(str(event_payload.get("toAnchorId", "")))
		return
	if event_type == "npc.move_progress":
		var progress := float(event_payload.get("progress", 0.0))
		_npc_statuses[npc_id] = "移动 %.0f%% → %s" % [
			progress * 100.0,
			_pretty_anchor(str(event_payload.get("toAnchorId", ""))),
		]
		return
	if event_type == "npc.arrived":
		_npc_statuses[npc_id] = "到达 %s" % _pretty_anchor(str(event_payload.get("anchorId", "")))
		return
	if event_type == "npc.action_started":
		_npc_statuses[npc_id] = "开始行动 · %s" % _short_action_label(str(event_payload.get("actionId", "")))
		return
	if event_type == "npc.action_tick":
		var action_progress := float(event_payload.get("progress", 0.0))
		_npc_statuses[npc_id] = "行动 %.0f%% · %s" % [
			action_progress * 100.0,
			_short_action_label(str(event_payload.get("actionId", ""))),
		]
		return
	if event_type == "npc.action_completed":
		_npc_statuses[npc_id] = "完成行动 · %s" % _short_action_label(str(event_payload.get("actionId", "")))


func _sync_event_beacons() -> void:
	var stale_event_ids: Array[String] = []
	for event_key in _event_beacons.keys():
		var event_id := str(event_key)
		if _active_event_records.has(event_id):
			continue
		stale_event_ids.append(event_id)

	for event_id in stale_event_ids:
		var stale_node = _event_beacons.get(event_id, null)
		if stale_node is Node:
			(stale_node as Node).queue_free()
		_event_beacons.erase(event_id)

	for event_key in _active_event_records.keys():
		var event_id := str(event_key)
		var record = _active_event_records.get(event_id, {})
		if not (record is Dictionary):
			continue
		var anchor_id := str(record.get("anchorId", ""))
		var anchor_point = _anchor_positions.get(anchor_id, null)
		if not (anchor_point is Vector2):
			continue
		var beacon := _ensure_event_beacon(event_id)
		beacon.global_position = (anchor_point as Vector2) + Vector2(0.0, -84.0)
		var label = beacon.get_node_or_null("Label")
		if label is Label:
			(label as Label).text = _truncate_text(str(record.get("title", event_id)), 26)


func _ensure_event_beacon(event_id: String) -> Node2D:
	if _event_beacons.has(event_id):
		return _event_beacons[event_id] as Node2D

	var beacon := Node2D.new()
	beacon.name = "EventBeacon_%s" % event_id
	beacon.z_index = 9
	debug_layer.add_child(beacon)

	var ring := ColorRect.new()
	ring.name = "PulseRing"
	ring.position = Vector2(-30.0, -30.0)
	ring.size = Vector2(60.0, 60.0)
	ring.color = Color(1.0, 0.62, 0.20, 0.22)
	ring.mouse_filter = Control.MOUSE_FILTER_IGNORE
	beacon.add_child(ring)

	var sprite := Sprite2D.new()
	sprite.name = "Icon"
	sprite.texture = _asset_registry.get_interaction_marker("event")
	sprite.scale = Vector2(0.65, 0.65)
	beacon.add_child(sprite)

	var label := Label.new()
	label.name = "Label"
	label.position = Vector2(-92.0, 30.0)
	label.size = Vector2(184.0, 26.0)
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label.add_theme_font_size_override("font_size", 14)
	label.add_theme_color_override("font_color", Color(1.0, 0.78, 0.40, 0.98))
	label.add_theme_color_override("font_shadow_color", Color(0.0, 0.0, 0.0, 0.92))
	label.add_theme_constant_override("shadow_offset_x", 2)
	label.add_theme_constant_override("shadow_offset_y", 2)
	beacon.add_child(label)

	_event_beacons[event_id] = beacon
	return beacon


func _update_event_beacons() -> void:
	if _event_beacons.is_empty():
		return
	var seconds := float(Time.get_ticks_msec()) / 1000.0
	var pulse := 1.0 + sin(seconds * 4.0) * 0.08
	var alpha := 0.70 + sin(seconds * 4.0) * 0.20
	for beacon_key in _event_beacons.keys():
		var beacon = _event_beacons.get(str(beacon_key), null)
		if not (beacon is Node2D):
			continue
		var node := beacon as Node2D
		node.scale = Vector2(pulse, pulse)
		var ring = node.get_node_or_null("PulseRing")
		if ring is ColorRect:
			var ring_color := Color(1.0, 0.62, 0.20, clampf(alpha * 0.34, 0.12, 0.42))
			(ring as ColorRect).color = ring_color


func _refresh_event_compass() -> void:
	if _event_compass_label == null:
		return
	if _active_event_records.is_empty() or _player_controller == null:
		_event_compass_label.visible = false
		return
	var event_id := str(_active_event_records.keys()[0])
	var record = _active_event_records.get(event_id, {})
	if not (record is Dictionary):
		_event_compass_label.visible = false
		return
	var event_location := str(record.get("locationId", ""))
	var player_location := _stage_id_for_position(_player_controller.global_position)
	if event_location == "" or event_location == player_location:
		_event_compass_label.visible = false
		return
	var anchor_id := str(record.get("anchorId", ""))
	var anchor_point = _anchor_positions.get(anchor_id, _player_controller.global_position)
	var direction := "→" if (anchor_point is Vector2 and (anchor_point as Vector2).x > _player_controller.global_position.x) else "←"
	_event_compass_label.text = "远处事件 %s %s：%s" % [
		direction,
		_pretty_location(event_location),
		_truncate_text(str(record.get("title", event_id)), 34),
	]
	_event_compass_label.visible = true


func _refresh_world_pulse_panel() -> void:
	if _pulse_clock_label == null or _pulse_event_label == null or _pulse_schedule_label == null:
		return
	_pulse_clock_label.text = _format_pulse_clock()
	_pulse_event_label.text = _format_pulse_event_line()

	var lines: Array[String] = []
	for npc_key in NPC_DISPLAY_NAMES.keys():
		var npc_id := str(npc_key)
		var npc_name := str(NPC_DISPLAY_NAMES.get(npc_id, npc_id))
		var status := str(_npc_statuses.get(npc_id, ""))
		if status == "":
			status = _format_npc_plan(npc_id)
		if status == "":
			continue
		lines.append("· %s：%s" % [npc_name, _truncate_text(status, 54)])
		if lines.size() >= PULSE_PANEL_MAX_LINES:
			break
	if lines.is_empty():
		_pulse_schedule_label.text = "NPC Plans: waiting for /api/world/state"
	else:
		_pulse_schedule_label.text = "NPC Plans:\n%s" % "\n".join(lines)


func _format_pulse_clock() -> String:
	if _latest_clock.is_empty():
		return "Clock: waiting for tick"
	var day := int(_latest_clock.get("day", 1))
	var hour := int(_latest_clock.get("hour", 0))
	var minute := int(_latest_clock.get("minute", 0))
	var phase := str(_latest_clock.get("phase", "unknown"))
	var tick := int(_latest_clock.get("tick", 0))
	return "Clock: Day %d %02d:%02d %s · tick %d" % [day, hour, minute, phase, tick]


func _format_pulse_event_line() -> String:
	if _active_event_summaries.is_empty():
		return "Event: no active event loaded"
	return "Event: %s" % _truncate_text(str(_active_event_summaries[0]), 82)


func _format_npc_plan(npc_id: String) -> String:
	var plan = _npc_plans.get(npc_id, {})
	if not (plan is Dictionary) or plan.is_empty():
		return ""
	var action_id := str(plan.get("actionId", ""))
	var target_anchor := str(plan.get("targetAnchor", ""))
	var source := str(plan.get("presenceSource", ""))
	var label := _short_action_label(action_id)
	var target := _pretty_anchor(target_anchor)
	if source != "":
		return "%s → %s · %s" % [label, target, source]
	return "%s → %s" % [label, target]


func _event_anchor_for(event: Dictionary) -> String:
	var event_id := str(event.get("id", ""))
	if EVENT_ANCHORS.has(event_id):
		return str(EVENT_ANCHORS[event_id])
	var location_id := str(event.get("locationId", ""))
	return str(DEFAULT_EVENT_ANCHORS.get(location_id, "plaza_fountain"))


func _short_action_label(action_id: String) -> String:
	var lowered := action_id.to_lower()
	if lowered == "social.chat_with":
		return "找人聊天"
	if lowered == "social.give_gift":
		return "送礼"
	if lowered == "farm.water_crop":
		return "浇水"
	if lowered == "shop.open_shop":
		return "开店"
	if lowered == "cook.prepare_meal":
		return "做饭"
	if lowered == "craft.repair_stall":
		return "修摊位"
	if lowered == "strategic.spread_rumor":
		return "传播传闻"
	if lowered.contains("morning"):
		return "晨间例行"
	if lowered.contains("afternoon"):
		return "白天协作"
	if lowered.contains("evening"):
		return "夜间收束"
	if lowered.contains("routine"):
		return "日常安排"
	if action_id == "":
		return "生活行动"
	return action_id.replace("life_", "").replace("_", " ")


func _need_label(need_id: String) -> String:
	match need_id:
		"energy":
			return "恢复体力"
		"money_anxiety":
			return "稳定收入"
		"affiliation":
			return "建立联结"
		"recognition":
			return "获得认可"
		"":
			return "等待动机"
		_:
			return need_id.replace("_", " ")


func _pretty_anchor(anchor_id: String) -> String:
	if anchor_id == "":
		return "未知地点"
	return anchor_id.replace("_", " ")


func _pretty_location(location_id: String) -> String:
	return str(STAGE_NAMES.get(location_id, location_id)).replace(" / %s" % location_id, "")


func _truncate_text(value: String, max_chars: int) -> String:
	if value.length() <= max_chars:
		return value
	return "%s…" % value.substr(0, max(0, max_chars - 1))


func _update_event_label(npc_id: String, event_type: String, event_payload: Dictionary) -> void:
	if _event_label == null:
		return
	var npc_name := str(NPC_DISPLAY_NAMES.get(npc_id, npc_id))
	if event_type == "npc.move_progress":
		_event_label.text = "%s moving: %s -> %s  %.0f%%" % [
			npc_name,
			str(event_payload.get("fromAnchorId", "?")),
			str(event_payload.get("toAnchorId", "?")),
			float(event_payload.get("progress", 0.0)) * 100.0,
		]
		return
	if event_type == "npc.action_started":
		_event_label.text = "%s action: %s" % [npc_name, str(event_payload.get("actionId", "action"))]
		return
	if event_type == "player.talked":
		var receipt := _talk_status_text(event_payload).replace("\n", " · ")
		_event_label.text = "Player talked with %s · %s" % [npc_name, _truncate_text(receipt, 96)]
		return
	_event_label.text = "%s / %s" % [npc_name, event_type]


func _update_camera_target() -> void:
	if _camera == null or _player_controller == null:
		return
	_camera.global_position = _player_controller.global_position


func _update_nearest_npc_hint() -> void:
	if _player_controller == null or _vn_panel == null:
		return
	var nearest_id := ""
	var nearest_distance := INF
	var player_point: Vector2 = _player_controller.interaction_origin()
	for npc_key in _npc_nodes.keys():
		var npc_id := str(npc_key)
		var controller := _npc_nodes[npc_id] as NpcController
		if controller == null:
			continue
		var distance: float = player_point.distance_to(controller.global_position)
		if distance < nearest_distance:
			nearest_distance = distance
			nearest_id = npc_id
	if nearest_id != "" and nearest_distance <= PLAYER_INTERACT_RADIUS:
		_nearest_npc_id = nearest_id
		_vn_panel.show_hint("E: talk to %s  (%.0f px)" % [str(NPC_DISPLAY_NAMES.get(nearest_id, nearest_id)), nearest_distance], true)
		return
	_nearest_npc_id = ""
	_vn_panel.show_hint("WASD / Arrow move - get close to an NPC and press E to talk", false)


func _submit_talk(npc_id: String) -> void:
	if _talk_in_flight:
		return
	_talk_in_flight = true
	var npc_name := str(NPC_DISPLAY_NAMES.get(npc_id, npc_id))
	if _vn_panel != null:
		_vn_panel.show_busy(npc_name)
	var response := await _api_client.post_player_action({
		"type": "talk",
		"targetId": npc_id,
		"locationId": _stage_id_for_position(_player_controller.global_position),
		"topic": "world_map_greeting",
		"message": "我在小镇里靠近你，想听听你现在正在忙什么。",
	})
	_talk_in_flight = false
	if not bool(response.get("ok", false)):
		if _vn_panel != null:
			_vn_panel.show_error(str(response.get("error", "talk failed")))
		return
	var result = response.get("data", {})
	if not (result is Dictionary):
		if _vn_panel != null:
			_vn_panel.show_error("Talk response is not a dictionary.")
		return
	var action_result := _action_result_payload(result as Dictionary)
	var state_payload = (result as Dictionary).get("state", {})
	if state_payload is Dictionary:
		_apply_world_state_snapshot(state_payload as Dictionary)
	var dialogue_text := _dialogue_text(action_result)
	var status_text := _talk_status_text(action_result)
	if _vn_panel != null:
		_vn_panel.show_dialogue(npc_name, dialogue_text, status_text)
	_update_event_label(npc_id, "player.talked", action_result)
	_observer_phase2_cache.erase(npc_id)
	_observer_phase2_request_msec.erase(npc_id)
	if _selected_observer_npc_id == npc_id:
		_request_phase2_debug_for_observer(npc_id)


func _dialogue_text(result: Dictionary) -> String:
	var dialogue = result.get("dialogue", [])
	if dialogue is Array and not dialogue.is_empty():
		var lines: Array[String] = []
		for item in dialogue:
			if item is Dictionary:
				var speaker := str(item.get("speakerName", item.get("speakerId", "NPC")))
				var text := str(item.get("text", ""))
				if text != "":
					lines.append("%s: %s" % [speaker, text])
		if not lines.is_empty():
			return "\n".join(lines)
	var feedback = result.get("actionFeedback", {})
	if feedback is Dictionary and str(feedback.get("summary", "")) != "":
		return str(feedback.get("summary", ""))
	return "The NPC nods to you."


func _action_result_payload(response_payload: Dictionary) -> Dictionary:
	var nested = response_payload.get("result", {})
	if nested is Dictionary:
		return nested as Dictionary
	return response_payload


func _talk_status_text(result: Dictionary) -> String:
	var relation_count := _array_size(result.get("relationshipDeltas", []))
	var memory_count := _array_size(result.get("memoryWrites", []))
	var event_count := _array_size(result.get("eventIds", []))
	var lines: Array[String] = ["因果链：关系%d / 记忆%d / 事件%d" % [relation_count, memory_count, event_count]]
	var deltas = result.get("relationshipDeltas", [])
	if deltas is Array:
		var delta_items := deltas as Array
		if not delta_items.is_empty() and delta_items[0] is Dictionary:
			var delta = (delta_items[0] as Dictionary).get("delta", {})
			if delta is Dictionary:
				lines.append("关系变化：%s" % _relation_delta_text(delta as Dictionary))
	var memory_text := _latest_memory_write_text(result.get("memoryWrites", []))
	if memory_text != "":
		lines.append("写入记忆：%s" % _truncate_text(memory_text, 54))
	var profile = result.get("playerProfile", {})
	if profile is Dictionary:
		var style_summary := str((profile as Dictionary).get("styleSummary", ""))
		if style_summary != "":
			lines.append("玩家风格：%s" % _truncate_text(style_summary, 42))
	return "\n".join(lines)


func _relation_delta_text(delta: Dictionary) -> String:
	var parts: Array[String] = []
	for key in ["affection", "trust", "conflict"]:
		var value := int(delta.get(key, 0))
		if value == 0:
			continue
		var sign := "+" if value > 0 else ""
		parts.append("%s%s%d" % [_relation_label(str(key)), sign, value])
	if parts.is_empty():
		return "无数值变化"
	return " / ".join(parts)


func _relation_label(key: String) -> String:
	match key:
		"affection":
			return "亲密"
		"trust":
			return "信任"
		"conflict":
			return "冲突"
		_:
			return key


func _latest_memory_write_text(value) -> String:
	if not (value is Array):
		return ""
	var fallback := ""
	var write_items := value as Array
	for item in write_items:
		if not (item is Dictionary):
			continue
		var text := str((item as Dictionary).get("text", ""))
		if text == "":
			continue
		fallback = text
		if str((item as Dictionary).get("agentId", "")) != "player":
			return text
	return fallback


func _array_size(value) -> int:
	if value is Array:
		return value.size()
	return 0


func _stage_id_for_position(point: Vector2) -> String:
	var index := int(clamp(floor(point.x / STAGE_WIDTH), 0.0, float(STAGE_ORDER.size() - 1)))
	return str(STAGE_ORDER[index])


func _player_world_bounds() -> Rect2:
	return Rect2(Vector2(48.0, 132.0), Vector2(STAGE_WIDTH * float(STAGE_ORDER.size()) - 96.0, STAGE_HEIGHT - 252.0))


func _get_event_bus() -> EventBus:
	if has_node("/root/EventBusService"):
		return get_node("/root/EventBusService") as EventBus
	return null


func _get_world_clock() -> WorldClock:
	if has_node("/root/WorldClockService"):
		return get_node("/root/WorldClockService") as WorldClock
	return null


func _anchor_ids_for_stage(stage_id: String) -> Array:
	var stage_anchors: Dictionary = STAGE_ANCHORS.get(stage_id, {})
	var ids: Array = []
	for anchor_key in stage_anchors.keys():
		ids.append(str(anchor_key))
	return ids


func _stage_color(stage_id: String) -> Color:
	match stage_id:
		"farm":
			return Color(0.63, 0.82, 0.56, 1.0)
		"plaza":
			return Color(0.72, 0.73, 0.78, 1.0)
		"tavern":
			return Color(0.64, 0.56, 0.52, 1.0)
		_:
			return Color(0.25, 0.25, 0.25, 1.0)
