extends Control

const ApiClientScript := preload("res://scripts/api_client.gd")
const AssetRegistryScript := preload("res://scripts/asset_registry.gd")
const WorldSyncScript := preload("res://scripts/world_sync.gd")

const DESIGN_VIEWPORT_HEIGHT := 1080.0
const UI_SCALE_MIN := 0.85
const UI_SCALE_MAX := 2.1
const UI_CREAM := Color(0.98, 0.94, 0.84, 0.96)
const UI_CREAM_SOFT := Color(1.0, 0.97, 0.89, 0.94)
const UI_GREEN := Color(0.22, 0.32, 0.19, 0.98)
const UI_GREEN_SOFT := Color(0.45, 0.55, 0.30, 1.0)
const UI_GOLD := Color(0.92, 0.60, 0.20, 1.0)
const UI_GOLD_LIGHT := Color(1.0, 0.83, 0.36, 1.0)
const UI_BROWN := Color(0.34, 0.22, 0.12, 1.0)
const UI_TEXT := Color(0.24, 0.19, 0.12, 1.0)
const UI_TEXT_MUTED := Color(0.42, 0.33, 0.22, 1.0)

const MAP_NODE_SIZE := Vector2(112, 138)
const MAP_SPRITE_SIZE := 64.0
const MAP_SPRITE_SCALE := 1.35
const MAP_MARKER_SCALE := 0.43
const MAP_EVENT_MARKER_SCALE := 0.68
const PLAYER_LOCAL_MOVE_SPEED := 520.0
const PLAYER_LOCAL_STOP_DISTANCE := 3.0
const PLAYER_LOCAL_INTERACT_RADIUS := 86.0
const PLAYER_LOCAL_INTERACT_EXIT_MARGIN := 28.0
const MAP_CONTEXT_PANEL_WIDTH := 520.0
const MAP_CONTEXT_PANEL_HEIGHT := 108.0
# 地图移动 Debug 面板默认关闭；需要现场排查时临时改为 true。
const MAP_MOVEMENT_DEBUG_ENABLED := false
const MAP_DEBUG_NOTE_LIMIT := 5
const MAP_PLAYER_SPAWN_RATIO := Vector2(0.50, 0.66)
const MAP_NPC_SLOT_RATIOS := [
	Vector2(0.24, 0.30),
	Vector2(0.76, 0.30),
	Vector2(0.24, 0.56),
	Vector2(0.76, 0.56),
	Vector2(0.50, 0.18),
	Vector2(0.13, 0.43),
	Vector2(0.87, 0.43),
	Vector2(0.50, 0.58),
]

var api_client: Node
var asset_registry
var world_sync: Node
var background_rect: TextureRect
var map_character_layer: Control
var status_label: Label
var player_label: Label
var location_list: VBoxContainer
var scene_action_list: VBoxContainer
var npc_list: VBoxContainer
var event_list: VBoxContainer
var event_choice_list: VBoxContainer
var dialogue_scroll: ScrollContainer
var portrait_rect: TextureRect
var speaker_label: Label
var dialogue_label: Label
var selected_location_id := "farm"
var selected_npc_id := "orren"
var selected_expression := "neutral"
var selected_event_id := ""
var selected_event_location_id := ""
var ui_scale := 1.0
var layout_viewport_size := Vector2.ZERO
var player_local_position := Vector2.ZERO
var player_local_target := Vector2.ZERO
var player_local_has_click_target := false
var player_local_initialized := false
var player_local_location_id := ""
var player_local_anchor_id := ""
var current_near_npc_id := ""
var current_near_event_id := ""
var current_near_anchor_id := ""
var current_near_interactable_id := ""
var map_hint_label: Label
var map_context_panel: PanelContainer
var map_context_title_label: Label
var map_context_body_label: Label
var map_context_candidates: Array[Dictionary] = []
var map_context_selected_index := 0
var map_context_sidebar_signature := ""
var map_context_action_pending := false
var map_debug_panel: PanelContainer
var map_debug_label: Label
var player_actor_node: Control
var player_target_marker: Label
var last_move_axis := Vector2.ZERO
var last_click_debug := "未点击"
var last_motion_debug := "未移动"
var last_location_debug := "等待同步"
var last_proximity_debug := "未计算"
var map_debug_notes: Array[String] = []


func _ready() -> void:
	_ensure_local_input_actions()
	ui_scale = _compute_ui_scale()
	layout_viewport_size = get_viewport_rect().size
	theme = _make_scaled_theme()
	print("[AgentValleyClient] VN visual refresh active · project=", ProjectSettings.globalize_path("res://"), " · ui_scale=", ui_scale, " · viewport=", get_viewport_rect().size)
	api_client = ApiClientScript.new()
	asset_registry = AssetRegistryScript.new()
	world_sync = WorldSyncScript.new()
	add_child(api_client)
	add_child(asset_registry)
	add_child(world_sync)
	_build_layout()
	await _refresh_world()
	_show_selected_npc_hint()


func _ensure_local_input_actions() -> void:
	# 使用独立 WASD 动作，避免方向键焦点被按钮或列表控件抢走。
	var bindings := {
		"move_left": KEY_A,
		"move_right": KEY_D,
		"move_up": KEY_W,
		"move_down": KEY_S,
	}
	for action_name in bindings:
		if not InputMap.has_action(action_name):
			InputMap.add_action(action_name)
		var keycode: int = int(bindings[action_name])
		var has_binding := false
		for event in InputMap.action_get_events(action_name):
			if event is InputEventKey and ((event as InputEventKey).physical_keycode == keycode or (event as InputEventKey).keycode == keycode):
				has_binding = true
				break
		if not has_binding:
			var key_event := InputEventKey.new()
			key_event.physical_keycode = keycode
			key_event.keycode = keycode
			InputMap.action_add_event(action_name, key_event)


func _notification(what: int) -> void:
	if what == NOTIFICATION_RESIZED:
		_refresh_scale_for_viewport()


func _process(delta: float) -> void:
	_tick_local_player_motion(delta)


func _unhandled_input(event: InputEvent) -> void:
	# 鼠标落点由地图角色层直接处理，避免被全屏背景或 UI 焦点链路吞掉。
	# 键盘 E / Space 触发当前上下文动作，Tab / Q 切换候选动作。
	if not (event is InputEventKey):
		return
	var key_event := event as InputEventKey
	if not key_event.pressed or key_event.echo:
		return
	if key_event.keycode == KEY_E or key_event.keycode == KEY_SPACE:
		if _trigger_current_map_context_action():
			get_viewport().set_input_as_handled()
		return
	if key_event.keycode == KEY_TAB:
		if _cycle_map_context_candidate(1):
			get_viewport().set_input_as_handled()
		return
	if key_event.keycode == KEY_Q:
		if _cycle_map_context_candidate(-1):
			get_viewport().set_input_as_handled()


func _refresh_scale_for_viewport() -> void:
	if not is_inside_tree() or background_rect == null:
		return
	var viewport_size: Vector2 = get_viewport_rect().size
	var next_scale: float = _compute_ui_scale()
	var scale_changed: bool = abs(next_scale - ui_scale) >= 0.04
	var size_changed: bool = viewport_size.distance_to(layout_viewport_size) >= 12.0
	if not scale_changed and not size_changed:
		return
	ui_scale = next_scale
	layout_viewport_size = viewport_size
	theme = _make_scaled_theme()
	_rebuild_visual_layers()


func _rebuild_visual_layers() -> void:
	# 视口变化时只重建展示节点；后端状态、选中项和 API 连接保持原样。
	var previous_status := status_label.text if status_label != null else "等待同步..."
	var previous_speaker := speaker_label.text if speaker_label != null else ""
	var previous_dialogue := dialogue_label.text if dialogue_label != null else ""
	for child in get_children():
		if child == api_client or child == asset_registry or child == world_sync:
			continue
		remove_child(child)
		child.queue_free()
	_build_layout()
	if world_sync != null and not world_sync.get_player().is_empty():
		_render_world()
	if status_label != null:
		status_label.text = previous_status
	if speaker_label != null and not previous_speaker.is_empty():
		speaker_label.text = previous_speaker
	if dialogue_label != null and not previous_dialogue.is_empty():
		dialogue_label.text = previous_dialogue


func _build_layout() -> void:
	_build_background()
	_build_map_character_layer()
	_build_top_layer()
	_build_dialogue_layer()


func _build_background() -> void:
	background_rect = TextureRect.new()
	background_rect.set_anchors_preset(Control.PRESET_FULL_RECT)
	background_rect.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	background_rect.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	background_rect.mouse_filter = Control.MOUSE_FILTER_IGNORE
	background_rect.texture = asset_registry.get_location_background(selected_location_id)
	add_child(background_rect)


func _build_map_character_layer() -> void:
	# 地图角色层只负责展示与提交动作，坐标和可交互状态都从后端状态派生。
	map_character_layer = Control.new()
	map_character_layer.name = "MapCharacterLayer"
	map_character_layer.set_anchors_preset(Control.PRESET_FULL_RECT)
	map_character_layer.mouse_filter = Control.MOUSE_FILTER_STOP
	map_character_layer.gui_input.connect(_on_map_character_layer_gui_input)
	add_child(map_character_layer)


func _on_map_character_layer_gui_input(event: InputEvent) -> void:
	# 当前还没有正式 tile 地图，空白舞台点击先作为本地落点表现处理。
	if event is InputEventMouseButton:
		var mouse_event := event as InputEventMouseButton
		if mouse_event.pressed and mouse_event.button_index == MOUSE_BUTTON_LEFT:
			if _set_local_player_target(mouse_event.position, true):
				get_viewport().set_input_as_handled()


func _build_top_layer() -> void:
	var margin := MarginContainer.new()
	margin.set_anchors_preset(Control.PRESET_FULL_RECT)
	margin.mouse_filter = Control.MOUSE_FILTER_IGNORE
	margin.add_theme_constant_override("margin_left", _scaled_int(28))
	margin.add_theme_constant_override("margin_right", _scaled_int(28))
	margin.add_theme_constant_override("margin_top", _scaled_int(22))
	margin.add_theme_constant_override("margin_bottom", _top_layer_reserved_bottom())
	add_child(margin)

	var columns := HBoxContainer.new()
	columns.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	columns.size_flags_vertical = Control.SIZE_EXPAND_FILL
	columns.mouse_filter = Control.MOUSE_FILTER_IGNORE
	columns.add_theme_constant_override("separation", _scaled_int(22))
	margin.add_child(columns)

	var left_panel_frame := _create_panel(columns, Vector2(330, 0), "✦ Loomstead · VN UI")
	var left_panel := _create_scroll_body(left_panel_frame)

	status_label = Label.new()
	status_label.text = "等待同步..."
	status_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_style_body_label(status_label)
	left_panel.add_child(status_label)

	player_label = Label.new()
	player_label.text = "玩家状态等待同步..."
	player_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_style_body_label(player_label)
	left_panel.add_child(player_label)

	var refresh_button := Button.new()
	refresh_button.text = "刷新世界状态"
	_style_button(refresh_button)
	refresh_button.pressed.connect(_on_refresh_pressed)
	left_panel.add_child(refresh_button)

	var location_title := Label.new()
	location_title.text = "地点"
	_style_section_label(location_title)
	left_panel.add_child(location_title)

	location_list = VBoxContainer.new()
	location_list.size_flags_vertical = Control.SIZE_EXPAND_FILL
	location_list.add_theme_constant_override("separation", _scaled_int(7))
	left_panel.add_child(location_list)

	var scene_action_title := Label.new()
	scene_action_title.text = "场景行动"
	_style_section_label(scene_action_title)
	left_panel.add_child(scene_action_title)

	scene_action_list = VBoxContainer.new()
	scene_action_list.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scene_action_list.add_theme_constant_override("separation", _scaled_int(7))
	left_panel.add_child(scene_action_list)

	var spacer := Control.new()
	spacer.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	spacer.mouse_filter = Control.MOUSE_FILTER_IGNORE
	columns.add_child(spacer)

	var right_panel_frame := _create_panel(columns, Vector2(360, 0), "✦ 小镇观察")
	var right_panel := _create_scroll_body(right_panel_frame)
	var npc_title := Label.new()
	npc_title.text = "首发居民"
	_style_section_label(npc_title)
	right_panel.add_child(npc_title)

	npc_list = VBoxContainer.new()
	npc_list.size_flags_vertical = Control.SIZE_EXPAND_FILL
	npc_list.add_theme_constant_override("separation", _scaled_int(7))
	right_panel.add_child(npc_list)

	var event_title := Label.new()
	event_title.text = "进行中事件"
	_style_section_label(event_title)
	right_panel.add_child(event_title)

	event_list = VBoxContainer.new()
	event_list.size_flags_vertical = Control.SIZE_EXPAND_FILL
	event_list.add_theme_constant_override("separation", _scaled_int(8))
	right_panel.add_child(event_list)


