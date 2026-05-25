class_name WorldVnPanel
extends CanvasLayer

const ResearchThemeScript := preload("res://scripts/ui/research_theme.gd")

var _dialogue_panel: PanelContainer
var _speaker_label: Label
var _body_label: Label
var _status_label: Label
var _hint_label: Label


func _ready() -> void:
	layer = 30
	_build_hint_label()
	_build_dialogue_panel()
	hide_dialogue()
	show_hint("WASD / Arrow 移动，靠近 NPC 后按 E 聊天", false)


func show_hint(text: String, active: bool) -> void:
	if _hint_label == null:
		return
	_hint_label.text = text
	_hint_label.add_theme_color_override("font_color", Color(1.0, 0.94, 0.58, 1.0) if active else Color(0.93, 1.0, 0.92, 0.94))


func show_busy(target_name: String) -> void:
	show_dialogue("正在连接", "向 %s 发起后端 talk 动作，等待 NPC 回复……" % target_name, "Backend talk pending")


func show_dialogue(speaker_name: String, text: String, status_text: String = "") -> void:
	if _dialogue_panel == null:
		return
	_dialogue_panel.visible = true
	_speaker_label.text = speaker_name
	_body_label.text = text
	_status_label.text = status_text


func show_error(message: String) -> void:
	show_dialogue("系统", message, "Error")


func hide_dialogue() -> void:
	if _dialogue_panel != null:
		_dialogue_panel.visible = false


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey:
		var key_event := event as InputEventKey
		if key_event.pressed and not key_event.echo and key_event.keycode == KEY_ESCAPE:
			hide_dialogue()


func _build_hint_label() -> void:
	# WorldHint 已迁移到 TopBanner；这里保留隐藏 Label 保持 show_hint API
	# 不破坏，便于其它代码（包括测试脚本）继续调用 vn_panel.show_hint。
	_hint_label = Label.new()
	_hint_label.name = "WorldHint"
	_hint_label.visible = false
	add_child(_hint_label)


func _build_dialogue_panel() -> void:
	_dialogue_panel = PanelContainer.new()
	_dialogue_panel.name = "WorldVnDialogue"
	_dialogue_panel.anchor_left = 0.08
	_dialogue_panel.anchor_top = 1.0
	_dialogue_panel.anchor_right = 0.92
	_dialogue_panel.anchor_bottom = 1.0
	_dialogue_panel.offset_top = -230.0
	_dialogue_panel.offset_bottom = -28.0
	_dialogue_panel.add_theme_stylebox_override("panel", _make_panel_style())
	add_child(_dialogue_panel)

	var margin := MarginContainer.new()
	margin.add_theme_constant_override("margin_left", 22)
	margin.add_theme_constant_override("margin_right", 22)
	margin.add_theme_constant_override("margin_top", 16)
	margin.add_theme_constant_override("margin_bottom", 16)
	_dialogue_panel.add_child(margin)

	var column := VBoxContainer.new()
	column.add_theme_constant_override("separation", 9)
	margin.add_child(column)

	_speaker_label = Label.new()
	_speaker_label.name = "Speaker"
	ResearchThemeScript.apply_label_style(_speaker_label, 22, ResearchThemeScript.COLOR_TEXT_TITLE, true)
	column.add_child(_speaker_label)

	_body_label = Label.new()
	_body_label.name = "Body"
	_body_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_body_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	ResearchThemeScript.apply_label_style(_body_label, 17, ResearchThemeScript.COLOR_TEXT_PRIMARY, true)
	column.add_child(_body_label)

	_status_label = Label.new()
	_status_label.name = "Status"
	ResearchThemeScript.apply_label_style(_status_label, 13, ResearchThemeScript.COLOR_TEXT_MUTED)
	column.add_child(_status_label)


func _make_panel_style() -> StyleBoxFlat:
	return ResearchThemeScript.make_panel_style(
		Color(0.06, 0.08, 0.11, 0.92),
		Color(0.95, 0.75, 0.32, 0.85),
		18,
		2
	)
