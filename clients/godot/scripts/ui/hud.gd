class_name WorldHud
extends CanvasLayer

# 左上 HUD：世界时钟 + 暂停 / 倍速控制。
# 比旧版多了卡片化样式（research_theme）、激活态倍速按钮、状态颜色提示，
# 与右侧 Research Dock 视觉一致。

const ResearchThemeScript := preload("res://scripts/ui/research_theme.gd")

const SPEED_OPTIONS := [1.0, 2.0, 4.0]

var _clock_label: Label
var _clock_meta_label: Label
var _status_dot: ColorRect
var _status_label: Label
var _pause_button: Button
var _speed_buttons: Array[Button] = []
var _current_speed: float = 1.0
var _is_paused: bool = false


func _ready() -> void:
	layer = 10
	_build_panel()
	_connect_bus_signals()
	_connect_clock_signals()
	_update_status_visuals()


func _build_panel() -> void:
	var panel := PanelContainer.new()
	panel.name = "HudPanel"
	panel.offset_left = 16.0
	panel.offset_top = 16.0
	panel.offset_right = 296.0
	panel.offset_bottom = 168.0
	panel.add_theme_stylebox_override("panel", ResearchThemeScript.make_panel_style())
	add_child(panel)

	var margin := MarginContainer.new()
	margin.add_theme_constant_override("margin_left", 14)
	margin.add_theme_constant_override("margin_right", 14)
	margin.add_theme_constant_override("margin_top", 10)
	margin.add_theme_constant_override("margin_bottom", 12)
	panel.add_child(margin)

	var column := VBoxContainer.new()
	column.add_theme_constant_override("separation", 6)
	margin.add_child(column)

	_clock_label = Label.new()
	_clock_label.text = "Day 1 · 00:00"
	ResearchThemeScript.apply_label_style(
		_clock_label,
		ResearchThemeScript.FONT_SIZE_TITLE,
		ResearchThemeScript.COLOR_TEXT_TITLE
	)
	column.add_child(_clock_label)

	_clock_meta_label = Label.new()
	_clock_meta_label.text = "waiting for tick"
	ResearchThemeScript.apply_label_style(
		_clock_meta_label,
		ResearchThemeScript.FONT_SIZE_SMALL,
		ResearchThemeScript.COLOR_TEXT_MUTED
	)
	column.add_child(_clock_meta_label)

	column.add_child(ResearchThemeScript.make_separator())

	var status_row := HBoxContainer.new()
	status_row.add_theme_constant_override("separation", 8)
	column.add_child(status_row)
	_status_dot = ColorRect.new()
	_status_dot.color = ResearchThemeScript.COLOR_STATUS_OK
	_status_dot.custom_minimum_size = Vector2(10, 10)
	_status_dot.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	status_row.add_child(_status_dot)
	_status_label = Label.new()
	_status_label.text = "Running · 1.0x"
	_status_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	ResearchThemeScript.apply_label_style(
		_status_label,
		ResearchThemeScript.FONT_SIZE_BODY,
		ResearchThemeScript.COLOR_TEXT_PRIMARY
	)
	status_row.add_child(_status_label)

	var control_row := HBoxContainer.new()
	control_row.add_theme_constant_override("separation", 6)
	column.add_child(control_row)

	_pause_button = Button.new()
	_pause_button.text = "⏸ 暂停"
	_pause_button.focus_mode = Control.FOCUS_NONE
	ResearchThemeScript.apply_button_style(_pause_button, ResearchThemeScript.FONT_SIZE_BODY)
	_pause_button.pressed.connect(_on_pause_pressed)
	control_row.add_child(_pause_button)

	_speed_buttons.clear()
	for speed_value in SPEED_OPTIONS:
		var btn := Button.new()
		btn.text = "%dx" % int(speed_value)
		btn.focus_mode = Control.FOCUS_NONE
		btn.toggle_mode = true
		btn.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		ResearchThemeScript.apply_button_style(btn, ResearchThemeScript.FONT_SIZE_BODY)
		btn.pressed.connect(_on_speed_pressed.bind(float(speed_value)))
		control_row.add_child(btn)
		_speed_buttons.append(btn)


func _connect_bus_signals() -> void:
	if not has_node("/root/EventBusService"):
		return
	var event_bus := get_node("/root/EventBusService") as EventBus
	if event_bus == null:
		return
	if not event_bus.tick_clock_updated.is_connected(_on_tick_clock_updated):
		event_bus.tick_clock_updated.connect(_on_tick_clock_updated)


func _connect_clock_signals() -> void:
	if not has_node("/root/WorldClockService"):
		return
	var world_clock := get_node("/root/WorldClockService") as WorldClock
	if world_clock == null:
		return
	if not world_clock.paused_changed.is_connected(_on_pause_changed):
		world_clock.paused_changed.connect(_on_pause_changed)
	if not world_clock.speed_changed.is_connected(_on_speed_changed):
		world_clock.speed_changed.connect(_on_speed_changed)
	if not world_clock.tick_failed.is_connected(_on_tick_failed):
		world_clock.tick_failed.connect(_on_tick_failed)


func _on_pause_pressed() -> void:
	if has_node("/root/WorldClockService"):
		var world_clock := get_node("/root/WorldClockService") as WorldClock
		if world_clock != null:
			world_clock.toggle_paused()


func _on_speed_pressed(next_speed: float) -> void:
	if has_node("/root/WorldClockService"):
		var world_clock := get_node("/root/WorldClockService") as WorldClock
		if world_clock != null:
			world_clock.set_speed(next_speed)


func _on_tick_clock_updated(clock: Dictionary) -> void:
	var day := int(clock.get("day", 1))
	var hour := int(clock.get("hour", 0))
	var minute := int(clock.get("minute", 0))
	var phase := str(clock.get("phase", "unknown"))
	var tick := int(clock.get("tick", 0))
	if _clock_label != null:
		_clock_label.text = "Day %d · %02d:%02d" % [day, hour, minute]
	if _clock_meta_label != null:
		_clock_meta_label.text = "%s · tick %d" % [phase, tick]


func _on_pause_changed(is_paused: bool) -> void:
	_is_paused = is_paused
	_update_status_visuals()


func _on_speed_changed(new_speed: float) -> void:
	_current_speed = new_speed
	_update_status_visuals()


func _on_tick_failed(error_message: String) -> void:
	if _status_label != null:
		_status_label.text = "Tick failed · %s" % error_message
	if _status_dot != null:
		_status_dot.color = ResearchThemeScript.COLOR_STATUS_ERROR


func _update_status_visuals() -> void:
	if _status_label != null:
		var status_text := ("Paused" if _is_paused else "Running") + " · %.1fx" % _current_speed
		_status_label.text = status_text
		var color := ResearchThemeScript.COLOR_TEXT_MUTED if _is_paused else ResearchThemeScript.COLOR_STATUS_OK
		_status_label.add_theme_color_override("font_color", ResearchThemeScript.COLOR_TEXT_PRIMARY)
		if _status_dot != null:
			_status_dot.color = color
	if _pause_button != null:
		_pause_button.text = "▶ 继续" if _is_paused else "⏸ 暂停"
	for i in range(_speed_buttons.size()):
		var button: Button = _speed_buttons[i]
		var speed_value: float = float(SPEED_OPTIONS[i])
		var active: bool = absf(speed_value - _current_speed) < 0.05
		button.button_pressed = active
		var style := ResearchThemeScript.make_tab_style(active)
		button.add_theme_stylebox_override("normal", style)
		button.add_theme_stylebox_override("pressed", style)
		button.add_theme_stylebox_override("hover", style)
