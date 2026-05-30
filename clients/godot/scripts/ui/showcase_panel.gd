class_name ShowcasePanel
extends CanvasLayer

# Showcase Mode v1：面向评审录屏的摘要层。
# 只展示固定的星灯祭因果链摘要，完整调试仍交给 Observer Dock。
const ResearchThemeScript := preload("res://scripts/ui/research_theme.gd")

signal deep_dive_requested(npc_id, event_id, trace_id)
signal refresh_requested

const SCHEMA_VERSION := "showcase.starlight.v1"
const CARD_KEYS := ["goalCard", "directorCard", "eventSkillCard", "npcDecisionCard", "traceEvidenceCard"]
const CARD_ACCENTS := [
	Color(1.0, 0.86, 0.45, 0.82),
	Color(0.36, 0.71, 1.0, 0.82),
	Color(0.80, 0.62, 1.0, 0.82),
	Color(0.40, 0.86, 0.56, 0.82),
	Color(0.98, 0.70, 0.40, 0.82),
]

var _root: Control
var _left_panel: PanelContainer
var _right_panel: PanelContainer
var _trace_panel: PanelContainer
var _scenario_title_label: Label
var _scenario_caption_label: Label
var _director_rail_box: VBoxContainer
var _cards_box: VBoxContainer
var _trace_strip_box: HBoxContainer
var _status_label: Label
var _deep_dive_button: Button
var _refresh_button: Button
var _payload: Dictionary = {}


func _ready() -> void:
	# 低于 ObserverPanel(layer=20)，确保 Deep dive / Tab 后完整调试面板可覆盖摘要层。
	layer = 18
	_build_layout()
	_render_loading_state()
	set_panel_visible(true)


func set_showcase_payload(payload: Dictionary) -> void:
	_payload = payload.duplicate(true)
	var schema_version := str(_payload.get("schemaVersion", ""))
	if schema_version != SCHEMA_VERSION:
		show_backend_error("Showcase schema 不匹配：%s" % schema_version)
		return
	_render_payload()


func show_backend_error(message: String) -> void:
	_payload = {}
	_set_header_text("Showcase Mode", "后端不可达或聚合接口返回异常；窗口保持可操作，Tab 仍可打开 Observer Dock。")
	_status_label.text = "Backend error: %s" % message
	_clear_children(_director_rail_box)
	_clear_children(_cards_box)
	_clear_children(_trace_strip_box)
	var error_card := {
		"id": "backendError",
		"kicker": "Fallback",
		"title": "等待 /api/showcase/starlight",
		"summary": "请启动 backend 后点击 Refresh；ShowcasePanel 会继续保留可读错误卡。",
		"fields": [
			{"label": "endpoint", "value": "/api/showcase/starlight"},
			{"label": "reason", "value": message},
		],
		"evidenceRefs": [],
		"status": "error",
	}
	_cards_box.add_child(_make_card(error_card, ResearchThemeScript.COLOR_STATUS_ERROR))
	_trace_strip_box.add_child(_make_trace_chip({"label": "Backend", "summary": message, "status": "error", "eventType": "error"}))


func toggle_panel_visible() -> bool:
	set_panel_visible(not bool(_root.visible))
	return bool(_root.visible)


func set_panel_visible(next_visible: bool) -> void:
	if _root == null:
		return
	_root.visible = next_visible


func is_panel_visible() -> bool:
	return _root != null and bool(_root.visible)


