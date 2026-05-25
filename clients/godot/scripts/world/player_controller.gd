class_name PlayerController
extends Node2D

const SPRITE_SCALE := 1.35
const MOVE_EPSILON := 0.05

@export var move_speed_pixels: float = 360.0

var _world_bounds := Rect2(Vector2.ZERO, Vector2(1920.0, 1080.0))
var _visual_root: Node2D
var _sprite: Sprite2D
var _shadow: ColorRect
var _fallback_body: ColorRect
var _name_label: Label
var _state_label: Label
var _last_axis := Vector2.DOWN


func _ready() -> void:
	# 玩家控制器只处理本地表现坐标；权威位置和交互结算仍通过后端动作提交。
	z_index = 20
	_visual_root = Node2D.new()
	_visual_root.name = "VisualRoot"
	add_child(_visual_root)

	_shadow = ColorRect.new()
	_shadow.name = "GroundShadow"
	_shadow.color = Color(0.0, 0.0, 0.0, 0.30)
	_shadow.size = Vector2(60.0, 12.0)
	_shadow.position = Vector2(-30.0, -6.0)
	add_child(_shadow)

	_sprite = Sprite2D.new()
	_sprite.name = "MapSprite"
	_sprite.position = Vector2(0.0, -44.0)
	_sprite.scale = Vector2(SPRITE_SCALE, SPRITE_SCALE)
	_visual_root.add_child(_sprite)

	_fallback_body = ColorRect.new()
	_fallback_body.name = "FallbackBody"
	_fallback_body.color = Color(0.56, 0.88, 1.0, 1.0)
	_fallback_body.size = Vector2(42.0, 60.0)
	_fallback_body.position = Vector2(-21.0, -74.0)
	_visual_root.add_child(_fallback_body)

	_name_label = _make_label("NameLabel", "Player", Vector2(-74.0, -120.0), 148.0, 13)
	add_child(_name_label)

	# 简化后只在移动时显示 "Moving" 状态，避免静止时叠一行 WASD。
	_state_label = _make_label("StateLabel", "", Vector2(-74.0, -98.0), 148.0, 11)
	_state_label.visible = false
	_state_label.add_theme_color_override("font_color", Color(0.93, 0.96, 1.0, 0.85))
	add_child(_state_label)
	_apply_motion_state(false)


func configure_appearance(display_name: String, texture: Texture2D) -> void:
	if _name_label != null:
		_name_label.text = display_name
	if _sprite != null:
		_sprite.texture = texture
	var has_texture := texture != null
	if _sprite != null:
		_sprite.visible = has_texture
	if _fallback_body != null:
		_fallback_body.visible = not has_texture


func set_world_bounds(bounds: Rect2) -> void:
	_world_bounds = bounds
	global_position = _clamp_to_world(global_position)


func set_spawn_position(spawn_position: Vector2) -> void:
	global_position = _clamp_to_world(spawn_position)


func interaction_origin() -> Vector2:
	return global_position


func _process(delta: float) -> void:
	var axis := _read_move_axis()
	if axis.length() > MOVE_EPSILON:
		axis = axis.normalized()
		_last_axis = axis
		global_position = _clamp_to_world(global_position + axis * move_speed_pixels * delta)
		_apply_motion_state(true)
		return
	_apply_motion_state(false)


func _read_move_axis() -> Vector2:
	var axis := Vector2.ZERO
	if Input.is_key_pressed(KEY_A) or Input.is_key_pressed(KEY_LEFT):
		axis.x -= 1.0
	if Input.is_key_pressed(KEY_D) or Input.is_key_pressed(KEY_RIGHT):
		axis.x += 1.0
	if Input.is_key_pressed(KEY_W) or Input.is_key_pressed(KEY_UP):
		axis.y -= 1.0
	if Input.is_key_pressed(KEY_S) or Input.is_key_pressed(KEY_DOWN):
		axis.y += 1.0
	return axis


func _apply_motion_state(is_moving: bool) -> void:
	if _state_label != null:
		_state_label.text = "Moving" if is_moving else "Idle"
		_state_label.visible = is_moving
	if _sprite != null:
		_sprite.modulate = Color(0.80, 0.94, 1.0, 1.0) if is_moving else Color(1.0, 1.0, 1.0, 1.0)
		if abs(_last_axis.x) > 0.1:
			_sprite.flip_h = _last_axis.x < 0.0
	if _fallback_body != null:
		_fallback_body.color = Color(0.48, 0.78, 1.0, 1.0) if is_moving else Color(0.56, 0.88, 1.0, 1.0)
	if _visual_root != null:
		var seconds := float(Time.get_ticks_msec()) / 1000.0
		var amplitude := 3.5 if is_moving else 1.6
		_visual_root.position.y = sin(seconds * 5.4) * amplitude


func _clamp_to_world(point: Vector2) -> Vector2:
	return Vector2(
		clamp(point.x, _world_bounds.position.x, _world_bounds.end.x),
		clamp(point.y, _world_bounds.position.y, _world_bounds.end.y)
	)


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
	label.add_theme_color_override("font_shadow_color", Color(0.0, 0.0, 0.0, 0.92))
	label.add_theme_constant_override("shadow_offset_x", 2)
	label.add_theme_constant_override("shadow_offset_y", 2)
	return label