func _build_dialogue_layer() -> void:
	var dialogue_panel := PanelContainer.new()
	var bottom_margin := _dialogue_panel_bottom_margin()
	var panel_height := _dialogue_panel_height()
	dialogue_panel.anchor_left = 0.0
	dialogue_panel.anchor_top = 1.0
	dialogue_panel.anchor_right = 1.0
	dialogue_panel.anchor_bottom = 1.0
	dialogue_panel.offset_left = _scaled_int(30)
	dialogue_panel.offset_top = -int(panel_height + bottom_margin)
	dialogue_panel.offset_right = -_scaled_int(30)
	dialogue_panel.offset_bottom = -bottom_margin
	dialogue_panel.add_theme_stylebox_override("panel", _make_panel_style(UI_CREAM, UI_GOLD, _scaled_int(20), _scaled_int(3), _scaled_int(20)))
	add_child(dialogue_panel)

	var outer := VBoxContainer.new()
	outer.add_theme_constant_override("separation", _scaled_int(12))
	dialogue_panel.add_child(outer)

	var title_bar := _create_title_bar("✦ 星灯通讯 · 后端回执 ✦")
	outer.add_child(title_bar)

	var content := HBoxContainer.new()
	content.add_theme_constant_override("separation", _scaled_int(24))
	outer.add_child(content)

	portrait_rect = TextureRect.new()
	portrait_rect.custom_minimum_size = _portrait_box_size()
	portrait_rect.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	portrait_rect.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	content.add_child(portrait_rect)

	var text_box := VBoxContainer.new()
	text_box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	text_box.add_theme_constant_override("separation", _scaled_int(8))
	content.add_child(text_box)

	speaker_label = Label.new()
	speaker_label.text = "等待选择居民"
	_style_section_label(speaker_label, 24)
	text_box.add_child(speaker_label)

	dialogue_scroll = ScrollContainer.new()
	dialogue_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	text_box.add_child(dialogue_scroll)

	dialogue_label = Label.new()
	dialogue_label.text = "选择一个居民后，这里会显示对应立绘和后端返回的对话。"
	dialogue_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	dialogue_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_style_body_label(dialogue_label, 17)
	dialogue_scroll.add_child(dialogue_label)

	var actions := HBoxContainer.new()
	actions.add_theme_constant_override("separation", _scaled_int(12))
	text_box.add_child(actions)

	var talk_button := Button.new()
	talk_button.text = "聊天"
	_style_button(talk_button, 86)
	talk_button.pressed.connect(_on_talk_pressed)
	actions.add_child(talk_button)

	var gift_button := Button.new()
	gift_button.text = "送礼"
	_style_button(gift_button, 86)
	gift_button.pressed.connect(_on_gift_pressed)
	actions.add_child(gift_button)

	var farm_button := Button.new()
	farm_button.text = "回农场"
	_style_button(farm_button, 96)
	farm_button.pressed.connect(_on_location_pressed.bind("farm"))
	actions.add_child(farm_button)

	var plaza_button := Button.new()
	plaza_button.text = "去广场"
	_style_button(plaza_button, 96)
	plaza_button.pressed.connect(_on_location_pressed.bind("plaza"))
	actions.add_child(plaza_button)

	var tavern_button := Button.new()
	tavern_button.text = "去酒馆"
	_style_button(tavern_button, 96)
	tavern_button.pressed.connect(_on_location_pressed.bind("tavern"))
	actions.add_child(tavern_button)

	var choice_title := Label.new()
	choice_title.text = "事件选项"
	_style_section_label(choice_title)
	text_box.add_child(choice_title)

	event_choice_list = VBoxContainer.new()
	event_choice_list.add_theme_constant_override("separation", _scaled_int(7))
	text_box.add_child(event_choice_list)
	_render_event_choice_buttons([])


func _create_panel(parent: Control, minimum_size: Vector2, title_text: String = "") -> VBoxContainer:
	var panel := PanelContainer.new()
	panel.custom_minimum_size = _scaled_vector(minimum_size)
	panel.size_flags_vertical = Control.SIZE_EXPAND_FILL
	panel.clip_contents = true
	panel.add_theme_stylebox_override("panel", _make_panel_style(UI_CREAM, UI_GOLD, _scaled_int(18), _scaled_int(2), _scaled_int(14)))
	parent.add_child(panel)

	var box := VBoxContainer.new()
	box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	box.size_flags_vertical = Control.SIZE_EXPAND_FILL
	box.add_theme_constant_override("separation", _scaled_int(9))
	panel.add_child(box)
	if not title_text.is_empty():
		box.add_child(_create_title_bar(title_text))
	return box


func _create_scroll_body(parent: VBoxContainer) -> VBoxContainer:
	var scroll := ScrollContainer.new()
	scroll.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.clip_contents = true
	parent.add_child(scroll)

	var body := VBoxContainer.new()
	body.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	body.add_theme_constant_override("separation", _scaled_int(9))
	scroll.add_child(body)
	return body


func _create_title_bar(text: String) -> PanelContainer:
	var bar := PanelContainer.new()
	bar.custom_minimum_size = Vector2(0, _scaled(42))
	bar.add_theme_stylebox_override("panel", _make_panel_style(UI_GREEN, UI_GOLD_LIGHT, _scaled_int(15), _scaled_int(2), _scaled_int(10)))

	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", _scaled_int(7))
	bar.add_child(row)

	var left_star := _create_decor_label("✦", 22, UI_GOLD_LIGHT)
	row.add_child(left_star)

	var title := Label.new()
	title.text = text
	title.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	title.add_theme_font_size_override("font_size", _font_size(18))
	title.add_theme_color_override("font_color", Color(1.0, 0.95, 0.75, 1.0))
	title.add_theme_color_override("font_shadow_color", Color(0.07, 0.11, 0.06, 0.85))
	title.add_theme_constant_override("shadow_offset_x", _scaled_int(1))
	title.add_theme_constant_override("shadow_offset_y", _scaled_int(1))
	row.add_child(title)

	# 叶片与星灯用轻量符号实现，避免引入客户端运行时切图依赖。
	row.add_child(_create_decor_label("❧", 18, UI_GREEN_SOFT))
	row.add_child(_create_decor_label("✧", 20, UI_GOLD_LIGHT))
	return bar


func _create_decor_label(text: String, font_size: int, color: Color) -> Label:
	var label := Label.new()
	label.text = text
	label.add_theme_font_size_override("font_size", _font_size(font_size))
	label.add_theme_color_override("font_color", color)
	label.add_theme_color_override("font_shadow_color", Color(0.31, 0.18, 0.08, 0.42))
	label.add_theme_constant_override("shadow_offset_x", _scaled_int(1))
	label.add_theme_constant_override("shadow_offset_y", _scaled_int(1))
	return label


func _make_panel_style(color: Color, border_color: Color = UI_GOLD, radius: int = 10, border_width: int = 1, margin_size: int = 12) -> StyleBoxFlat:
	var style := StyleBoxFlat.new()
	style.bg_color = color
	style.border_color = border_color
	style.border_width_left = border_width
	style.border_width_top = border_width
	style.border_width_right = border_width
	style.border_width_bottom = border_width
	style.corner_radius_top_left = radius
	style.corner_radius_top_right = radius
	style.corner_radius_bottom_left = radius
	style.corner_radius_bottom_right = radius
	style.content_margin_left = margin_size
	style.content_margin_top = margin_size
	style.content_margin_right = margin_size
	style.content_margin_bottom = margin_size
	return style


func _make_button_style(color: Color, border_color: Color) -> StyleBoxFlat:
	var style := _make_panel_style(color, border_color, _scaled_int(15), _scaled_int(2), _scaled_int(10))
	style.shadow_color = Color(0.36, 0.21, 0.08, 0.20)
	style.shadow_size = _scaled_int(2)
	return style


func _make_scaled_theme() -> Theme:
	var scaled_theme := Theme.new()
	scaled_theme.set_color("font_color", "Label", UI_TEXT)
	scaled_theme.set_color("font_shadow_color", "Label", Color(1.0, 0.98, 0.90, 0.35))
	scaled_theme.set_constant("shadow_offset_x", "Label", _scaled_int(1))
	scaled_theme.set_constant("shadow_offset_y", "Label", _scaled_int(1))
	scaled_theme.set_font_size("font_size", "Label", _font_size(16))
	scaled_theme.set_font_size("font_size", "Button", _font_size(16))
	scaled_theme.set_color("font_color", "Button", UI_BROWN)
	scaled_theme.set_color("font_hover_color", "Button", UI_BROWN)
	scaled_theme.set_color("font_pressed_color", "Button", UI_BROWN)
	scaled_theme.set_color("font_disabled_color", "Button", Color(UI_TEXT_MUTED.r, UI_TEXT_MUTED.g, UI_TEXT_MUTED.b, 0.55))
	scaled_theme.set_stylebox("normal", "Button", _make_button_style(UI_CREAM_SOFT, UI_GOLD))
	scaled_theme.set_stylebox("hover", "Button", _make_button_style(Color(1.0, 0.91, 0.57, 0.98), UI_GOLD_LIGHT))
	scaled_theme.set_stylebox("pressed", "Button", _make_button_style(Color(0.93, 0.72, 0.32, 0.98), UI_GOLD))
	scaled_theme.set_stylebox("disabled", "Button", _make_button_style(Color(0.75, 0.72, 0.62, 0.55), Color(0.55, 0.49, 0.36, 0.50)))
	scaled_theme.set_stylebox("focus", "Button", StyleBoxEmpty.new())
	return scaled_theme


func _style_body_label(label: Label, base_font_size: int = 16) -> void:
	label.add_theme_font_size_override("font_size", _font_size(base_font_size))
	label.add_theme_color_override("font_color", UI_TEXT)
	label.add_theme_color_override("font_shadow_color", Color(1.0, 0.98, 0.90, 0.35))
	label.add_theme_constant_override("shadow_offset_x", _scaled_int(1))
	label.add_theme_constant_override("shadow_offset_y", _scaled_int(1))


func _style_section_label(label: Label, base_font_size: int = 18) -> void:
	label.add_theme_font_size_override("font_size", _font_size(base_font_size))
	label.add_theme_color_override("font_color", UI_GREEN)
	label.add_theme_color_override("font_shadow_color", Color(1.0, 0.89, 0.45, 0.38))
	label.add_theme_constant_override("shadow_offset_x", _scaled_int(1))
	label.add_theme_constant_override("shadow_offset_y", _scaled_int(1))


func _style_button(button: Button, min_width: float = 0.0) -> void:
	button.custom_minimum_size = Vector2(_scaled(min_width), _scaled(42))
	button.focus_mode = Control.FOCUS_NONE
	button.add_theme_font_size_override("font_size", _font_size(16))


func _top_layer_reserved_bottom() -> int:
	# 顶部侧栏明确避让底部 VN 框，侧栏内容过长时由内部滚动容器承接。
	return int(_dialogue_panel_height() + _dialogue_panel_bottom_margin() + _scaled(16))


func _dialogue_panel_bottom_margin() -> int:
	return _scaled_int(22)


func _dialogue_panel_height() -> float:
	var viewport_height := get_viewport_rect().size.y
	if viewport_height <= 0:
		viewport_height = DESIGN_VIEWPORT_HEIGHT
	return clamp(viewport_height * 0.30, _scaled(300), _scaled(420))


func _dialogue_content_height() -> float:
	return max(_scaled(180), _dialogue_panel_height() - _scaled(20 * 2 + 42 + 12))


func _portrait_box_size() -> Vector2:
	var content_height := _dialogue_content_height()
	return Vector2(min(_scaled(280), content_height * 0.86), content_height)


func _compute_ui_scale() -> float:
	var viewport_height := get_viewport_rect().size.y
	if viewport_height <= 0:
		viewport_height = DESIGN_VIEWPORT_HEIGHT
	return clamp(viewport_height / DESIGN_VIEWPORT_HEIGHT, UI_SCALE_MIN, UI_SCALE_MAX)


func _scaled(value: float) -> float:
	return round(value * ui_scale)


func _scaled_int(value: float) -> int:
	return int(_scaled(value))


func _scaled_vector(value: Vector2) -> Vector2:
	return Vector2(_scaled(value.x), _scaled(value.y))


func _font_size(base_size: int) -> int:
	return max(1, int(round(float(base_size) * ui_scale)))


func _map_node_size() -> Vector2:
	return MAP_NODE_SIZE * ui_scale


func _set_local_player_target(world_point: Vector2, from_click: bool) -> bool:
	if not player_local_initialized:
		last_click_debug = "拒绝：玩家本地坐标未初始化 point=%s" % _debug_vector(world_point)
		_push_map_debug_note(last_click_debug)
		return false
	var bounds := _map_bounds()
	if not get_viewport_rect().has_point(world_point):
		last_click_debug = "拒绝：点击点不在视口 point=%s viewport=%s" % [_debug_vector(world_point), _debug_rect(get_viewport_rect())]
		_push_map_debug_note(last_click_debug)
		return false
	var clamped_target := _clamp_point_to_walk_area(world_point, bounds)
	var target_was_clamped := clamped_target.distance_to(world_point) > _scaled(2)
	player_local_target = clamped_target
	player_local_has_click_target = true
	last_click_debug = "接受：raw=%s target=%s clamped=%s" % [_debug_vector(world_point), _debug_vector(clamped_target), str(target_was_clamped)]
	_push_map_debug_note(last_click_debug)
	_update_player_target_marker()
	if from_click:
		if target_was_clamped:
			_update_map_hint("已把落点修正到可行走边界，可继续 WASD 移动或靠近交互")
		else:
			_update_map_hint("已设置当前场景落点，可继续 WASD 移动或靠近交互")
	_update_map_proximity_feedback()
	return true


