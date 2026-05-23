class_name ObserverPanel
extends CanvasLayer

var _panel: PanelContainer
var _npc_id_value: Label
var _npc_name_value: Label
var _location_value: Label
var _anchor_value: Label
var _phase2_status_value: Label
var _motivation_value: Label
var _subjective_memory_value: Label
var _relationship_edges_value: Label
var _heuristics_value: Label
var _recent_trace_value: Label
var _panel_visible := false
var _current_npc_id := ""


func _ready() -> void:
	# Phase 2 观察者面板默认隐藏，通过 Tab 展示。
	layer = 20
	_build_panel()
	set_panel_visible(false)
	show_empty_selection()


func toggle_panel_visible() -> bool:
	set_panel_visible(not _panel_visible)
	return _panel_visible


func set_panel_visible(next_visible: bool) -> void:
	_panel_visible = next_visible
	if _panel != null:
		_panel.visible = next_visible


func is_panel_visible() -> bool:
	return _panel_visible


func show_empty_selection() -> void:
	_current_npc_id = ""
	_npc_id_value.text = "-"
	_npc_name_value.text = "未选择"
	_location_value.text = "-"
	_anchor_value.text = "-"
	_phase2_status_value.text = "状态：等待选择 NPC"
	_motivation_value.text = "-"
	_subjective_memory_value.text = "-"
	_relationship_edges_value.text = "-"
	_heuristics_value.text = "-"
	_recent_trace_value.text = "-"


func set_selected_npc(snapshot: Dictionary) -> void:
	var npc_id := str(snapshot.get("npcId", ""))
	var npc_name := str(snapshot.get("name", ""))
	var location_id := str(snapshot.get("location", ""))
	var anchor_id := str(snapshot.get("anchor", ""))
	var switched_npc := npc_id != _current_npc_id
	_current_npc_id = npc_id

	_npc_id_value.text = npc_id if npc_id != "" else "-"
	_npc_name_value.text = npc_name if npc_name != "" else "未命名"
	_location_value.text = location_id if location_id != "" else "-"
	_anchor_value.text = anchor_id if anchor_id != "" else "-"
	if switched_npc:
		_phase2_status_value.text = "状态：等待加载 Phase 2 Debug"
		_motivation_value.text = "-"
		_subjective_memory_value.text = "-"
		_relationship_edges_value.text = "-"
		_heuristics_value.text = "-"
		_recent_trace_value.text = "-"


func show_phase2_loading() -> void:
	_phase2_status_value.text = "状态：加载中..."


func show_phase2_error(error_message: String) -> void:
	_phase2_status_value.text = "状态：加载失败 - %s" % error_message


func set_phase2_debug_summary(summary: Dictionary) -> void:
	_phase2_status_value.text = "状态：已同步"
	_motivation_value.text = str(summary.get("motivation", "-"))
	_subjective_memory_value.text = str(summary.get("subjectiveMemory", "-"))
	_relationship_edges_value.text = str(summary.get("relationshipEdges", "-"))
	_heuristics_value.text = str(summary.get("heuristics", "-"))
	_recent_trace_value.text = str(summary.get("recentTraceEvents", "-"))


func _build_panel() -> void:
	_panel = PanelContainer.new()
	_panel.name = "ObserverPanelRoot"
	_panel.anchor_left = 1.0
	_panel.anchor_top = 0.0
	_panel.anchor_right = 1.0
	_panel.anchor_bottom = 0.0
	_panel.offset_left = -420.0
	_panel.offset_top = 318.0
	_panel.offset_right = -18.0
	_panel.offset_bottom = 748.0
	add_child(_panel)

	var margin := MarginContainer.new()
	margin.add_theme_constant_override("margin_left", 14)
	margin.add_theme_constant_override("margin_right", 14)
	margin.add_theme_constant_override("margin_top", 12)
	margin.add_theme_constant_override("margin_bottom", 12)
	_panel.add_child(margin)

	var vbox := VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 8)
	margin.add_child(vbox)

	var title := Label.new()
	title.text = "Observer Panel [Tab]"
	title.add_theme_font_size_override("font_size", 18)
	vbox.add_child(title)

	var rows := GridContainer.new()
	rows.columns = 2
	rows.add_theme_constant_override("h_separation", 12)
	rows.add_theme_constant_override("v_separation", 6)
	vbox.add_child(rows)

	_add_row(rows, "npcId")
	_npc_id_value = _add_value(rows)
	_add_row(rows, "名称")
	_npc_name_value = _add_value(rows)
	_add_row(rows, "location")
	_location_value = _add_value(rows)
	_add_row(rows, "anchor")
	_anchor_value = _add_value(rows)

	_phase2_status_value = _build_section_value(vbox, "Phase2 状态")
	_motivation_value = _build_section_value(vbox, "motivation")
	_subjective_memory_value = _build_section_value(vbox, "subjectiveMemory")
	_relationship_edges_value = _build_section_value(vbox, "relationshipEdges")
	_heuristics_value = _build_section_value(vbox, "heuristics")
	_recent_trace_value = _build_section_value(vbox, "recentTraceEvents")


func _add_row(parent: GridContainer, key_text: String) -> void:
	var key_label := Label.new()
	key_label.text = "%s:" % key_text
	key_label.add_theme_font_size_override("font_size", 13)
	parent.add_child(key_label)


func _add_value(parent: GridContainer) -> Label:
	var value_label := Label.new()
	value_label.add_theme_font_size_override("font_size", 13)
	parent.add_child(value_label)
	return value_label


func _build_section_value(parent: VBoxContainer, title_text: String) -> Label:
	var title := Label.new()
	title.text = "%s:" % title_text
	title.add_theme_font_size_override("font_size", 13)
	parent.add_child(title)

	var value := Label.new()
	value.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	value.add_theme_font_size_override("font_size", 12)
	value.add_theme_color_override("font_color", Color(0.92, 0.96, 1.0, 0.98))
	parent.add_child(value)
	return value
