class_name NpcController
extends Node2D

enum NpcState {
	IDLE,
	WALKING,
	PERFORMING,
}

const MOVE_EPSILON := 2.0
const SPRITE_SCALE := 1.35
const OBSERVER_HIGHLIGHT_PULSE_SPEED := 7.5

@export var npc_id: String = ""
@export var move_speed_pixels: float = 120.0

var current_state: NpcState = NpcState.IDLE
var current_anchor_id: String = ""
var target_anchor_id: String = ""
var anchor_graph: Dictionary = {}
var anchor_positions: Dictionary = {}
var move_target: Vector2 = Vector2.ZERO

var _display_name: String = ""
var _accent_color: Color = Color(1.0, 1.0, 1.0, 1.0)
var _base_visual_modulate: Color = Color(1.0, 1.0, 1.0, 1.0)
var _observer_highlight_until_msec := 0
var _observer_highlight_color: Color = Color(1.0, 0.92, 0.28, 1.0)
var _crowd_offset: Vector2 = Vector2.ZERO
var _pending_texture: Texture2D
var _visual_root: Node2D
var _observer_highlight: ColorRect
var _sprite: Sprite2D
var _shadow: ColorRect
var _fallback_body: ColorRect
var _intent_label: Label
var _name_label: Label
var _action_label: Label
var _player_nearby: bool = false
var _current_action_text: String = ""


func _ready() -> void:
	# 小地图优先显示真实 sprite，fallback 方块只用于定位缺图问题。
	z_index = 10
	_visual_root = Node2D.new()
	_visual_root.name = "VisualRoot"
	add_child(_visual_root)

	_observer_highlight = ColorRect.new()
	_observer_highlight.name = "ObserverHighlight"
	_observer_highlight.color = Color(1.0, 0.92, 0.28, 0.0)
	_observer_highlight.size = Vector2(78.0, 92.0)
	_observer_highlight.position = Vector2(-39.0, -88.0)
	_observer_highlight.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_observer_highlight.visible = false
	_visual_root.add_child(_observer_highlight)

	_shadow = ColorRect.new()
	_shadow.name = "GroundShadow"
	_shadow.color = Color(0.0, 0.0, 0.0, 0.28)
	_shadow.size = Vector2(56.0, 12.0)
	_shadow.position = Vector2(-28.0, -6.0)
	add_child(_shadow)

	_sprite = Sprite2D.new()
	_sprite.name = "MapSprite"
	_sprite.position = Vector2(0.0, -43.0)
	_sprite.scale = Vector2(SPRITE_SCALE, SPRITE_SCALE)
	_visual_root.add_child(_sprite)

	_fallback_body = ColorRect.new()
	_fallback_body.name = "FallbackBody"
	_fallback_body.color = _accent_color
	_fallback_body.size = Vector2(40.0, 58.0)
	_fallback_body.position = Vector2(-20.0, -72.0)
	_visual_root.add_child(_fallback_body)

	# 旧 IntentLabel 已迁移到 Research Dock Inspector Tab，这里保持节点存在但隐藏，
	# 避免破坏 set_intent_status 调用链。
	_intent_label = _make_label("IntentLabel", "", Vector2(-84.0, -150.0), 168.0, 12)
	_intent_label.visible = false
	add_child(_intent_label)

	_name_label = _make_label("NameLabel", _display_name if _display_name != "" else npc_id, Vector2(-72.0, -120.0), 144.0, 13)
	add_child(_name_label)

	_action_label = _make_label("ActionLabel", "Idle", Vector2(-74.0, -98.0), 148.0, 11)
	_action_label.visible = false
	_action_label.add_theme_color_override("font_color", Color(0.93, 0.96, 1.0, 0.92))
	add_child(_action_label)
	_apply_pending_texture()
	_enter_state(NpcState.IDLE, "Idle")
	_apply_label_visibility()


func _process(delta: float) -> void:
	_update_observer_highlight()
	_update_idle_bobbing()
	if current_state != NpcState.WALKING:
		return

	var to_target := move_target - global_position
	if to_target.length() <= MOVE_EPSILON:
		global_position = move_target
		_enter_state(NpcState.IDLE, "Idle")
		return

	var step: float = minf(to_target.length(), move_speed_pixels * delta)
	global_position += to_target.normalized() * step


func configure_anchor_graph(graph: Dictionary, positions: Dictionary) -> void:
	# graph: {"anchor_a": ["anchor_b", ...]}，positions: {"anchor_a": Vector2(...)}。
	anchor_graph = graph.duplicate(true)
	anchor_positions = positions.duplicate(true)