func _tick_local_player_motion(delta: float) -> void:
	# 按住 WASD 时每帧读取输入，保证移动手感连续；点击落点仍保留自动走向目标点。
	if not player_local_initialized or map_character_layer == null:
		return
	var bounds := _map_bounds()
	var previous_position := player_local_position
	var input_axis := _read_local_move_axis()
	last_move_axis = input_axis
	var moved := false
	if input_axis.length() > 0.0:
		player_local_position = _clamp_point_to_walk_area(
			player_local_position + input_axis * _scaled(PLAYER_LOCAL_MOVE_SPEED) * delta,
			bounds
		)
		player_local_target = player_local_position
		player_local_has_click_target = false
		_update_player_target_marker()
		moved = true
	var stop_distance := _scaled(PLAYER_LOCAL_STOP_DISTANCE)
	if not moved and player_local_has_click_target and player_local_position.distance_to(player_local_target) > stop_distance:
		var move_step := _scaled(PLAYER_LOCAL_MOVE_SPEED) * delta
		player_local_position = player_local_position.move_toward(player_local_target, move_step)
		moved = true
	elif player_local_has_click_target:
		player_local_has_click_target = false
		_update_player_target_marker()
	if moved:
		_apply_local_player_visual()
		_update_player_target_marker()
		last_motion_debug = "axis=%s pos=%s delta=%.2f clickTarget=%s" % [
			_debug_vector(input_axis),
			_debug_vector(player_local_position),
			previous_position.distance_to(player_local_position),
			str(player_local_has_click_target),
		]
	_update_map_proximity_feedback()
	_update_map_debug_label(bounds)


func _read_local_move_axis() -> Vector2:
	# 直接读取物理键作为兜底，避免输入动作被某些 UI 焦点状态吞掉。
	var input_axis := Input.get_vector("move_left", "move_right", "move_up", "move_down")
	var direct_axis := Vector2.ZERO
	if Input.is_physical_key_pressed(KEY_A):
		direct_axis.x -= 1.0
	if Input.is_physical_key_pressed(KEY_D):
		direct_axis.x += 1.0
	if Input.is_physical_key_pressed(KEY_W):
		direct_axis.y -= 1.0
	if Input.is_physical_key_pressed(KEY_S):
		direct_axis.y += 1.0
	if direct_axis.length() > 0.0:
		input_axis = direct_axis
	return input_axis.normalized() if input_axis.length() > 1.0 else input_axis


func _apply_local_player_visual() -> void:
	if map_character_layer == null:
		return
	var player_actor := _get_player_actor_node()
	if player_actor == null:
		last_motion_debug = "视觉节点缺失：pos=%s" % _debug_vector(player_local_position)
		_push_map_debug_note(last_motion_debug)
		return
	var node_size := _map_node_size()
	player_actor.position = player_local_position - Vector2(node_size.x * 0.5, node_size.y)
	player_actor.set_meta("anchor", player_local_position)


func _get_player_actor_node() -> Control:
	# 地图层同帧重绘时旧节点会先退出树，保留稳定引用并用 meta 兜底查找玩家小人。
	if player_actor_node != null and is_instance_valid(player_actor_node) and player_actor_node.get_parent() == map_character_layer:
		return player_actor_node
	if map_character_layer == null:
		return null
	for child in map_character_layer.get_children():
		if child is Control and str(child.get_meta("agentId", "")) == "player":
			player_actor_node = child as Control
			return player_actor_node
	return null


func _resolve_player_anchor(player_location: String, bounds: Rect2) -> Vector2:
	var player: Dictionary = world_sync.get_player()
	var state_anchor_id := str(player.get("anchorId", ""))
	var location_anchor := _position_for_anchor_id(state_anchor_id, bounds, _player_spawn_for_location(player_location, bounds))
	if not player_local_initialized or player_local_location_id != player_location or player_local_anchor_id != state_anchor_id:
		player_local_initialized = true
		player_local_location_id = player_location
		player_local_anchor_id = state_anchor_id
		player_local_position = location_anchor
		player_local_target = location_anchor
		player_local_has_click_target = false
		last_location_debug = "权威锚点：%s anchor=%s pos=%s" % [player_location, state_anchor_id, _debug_vector(location_anchor)]
		_push_map_debug_note(last_location_debug)
	else:
		player_local_position = _clamp_point_to_walk_area(player_local_position, bounds)
		player_local_target = _clamp_point_to_walk_area(player_local_target, bounds)
	return player_local_position


func _player_spawn_for_location(_location_id: String, bounds: Rect2) -> Vector2:
	# 玩家固定出生在舞台下缘偏中位置，和 NPC 站位槽错开，避免切场景后直接压在居民头上。
	return _scene_anchor_from_ratio(bounds, MAP_PLAYER_SPAWN_RATIO)


func _clamp_point_to_walk_area(point: Vector2, bounds: Rect2) -> Vector2:
	# 当前没有正式 tile 地图，先把可移动区域定义为场景舞台主体，避开 UI 面板。
	var clamped := point
	var bounds_margin := _scaled(18)
	clamped.x = clamp(clamped.x, bounds.position.x + bounds_margin, bounds.end.x - bounds_margin)
	clamped.y = clamp(clamped.y, bounds.position.y + bounds_margin, bounds.end.y - bounds_margin)
	return clamped


func _on_refresh_pressed() -> void:
	await _refresh_world()


func _on_location_pressed(location_id: String) -> void:
	_clear_event_focus()
	_push_map_debug_note("请求切场景：selected=%s -> %s" % [selected_location_id, location_id])
	_set_status("正在移动到 %s ..." % location_id)
	var response = await api_client.post_player_action({"type": "move", "locationId": location_id})
	if not _is_action_response_ok(response):
		_push_map_debug_note("切场景失败：%s" % _response_error(response))
		_render_world()
		_set_status("移动失败：%s" % _response_error(response))
		return
	var response_player: Dictionary = response["data"]["state"].get("player", {})
	var anchor_key := "anchor" + "Id"
	_push_map_debug_note("切场景回执：player=%s anchor=%s" % [response_player.get("locationId", "?"), response_player.get(anchor_key, "?")])
	_apply_authoritative_state(response["data"]["state"])
	_render_world()
	_set_status("已到达：%s" % _get_location_name(selected_location_id))


func _on_move_to_anchor_pressed(anchor_id: String, location_id: String) -> void:
	var interaction: Dictionary = world_sync.find_interaction("move_to_anchor", "anchor", anchor_id)
	if not interaction.is_empty() and not _is_interaction_enabled(interaction):
		_set_status("暂时不能移动到锚点：%s" % _interaction_reason(interaction))
		return
	var payload := _payload_from_interaction(interaction)
	if payload.is_empty():
		payload = {"type": "move_to_anchor", "locationId": location_id, "anchorId": anchor_id}
	await _submit_player_action_with_feedback("移动到锚点", payload)


func _on_scene_interaction_pressed(interaction_id: String) -> void:
	var interaction: Dictionary = world_sync.find_interaction_by_id(interaction_id)
	if interaction.is_empty():
		_set_status("场景行动已失效，请刷新世界状态。")
		return
	if not _is_interaction_enabled(interaction):
		_set_status("暂时不能执行场景行动：%s" % _interaction_reason(interaction))
		return
	var payload := _payload_from_interaction(interaction)
	if payload.is_empty():
		_set_status("场景行动缺少后端 payload：%s" % interaction_id)
		return
	await _submit_player_action_with_feedback(str(interaction.get("label", "场景行动")), payload)


func _on_end_phase_pressed() -> void:
	var interaction: Dictionary = world_sync.find_interaction_by_id("end_phase")
	if not interaction.is_empty() and not _is_interaction_enabled(interaction):
		_set_status("暂时不能结束时段：%s" % _interaction_reason(interaction))
		return
	var payload := _payload_from_interaction(interaction)
	if payload.is_empty():
		payload = {"type": "end_phase"}
	await _submit_player_action_with_feedback("结束时段", payload)


func _on_scene_fallback_interaction_pressed(interaction_id: String) -> void:
	var interaction: Dictionary = world_sync.find_interaction_by_id(interaction_id)
	if interaction.is_empty():
		_set_status("兜底动作已过期，请刷新世界状态。")
		return
	if not _is_interaction_enabled(interaction):
		_set_status("当前动作不可用：%s" % _interaction_reason(interaction))
		return
	if map_context_action_pending:
		_set_status("已有动作在执行中，请稍候。")
		return
	map_context_action_pending = true
	_execute_map_context_interaction_async(interaction.duplicate(true))


func _submit_player_action_with_feedback(action_label: String, payload: Dictionary) -> void:
	_set_status("正在执行：%s ..." % action_label)
	var response = await api_client.post_player_action(payload)
	if not _is_action_response_ok(response):
		_set_status("动作失败：%s" % _response_error(response))
		return
	_apply_authoritative_state(response["data"]["state"])
	_render_world()
	_render_action_feedback_result(action_label, response["data"].get("result", {}))
	_set_status("动作完成：%s · %s" % [action_label, world_sync.get_clock_label()])


func _on_talk_pressed() -> void:
	await _submit_talk(selected_npc_id)


func _on_gift_pressed() -> void:
	await _submit_gift(selected_npc_id)


func _on_map_npc_pressed(npc_id: String) -> void:
	_select_npc(npc_id, true)
	_render_world()
	await _submit_talk(npc_id)


func _on_map_talk_marker_pressed(npc_id: String) -> void:
	_select_npc(npc_id, true)
	_render_world()
	await _submit_talk(npc_id)


func _on_map_gift_marker_pressed(npc_id: String) -> void:
	_select_npc(npc_id, true)
	_render_world()
	await _submit_gift(npc_id)


func _on_map_event_marker_pressed(event_id: String, event_location: String) -> void:
	await _on_inspect_event_pressed(event_id, event_location)


func _submit_talk(npc_id: String) -> void:
	if npc_id.is_empty():
		_set_status("请先选择一个居民。")
		return
	var npc := _find_npc(npc_id)
	if npc.is_empty():
		_set_status("居民已不在当前首发列表：%s" % npc_id)
		return
	_clear_event_focus()
	selected_npc_id = npc_id
	_render_portrait(npc)
	var action_location_id := str(npc.get("locationId", selected_location_id))
	var payload := _interaction_payload_or_fallback(
		"talk",
		"npc",
		npc_id,
		{"type": "talk", "targetId": npc_id, "locationId": action_location_id, "topic": "first_meeting"}
	)
	payload["topic"] = str(payload.get("topic", "first_meeting"))
	payload["message"] = str(payload.get("message", "你好，我刚搬到晨露农场，想认识一下小镇。"))
	_set_status("正在和 %s 聊天..." % npc.get("name", npc_id))
	var response = await api_client.post_player_action(payload)
	if not _is_action_response_ok(response):
		_set_status("对话动作失败：%s" % _response_error(response))
		return
	_apply_authoritative_state(response["data"]["state"])
	_render_social_action_result("对话", response["data"].get("result", {}))
	_render_world()
	_set_status("对话完成：%s" % world_sync.get_clock_label())


func _submit_gift(npc_id: String) -> void:
	if npc_id.is_empty():
		_set_status("请先选择一个居民。")
		return
	var npc := _find_npc(npc_id)
	if npc.is_empty():
		_set_status("居民已不在当前首发列表：%s" % npc_id)
		return
	var gift_interaction: Dictionary = world_sync.find_interaction("give_gift", "npc", npc_id)
	if not gift_interaction.is_empty() and not _is_interaction_enabled(gift_interaction):
		_set_status("暂时不能送礼：%s" % _interaction_reason(gift_interaction))
		return
	_clear_event_focus()
	selected_npc_id = npc_id
	_render_portrait(npc)
	var action_location_id := str(npc.get("locationId", selected_location_id))
	var payload := _interaction_payload_or_fallback(
		"give_gift",
		"npc",
		npc_id,
		{"type": "give_gift", "targetId": npc_id, "locationId": action_location_id, "itemId": _first_gift_item_id()}
	)
	if str(payload.get("itemId", "")).is_empty():
		_set_status("背包里暂时没有可送出的礼物。")
		return
	_set_status("正在给 %s 送礼..." % npc.get("name", npc_id))
	var response = await api_client.post_player_action(payload)
	if not _is_action_response_ok(response):
		_set_status("送礼动作失败：%s" % _response_error(response))
		return
	_apply_authoritative_state(response["data"]["state"])
	_render_social_action_result("送礼", response["data"].get("result", {}))
	_render_world()
	_set_status("送礼完成：%s" % world_sync.get_clock_label())


func _on_inspect_event_pressed(event_id: String, event_location: String) -> void:
	selected_event_id = event_id
	selected_event_location_id = event_location
	_set_status("正在查看事件：%s ..." % event_id)
	# 事件查看只通过后端 inspect 获取可见信息，客户端保持展示层职责。
	var payload := _interaction_payload_or_fallback(
		"inspect",
		"event",
		event_id,
		{"type": "inspect", "eventId": event_id, "locationId": event_location}
	)
	var response = await api_client.post_player_action(payload)
	if not _is_action_response_ok(response):
		_set_status("查看事件失败：%s" % _response_error(response))
		return
	_apply_authoritative_state(response["data"]["state"])
	var inspect_payload: Dictionary = response["data"].get("result", {}).get("inspect", {})
	_render_world()
	_render_inspect_result(inspect_payload)
	_set_status("已获取事件线索：%s" % inspect_payload.get("title", event_id))


