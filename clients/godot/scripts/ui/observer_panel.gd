class_name ObserverPanel
extends CanvasLayer

var _panel: PanelContainer
var _npc_id_value: Label
var _npc_name_value: Label
var _location_value: Label
var _anchor_value: Label
var _trace_hint_label: Label
var _panel_visible := false


func _ready() -> void:
	# Phase 2 观察者模式最小骨架：默认隐藏，按 Tab 显示。
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
	_npc_id_value.text = "-"
	_npc_name_value.text = "未选择"
	_location_value.text = "-"
	_anchor_value.text = "-"
	_trace_hint_label.text = "提示：点击 NPC 或通过选择逻辑写入对象，后续在这里接后端 trace。"


func set_selected_npc(snapshot: Dictionary) -> void:
	var npc_id := str(snapshot.get("npcId", ""))
	var npc_name := str(snapshot.get("name", ""))
	var location_id := str(snapshot.get("location", ""))
	var anchor_id := str(snapshot.get("anchor", ""))

	_npc_id_value.text = npc_id if npc_id != "" else "-"
	_npc_name_value.text = npc_name if npc_name != "" else "未命名"
	_location_value.text = location_id if location_id != "" else "-"
	_anchor_value.text = anchor_id if anchor_id != "" else "-"
	_trace_hint_label.text = "提示：后续接入 /api/debug/agent-trace、动机链路和 process fidelity trace。"


func _build_panel() -> void:
	_panel = PanelContainer.new()
	_panel.name = "ObserverPanelRoot"
	_panel.anchor_left = 1.0
	_panel.anchor_top = 0.0
	_panel.anchor_right = 1.0
	_panel.anchor_bottom = 0.0
	_panel.offset_left = -420.0
	_panel.offset_top = 338.0
	_panel.offset_right = -18.0
	_panel.offset_bottom = 576.0
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

	_trace_hint_label = Label.new()
	_trace_hint_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_trace_hint_label.add_theme_font_size_override("font_size", 13)
	vbox.add_child(_trace_hint_label)


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