func _build_layout() -> void:
	_root = Control.new()
	_root.name = "ShowcaseRoot"
	_root.set_anchors_preset(Control.PRESET_FULL_RECT)
	_root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(_root)

	_left_panel = _make_panel("DirectorRail", Vector2(18.0, 126.0), Vector2(382.0, 666.0))
	_root.add_child(_left_panel)
	var left_box := _make_margin_vbox(_left_panel)
	_scenario_title_label = _make_label("Showcase Mode", ResearchThemeScript.FONT_SIZE_TITLE, ResearchThemeScript.COLOR_TEXT_TITLE)
	left_box.add_child(_scenario_title_label)
	_scenario_caption_label = _make_label("加载星灯祭演示链…", ResearchThemeScript.FONT_SIZE_SMALL, ResearchThemeScript.COLOR_TEXT_MUTED)
	_scenario_caption_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	left_box.add_child(_scenario_caption_label)
	_status_label = _make_label("F1 隐藏 / 显示；Tab 打开 Observer Dock。", ResearchThemeScript.FONT_SIZE_SMALL, ResearchThemeScript.COLOR_TEXT_MUTED)
	_status_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	left_box.add_child(_status_label)
	_add_separator(left_box)
	_director_rail_box = VBoxContainer.new()
	_director_rail_box.add_theme_constant_override("separation", int(round(ResearchThemeScript.scale_px(8.0))))
	left_box.add_child(_director_rail_box)
	var left_actions := HBoxContainer.new()
	left_actions.add_theme_constant_override("separation", int(round(ResearchThemeScript.scale_px(8.0))))
	left_box.add_child(left_actions)
	_deep_dive_button = _make_button("Deep dive")
	_deep_dive_button.pressed.connect(_on_deep_dive_pressed)
	left_actions.add_child(_deep_dive_button)
	_refresh_button = _make_button("Refresh")
	_refresh_button.pressed.connect(_on_refresh_pressed)
	left_actions.add_child(_refresh_button)

	_right_panel = PanelContainer.new()
	_right_panel.name = "CausalCards"
	_right_panel.anchor_left = 1.0
	_right_panel.anchor_right = 1.0
	_right_panel.anchor_top = 0.0
	_right_panel.anchor_bottom = 1.0
	_right_panel.offset_left = -482.0
	_right_panel.offset_right = -18.0
	_right_panel.offset_top = 94.0
	_right_panel.offset_bottom = -178.0
	_right_panel.mouse_filter = Control.MOUSE_FILTER_STOP
	_right_panel.add_theme_stylebox_override("panel", ResearchThemeScript.make_panel_style(Color(0.06, 0.08, 0.11, 0.90), ResearchThemeScript.COLOR_BORDER_SOFT))
	_root.add_child(_right_panel)
	var right_margin := MarginContainer.new()
	_right_panel.add_child(right_margin)
	var scroll := ScrollContainer.new()
	scroll.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	right_margin.add_child(scroll)
	_cards_box = VBoxContainer.new()
	_cards_box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_cards_box.add_theme_constant_override("separation", int(round(ResearchThemeScript.scale_px(10.0))))
	scroll.add_child(_cards_box)

	_trace_panel = PanelContainer.new()
	_trace_panel.name = "TraceEvidenceStrip"
	_trace_panel.anchor_left = 0.0
	_trace_panel.anchor_right = 1.0
	_trace_panel.anchor_top = 1.0
	_trace_panel.anchor_bottom = 1.0
	_trace_panel.offset_left = 244.0
	_trace_panel.offset_right = -244.0
	_trace_panel.offset_top = -152.0
	_trace_panel.offset_bottom = -18.0
	_trace_panel.mouse_filter = Control.MOUSE_FILTER_STOP
	_trace_panel.add_theme_stylebox_override("panel", ResearchThemeScript.make_panel_style(Color(0.06, 0.08, 0.11, 0.88), ResearchThemeScript.COLOR_BORDER_SOFT))
	_root.add_child(_trace_panel)
	var trace_margin := MarginContainer.new()
	_trace_panel.add_child(trace_margin)
	_trace_strip_box = HBoxContainer.new()
	_trace_strip_box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_trace_strip_box.add_theme_constant_override("separation", int(round(ResearchThemeScript.scale_px(8.0))))
	trace_margin.add_child(_trace_strip_box)