func _on_attend_event_choice_pressed(event_id: String, event_location: String, choice_id: String) -> void:
	_set_status("正在提交事件选择：%s ..." % choice_id)
	# 玩家选择统一提交后端，事件结算、关系变化和记忆写入都由 Runtime 返回。
	var interaction: Dictionary = world_sync.find_event_choice_interaction(event_id, choice_id)
	if not interaction.is_empty() and not _is_interaction_enabled(interaction):
		_set_status("事件选项暂不可用：%s" % _interaction_reason(interaction))
		return
	var payload := _payload_from_interaction(interaction)
	if payload.is_empty():
		payload = {"type": "attend_event", "eventId": event_id, "choice": choice_id, "locationId": event_location}
	var response = await api_client.post_player_action(payload)
	if not _is_action_response_ok(response):
		_set_status("事件结算失败：%s" % _response_error(response))
		return
	_apply_authoritative_state(response["data"]["state"])
	_render_world()
	_render_attend_result(response["data"].get("result", {}))
	_set_status("事件已提交：%s" % choice_id)


func _on_npc_pressed(npc_id: String) -> void:
	_select_npc(npc_id, true)
	_render_world()
	var npc := _find_npc(npc_id)
	if npc.is_empty():
		return
	dialogue_label.text = "%s 正在 %s。点击地图小人或“聊天 / 送礼”按钮会向后端提交动作。" % [
		npc.get("name", npc_id),
		_get_location_name(str(npc.get("locationId", "unknown")))
	]
	_set_status("已选择居民：%s" % npc.get("name", npc_id))


func _refresh_world() -> void:
	_set_status("正在读取 /api/world/state ...")
	var response = await api_client.get_world_state()
	if not response.get("ok", false):
		_set_status("世界状态读取失败：%s" % response.get("error", "unknown"))
		return
	_apply_authoritative_state(response["data"])
	_render_world()
	_set_status("世界状态已同步：%s" % world_sync.get_clock_label())


func _apply_authoritative_state(state: Dictionary) -> void:
	# 所有动作回执都以 state 为准，客户端只保留当前选中项和 VN 展示文本。
	var previous_location_id := selected_location_id
	var previous_player = world_sync.get_player()
	if not previous_player.is_empty():
		previous_location_id = str(previous_player.get("locationId", selected_location_id))
	world_sync.apply_state(state)
	selected_location_id = str(state.get("player", {}).get("locationId", selected_location_id))
	last_location_debug = "权威状态：prev=%s selected=%s local=%s" % [previous_location_id, selected_location_id, player_local_location_id]
	if selected_location_id != previous_location_id:
		_clear_map_proximity_focus()
		_push_map_debug_note("权威切场景：%s -> %s" % [previous_location_id, selected_location_id])
	_ensure_selected_npc()
	_sync_event_focus_with_world()


func _clear_map_proximity_focus() -> void:
	# 切场景必须清掉旧场景的靠近目标和点击落点，避免单个旧焦点把新场景锁住。
	current_near_npc_id = ""
	current_near_event_id = ""
	current_near_anchor_id = ""
	current_near_interactable_id = ""
	map_context_candidates.clear()
	map_context_selected_index = 0
	map_context_sidebar_signature = ""
	player_local_has_click_target = false
	last_proximity_debug = "已清理靠近焦点"


func _render_world() -> void:
	player_label.text = world_sync.get_player_label()
	_render_background()
	_render_map_characters()
	_render_locations()
	_render_scene_actions()
	_render_npcs()
	_render_events()
	_render_focus_visual()


func _render_background() -> void:
	var texture: Texture2D = asset_registry.get_location_background(selected_location_id)
	if texture == null:
		texture = asset_registry.get_location_background("farm")
	background_rect.texture = texture


func _render_map_characters() -> void:
	if map_character_layer == null:
		return
	_clear_control_children(map_character_layer)
	map_hint_label = null
	map_context_panel = null
	map_context_title_label = null
	map_context_body_label = null
	map_debug_panel = null
	map_debug_label = null
	player_actor_node = null
	player_target_marker = null
	var bounds := _map_bounds()
	_ensure_map_hint_label(bounds)
	_render_map_anchor_markers(bounds)
	_render_map_scene_actions(bounds)
	_render_map_event_markers(bounds)

	var occupancy: Dictionary = {}
	var player: Dictionary = world_sync.get_player()
	var player_location := str(player.get("locationId", selected_location_id))
	var player_anchor := _resolve_player_anchor(player_location, bounds)
	var player_actor := _create_map_actor_node("player", str(player.get("name", "新来的农场主")), player_location, true, player_anchor)
	map_character_layer.add_child(player_actor)
	player_actor_node = player_actor
	occupancy[player_location] = 0
	for npc in world_sync.get_npcs():
		if not (npc is Dictionary):
			continue
		var npc_id := str(npc.get("id", ""))
		if npc_id.is_empty() or not asset_registry.has_map_sprite(npc_id):
			continue
		var npc_location := str(npc.get("locationId", selected_location_id))
		if npc_location != selected_location_id:
			continue
		_add_map_actor(npc_id, str(npc.get("name", npc_id)), npc_location, false, occupancy, bounds)
	_update_player_target_marker()
	_update_map_proximity_feedback()
	_update_map_debug_label(bounds)


func _render_map_event_markers(bounds: Rect2) -> void:
	for event_data in world_sync.get_active_events():
		if not (event_data is Dictionary):
			continue
		var event_id := str(event_data.get("id", ""))
		if event_id.is_empty() or str(event_data.get("status", "available")) == "resolved":
			continue
		var event_location := str(event_data.get("locationId", selected_location_id))
		if event_location != selected_location_id:
			continue
		var event_title := str(event_data.get("title", event_id))
		var anchor := _map_position_for_location(event_location, bounds) + Vector2(0, -_scaled(118))
		var event_marker_scale := MAP_EVENT_MARKER_SCALE * ui_scale
		var marker := TextureButton.new()
		marker.name = "MapEvent_%s" % event_id
		marker.focus_mode = Control.FOCUS_NONE
		marker.texture_normal = asset_registry.get_interaction_marker("event")
		marker.scale = Vector2(event_marker_scale, event_marker_scale)
		marker.position = anchor - Vector2(MAP_SPRITE_SIZE * event_marker_scale * 0.5, MAP_SPRITE_SIZE * event_marker_scale * 0.5)
		marker.tooltip_text = "查看事件：%s" % event_title
		marker.set_meta("eventId", event_id)
		marker.set_meta("eventTitle", event_title)
		marker.set_meta("locationId", event_location)
		marker.set_meta("anchor", anchor)
		marker.set_meta("interactable", true)
		marker.pressed.connect(_on_map_event_marker_pressed.bind(event_id, event_location))
		map_character_layer.add_child(marker)

		var label := _create_map_label(event_title, 160, 14)
		label.position = marker.position + Vector2(-_scaled(58), _scaled(44))
		map_character_layer.add_child(label)


func _render_map_anchor_markers(bounds: Rect2) -> void:
	var player: Dictionary = world_sync.get_player()
	var player_anchor_id := str(player.get("anchorId", ""))
	for anchor in world_sync.get_anchors():
		if not (anchor is Dictionary):
			continue
		var anchor_id := str(anchor.get("id", ""))
		var anchor_location := str(anchor.get("locationId", ""))
		if anchor_id.is_empty() or anchor_location != selected_location_id:
			continue
		var interaction: Dictionary = world_sync.find_interaction("move_to_anchor", "anchor", anchor_id)
		var button := Button.new()
		button.name = "MapAnchor_%s" % _safe_node_suffix(anchor_id)
		button.text = _anchor_display_label(anchor)
		button.focus_mode = Control.FOCUS_NONE
		button.tooltip_text = "移动到锚点：%s" % anchor_id
		button.disabled = anchor_id == player_anchor_id or (not interaction.is_empty() and not _is_interaction_enabled(interaction))
		if button.disabled and anchor_id == player_anchor_id:
			button.tooltip_text = "当前所在锚点：%s" % anchor_id
		elif button.disabled and not interaction.is_empty():
			button.tooltip_text = _interaction_reason(interaction)
		_style_button(button, 92)
		button.size = Vector2(_scaled(112), _scaled(38))
		button.position = _position_for_anchor_id(anchor_id, bounds, _scene_stage_center(bounds)) - Vector2(button.size.x * 0.5, _scaled(20))
		button.z_index = 8
		button.pressed.connect(_on_move_to_anchor_pressed.bind(anchor_id, anchor_location))
		map_character_layer.add_child(button)


func _render_map_scene_actions(bounds: Rect2) -> void:
	var offsets_by_anchor: Dictionary = {}
	for interactable in world_sync.get_interactables():
		if not (interactable is Dictionary):
			continue
		var interactable_data: Dictionary = interactable
		var location_id := str(interactable_data.get("locationId", ""))
		if location_id != selected_location_id:
			continue
		var anchor_id := str(interactable_data.get("anchorId", ""))
		var index := int(offsets_by_anchor.get(anchor_id, 0))
		offsets_by_anchor[anchor_id] = index + 1
		var anchor_pos := _position_for_anchor_id(anchor_id, bounds, _scene_stage_center(bounds))
		var hint := _create_map_label("交互体：%s" % _interactable_display_label(interactable_data), 208, 13)
		hint.name = "MapInteractable_%s" % _safe_node_suffix(str(interactable_data.get("id", "")))
		hint.position = anchor_pos + Vector2(-hint.size.x * 0.5, _scaled(18 + index * 22))
		hint.modulate = Color(1.0, 1.0, 1.0, 0.72)
		hint.z_index = 16
		map_character_layer.add_child(hint)


func _add_map_actor(owner_id: String, display_name: String, location_id: String, is_player: bool, occupancy: Dictionary, bounds: Rect2) -> void:
	var index := int(occupancy.get(location_id, 0))
	occupancy[location_id] = index + 1
	var anchor := _scene_npc_anchor(index, bounds) if location_id == selected_location_id else _map_position_for_location(location_id, bounds)
	var actor := _create_map_actor_node(owner_id, display_name, location_id, is_player, anchor)
	map_character_layer.add_child(actor)


func _create_map_actor_node(owner_id: String, display_name: String, location_id: String, is_player: bool, anchor: Vector2) -> Control:
	var actor := Control.new()
	var node_size := _map_node_size()
	var sprite_scale := MAP_SPRITE_SCALE * ui_scale
	actor.name = "MapActor_%s" % owner_id
	actor.mouse_filter = Control.MOUSE_FILTER_PASS
	actor.z_index = 30 if is_player else 10
	actor.position = anchor - Vector2(node_size.x * 0.5, node_size.y)
	actor.size = node_size
	actor.set_meta("agentId", owner_id)
	actor.set_meta("displayName", display_name)
	actor.set_meta("locationId", location_id)
	actor.set_meta("anchor", anchor)
	actor.set_meta("interactable", not is_player)

	var sprite_button := TextureButton.new()
	sprite_button.name = "Sprite"
	sprite_button.focus_mode = Control.FOCUS_NONE
	sprite_button.texture_normal = asset_registry.get_map_sprite(owner_id)
	sprite_button.scale = Vector2(sprite_scale, sprite_scale)
	sprite_button.position = Vector2((node_size.x - MAP_SPRITE_SIZE * sprite_scale) * 0.5, _scaled(38))
	sprite_button.disabled = is_player
	sprite_button.mouse_filter = Control.MOUSE_FILTER_IGNORE if is_player else Control.MOUSE_FILTER_PASS
	sprite_button.tooltip_text = "%s · %s" % [display_name, _get_location_name(location_id)]
	if not is_player:
		sprite_button.pressed.connect(_on_map_npc_pressed.bind(owner_id))
	actor.add_child(sprite_button)

	if is_player:
		var player_marker := _create_map_label("玩家", 52, 13)
		player_marker.position = _scaled_vector(Vector2(30, 9))
		actor.add_child(player_marker)
	else:
		var talk_interaction: Dictionary = world_sync.find_interaction("talk", "npc", owner_id)
		var gift_interaction: Dictionary = world_sync.find_interaction("give_gift", "npc", owner_id)
		var talk_enabled := _is_interaction_enabled_or_missing(talk_interaction)
		var gift_enabled := _is_interaction_enabled_or_missing(gift_interaction)
		actor.set_meta("interactable", talk_enabled or gift_enabled)
		actor.set_meta("talkEnabled", talk_enabled)
		actor.set_meta("giftEnabled", gift_enabled)

		var talk_marker := _create_actor_marker("talk", "聊天：%s" % display_name, talk_enabled)
		talk_marker.name = "TalkMarker"
		talk_marker.position = _scaled_vector(Vector2(6, 8))
		talk_marker.pressed.connect(_on_map_talk_marker_pressed.bind(owner_id))
		actor.add_child(talk_marker)

		var gift_marker := _create_actor_marker("gift", "送礼：%s" % display_name, gift_enabled)
		gift_marker.name = "GiftMarker"
		gift_marker.position = _scaled_vector(Vector2(78, 8))
		gift_marker.pressed.connect(_on_map_gift_marker_pressed.bind(owner_id))
		actor.add_child(gift_marker)

	var name_label := _create_map_label(display_name, int(MAP_NODE_SIZE.x), 14)
	name_label.position = Vector2(0, _scaled(116))
	actor.add_child(name_label)
	return actor


