class_name TopBanner
extends CanvasLayer

# 顶部居中横幅：三块拼合
#   - 左块：当前 stage（Farm / Plaza / Tavern）
#   - 中块：玩家操作提示（取代旧 WorldHint）
#   - 右块：远处事件指引（取代旧 RemoteEventCompass）
#
# TownMap 通过 set_stage / set_hint / set_remote_event 推数据。

const ResearchThemeScript := preload("res://scripts/ui/research_theme.gd")

var _panel: PanelContainer
var _stage_label: Label
var _hint_label: Label
var _remote_event_label: Label
var _remote_separator: Control


func _ready() -> void:
	layer = 18
	_build_panel()
	set_stage("")
	set_hint("WASD / Arrow 移动，靠近 NPC 后按 E 聊天", false)
	set_remote_event("")


func set_stage(stage_text: String) -> void:
	if _stage_label == null:
		return
	_stage_label.text = stage_text if stage_text != "" else "—"


func set_hint(text: String, highlight: bool) -> void:
	if _hint_label == null:
		return
	_hint_label.text = text
	var color := ResearchThemeScript.COLOR_TEXT_TITLE if highlight else ResearchThemeScript.COLOR_TEXT_PRIMARY
	_hint_label.add_theme_color_override("font_color", color)


func set_remote_event(text: String) -> void:
	if _remote_event_label == null:
		return
	var trimmed := text.strip_edges()
	_remote_event_label.text = trimmed
	_remote_event_label.visible = trimmed != ""
	if _remote_separator != null:
		_remote_separator.visible = trimmed != ""


func _build_panel() -> void:
	_panel = PanelContainer.new()
	_panel.name = "TopBannerPanel"
	# 横幅居中：宽 980px，留出左右 HUD / 占位空间。
	_panel.anchor_left = 0.5
	_panel.anchor_top = 0.0
	_panel.anchor_right = 0.5
	_panel.anchor_bottom = 0.0
	_panel.offset_left = -490.0
	_panel.offset_top = 16.0
	_panel.offset_right = 490.0
	_panel.offset_bottom = 70.0
	_panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_panel.add_theme_stylebox_override("panel", ResearchThemeScript.make_panel_style())
	add_child(_panel)

	var margin := MarginContainer.new()
	margin.add_theme_constant_override("margin_left", 16)
	margin.add_theme_constant_override("margin_right", 16)
	margin.add_theme_constant_override("margin_top", 6)
	margin.add_theme_constant_override("margin_bottom", 6)
	margin.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_panel.add_child(margin)

	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 12)
	row.alignment = BoxContainer.ALIGNMENT_BEGIN
	margin.add_child(row)

	_stage_label = Label.new()
	_stage_label.custom_minimum_size = Vector2(180, 0)
	ResearchThemeScript.apply_label_style(
		_stage_label,
		ResearchThemeScript.FONT_SIZE_SUBTITLE,
		ResearchThemeScript.COLOR_ACCENT
	)
	row.add_child(_stage_label)

	row.add_child(_make_vertical_separator())

	_hint_label = Label.new()
	_hint_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_hint_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_hint_label.clip_text = true
	ResearchThemeScript.apply_label_style(
		_hint_label,
		ResearchThemeScript.FONT_SIZE_BODY,
		ResearchThemeScript.COLOR_TEXT_PRIMARY
	)
	row.add_child(_hint_label)

	_remote_separator = _make_vertical_separator()
	row.add_child(_remote_separator)

	_remote_event_label = Label.new()
	_remote_event_label.custom_minimum_size = Vector2(260, 0)
	_remote_event_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	_remote_event_label.clip_text = true
	ResearchThemeScript.apply_label_style(
		_remote_event_label,
		ResearchThemeScript.FONT_SIZE_BODY,
		ResearchThemeScript.COLOR_TYPE_INTERRUPT
	)
	row.add_child(_remote_event_label)


func _make_vertical_separator() -> Control:
	var separator := ColorRect.new()
	separator.color = ResearchThemeScript.COLOR_BORDER_SOFT
	separator.custom_minimum_size = Vector2(1, 26)
	separator.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return separator