func _make_panel(node_name: String, offset_pos: Vector2, offset_size: Vector2) -> PanelContainer:
	var panel := PanelContainer.new()
	panel.name = node_name
	panel.anchor_left = 0.0
	panel.anchor_top = 0.0
	panel.anchor_right = 0.0
	panel.anchor_bottom = 0.0
	panel.offset_left = offset_pos.x
	panel.offset_top = offset_pos.y
	panel.offset_right = offset_pos.x + offset_size.x
	panel.offset_bottom = offset_pos.y + offset_size.y
	panel.mouse_filter = Control.MOUSE_FILTER_STOP
	panel.add_theme_stylebox_override("panel", ResearchThemeScript.make_panel_style(Color(0.06, 0.08, 0.11, 0.90), ResearchThemeScript.COLOR_BORDER))
	return panel


func _make_margin_vbox(panel: PanelContainer) -> VBoxContainer:
	var margin := MarginContainer.new()
	margin.add_theme_constant_override("margin_left", int(round(ResearchThemeScript.scale_px(12.0))))
	margin.add_theme_constant_override("margin_right", int(round(ResearchThemeScript.scale_px(12.0))))
	margin.add_theme_constant_override("margin_top", int(round(ResearchThemeScript.scale_px(12.0))))
	margin.add_theme_constant_override("margin_bottom", int(round(ResearchThemeScript.scale_px(12.0))))
	panel.add_child(margin)
	var box := VBoxContainer.new()
	box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	box.add_theme_constant_override("separation", int(round(ResearchThemeScript.scale_px(8.0))))
	margin.add_child(box)
	return box


func _render_loading_state() -> void:
	_set_header_text("Showcase Mode", "加载星灯祭演示链：Goal → Director Beat → Event Skill → NPC Decision → Trace Evidence。")
	_status_label.text = "F1 隐藏 / 显示；Tab 打开 Observer Dock。"
	_clear_children(_director_rail_box)
	_clear_children(_cards_box)
	_clear_children(_trace_strip_box)
	var loading := {
		"id": "loading",
		"kicker": "Loading",
		"title": "等待后端聚合接口",
		"summary": "ShowcasePanel 默认可见；数据到达后会替换为真实 runtime 摘要。",
		"fields": [{"label": "endpoint", "value": "/api/showcase/starlight"}],
		"status": "loading",
	}
	_cards_box.add_child(_make_card(loading, ResearchThemeScript.COLOR_ACCENT))


func _render_payload() -> void:
	var scenario = _payload.get("scenario", {})
	if not (scenario is Dictionary):
		scenario = {}
	var scenario_dict := scenario as Dictionary
	_set_header_text(str(scenario_dict.get("title", "星灯祭供应短缺")), str(scenario_dict.get("caption", "")))
	_status_label.text = "Hybrid runtime / schema=%s / F1=Showcase / Tab=Observer" % str(_payload.get("schemaVersion", ""))
	_clear_children(_director_rail_box)
	_clear_children(_cards_box)
	_clear_children(_trace_strip_box)

	var director_card = _payload.get("directorCard", {})
	if director_card is Dictionary:
		_director_rail_box.add_child(_make_card(director_card as Dictionary, ResearchThemeScript.COLOR_ACCENT))
	var goal_card = _payload.get("goalCard", {})
	if goal_card is Dictionary:
		_director_rail_box.add_child(_make_card(goal_card as Dictionary, Color(1.0, 0.86, 0.45, 0.82)))

	for i in range(CARD_KEYS.size()):
		var key := str(CARD_KEYS[i])
		var card = _payload.get(key, {})
		if not (card is Dictionary):
			continue
		_cards_box.add_child(_make_card(card as Dictionary, CARD_ACCENTS[i]))

	var trace_strip = _payload.get("traceStrip", [])
	if trace_strip is Array:
		for item in trace_strip:
			if item is Dictionary:
				_trace_strip_box.add_child(_make_trace_chip(item as Dictionary))


func _set_header_text(title: String, caption: String) -> void:
	if _scenario_title_label != null:
		_scenario_title_label.text = title
	if _scenario_caption_label != null:
		_scenario_caption_label.text = caption