func _create_actor_marker(marker_id: String, tooltip: String, enabled: bool) -> TextureButton:
	var marker := TextureButton.new()
	marker.focus_mode = Control.FOCUS_NONE
	marker.texture_normal = asset_registry.get_interaction_marker(marker_id)
	var marker_scale := MAP_MARKER_SCALE * ui_scale
	marker.scale = Vector2(marker_scale, marker_scale)
	marker.tooltip_text = tooltip
	marker.disabled = not enabled
	if not enabled:
		marker.modulate = Color(1, 1, 1, 0.34)
	return marker


func _create_map_label(text: String, width: int, font_size: int) -> Label:
	var label := Label.new()
	label.text = text
	label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	label.size = Vector2(_scaled(width), _scaled(26))
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label.add_theme_font_size_override("font_size", _font_size(font_size))
	label.add_theme_color_override("font_color", Color(1, 0.96, 0.84, 1))
	label.add_theme_color_override("font_shadow_color", Color(0, 0, 0, 0.9))
	label.add_theme_constant_override("shadow_offset_x", _scaled_int(1))
	label.add_theme_constant_override("shadow_offset_y", _scaled_int(1))
	return label


func _map_bounds() -> Rect2:
	var viewport_size := get_viewport_rect().size
	var side_margin: float = min(_scaled(240), max(_scaled(64), viewport_size.x * 0.10))
	var left: float = side_margin
	var right: float = max(left + _scaled(420), viewport_size.x - side_margin)
	var top: float = min(_scaled(92), max(_scaled(58), viewport_size.y * 0.12))
	var bottom: float = max(top + _scaled(270), viewport_size.y - _top_layer_reserved_bottom() - _scaled(8))
	return Rect2(left, top, right - left, bottom - top)


func _map_position_for_location(location_id: String, bounds: Rect2) -> Vector2:
	if location_id == selected_location_id:
		return _scene_stage_center(bounds)
	var location := _find_location(location_id)
	var x_ratio := float(location.get("x", 50.0)) / 100.0 if not location.is_empty() else 0.5
	var y_ratio := float(location.get("y", 55.0)) / 100.0 if not location.is_empty() else 0.55
	return Vector2(bounds.position.x + bounds.size.x * x_ratio, bounds.position.y + bounds.size.y * y_ratio)


func _position_for_anchor_id(anchor_id: String, bounds: Rect2, fallback: Vector2) -> Vector2:
	if anchor_id.is_empty():
		return fallback
	var anchor: Dictionary = world_sync.find_anchor(anchor_id)
	if anchor.is_empty():
		return fallback
	return _position_for_anchor(anchor, bounds, fallback)


func _position_for_anchor(anchor: Dictionary, bounds: Rect2, fallback: Vector2) -> Vector2:
	var screen_position = anchor.get("screenPosition", {})
	if not (screen_position is Dictionary):
		return fallback
	var screen_data: Dictionary = screen_position
	var ratio := Vector2(float(screen_data.get("x", 0.5)), float(screen_data.get("y", 0.5)))
	return _scene_anchor_from_ratio(bounds, ratio)


func _scene_stage_center(bounds: Rect2) -> Vector2:
	# 当前只渲染当前场景，统一用舞台中心排阵，避免世界地图坐标把角色挤到边角。
	return Vector2(bounds.position.x + bounds.size.x * 0.5, bounds.position.y + bounds.size.y * 0.42)


func _scene_npc_anchor(index: int, bounds: Rect2) -> Vector2:
	# NPC 使用按场景比例定义的固定站位槽，不再围绕玩家或单一中心点堆叠。
	if index < MAP_NPC_SLOT_RATIOS.size():
		return _scene_anchor_from_ratio(bounds, MAP_NPC_SLOT_RATIOS[index])
	var column := index % 4
	var row := int(index / 4)
	var ratio := Vector2(0.20 + float(column) * 0.20, min(0.62, 0.24 + float(row) * 0.14))
	return _scene_anchor_from_ratio(bounds, ratio)


func _scene_anchor_from_ratio(bounds: Rect2, ratio: Vector2) -> Vector2:
	# 用当前可移动区域的比例点生成锚点，适配不同窗口尺寸和 UI 缩放。
	var anchor := Vector2(bounds.position.x + bounds.size.x * ratio.x, bounds.position.y + bounds.size.y * ratio.y)
	return _clamp_point_to_walk_area(anchor, bounds)


func _ensure_map_hint_label(bounds: Rect2) -> void:
	if map_character_layer == null:
		return
	if map_hint_label == null or not is_instance_valid(map_hint_label):
		map_hint_label = Label.new()
		map_hint_label.name = "MapMoveHint"
		map_hint_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		map_hint_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
		_style_body_label(map_hint_label, 14)
	map_hint_label.size = Vector2(max(_scaled(300), bounds.size.x - _scaled(12)), _scaled(56))
	map_hint_label.position = Vector2(bounds.position.x + _scaled(8), bounds.position.y + _scaled(6))
	if map_hint_label.get_parent() != map_character_layer:
		map_character_layer.add_child(map_hint_label)
	_update_map_hint("WASD 连续移动；点击当前场景空地可设置落点")


func _update_map_hint(text: String) -> void:
	if map_hint_label != null:
		map_hint_label.text = text


func _ensure_map_context_panel(bounds: Rect2) -> void:
	if map_character_layer == null:
		return
	if map_context_panel == null or not is_instance_valid(map_context_panel):
		map_context_panel = PanelContainer.new()
		map_context_panel.name = "MapContextActions"
		map_context_panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
		map_context_panel.z_index = 210
		map_context_panel.add_theme_stylebox_override("panel", _make_panel_style(Color(0.09, 0.14, 0.11, 0.88), UI_GOLD_LIGHT, _scaled_int(12), _scaled_int(2), _scaled_int(10)))

		var body := VBoxContainer.new()
		body.name = "Body"
		body.mouse_filter = Control.MOUSE_FILTER_IGNORE
		body.add_theme_constant_override("separation", _scaled_int(4))
		map_context_panel.add_child(body)

		map_context_title_label = Label.new()
		map_context_title_label.name = "Title"
		map_context_title_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
		map_context_title_label.add_theme_font_size_override("font_size", _font_size(14))
		map_context_title_label.add_theme_color_override("font_color", Color(1.0, 0.92, 0.66, 1.0))
		body.add_child(map_context_title_label)

		map_context_body_label = Label.new()
		map_context_body_label.name = "Actions"
		map_context_body_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		map_context_body_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
		map_context_body_label.add_theme_font_size_override("font_size", _font_size(13))
		map_context_body_label.add_theme_color_override("font_color", Color(0.94, 1.0, 0.91, 1.0))
		map_context_body_label.add_theme_color_override("font_shadow_color", Color(0.0, 0.0, 0.0, 0.92))
		map_context_body_label.add_theme_constant_override("shadow_offset_x", _scaled_int(1))
		map_context_body_label.add_theme_constant_override("shadow_offset_y", _scaled_int(1))
		body.add_child(map_context_body_label)
	if map_context_panel.get_parent() != map_character_layer:
		map_character_layer.add_child(map_context_panel)
	var panel_size := Vector2(min(_scaled(MAP_CONTEXT_PANEL_WIDTH), bounds.size.x - _scaled(12)), _scaled(MAP_CONTEXT_PANEL_HEIGHT))
	map_context_panel.custom_minimum_size = panel_size
	map_context_panel.size = panel_size
	map_context_panel.position = Vector2(bounds.position.x + _scaled(8), bounds.end.y - panel_size.y - _scaled(10))


func _refresh_map_context_panel() -> void:
	if map_character_layer == null:
		return
	_ensure_map_context_panel(_map_bounds())
	if map_context_title_label == null or map_context_body_label == null:
		return
	if map_context_candidates.is_empty():
		map_context_selected_index = 0
		map_context_title_label.text = "附近动作（E/Space 执行，Tab/Q 切换）"
		map_context_body_label.text = "当前附近没有可执行动作，继续移动靠近锚点、居民、事件或交互体。"
		_update_map_hint("WASD 连续移动；点击当前场景空地可设置落点")
		return
	map_context_selected_index = int(clamp(map_context_selected_index, 0, map_context_candidates.size() - 1))
	var candidate: Dictionary = map_context_candidates[map_context_selected_index]
	var target_name := str(candidate.get("targetLabel", "当前目标"))
	var lines: Array[String] = []
	for index in range(map_context_candidates.size()):
		var item: Dictionary = map_context_candidates[index]
		var prefix := "▶" if index == map_context_selected_index else "·"
		var state := "可执行" if bool(item.get("enabled", false)) else "暂不可用"
		var reason := str(item.get("reason", ""))
		if not bool(item.get("enabled", false)) and not reason.is_empty():
			state = "%s（%s）" % [state, reason]
		lines.append("%s %s [%s]" % [prefix, str(item.get("label", "动作")), state])
	map_context_title_label.text = "附近动作 · %s（E/Space 执行，Tab/Q 切换）" % target_name
	map_context_body_label.text = "\n".join(lines)
	var selected_label := str(candidate.get("label", "动作"))
	if bool(candidate.get("enabled", false)):
		_update_map_hint("当前动作：%s，按 E 或 Space 执行；Tab/Q 切换。" % selected_label)
	else:
		var selected_reason := str(candidate.get("reason", "后端暂未开放该动作"))
		_update_map_hint("当前动作：%s（暂不可用：%s），继续移动或按 Tab/Q 切换。" % [selected_label, selected_reason])
	if map_context_panel != null and map_context_panel.get_parent() == map_character_layer:
		map_character_layer.move_child(map_context_panel, map_character_layer.get_child_count() - 1)


func _cycle_map_context_candidate(direction: int) -> bool:
	if map_context_candidates.is_empty():
		return false
	var count := map_context_candidates.size()
	if count <= 1:
		_refresh_map_context_panel()
		if scene_action_list != null:
			_render_scene_actions()
		return false
	map_context_selected_index = (map_context_selected_index + direction) % count
	if map_context_selected_index < 0:
		map_context_selected_index += count
	_refresh_map_context_panel()
	if scene_action_list != null:
		_render_scene_actions()
	return true


func _ensure_map_debug_label(bounds: Rect2) -> void:
	if not MAP_MOVEMENT_DEBUG_ENABLED or map_character_layer == null:
		return
	if map_debug_panel == null or not is_instance_valid(map_debug_panel):
		map_debug_panel = PanelContainer.new()
		map_debug_panel.name = "MapMovementDebug"
		map_debug_panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
		map_debug_panel.z_index = 240
		map_debug_panel.add_theme_stylebox_override("panel", _make_panel_style(Color(0.04, 0.06, 0.05, 0.78), UI_GOLD_LIGHT, _scaled_int(12), _scaled_int(2), _scaled_int(10)))

		map_debug_label = Label.new()
		map_debug_label.name = "DebugText"
		map_debug_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		map_debug_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
		map_debug_label.add_theme_font_size_override("font_size", _font_size(13))
		map_debug_label.add_theme_color_override("font_color", Color(0.92, 1.0, 0.86, 1.0))
		map_debug_label.add_theme_color_override("font_shadow_color", Color(0.0, 0.0, 0.0, 0.95))
		map_debug_label.add_theme_constant_override("shadow_offset_x", _scaled_int(1))
		map_debug_label.add_theme_constant_override("shadow_offset_y", _scaled_int(1))
		map_debug_panel.add_child(map_debug_label)
	if map_debug_panel.get_parent() != map_character_layer:
		map_character_layer.add_child(map_debug_panel)
	var debug_size := Vector2(max(_scaled(430), bounds.size.x * 0.34), _scaled(228))
	map_debug_panel.custom_minimum_size = debug_size
	map_debug_panel.size = debug_size
	map_debug_panel.position = Vector2(bounds.end.x - debug_size.x - _scaled(8), bounds.position.y + _scaled(68))