func configure_appearance(display_name: String, texture: Texture2D, accent_color: Color) -> void:
	_display_name = display_name
	_pending_texture = texture
	_accent_color = accent_color
	if _name_label != null:
		_name_label.text = display_name
	if _fallback_body != null:
		_fallback_body.color = accent_color
	_apply_pending_texture()


func set_crowd_offset(offset: Vector2) -> void:
	# 同一锚点允许多个 NPC 站位，表现层加小偏移避免名字和 sprite 完全重叠。
	_crowd_offset = offset


func set_intent_status(text: String) -> void:
	# intent 文本只保留为数据缓存供其它系统读取；头顶展示已移除。
	if _intent_label == null:
		return
	_intent_label.text = _short_label_text(text.strip_edges(), 30)


func set_action_status(text: String) -> void:
	var trimmed := text.strip_edges()
	if trimmed == "":
		return
	_current_action_text = _short_label_text(trimmed, 28)
	_apply_label_visibility()


func set_player_nearby(is_near: bool) -> void:
	if _player_nearby == is_near:
		return
	_player_nearby = is_near
	_apply_label_visibility()


func _apply_label_visibility() -> void:
	if _action_label != null:
		_action_label.text = _current_action_text if _current_action_text != "" else "Idle"
		_action_label.visible = _player_nearby and _current_action_text != ""


func flash_observer_highlight(duration_msec: int = 2200, highlight_color: Color = Color(1.0, 0.92, 0.28, 1.0)) -> void:
	# ObserverPanel trace 点击会短暂点亮对应 NPC，帮助人工核对 agentId / observerScope。
	_observer_highlight_color = highlight_color
	_observer_highlight_until_msec = Time.get_ticks_msec() + duration_msec
	if _observer_highlight != null:
		_observer_highlight.visible = true
	_apply_visual_modulate()


func apply_tick_event(event_payload: Dictionary) -> void:
	var event_type := str(event_payload.get("type", ""))
	if event_type == "npc.move_started":
		_handle_move_started(event_payload)
		return
	if event_type == "npc.move_progress":
		_handle_move_progress(event_payload)
		return
	if event_type == "npc.arrived":
		_handle_arrived(event_payload)
		return
	if event_type == "npc.action_started":
		_enter_state(NpcState.PERFORMING, _action_label_from_event(event_payload, "Performing"))
		return
	if event_type == "npc.action_completed":
		_enter_state(NpcState.IDLE, "Idle")


func set_anchor_position(anchor_id: String) -> void:
	var point = _anchor_point_with_offset(anchor_id)
	if point is Vector2:
		current_anchor_id = anchor_id
		target_anchor_id = anchor_id
		global_position = point


func _handle_move_started(event_payload: Dictionary) -> void:
	var from_anchor := str(event_payload.get("fromAnchorId", event_payload.get("from", "")))
	var to_anchor := str(event_payload.get("toAnchorId", event_payload.get("to", "")))
	if from_anchor != "":
		set_anchor_position(from_anchor)
	if to_anchor == "":
		return
	_target_anchor_move(to_anchor)


func _handle_move_progress(event_payload: Dictionary) -> void:
	# 后端当前直接下发起点和终点，优先用 progress 还原 NPC 的权威位置。
	var position_payload = event_payload.get("position", null)
	if position_payload is Dictionary:
		var x := float(position_payload.get("x", global_position.x))
		var y := float(position_payload.get("y", global_position.y))
		global_position = Vector2(x, y)
		_enter_state(NpcState.WALKING, _move_label(event_payload))
		return

	var progress := float(event_payload.get("progress", -1.0))
	if progress < 0.0:
		return

	var from_anchor := str(event_payload.get("fromAnchorId", current_anchor_id))
	var to_anchor := str(event_payload.get("toAnchorId", target_anchor_id))
	var from_point = _anchor_point_with_offset(from_anchor)
	var to_point = _anchor_point_with_offset(to_anchor)
	if from_point is Vector2 and to_point is Vector2:
		var from_vec: Vector2 = from_point
		var to_vec: Vector2 = to_point
		global_position = from_vec.lerp(to_vec, clamp(progress, 0.0, 1.0))
		_enter_state(NpcState.WALKING, _move_label(event_payload))