func _make_card(card: Dictionary, accent: Color) -> PanelContainer:
	var panel := PanelContainer.new()
	panel.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	panel.add_theme_stylebox_override("panel", ResearchThemeScript.make_card_style(accent))
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", int(round(ResearchThemeScript.scale_px(4.0))))
	panel.add_child(box)

	var kicker := _make_label(str(card.get("kicker", "Card")).to_upper(), ResearchThemeScript.FONT_SIZE_SMALL, accent)
	box.add_child(kicker)
	var title := _make_label(str(card.get("title", "")), ResearchThemeScript.FONT_SIZE_SUBTITLE, ResearchThemeScript.COLOR_TEXT_TITLE)
	title.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	box.add_child(title)
	var summary := _make_label(str(card.get("summary", "")), ResearchThemeScript.FONT_SIZE_BODY, ResearchThemeScript.COLOR_TEXT_PRIMARY)
	summary.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	box.add_child(summary)

	var fields = card.get("fields", [])
	if fields is Array:
		for field in fields:
			if field is Dictionary:
				box.add_child(_make_field_row(field as Dictionary))
	return panel


func _make_field_row(field: Dictionary) -> Label:
	var label := _make_label("%s: %s" % [str(field.get("label", "field")), str(field.get("value", ""))], ResearchThemeScript.FONT_SIZE_SMALL, ResearchThemeScript.COLOR_TEXT_MUTED)
	label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	return label


func _make_trace_chip(item: Dictionary) -> PanelContainer:
	var color := ResearchThemeScript.trace_type_color(str(item.get("eventType", "")))
	if str(item.get("status", "")) in ["fallback", "loading"]:
		color = ResearchThemeScript.COLOR_TEXT_MUTED
	if str(item.get("status", "")) == "error":
		color = ResearchThemeScript.COLOR_STATUS_ERROR
	var chip := PanelContainer.new()
	chip.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	chip.custom_minimum_size = Vector2(130.0, 92.0)
	chip.add_theme_stylebox_override("panel", ResearchThemeScript.make_card_style(color))
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", int(round(ResearchThemeScript.scale_px(3.0))))
	chip.add_child(box)
	var label := _make_label(str(item.get("label", "Trace")), ResearchThemeScript.FONT_SIZE_SMALL, color)
	box.add_child(label)
	var summary := _make_label(str(item.get("summary", "")), ResearchThemeScript.FONT_SIZE_SMALL, ResearchThemeScript.COLOR_TEXT_PRIMARY)
	summary.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	box.add_child(summary)
	return chip


func _make_label(text: String, font_size: int, color: Color) -> Label:
	var label := Label.new()
	label.text = text
	label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	ResearchThemeScript.apply_label_style(label, font_size, color)
	return label


func _make_button(text: String) -> Button:
	var button := Button.new()
	button.text = text
	button.focus_mode = Control.FOCUS_NONE
	button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	ResearchThemeScript.apply_button_style(button, ResearchThemeScript.FONT_SIZE_SMALL)
	return button


func _add_separator(parent: VBoxContainer) -> void:
	parent.add_child(ResearchThemeScript.make_separator(ResearchThemeScript.COLOR_BORDER_SOFT, 1))


func _clear_children(node: Node) -> void:
	if node == null:
		return
	for child in node.get_children():
		node.remove_child(child)
		child.queue_free()


func _on_deep_dive_pressed() -> void:
	var scenario = _payload.get("scenario", {})
	var npc_id := "kai"
	if scenario is Dictionary:
		npc_id = str((scenario as Dictionary).get("primaryNpcId", "kai"))
	var focus := _trace_focus_from_strip()
	deep_dive_requested.emit(npc_id, str(focus.get("eventId", "")), str(focus.get("traceId", "")))


func _on_refresh_pressed() -> void:
	refresh_requested.emit()


func _trace_focus_from_strip() -> Dictionary:
	var trace_strip = _payload.get("traceStrip", [])
	if trace_strip is Array:
		for item in trace_strip:
			if not (item is Dictionary):
				continue
			var item_dict := item as Dictionary
			var event_id := str(item_dict.get("eventId", ""))
			var trace_id := str(item_dict.get("traceId", ""))
			if event_id != "" or trace_id != "":
				return {"eventId": event_id, "traceId": trace_id}
	return {"eventId": "", "traceId": ""}