func _update_map_debug_label(bounds: Rect2) -> void:
	if not MAP_MOVEMENT_DEBUG_ENABLED or map_character_layer == null:
		return
	_ensure_map_debug_label(bounds)
	if map_debug_label == null:
		return
	var player: Dictionary = {}
	if world_sync != null:
		player = world_sync.get_player()
	var state_location := str(player.get("locationId", "未同步"))
	var anchor_key := "anchor" + "Id"
	var state_anchor := str(player.get(anchor_key, "无"))
	var player_actor := _get_player_actor_node()
	var actor_anchor := "缺失"
	var actor_name := "缺失"
	if player_actor != null:
		actor_anchor = _debug_vector(player_actor.get_meta("anchor", Vector2.ZERO))
		actor_name = player_actor.name
	var lines: Array[String] = []
	lines.append("Map Debug")
	lines.append("selected=%s | state=%s | local=%s | anchor=%s" % [selected_location_id, state_location, player_local_location_id, state_anchor])
	lines.append("pos=%s | actor=%s %s | target=%s | hasTarget=%s" % [_debug_vector(player_local_position), actor_name, actor_anchor, _debug_vector(player_local_target), str(player_local_has_click_target)])
	lines.append("axis=%s | motion=%s" % [_debug_vector(last_move_axis), last_motion_debug])
	lines.append("nearNpc=%s | nearEvent=%s | %s" % [current_near_npc_id, current_near_event_id, last_proximity_debug])
	lines.append("click=%s" % last_click_debug)
	lines.append("location=%s" % last_location_debug)
	lines.append("bounds=%s | viewport=%s" % [_debug_rect(bounds), _debug_rect(get_viewport_rect())])
	if not map_debug_notes.is_empty():
		lines.append("notes:")
		for note in map_debug_notes:
			lines.append("- %s" % note)
	map_debug_label.text = "\n".join(lines)
	if map_debug_panel != null and map_debug_panel.get_parent() == map_character_layer:
		map_character_layer.move_child(map_debug_panel, map_character_layer.get_child_count() - 1)


func _push_map_debug_note(message: String) -> void:
	if not MAP_MOVEMENT_DEBUG_ENABLED:
		return
	map_debug_notes.append(message)
	while map_debug_notes.size() > MAP_DEBUG_NOTE_LIMIT:
		map_debug_notes.remove_at(0)
	print("[MapMovementDebug] ", message)
	if map_character_layer != null:
		_update_map_debug_label(_map_bounds())


func _debug_vector(value: Vector2) -> String:
	return "(%.1f, %.1f)" % [value.x, value.y]


func _debug_rect(value: Rect2) -> String:
	return "p=%s s=%s" % [_debug_vector(value.position), _debug_vector(value.size)]


func _debug_distance(value: float) -> String:
	if value == INF:
		return "inf"
	return "%.1f" % value


func _trigger_current_map_context_action() -> bool:
	if map_context_action_pending:
		_set_status("当前动作仍在执行中，请稍候。")
		return true
	if map_context_candidates.is_empty():
		_set_status("附近暂无可执行动作，先移动到锚点或交互体附近。")
		return false
	map_context_selected_index = int(clamp(map_context_selected_index, 0, map_context_candidates.size() - 1))
	var candidate: Dictionary = map_context_candidates[map_context_selected_index]
	if not bool(candidate.get("enabled", false)):
		var reason := str(candidate.get("reason", "后端暂未开放该动作"))
		_set_status("动作暂不可用：%s" % reason)
		return true
	var interaction = candidate.get("interaction", {})
	if not (interaction is Dictionary) or (interaction as Dictionary).is_empty():
		_set_status("动作数据已过期，请刷新世界状态后重试。")
		return true
	map_context_action_pending = true
	_execute_map_context_interaction_async((interaction as Dictionary).duplicate(true))
	return true


func _execute_map_context_interaction_async(interaction: Dictionary) -> void:
	var action_type := str(interaction.get("type", ""))
	var target = interaction.get("target", {})
	var target_data: Dictionary = target if target is Dictionary else {}
	var payload := _payload_from_interaction(interaction)
	match action_type:
		"talk":
			await _submit_talk(str(target_data.get("id", "")))
		"give_gift":
			await _submit_gift(str(target_data.get("id", "")))
		"inspect":
			var event_id := str(target_data.get("id", payload.get("eventId", "")))
			var event_location := str(target_data.get("locationId", payload.get("locationId", selected_location_id)))
			await _on_inspect_event_pressed(event_id, event_location)
		"attend_event":
			var event_id := str(payload.get("eventId", target_data.get("id", "")))
			var event_location := str(payload.get("locationId", target_data.get("locationId", selected_location_id)))
			var choice_id := str(payload.get("choice", ""))
			if choice_id.is_empty():
				_set_status("事件动作缺少 choice 参数：%s" % str(interaction.get("id", "attend_event")))
			else:
				await _on_attend_event_choice_pressed(event_id, event_location, choice_id)
		"move_to_anchor":
			var anchor_id := str(target_data.get("id", payload.get("anchorId", "")))
			var location_id := str(target_data.get("locationId", payload.get("locationId", selected_location_id)))
			await _on_move_to_anchor_pressed(anchor_id, location_id)
		"scene_action":
			await _on_scene_interaction_pressed(str(interaction.get("id", "")))
		"farm_action":
			if payload.is_empty():
				_set_status("农场动作缺少 payload：%s" % str(interaction.get("id", "farm_action")))
			else:
				await _submit_player_action_with_feedback(str(interaction.get("label", "农场行动")), payload)
		"end_phase":
			await _on_end_phase_pressed()
		_:
			if payload.is_empty():
				_set_status("暂不支持该动作：%s" % action_type)
			else:
				await _submit_player_action_with_feedback(str(interaction.get("label", action_type)), payload)
	map_context_action_pending = false


func _rebuild_map_context_candidates() -> void:
	var candidates: Array[Dictionary] = []
	var seen_ids: Dictionary = {}
	var near_anchor := current_near_anchor_id
	var near_interactable := current_near_interactable_id
	var near_npc := current_near_npc_id
	var near_event := current_near_event_id
	for interaction in world_sync.get_available_interactions():
		if not (interaction is Dictionary):
			continue
		var interaction_data: Dictionary = interaction
		var target = interaction_data.get("target", {})
		if not (target is Dictionary):
			continue
		var target_data: Dictionary = target
		var location_id := str(target_data.get("locationId", ""))
		if not location_id.is_empty() and location_id != selected_location_id:
			continue
		var action_type := str(interaction_data.get("type", ""))
		var target_kind := str(target_data.get("kind", ""))
		var target_id := str(target_data.get("id", ""))
		var match_context := false
		var target_label := ""
		if action_type == "talk" or action_type == "give_gift":
			match_context = target_kind == "npc" and target_id == near_npc
			target_label = "居民"
		elif action_type == "inspect" or action_type == "attend_event":
			match_context = target_kind == "event" and target_id == near_event
			target_label = "事件"
		elif action_type == "scene_action" or action_type == "farm_action":
			var target_anchor_id := str(target_data.get("anchorId", ""))
			match_context = (not near_interactable.is_empty() and target_id == near_interactable) or (not near_anchor.is_empty() and target_anchor_id == near_anchor)
			target_label = "交互体"
		elif action_type == "move_to_anchor":
			match_context = target_kind == "anchor" and target_id == near_anchor
			target_label = "锚点"
		if not match_context:
			continue
		var interaction_id := str(interaction_data.get("id", ""))
		if interaction_id.is_empty():
			interaction_id = "%s:%s:%s" % [action_type, target_kind, target_id]
		if seen_ids.has(interaction_id):
			continue
		seen_ids[interaction_id] = true
		var enabled := _is_interaction_enabled(interaction_data)
		candidates.append({
			"id": interaction_id,
			"label": str(interaction_data.get("label", action_type)),
			"enabled": enabled,
			"reason": _interaction_reason(interaction_data) if not enabled else "",
			"targetLabel": target_label,
			"interaction": interaction_data.duplicate(true),
		})
	map_context_candidates = candidates
	if map_context_candidates.is_empty():
		map_context_selected_index = 0
	else:
		map_context_selected_index = int(clamp(map_context_selected_index, 0, map_context_candidates.size() - 1))
	var signature_parts: Array[String] = []
	for candidate in map_context_candidates:
		signature_parts.append("%s:%s" % [str(candidate.get("id", "")), str(candidate.get("enabled", false))])
	signature_parts.append("selected=%d" % map_context_selected_index)
	var signature := "|".join(signature_parts)
	if signature != map_context_sidebar_signature:
		map_context_sidebar_signature = signature
		if scene_action_list != null:
			_render_scene_actions()
	_refresh_map_context_panel()


func _update_player_target_marker() -> void:
	if map_character_layer == null:
		return
	if not player_local_has_click_target:
		if player_target_marker != null and is_instance_valid(player_target_marker):
			player_target_marker.visible = false
		return
	if player_target_marker == null or not is_instance_valid(player_target_marker):
		player_target_marker = Label.new()
		player_target_marker.name = "PlayerMoveTarget"
		player_target_marker.text = "◎"
		player_target_marker.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		player_target_marker.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		player_target_marker.mouse_filter = Control.MOUSE_FILTER_IGNORE
		player_target_marker.size = _scaled_vector(Vector2(34, 34))
		player_target_marker.add_theme_font_size_override("font_size", _font_size(22))
		player_target_marker.add_theme_color_override("font_color", Color(0.92, 1.0, 1.0, 0.88))
		player_target_marker.add_theme_color_override("font_shadow_color", Color(0.05, 0.18, 0.18, 0.95))
		player_target_marker.add_theme_constant_override("shadow_offset_x", _scaled_int(1))
		player_target_marker.add_theme_constant_override("shadow_offset_y", _scaled_int(1))
	if player_target_marker.get_parent() != map_character_layer:
		map_character_layer.add_child(player_target_marker)
	player_target_marker.position = player_local_target - player_target_marker.size * 0.5
	player_target_marker.visible = true
	map_character_layer.move_child(player_target_marker, map_character_layer.get_child_count() - 1)