func _handle_arrived(event_payload: Dictionary) -> void:
	var arrived_anchor := str(event_payload.get("anchorId", event_payload.get("toAnchorId", target_anchor_id)))
	if arrived_anchor != "":
		set_anchor_position(arrived_anchor)
	_enter_state(NpcState.IDLE, "Idle")


func _target_anchor_move(anchor_id: String) -> void:
	var target = _anchor_point_with_offset(anchor_id)
	if not (target is Vector2):
		return
	var next_target := target as Vector2

	# move_started 到首个 progress 之间也给出本地过渡，避免视觉停顿。
	target_anchor_id = anchor_id
	move_target = next_target
	_enter_state(NpcState.WALKING, "Moving")


func _anchor_point_with_offset(anchor_id: String):
	var point = anchor_positions.get(anchor_id, null)
	if point is Vector2:
		return (point as Vector2) + _crowd_offset
	return null


func _move_label(event_payload: Dictionary) -> String:
	var progress := float(event_payload.get("progress", 0.0))
	var to_anchor := str(event_payload.get("toAnchorId", target_anchor_id))
	return "Moving -> %s %.0f%%" % [to_anchor.replace("_", " "), progress * 100.0]


func _action_label_from_event(event_payload: Dictionary, fallback_text: String) -> String:
	var action_name := str(event_payload.get("actionName", ""))
	if action_name != "":
		return action_name
	var action_id := str(event_payload.get("actionId", ""))
	if action_id != "":
		return action_id.replace("life_", "").replace("_", " ")
	return fallback_text


func _enter_state(next_state: NpcState, label_text: String) -> void:
	current_state = next_state
	_current_action_text = label_text
	_apply_label_visibility()
	match current_state:
		NpcState.IDLE:
			_set_visual_modulate(Color(1.0, 1.0, 1.0, 1.0))
		NpcState.WALKING:
			_set_visual_modulate(Color(0.82, 0.92, 1.0, 1.0))
		NpcState.PERFORMING:
			_set_visual_modulate(Color(0.88, 1.0, 0.80, 1.0))


func _set_visual_modulate(color: Color) -> void:
	_base_visual_modulate = color
	_apply_visual_modulate()


func _apply_visual_modulate() -> void:
	var final_color := _base_visual_modulate
	if _observer_highlight_until_msec > Time.get_ticks_msec():
		final_color = final_color.lerp(_observer_highlight_color, 0.36)
	if _sprite != null:
		_sprite.modulate = final_color
	if _fallback_body != null:
		_fallback_body.color = _accent_color * final_color


func _update_observer_highlight() -> void:
	if _observer_highlight == null:
		return
	var now := Time.get_ticks_msec()
	if _observer_highlight_until_msec <= now:
		if _observer_highlight.visible:
			_observer_highlight.visible = false
			_apply_visual_modulate()
		return
	var seconds := float(now) / 1000.0
	var pulse := 0.44 + sin(seconds * OBSERVER_HIGHLIGHT_PULSE_SPEED + float(abs(npc_id.hash() % 17))) * 0.16
	var color := _observer_highlight_color
	color.a = clampf(pulse, 0.24, 0.72)
	_observer_highlight.color = color


func _update_idle_bobbing() -> void:
	if _visual_root == null:
		return
	var seconds := float(Time.get_ticks_msec()) / 1000.0
	var amplitude := 4.0 if current_state == NpcState.PERFORMING else 2.4
	_visual_root.position.y = sin(seconds * 3.2 + float(abs(npc_id.hash() % 31))) * amplitude


func _apply_pending_texture() -> void:
	if _sprite == null or _fallback_body == null:
		return
	_sprite.texture = _pending_texture
	var has_texture := _pending_texture != null
	_sprite.visible = has_texture
	_fallback_body.visible = not has_texture


func _make_label(label_name: String, text: String, label_position: Vector2, width: float, font_size: int) -> Label:
	var label := Label.new()
	label.name = label_name
	label.text = text
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	label.position = label_position
	label.size = Vector2(width, 22.0)
	label.add_theme_font_size_override("font_size", font_size)
	label.add_theme_color_override("font_color", Color(1.0, 1.0, 1.0, 1.0))
	label.add_theme_color_override("font_shadow_color", Color(0.0, 0.0, 0.0, 0.9))
	label.add_theme_constant_override("shadow_offset_x", 2)
	label.add_theme_constant_override("shadow_offset_y", 2)
	return label


func _short_label_text(text: String, max_chars: int) -> String:
	if text.length() <= max_chars:
		return text
	return "%s…" % text.substr(0, max(0, max_chars - 1))