func _update_map_proximity_feedback() -> void:
	# 靠近反馈只控制高亮与可点状态，交互提交仍走既有 talk/give_gift/inspect/attend_event。
	if not player_local_initialized or map_character_layer == null:
		return
	var bounds := _map_bounds()
	var interact_radius := _scaled(PLAYER_LOCAL_INTERACT_RADIUS)
	var exit_radius := interact_radius + _scaled(PLAYER_LOCAL_INTERACT_EXIT_MARGIN)
	var nearest_npc_name := ""
	var nearest_event_title := ""
	var nearest_anchor_id := ""
	var nearest_anchor_kind := ""
	var nearest_interactable_id := ""
	var nearest_npc_distance := INF
	var nearest_event_distance := INF
	var nearest_anchor_distance := INF
	var nearest_interactable_distance := INF
	var nearest_npc_actor: Control = null
	var nearest_event_marker: TextureButton = null
	var previous_anchor_id := ""
	var previous_anchor_kind := ""
	var previous_interactable_id := ""
	var previous_npc_name := ""
	var previous_npc_actor: Control = null
	var previous_event_title := ""
	var previous_event_marker: TextureButton = null
	for child in map_character_layer.get_children():
		if child is TextureButton:
			var marker := child as TextureButton
			if not marker.name.begins_with("MapEvent_"):
				continue
			var event_anchor: Vector2 = marker.get_meta("anchor", Vector2.ZERO)
			var event_location := str(marker.get_meta("locationId", ""))
			var same_location := event_location == selected_location_id
			var distance := player_local_position.distance_to(event_anchor)
			var event_id := str(marker.get_meta("eventId", ""))
			if same_location and event_id == current_near_event_id and distance <= exit_radius:
				previous_event_title = str(marker.get_meta("eventTitle", event_id))
				previous_event_marker = marker
			if same_location and distance <= interact_radius and distance < nearest_event_distance:
				nearest_event_distance = distance
				nearest_event_title = str(marker.get_meta("eventTitle", marker.get_meta("eventId", "事件")))
				nearest_event_marker = marker
		elif child is Control:
			var actor := child as Control
			if not actor.name.begins_with("MapActor_"):
				continue
			if actor.name == "MapActor_player":
				continue
			var actor_anchor: Vector2 = actor.get_meta("anchor", Vector2.ZERO)
			var actor_location := str(actor.get_meta("locationId", ""))
			var same_location := actor_location == selected_location_id
			var can_interact: bool = bool(actor.get_meta("interactable", false))
			var distance := player_local_position.distance_to(actor_anchor)
			var actor_id := str(actor.get_meta("agentId", ""))
			if same_location and can_interact and actor_id == current_near_npc_id and distance <= exit_radius:
				previous_npc_name = str(actor.get_meta("displayName", actor_id))
				previous_npc_actor = actor
			if same_location and can_interact and distance <= interact_radius and distance < nearest_npc_distance:
				nearest_npc_distance = distance
				nearest_npc_name = str(actor.get_meta("displayName", actor.get_meta("agentId", "居民")))
				nearest_npc_actor = actor

	for anchor in world_sync.get_anchors():
		if not (anchor is Dictionary):
			continue
		var anchor_data: Dictionary = anchor
		var anchor_id := str(anchor_data.get("id", ""))
		var anchor_location := str(anchor_data.get("locationId", ""))
		if anchor_id.is_empty() or anchor_location != selected_location_id:
			continue
		var anchor_pos := _position_for_anchor(anchor_data, bounds, _scene_stage_center(bounds))
		var distance := player_local_position.distance_to(anchor_pos)
		if anchor_id == current_near_anchor_id and distance <= exit_radius:
			previous_anchor_id = anchor_id
			previous_anchor_kind = _anchor_kind_label(str(anchor_data.get("kind", "")))
		if distance <= interact_radius and distance < nearest_anchor_distance:
			nearest_anchor_distance = distance
			nearest_anchor_id = anchor_id
			nearest_anchor_kind = _anchor_kind_label(str(anchor_data.get("kind", "")))
	for interactable in world_sync.get_interactables():
		if not (interactable is Dictionary):
			continue
		var interactable_data: Dictionary = interactable
		var interactable_id := str(interactable_data.get("id", ""))
		var interactable_location := str(interactable_data.get("locationId", ""))
		if interactable_id.is_empty() or interactable_location != selected_location_id:
			continue
		var interactable_anchor_id := str(interactable_data.get("anchorId", ""))
		var anchor_pos := _position_for_anchor_id(interactable_anchor_id, bounds, _scene_stage_center(bounds))
		var distance := player_local_position.distance_to(anchor_pos)
		if interactable_id == current_near_interactable_id and distance <= exit_radius:
			previous_interactable_id = interactable_id
		if distance <= interact_radius and distance < nearest_interactable_distance:
			nearest_interactable_distance = distance
			nearest_interactable_id = interactable_id

	if previous_npc_actor != null:
		nearest_npc_actor = previous_npc_actor
		nearest_npc_name = previous_npc_name
	if previous_event_marker != null:
		nearest_event_marker = previous_event_marker
		nearest_event_title = previous_event_title
	if not previous_anchor_id.is_empty():
		nearest_anchor_id = previous_anchor_id
		nearest_anchor_kind = previous_anchor_kind
	if not previous_interactable_id.is_empty():
		nearest_interactable_id = previous_interactable_id
	current_near_npc_id = str(nearest_npc_actor.get_meta("agentId", "")) if nearest_npc_actor != null else ""
	current_near_event_id = str(nearest_event_marker.get_meta("eventId", "")) if nearest_event_marker != null else ""
	current_near_anchor_id = nearest_anchor_id
	current_near_interactable_id = nearest_interactable_id
	last_proximity_debug = "npcDist=%s eventDist=%s anchorDist=%s interactableDist=%s radius=%.1f exit=%.1f" % [
		_debug_distance(nearest_npc_distance),
		_debug_distance(nearest_event_distance),
		_debug_distance(nearest_anchor_distance),
		_debug_distance(nearest_interactable_distance),
		interact_radius,
		exit_radius,
	]

	# 同一时间只激活最近的 NPC / 事件，避免多人重叠时焦点在多个 marker 之间抖动。
	for child in map_character_layer.get_children():
		if child is TextureButton:
			var marker := child as TextureButton
			if not marker.name.begins_with("MapEvent_"):
				continue
			var is_near := marker == nearest_event_marker
			marker.disabled = not is_near
			if selected_event_id == str(marker.get_meta("eventId", "")):
				marker.modulate = Color(1.0, 0.92, 0.45, 1.0 if is_near else 0.75)
			else:
				marker.modulate = Color(1.0, 1.0, 1.0, 1.0 if is_near else 0.46)
		elif child is Control:
			var actor := child as Control
			if not actor.name.begins_with("MapActor_"):
				continue
			if actor.name == "MapActor_player":
				continue
			var is_near: bool = actor == nearest_npc_actor
			var sprite_button := actor.get_node_or_null("Sprite") as TextureButton
			if sprite_button != null:
				sprite_button.disabled = false
				var owner_id := str(actor.get_meta("agentId", ""))
				var tint := Color(1.0, 0.94, 0.72, 1.0) if owner_id == selected_npc_id or is_near else Color(1.0, 1.0, 1.0, 0.70)
				sprite_button.modulate = tint
			var talk_marker := actor.get_node_or_null("TalkMarker") as TextureButton
			if talk_marker != null:
				var talk_enabled: bool = bool(actor.get_meta("talkEnabled", true))
				talk_marker.disabled = not (is_near and talk_enabled)
				talk_marker.modulate = Color(1.0, 1.0, 1.0, 1.0 if is_near and talk_enabled else 0.34)
			var gift_marker := actor.get_node_or_null("GiftMarker") as TextureButton
			if gift_marker != null:
				var gift_enabled: bool = bool(actor.get_meta("giftEnabled", true))
				gift_marker.disabled = not (is_near and gift_enabled)
				gift_marker.modulate = Color(1.0, 1.0, 1.0, 1.0 if is_near and gift_enabled else 0.34)
	_rebuild_map_context_candidates()
	if map_context_candidates.is_empty():
		var fallback_hint := "WASD 连续移动；点击当前场景空地可设置落点"
		if not nearest_interactable_id.is_empty():
			fallback_hint = "已靠近交互体：%s，等待后端动作开放。" % nearest_interactable_id
		elif not nearest_anchor_id.is_empty():
			fallback_hint = "已靠近锚点：%s（%s）" % [nearest_anchor_id, nearest_anchor_kind]
		elif not nearest_event_title.is_empty():
			fallback_hint = "已靠近事件：%s，点击事件标记查看细节" % nearest_event_title
		elif not nearest_npc_name.is_empty():
			fallback_hint = "已靠近居民：%s，可点小人或聊天 / 送礼标记" % nearest_npc_name
		_update_map_hint(fallback_hint)
	if map_hint_label != null and map_hint_label.get_parent() == map_character_layer:
		map_character_layer.move_child(map_hint_label, map_character_layer.get_child_count() - 1)


func _render_locations() -> void:
	_clear_column(location_list)
	for location in world_sync.get_locations():
		var location_id := str(location.get("id", "unknown"))
		var location_name: String = str(location.get("name", location_id))
		var has_visual: bool = asset_registry.has_location_background(location_id)
		var current_marker: String = "（当前）" if location_id == selected_location_id else ""
		var button := Button.new()
		button.text = "%s%s\n%s" % [location_name, current_marker, location_id]
		button.disabled = not has_visual or location_id == selected_location_id
		button.tooltip_text = ("移动到 %s" % location_name) if has_visual else "首版暂未接入该地点背景"
		_style_button(button)
		button.pressed.connect(_on_location_pressed.bind(location_id))
		location_list.add_child(button)


func _render_scene_actions() -> void:
	if scene_action_list == null:
		return
	_clear_column(scene_action_list)
	var player: Dictionary = world_sync.get_player()
	var player_anchor: Dictionary = world_sync.get_player_anchor()
	var anchor_id := str(player.get("anchorId", ""))
	var anchor_kind := str(player_anchor.get("kind", "场景锚点")) if not player_anchor.is_empty() else "场景锚点"
	var action_budget := int(world_sync.current_state.get("clock", {}).get("actionBudget", 0))
	var summary := Label.new()
	summary.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	summary.text = "当前位置：%s · %s\n行动预算：%d\n地图主交互：靠近目标后按 E/Space 执行，Tab/Q 切换候选。" % [_anchor_kind_label(anchor_kind), anchor_id, action_budget]
	_style_body_label(summary, 14)
	scene_action_list.add_child(summary)

	if map_context_candidates.is_empty():
		var empty_hint := Label.new()
		empty_hint.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		empty_hint.text = "当前附近没有候选动作。可先移动到锚点、事件或居民附近。"
		_style_body_label(empty_hint, 14)
		scene_action_list.add_child(empty_hint)
	else:
		var fallback_title := Label.new()
		fallback_title.text = "调试兜底按钮（与地图候选同步）"
		_style_section_label(fallback_title, 15)
		scene_action_list.add_child(fallback_title)
		for index in range(map_context_candidates.size()):
			var candidate: Dictionary = map_context_candidates[index]
			var interaction = candidate.get("interaction", {})
			if not (interaction is Dictionary):
				continue
			var interaction_data: Dictionary = interaction
			var button := Button.new()
			var prefix := "▶ " if index == map_context_selected_index else ""
			button.text = "%s%s" % [prefix, str(candidate.get("label", "动作"))]
			button.tooltip_text = "地图上下文候选；可用快捷键 E/Space 执行，Tab/Q 切换。"
			button.disabled = not bool(candidate.get("enabled", false))
			if button.disabled:
				button.tooltip_text = str(candidate.get("reason", "后端暂未开放该动作"))
			_style_button(button)
			button.pressed.connect(_on_scene_fallback_interaction_pressed.bind(str(interaction_data.get("id", ""))))
			scene_action_list.add_child(button)

	var end_phase_interaction: Dictionary = world_sync.find_interaction_by_id("end_phase")
	var end_phase_button := Button.new()
	end_phase_button.text = "结束当前时段（兜底）"
	end_phase_button.disabled = not end_phase_interaction.is_empty() and not _is_interaction_enabled(end_phase_interaction)
	_style_button(end_phase_button)
	end_phase_button.pressed.connect(_on_end_phase_pressed)
	scene_action_list.add_child(end_phase_button)


func _render_npcs() -> void:
	_clear_column(npc_list)
	for npc in world_sync.get_npcs():
		var npc_id := str(npc.get("id", "unknown"))
		if not asset_registry.has_portrait(npc_id, selected_expression):
			continue
		var selected_marker: String = "（选中）" if npc_id == selected_npc_id else ""
		var button := Button.new()
		button.text = "%s%s · %s\n%s" % [
			npc.get("name", npc_id),
			selected_marker,
			npc.get("job", "居民"),
			_get_location_name(str(npc.get("locationId", "unknown")))
		]
		_style_button(button)
		button.pressed.connect(_on_npc_pressed.bind(npc_id))
		npc_list.add_child(button)


func _render_events() -> void:
	_clear_column(event_list)
	var active_events: Array = world_sync.get_active_events()
	if active_events.is_empty():
		var empty_item := Label.new()
		empty_item.text = "当前无进行中事件"
		_style_body_label(empty_item)
		event_list.add_child(empty_item)
	else:
		for event_data in active_events:
			var event_id := str(event_data.get("id", ""))
			var event_location := str(event_data.get("locationId", selected_location_id))
			var event_title := str(event_data.get("title", event_id))
			var event_status := str(event_data.get("status", "unknown"))
			var event_box := VBoxContainer.new()
			event_box.add_theme_constant_override("separation", _scaled_int(5))
			event_list.add_child(event_box)

			var header := Label.new()
			header.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
			header.text = "%s（%s）" % [event_title, event_status]
			_style_section_label(header, 16)
			event_box.add_child(header)

			var summary := Label.new()
			summary.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
			summary.text = str(event_data.get("summary", ""))
			_style_body_label(summary, 14)
			event_box.add_child(summary)

			var inspect_button := Button.new()
			inspect_button.text = "查看事件"
			inspect_button.disabled = event_id.is_empty()
			_style_button(inspect_button)
			inspect_button.pressed.connect(_on_inspect_event_pressed.bind(event_id, event_location))
			event_box.add_child(inspect_button)

	var history_title := Label.new()
	history_title.text = "最近事件日志"
	_style_section_label(history_title, 16)
	event_list.add_child(history_title)

	var history: Array = world_sync.get_recent_events().duplicate()
	history = history.slice(max(0, history.size() - 5))
	history.reverse()
	if history.is_empty():
		var history_empty := Label.new()
		history_empty.text = "暂无日志"
		_style_body_label(history_empty, 14)
		event_list.add_child(history_empty)
		return
	for event in history:
		var item := Label.new()
		item.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		var payload: Dictionary = event.get("payload", {})
		item.text = "%s\n%s" % [event.get("type", "event"), payload.get("summary", payload.get("message", payload.get("speech", "")))]
		_style_body_label(item, 14)
		event_list.add_child(item)


func _render_focus_visual() -> void:
	if selected_event_id.is_empty():
		_render_portrait(_find_npc(selected_npc_id))
		return
	var event_texture: Texture2D = asset_registry.get_event_cg(selected_event_id)
	if event_texture == null:
		_render_portrait(_find_npc(selected_npc_id))
		return
	portrait_rect.texture = event_texture


func _render_inspect_result(inspect_payload: Dictionary) -> void:
	var title := str(inspect_payload.get("title", selected_event_id))
	var summary := str(inspect_payload.get("summary", "暂无事件描述。"))
	var location_name := _get_location_name(str(inspect_payload.get("locationId", selected_event_location_id)))
	var event_status := str(inspect_payload.get("status", "available"))
	speaker_label.text = "事件 · %s" % title
	dialogue_label.text = "%s\n地点：%s\n状态：%s\n\n%s" % [title, location_name, event_status, summary]
	if event_status == "resolved":
		dialogue_label.text += "\n\n事件已结算，不能再次提交选择。"
		_render_event_choice_buttons([])
	else:
		_render_event_choice_buttons(inspect_payload.get("choices", []))
	_render_focus_visual()


func _render_event_choice_buttons(choices: Array) -> void:
	if event_choice_list == null:
		return
	_clear_column(event_choice_list)
	if selected_event_id.is_empty() or choices.is_empty():
		var empty_hint := Label.new()
		empty_hint.text = "当前事件没有可提交选项。"
		_style_body_label(empty_hint, 14)
		event_choice_list.add_child(empty_hint)
		return
	for choice_data in choices:
		var choice_id := str(choice_data.get("id", ""))
		var choice_label := str(choice_data.get("label", choice_id))
		var interaction: Dictionary = world_sync.find_event_choice_interaction(selected_event_id, choice_id)
		var button := Button.new()
		button.text = choice_label
		button.disabled = choice_id.is_empty() or (not interaction.is_empty() and not _is_interaction_enabled(interaction))
		_style_button(button)
		button.pressed.connect(_on_attend_event_choice_pressed.bind(selected_event_id, selected_event_location_id, choice_id))
		event_choice_list.add_child(button)


func _render_social_action_result(action_label: String, result: Dictionary) -> void:
	var lines: Array[String] = []
	var dialogue: Array = result.get("dialogue", [])
	if not dialogue.is_empty():
		var first_line: Dictionary = dialogue[0]
		lines.append(str(first_line.get("text", first_line.get("speech", "对方轻轻点头。"))))
		speaker_label.text = "%s · %s" % [action_label, first_line.get("speakerName", first_line.get("speakerId", selected_npc_id))]
	else:
		lines.append("动作已提交。")
		speaker_label.text = action_label
	var relationship_deltas: Array = result.get("relationshipDeltas", [])
	if not relationship_deltas.is_empty():
		lines.append("\n关系变化：")
		for delta in relationship_deltas:
			var change: Dictionary = delta.get("delta", {})
			lines.append(
				"- %s 亲密%+d / 信任%+d / 冲突%+d"
				% [
					delta.get("targetName", delta.get("targetId", "未知角色")),
					int(change.get("affection", 0)),
					int(change.get("trust", 0)),
					int(change.get("conflict", 0)),
				]
			)
	var memory_writes: Array = result.get("memoryWrites", [])
	if not memory_writes.is_empty():
		lines.append("\n记忆写入：")
		for memory in memory_writes.slice(0, 3):
			if memory is Dictionary:
				lines.append("- %s：%s" % [memory.get("agentName", memory.get("agentId", "系统")), memory.get("text", "")])
	dialogue_label.text = "\n".join(lines)


func _render_action_feedback_result(action_label: String, result: Dictionary) -> void:
	var feedback = result.get("actionFeedback", {})
	var lines: Array[String] = []
	if feedback is Dictionary and not feedback.is_empty():
		var feedback_data: Dictionary = feedback
		var title := str(feedback_data.get("title", action_label))
		var summary := str(feedback_data.get("summary", "动作已提交。"))
		speaker_label.text = "行动反馈 · %s" % title
		lines.append(summary)
		var location_name := _get_location_name(str(feedback_data.get("locationId", selected_location_id)))
		var anchor_id := str(feedback_data.get("anchorId", ""))
		if not anchor_id.is_empty():
			lines.append("位置：%s · %s" % [location_name, anchor_id])
		var changed_resources: Array = feedback_data.get("changedResources", [])
		if not changed_resources.is_empty():
			lines.append("\n变化：")
			for change in changed_resources.slice(0, 5):
				if change is Dictionary:
					lines.append("- %s" % _format_resource_change(change))
			if changed_resources.size() > 5:
				lines.append("- 还有 %d 条变化已写入后端事件。" % (changed_resources.size() - 5))
	else:
		var dialogue: Array = result.get("dialogue", [])
		if not dialogue.is_empty() and dialogue[0] is Dictionary:
			var first_line: Dictionary = dialogue[0]
			lines.append(str(first_line.get("text", "动作已提交。")))
		else:
			lines.append("动作已提交。")
		speaker_label.text = "行动反馈 · %s" % action_label

	var clock_transition = result.get("clockTransition", {})
	if clock_transition is Dictionary and not clock_transition.is_empty():
		var transition: Dictionary = clock_transition
		lines.append("\n时段：%s → %s；新预算：%s" % [
			transition.get("fromPhase", "?"),
			transition.get("toPhase", "?"),
			transition.get("actionBudget", "?"),
		])
	dialogue_label.text = "\n".join(lines)


func _render_attend_result(result: Dictionary) -> void:
	var lines: Array[String] = []
	var event_result: Dictionary = result.get("eventResult", {})
	if not event_result.is_empty():
		lines.append("事件结果：%s" % str(event_result.get("summary", "")))
	var dialogue: Array = result.get("dialogue", [])
	if not dialogue.is_empty():
		lines.append("NPC 台词：")
		for item in dialogue:
			lines.append("- %s：%s" % [item.get("speakerName", item.get("speakerId", "未知角色")), item.get("text", "")])
	var relationship_deltas: Array = result.get("relationshipDeltas", [])
	if not relationship_deltas.is_empty():
		lines.append("关系变化：")
		for delta in relationship_deltas:
			var change: Dictionary = delta.get("delta", {})
			lines.append(
				"- %s 亲密%+d / 信任%+d / 冲突%+d"
				% [
					delta.get("targetName", delta.get("targetId", "未知角色")),
					int(change.get("affection", 0)),
					int(change.get("trust", 0)),
					int(change.get("conflict", 0)),
				]
			)
	var memory_writes: Array = result.get("memoryWrites", [])
	var immediate_memories: Array = []
	var night_reflections: Array = []
	for memory in memory_writes:
		if not (memory is Dictionary):
			continue
		if _memory_has_tag(memory, "night_reflection"):
			night_reflections.append(memory)
		else:
			immediate_memories.append(memory)
	if not immediate_memories.is_empty():
		lines.append("记忆写入：")
		for memory in immediate_memories:
			lines.append("- %s：%s" % [memory.get("agentName", memory.get("agentId", "系统")), memory.get("text", "")])
	if not night_reflections.is_empty():
		lines.append("夜间反思摘要：")
		for memory in night_reflections:
			lines.append("- %s：%s" % [memory.get("agentName", memory.get("agentId", "系统")), memory.get("text", "")])
	if lines.is_empty():
		lines.append("事件提交完成。")
	dialogue_label.text = "\n".join(lines)
	speaker_label.text = "事件结算回执"
	_clear_event_focus()


func _clear_event_focus() -> void:
	selected_event_id = ""
	selected_event_location_id = ""
	_render_event_choice_buttons([])


func _sync_event_focus_with_world() -> void:
	if selected_event_id.is_empty():
		return
	var current_event: Dictionary = world_sync.find_active_event(selected_event_id)
	if current_event.is_empty():
		_clear_event_focus()


func _memory_has_tag(memory: Dictionary, target_tag: String) -> bool:
	var tags: Array = memory.get("tags", [])
	for tag in tags:
		if str(tag) == target_tag:
			return true
	return false


func _render_portrait(npc: Dictionary) -> void:
	if npc.is_empty():
		portrait_rect.texture = asset_registry.get_portrait("player", selected_expression)
		speaker_label.text = "新来的农场主"
		return
	var npc_id := str(npc.get("id", selected_npc_id))
	var texture: Texture2D = asset_registry.get_portrait(npc_id, selected_expression)
	portrait_rect.texture = texture
	speaker_label.text = "%s · %s" % [npc.get("name", npc_id), npc.get("job", "居民")]


func _select_npc(npc_id: String, clear_event: bool) -> void:
	if clear_event:
		_clear_event_focus()
	selected_npc_id = npc_id
	var npc := _find_npc(npc_id)
	if npc.is_empty():
		return
	_render_portrait(npc)


func _ensure_selected_npc() -> void:
	var selected_npc := _find_npc(selected_npc_id)
	if not selected_npc.is_empty() and asset_registry.has_portrait(selected_npc_id, selected_expression):
		return
	for npc in world_sync.get_npcs():
		var npc_id := str(npc.get("id", ""))
		if asset_registry.has_portrait(npc_id, selected_expression):
			selected_npc_id = npc_id
			return
	selected_npc_id = ""


func _show_selected_npc_hint() -> void:
	var npc := _find_npc(selected_npc_id)
	if npc.is_empty():
		dialogue_label.text = "后端已同步，但当前没有可交互居民。"
		return
	dialogue_label.text = "%s 正在 %s。点击地图小人会直接聊天，也可以使用 marker 快速聊天或送礼。" % [
		npc.get("name", selected_npc_id),
		_get_location_name(str(npc.get("locationId", "unknown")))
	]


func _find_npc(npc_id: String) -> Dictionary:
	for npc in world_sync.get_npcs():
		if str(npc.get("id", "")) == npc_id:
			return npc
	return {}


func _find_location(location_id: String) -> Dictionary:
	for location in world_sync.get_locations():
		if str(location.get("id", "")) == location_id:
			return location
	return {}


func _get_location_name(location_id: String) -> String:
	var location := _find_location(location_id)
	if not location.is_empty():
		return str(location.get("name", location_id))
	return location_id


func _anchor_kind_label(kind: String) -> String:
	var labels := {
		"entry": "入口",
		"farm_field": "田地",
		"social_spot": "社交点",
		"market_spot": "市集",
		"event_spot": "舞台",
		"service_spot": "服务点",
	}
	return str(labels.get(kind, kind if not kind.is_empty() else "锚点"))


func _anchor_display_label(anchor: Dictionary) -> String:
	var kind := _anchor_kind_label(str(anchor.get("kind", "")))
	var anchor_id := str(anchor.get("id", ""))
	if anchor_id.is_empty():
		return kind
	if anchor_id.ends_with("_door") or anchor_id.ends_with("_gate"):
		return kind
	return "%s" % kind


func _scene_action_short_label(interaction: Dictionary) -> String:
	var label := str(interaction.get("label", "行动"))
	label = label.replace("farm_plot_01", "1号田")
	label = label.replace("farm_plot_02", "2号田")
	return label


func _interactable_display_label(interactable: Dictionary) -> String:
	var interactable_id := str(interactable.get("id", ""))
	var kind := str(interactable.get("kind", "interactable"))
	if kind == "farm_plot":
		return interactable_id.replace("farm_plot_", "田块 ")
	if kind == "notice_board":
		return "公告板"
	if kind == "event_marker":
		return "事件点"
	return interactable_id if not interactable_id.is_empty() else kind


func _safe_node_suffix(raw: String) -> String:
	return raw.replace(":", "_").replace("/", "_").replace(" ", "_")


func _format_resource_change(change: Dictionary) -> String:
	var resource_type := str(change.get("resourceType", "resource"))
	var resource_id := str(change.get("resourceId", ""))
	var prefix := "%s" % resource_type
	if not resource_id.is_empty():
		prefix = "%s %s" % [resource_type, resource_id]
	if change.has("delta"):
		return "%s：%s" % [prefix, _format_value_brief(change.get("delta"))]
	return "%s：%s → %s" % [prefix, _format_value_brief(change.get("before")), _format_value_brief(change.get("after"))]


func _format_value_brief(value) -> String:
	if value is Dictionary:
		var data: Dictionary = value
		if data.has("stage"):
			var crop_id := str(data.get("cropId", ""))
			return "%s%s" % [data.get("stage", "?"), (" / %s" % crop_id) if not crop_id.is_empty() and crop_id != "<null>" else ""]
		if data.has("locationId") or data.has("anchorId"):
			return "%s@%s" % [data.get("locationId", "?"), data.get("anchorId", "?")]
		return JSON.stringify(data)
	if value is Array:
		var parts: Array[String] = []
		for item in value:
			if item is Dictionary:
				var item_data: Dictionary = item
				parts.append("%s %+d" % [item_data.get("itemId", "item"), int(item_data.get("delta", 0))])
			else:
				parts.append(str(item))
		return "，".join(parts)
	return str(value)


func _interaction_payload_or_fallback(action_type: String, target_kind: String, target_id: String, fallback: Dictionary) -> Dictionary:
	var interaction: Dictionary = world_sync.find_interaction(action_type, target_kind, target_id)
	var payload := _payload_from_interaction(interaction)
	if not payload.is_empty():
		return payload
	return fallback.duplicate(true)


func _payload_from_interaction(interaction: Dictionary) -> Dictionary:
	if interaction.is_empty():
		return {}
	var payload = interaction.get("payload", {})
	if payload is Dictionary:
		var payload_data: Dictionary = payload
		return payload_data.duplicate(true)
	return {}


func _is_interaction_enabled(interaction: Dictionary) -> bool:
	if interaction.is_empty():
		return false
	return interaction.get("enabled", true) != false


func _is_interaction_enabled_or_missing(interaction: Dictionary) -> bool:
	if interaction.is_empty():
		return true
	return _is_interaction_enabled(interaction)


func _interaction_reason(interaction: Dictionary) -> String:
	var reason := str(interaction.get("reason", ""))
	if reason.is_empty():
		return "后端暂未开放该动作"
	return reason


func _first_gift_item_id() -> String:
	var player: Dictionary = world_sync.get_player()
	var inventory: Array = player.get("inventory", [])
	var fallback_id := ""
	for item in inventory:
		if not (item is Dictionary):
			continue
		if int(item.get("quantity", 0)) <= 0:
			continue
		var tags: Array = item.get("tags", [])
		if not tags.has("gift"):
			continue
		var item_id := str(item.get("id", ""))
		if item_id.is_empty():
			continue
		if item_id != "fresh_turnip":
			return item_id
		if fallback_id.is_empty():
			fallback_id = item_id
	return fallback_id


func _is_action_response_ok(response: Dictionary) -> bool:
	if not response.get("ok", false):
		return false
	var data: Dictionary = response.get("data", {})
	return data.get("ok", false) and data.has("state")


func _response_error(response: Dictionary) -> String:
	if not response.get("ok", false):
		return str(response.get("error", "unknown"))
	var data: Dictionary = response.get("data", {})
	return str(data.get("error", "unknown"))


func _clear_column(column: VBoxContainer) -> void:
	for child in column.get_children():
		child.queue_free()


func _clear_control_children(node: Control) -> void:
	for child in node.get_children():
		# 立即移出父节点，避免同帧重绘时旧名字占位导致新玩家节点被自动改名。
		node.remove_child(child)
		child.queue_free()


func _set_status(text: String) -> void:
	if status_label != null:
		status_label.text = text
