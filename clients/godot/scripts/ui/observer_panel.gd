class_name ObserverPanel
extends CanvasLayer

signal highlight_npcs_requested(npc_ids)
signal retry_requested(npc_id)

const TRACE_FILTER_IDS := ["all", "decision", "tool", "interrupt", "memory"]
const DETAIL_POPUP_MAX_CHARS := 12000
const SECTION_EMPTY_TEXT := {
	"motivation": "暂无 motivation：后端没有返回该 NPC 的决策记录，等待下一次世界 tick。",
	"subjectiveMemory": "暂无 subjectiveMemory：该 NPC 尚未写入主观记忆。",
	"relationshipEdges": "暂无 relationshipEdges：该 NPC 暂无可解释关系边。",
	"heuristics": "暂无 heuristics：该 NPC 暂无启发式学习记录。",
	"recentTraceEvents": "暂无 recentTraceEvents：该 NPC 尚未产生可解释 trace。",
	"traceDetails": "暂无 traceDetails：先等待 trace 产生，再查看明细。",
}

var _panel: PanelContainer
var _npc_id_value: Label
var _npc_name_value: Label
var _location_value: Label
var _anchor_value: Label
var _phase2_status_value: Label
var _phase2_retry_button: Button
var _motivation_value: Label
var _subjective_memory_value: Label
var _relationship_edges_value: Label
var _heuristics_value: Label
var _recent_trace_filter: OptionButton
var _trace_prev_button: Button
var _trace_next_button: Button
var _trace_copy_button: Button
var _trace_index_value: Label
var _recent_trace_value: Label
var _recent_trace_rows: VBoxContainer
var _recent_trace_detail_value: Label
var _trace_detail_popup: PanelContainer
var _trace_detail_popup_title: Label
var _trace_detail_scroll: ScrollContainer
var _trace_detail_popup_value: Label
var _trace_detail_close_button: Button
var _recent_trace_summaries: Dictionary = {}
var _recent_trace_event_groups: Dictionary = {}
var _recent_trace_detail_groups: Dictionary = {}
var _recent_trace_copy_detail_groups: Dictionary = {}
var _recent_trace_details := "-"
var _current_trace_detail_index := 0
var _current_trace_filter := "all"
var _panel_visible := false
var _current_npc_id := ""
var _normal_status_color := Color(0.92, 0.96, 1.0, 0.98)
var _error_status_color := Color(1.0, 0.64, 0.54, 1.0)


func _ready() -> void:
	# Phase 2 观察者面板默认隐藏，通过 Tab 展示。
	layer = 20
	_build_panel()
	set_panel_visible(false)
	show_empty_selection()


func _unhandled_input(event: InputEvent) -> void:
	if not _panel_visible:
		return
	if not (event is InputEventKey):
		return
	var key_event := event as InputEventKey
	if not key_event.pressed or key_event.echo:
		return
	if key_event.keycode == KEY_ESCAPE and _is_trace_detail_popup_visible():
		_hide_trace_details_popup()
		get_viewport().set_input_as_handled()
		return
	var filter_index := _trace_filter_index_for_key(key_event.keycode)
	if filter_index >= 0:
		_select_trace_filter_by_index(filter_index)
		get_viewport().set_input_as_handled()


func toggle_panel_visible() -> bool:
	set_panel_visible(not _panel_visible)
	return _panel_visible


func set_panel_visible(next_visible: bool) -> void:
	_panel_visible = next_visible
	if _panel != null:
		_panel.visible = next_visible
	if not next_visible:
		_hide_trace_details_popup()


func is_panel_visible() -> bool:
	return _panel_visible


func show_empty_selection() -> void:
	_current_npc_id = ""
	_npc_id_value.text = "-"
	_npc_name_value.text = "未选择"
	_location_value.text = "-"
	_anchor_value.text = "-"
	_set_phase2_status("状态：等待选择 NPC")
	_set_retry_visible(false)
	_motivation_value.text = "请选择 NPC 后查看 motivation。"
	_subjective_memory_value.text = "请选择 NPC 后查看 subjectiveMemory。"
	_relationship_edges_value.text = "请选择 NPC 后查看 relationshipEdges。"
	_heuristics_value.text = "请选择 NPC 后查看 heuristics。"
	_reset_recent_trace_view()


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
		_set_phase2_status("状态：等待加载 Phase 2 Debug")
		_set_retry_visible(false)
		_motivation_value.text = "等待后端返回 motivation 数据..."
		_subjective_memory_value.text = "等待后端返回 subjectiveMemory 数据..."
		_relationship_edges_value.text = "等待后端返回 relationshipEdges 数据..."
		_heuristics_value.text = "等待后端返回 heuristics 数据..."
		_reset_recent_trace_view()


func show_phase2_loading() -> void:
	_set_phase2_status("状态：加载中...")
	_set_retry_visible(false)


func show_phase2_error(error_message: String) -> void:
	var text := error_message.strip_edges()
	if text == "":
		text = "unknown error"
	_set_phase2_status("错误：%s" % text, true)
	_set_retry_visible(_current_npc_id != "")
	_motivation_value.text = "加载失败后保留空态：点击重试重新拉取 motivation。"
	_subjective_memory_value.text = "加载失败后保留空态：点击重试重新拉取 subjectiveMemory。"
	_relationship_edges_value.text = "加载失败后保留空态：点击重试重新拉取 relationshipEdges。"
	_heuristics_value.text = "加载失败后保留空态：点击重试重新拉取 heuristics。"
	_reset_recent_trace_view()


func set_phase2_debug_summary(summary: Dictionary) -> void:
	var previous_count := _trace_item_count()
	var was_following_latest := previous_count == 0 or _current_trace_detail_index >= previous_count - 1
	var previous_index := _current_trace_detail_index
	_set_phase2_status("状态：已同步")
	_set_retry_visible(false)
	_motivation_value.text = _section_text(summary, "motivation")
	_subjective_memory_value.text = _section_text(summary, "subjectiveMemory")
	_relationship_edges_value.text = _section_text(summary, "relationshipEdges")
	_heuristics_value.text = _section_text(summary, "heuristics")
	_recent_trace_summaries = _trace_summary_dict(summary)
	_recent_trace_event_groups = _trace_event_group_dict(summary)
	_recent_trace_detail_groups = _trace_detail_group_dict(summary)
	_recent_trace_copy_detail_groups = _trace_copy_detail_group_dict(summary)
	_recent_trace_details = _text_or_placeholder(summary.get("recentTraceDetails", ""), "traceDetails")
	if was_following_latest:
		_select_latest_trace_detail()
	else:
		_current_trace_detail_index = int(clamp(previous_index, 0, max(0, _trace_item_count() - 1)))
	_update_recent_trace_view()


func _build_panel() -> void:
	_panel = PanelContainer.new()
	_panel.name = "ObserverPanelRoot"
	_panel.anchor_left = 1.0
	_panel.anchor_top = 0.0
	_panel.anchor_right = 1.0
	_panel.anchor_bottom = 0.0
	_panel.offset_left = -420.0
	_panel.offset_top = 288.0
	_panel.offset_right = -18.0
	_panel.offset_bottom = 790.0
	_panel.mouse_filter = Control.MOUSE_FILTER_STOP
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

	_build_phase2_status(vbox)
	_motivation_value = _build_section_value(vbox, "motivation")
	_subjective_memory_value = _build_section_value(vbox, "subjectiveMemory")
	_relationship_edges_value = _build_section_value(vbox, "relationshipEdges")
	_heuristics_value = _build_section_value(vbox, "heuristics")
	_build_recent_trace_filter(vbox)
	_recent_trace_value = _build_section_value(vbox, "recentTraceEvents")
	_build_recent_trace_rows(vbox)
	_recent_trace_detail_value = _build_section_value(vbox, "traceDetails")
	_build_trace_detail_popup()


func _build_phase2_status(parent: VBoxContainer) -> void:
	var title := Label.new()
	title.text = "Phase2 状态:"
	title.add_theme_font_size_override("font_size", 13)
	parent.add_child(title)

	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 8)
	parent.add_child(row)

	_phase2_status_value = Label.new()
	_phase2_status_value.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_phase2_status_value.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_phase2_status_value.add_theme_font_size_override("font_size", 12)
	_phase2_status_value.add_theme_color_override("font_color", _normal_status_color)
	row.add_child(_phase2_status_value)

	_phase2_retry_button = Button.new()
	_phase2_retry_button.text = "重试"
	_phase2_retry_button.visible = false
	_phase2_retry_button.focus_mode = Control.FOCUS_NONE
	_phase2_retry_button.pressed.connect(_on_retry_pressed)
	row.add_child(_phase2_retry_button)


func _build_recent_trace_filter(parent: VBoxContainer) -> void:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 8)
	parent.add_child(row)

	var label := Label.new()
	label.text = "traceFilter:"
	label.add_theme_font_size_override("font_size", 13)
	row.add_child(label)

	_recent_trace_filter = OptionButton.new()
	_recent_trace_filter.focus_mode = Control.FOCUS_NONE
	for index in range(TRACE_FILTER_IDS.size()):
		var filter_id := str(TRACE_FILTER_IDS[index])
		_recent_trace_filter.add_item("%d %s" % [index + 1, filter_id])
		_recent_trace_filter.set_item_metadata(index, filter_id)
	_recent_trace_filter.item_selected.connect(_on_recent_trace_filter_selected)
	row.add_child(_recent_trace_filter)

	_trace_prev_button = Button.new()
	_trace_prev_button.text = "Prev"
	_trace_prev_button.focus_mode = Control.FOCUS_NONE
	_trace_prev_button.pressed.connect(_on_trace_prev_pressed)
	row.add_child(_trace_prev_button)

	_trace_next_button = Button.new()
	_trace_next_button.text = "Next"
	_trace_next_button.focus_mode = Control.FOCUS_NONE
	_trace_next_button.pressed.connect(_on_trace_next_pressed)
	row.add_child(_trace_next_button)

	_trace_copy_button = Button.new()
	_trace_copy_button.text = "Copy trace"
	_trace_copy_button.focus_mode = Control.FOCUS_NONE
	_trace_copy_button.pressed.connect(_on_trace_copy_pressed)
	row.add_child(_trace_copy_button)

	_trace_index_value = Label.new()
	_trace_index_value.text = "0/0"
	_trace_index_value.add_theme_font_size_override("font_size", 12)
	row.add_child(_trace_index_value)


func _build_recent_trace_rows(parent: VBoxContainer) -> void:
	_recent_trace_rows = VBoxContainer.new()
	_recent_trace_rows.add_theme_constant_override("separation", 4)
	parent.add_child(_recent_trace_rows)


func _build_trace_detail_popup() -> void:
	_trace_detail_popup = PanelContainer.new()
	_trace_detail_popup.name = "TraceDetailsPopup"
	_trace_detail_popup.visible = false
	_trace_detail_popup.anchor_left = 0.0
	_trace_detail_popup.anchor_top = 0.0
	_trace_detail_popup.anchor_right = 1.0
	_trace_detail_popup.anchor_bottom = 1.0
	_trace_detail_popup.offset_left = 12.0
	_trace_detail_popup.offset_top = 116.0
	_trace_detail_popup.offset_right = -12.0
	_trace_detail_popup.offset_bottom = -12.0
	_trace_detail_popup.mouse_filter = Control.MOUSE_FILTER_STOP
	_trace_detail_popup.z_index = 50
	_trace_detail_popup.add_theme_stylebox_override("panel", _make_trace_popup_style())
	_panel.add_child(_trace_detail_popup)

	var margin := MarginContainer.new()
	margin.add_theme_constant_override("margin_left", 12)
	margin.add_theme_constant_override("margin_right", 12)
	margin.add_theme_constant_override("margin_top", 10)
	margin.add_theme_constant_override("margin_bottom", 10)
	_trace_detail_popup.add_child(margin)

	var column := VBoxContainer.new()
	column.add_theme_constant_override("separation", 8)
	margin.add_child(column)

	var title_row := HBoxContainer.new()
	title_row.add_theme_constant_override("separation", 8)
	column.add_child(title_row)

	_trace_detail_popup_title = Label.new()
	_trace_detail_popup_title.text = "Trace details"
	_trace_detail_popup_title.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_trace_detail_popup_title.add_theme_font_size_override("font_size", 14)
	title_row.add_child(_trace_detail_popup_title)

	_trace_detail_close_button = Button.new()
	_trace_detail_close_button.text = "关闭 [Esc]"
	_trace_detail_close_button.focus_mode = Control.FOCUS_NONE
	_trace_detail_close_button.pressed.connect(_hide_trace_details_popup)
	title_row.add_child(_trace_detail_close_button)

	_trace_detail_scroll = ScrollContainer.new()
	_trace_detail_scroll.focus_mode = Control.FOCUS_NONE
	_trace_detail_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_trace_detail_scroll.custom_minimum_size = Vector2(0.0, 250.0)
	column.add_child(_trace_detail_scroll)

	_trace_detail_popup_value = Label.new()
	_trace_detail_popup_value.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_trace_detail_popup_value.add_theme_font_size_override("font_size", 11)
	_trace_detail_popup_value.add_theme_color_override("font_color", Color(0.96, 0.98, 1.0, 1.0))
	_trace_detail_scroll.add_child(_trace_detail_popup_value)


func _make_trace_popup_style() -> StyleBoxFlat:
	var style := StyleBoxFlat.new()
	style.bg_color = Color(0.03, 0.05, 0.08, 0.96)
	style.border_color = Color(0.58, 0.82, 1.0, 0.92)
	style.set_border_width_all(1)
	style.set_corner_radius_all(10)
	style.shadow_color = Color(0.0, 0.0, 0.0, 0.35)
	style.shadow_size = 8
	return style


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


func _on_recent_trace_filter_selected(index: int) -> void:
	if _recent_trace_filter == null:
		return
	_current_trace_filter = str(_recent_trace_filter.get_item_metadata(index))
	_select_latest_trace_detail()
	_update_recent_trace_view()


func _select_trace_filter_by_index(index: int) -> void:
	if index < 0 or index >= TRACE_FILTER_IDS.size():
		return
	_current_trace_filter = str(TRACE_FILTER_IDS[index])
	if _recent_trace_filter != null:
		_recent_trace_filter.select(index)
	_select_latest_trace_detail()
	_update_recent_trace_view()


func _trace_filter_index_for_key(keycode: int) -> int:
	match keycode:
		KEY_1:
			return 0
		KEY_2:
			return 1
		KEY_3:
			return 2
		KEY_4:
			return 3
		KEY_5:
			return 4
		_:
			return -1


func _trace_summary_dict(summary: Dictionary) -> Dictionary:
	var groups = summary.get("recentTraceEventGroups", {})
	if groups is Dictionary:
		return (groups as Dictionary).duplicate(true)
	return _empty_trace_summary_dict()


func _trace_event_group_dict(summary: Dictionary) -> Dictionary:
	var groups = summary.get("recentTraceEventRows", {})
	if groups is Dictionary:
		return (groups as Dictionary).duplicate(true)
	return _empty_trace_event_group_dict()


func _trace_detail_group_dict(summary: Dictionary) -> Dictionary:
	var groups = summary.get("recentTraceDetailGroups", {})
	if groups is Dictionary:
		return (groups as Dictionary).duplicate(true)
	return _empty_trace_detail_group_dict()


func _trace_copy_detail_group_dict(summary: Dictionary) -> Dictionary:
	var groups = summary.get("recentTraceCopyDetailGroups", {})
	if groups is Dictionary:
		return (groups as Dictionary).duplicate(true)
	return _trace_detail_group_dict(summary)


func _reset_recent_trace_view() -> void:
	_recent_trace_summaries = _empty_trace_summary_dict()
	_recent_trace_event_groups = _empty_trace_event_group_dict()
	_recent_trace_detail_groups = _empty_trace_detail_group_dict()
	_recent_trace_copy_detail_groups = _empty_trace_detail_group_dict()
	_recent_trace_details = str(SECTION_EMPTY_TEXT["traceDetails"])
	_current_trace_detail_index = 0
	_current_trace_filter = "all"
	if _recent_trace_filter != null:
		_recent_trace_filter.select(0)
	_hide_trace_details_popup()
	_update_recent_trace_view()


func _update_recent_trace_view() -> void:
	var rows := _trace_events_for_filter()
	if _recent_trace_value != null:
		if rows.is_empty():
			_recent_trace_value.text = _trace_summary_text_for_filter()
		else:
			_recent_trace_value.text = "点击 trace 行：decision 高亮参与 NPC；tool 展开 details；memory 高亮观察者。"
	_rebuild_recent_trace_rows(rows)
	_update_recent_trace_detail_text()


func _update_recent_trace_detail_text() -> void:
	if _recent_trace_detail_value == null:
		_update_trace_index_label()
		return
	var details := _trace_details_for_filter()
	var item_count := _trace_item_count()
	if item_count <= 0:
		_recent_trace_detail_value.text = _recent_trace_details
		_update_trace_index_label()
		return
	_current_trace_detail_index = int(clamp(_current_trace_detail_index, 0, item_count - 1))
	if _current_trace_detail_index < details.size():
		_recent_trace_detail_value.text = str(details[_current_trace_detail_index])
	else:
		_recent_trace_detail_value.text = _recent_trace_details
	_update_trace_index_label()


func _rebuild_recent_trace_rows(rows: Array) -> void:
	if _recent_trace_rows == null:
		return
	for child in _recent_trace_rows.get_children():
		child.queue_free()
	for index in range(rows.size()):
		if not (rows[index] is Dictionary):
			continue
		var entry := (rows[index] as Dictionary).duplicate(true)
		var row_button := Button.new()
		row_button.focus_mode = Control.FOCUS_NONE
		row_button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		row_button.clip_text = true
		var prefix := "▶" if index == _current_trace_detail_index else "•"
		row_button.text = "%s %s" % [prefix, _trace_row_text(entry)]
		row_button.tooltip_text = "点击执行 trace 动作"
		row_button.pressed.connect(_on_trace_row_pressed.bind(entry, index))
		_recent_trace_rows.add_child(row_button)


func _trace_summary_text_for_filter() -> String:
	var fallback := str(_recent_trace_summaries.get(_current_trace_filter, _recent_trace_summaries.get("all", "")))
	return _text_or_placeholder(fallback, "recentTraceEvents")


func _trace_details_for_filter() -> Array:
	var details = _recent_trace_detail_groups.get(_current_trace_filter, _recent_trace_detail_groups.get("all", []))
	if details is Array:
		return details as Array
	return []


func _trace_copy_details_for_filter() -> Array:
	var details = _recent_trace_copy_detail_groups.get(_current_trace_filter, _recent_trace_copy_detail_groups.get("all", []))
	if details is Array:
		return details as Array
	return _trace_details_for_filter()


func _trace_events_for_filter() -> Array:
	var rows = _recent_trace_event_groups.get(_current_trace_filter, _recent_trace_event_groups.get("all", []))
	if rows is Array:
		return rows as Array
	return []


func _trace_item_count() -> int:
	return int(max(_trace_details_for_filter().size(), _trace_events_for_filter().size()))


func _select_latest_trace_detail() -> void:
	_current_trace_detail_index = max(0, _trace_item_count() - 1)


func _update_trace_index_label() -> void:
	if _trace_index_value == null:
		return
	var item_count := _trace_item_count()
	if item_count <= 0:
		_trace_index_value.text = "0/0"
		return
	_trace_index_value.text = "%d/%d" % [_current_trace_detail_index + 1, item_count]


func _on_trace_prev_pressed() -> void:
	var item_count := _trace_item_count()
	if item_count <= 0:
		return
	_current_trace_detail_index = max(0, _current_trace_detail_index - 1)
	_update_recent_trace_view()


func _on_trace_next_pressed() -> void:
	var item_count := _trace_item_count()
	if item_count <= 0:
		return
	_current_trace_detail_index = min(item_count - 1, _current_trace_detail_index + 1)
	_update_recent_trace_view()


func _on_trace_copy_pressed() -> void:
	var copy_details := _trace_copy_details_for_filter()
	var rows := _trace_events_for_filter()
	if copy_details.is_empty() and rows.is_empty():
		return
	var copy_text := ""
	if _current_trace_detail_index < copy_details.size():
		copy_text = str(copy_details[_current_trace_detail_index])
	elif _current_trace_detail_index < rows.size() and rows[_current_trace_detail_index] is Dictionary:
		copy_text = JSON.stringify(rows[_current_trace_detail_index], "\t")
	if copy_text == "":
		return
	# 复制当前单条 trace detail，便于真实窗口验收时粘贴到 issue / 文档。
	DisplayServer.clipboard_set(copy_text)
	_set_phase2_status("状态：已复制 trace detail")


func _on_trace_row_pressed(entry: Dictionary, row_index: int) -> void:
	_current_trace_detail_index = row_index
	_update_recent_trace_detail_text()
	_rebuild_recent_trace_rows(_trace_events_for_filter())
	var event_type := _trace_event_type(entry)
	if event_type == "motivation.decision_made":
		_hide_trace_details_popup()
		_emit_highlight(_decision_trace_agent_ids(entry), "decision trace")
		return
	if event_type == "memory.result_observed":
		_hide_trace_details_popup()
		_emit_highlight(_memory_observer_ids(entry), "memory observers")
		return
	_show_trace_details_popup(entry)


func _on_retry_pressed() -> void:
	if _current_npc_id == "":
		return
	_set_phase2_status("状态：重试加载中...")
	_set_retry_visible(false)
	retry_requested.emit(_current_npc_id)


func _emit_highlight(npc_ids: Array, label_text: String) -> void:
	var normalized := _unique_ids(npc_ids)
	if normalized.is_empty():
		_set_phase2_status("状态：%s 未提供可高亮 NPC" % label_text)
		return
	highlight_npcs_requested.emit(normalized)
	_set_phase2_status("状态：已高亮 %s：%s" % [label_text, ", ".join(normalized)])


func _show_trace_details_popup(entry: Dictionary) -> void:
	if _trace_detail_popup == null:
		return
	var event_type := _trace_event_type(entry)
	var trace_id := str(entry.get("traceId", entry.get("id", "-")))
	_trace_detail_popup_title.text = "%s details · %s" % [_pretty_trace_type(event_type), trace_id]
	var details = entry.get("details", {})
	var detail_text := "{}"
	if details is Dictionary or details is Array:
		detail_text = JSON.stringify(details, "\t")
	else:
		detail_text = str(details)
	if detail_text.length() > DETAIL_POPUP_MAX_CHARS:
		detail_text = "%s\n... 已截断，Copy trace 可复制完整 trace 文本。" % detail_text.substr(0, DETAIL_POPUP_MAX_CHARS)
	_trace_detail_popup_value.text = detail_text
	_trace_detail_popup.visible = true
	_set_phase2_status("状态：已展开 %s details，可按 Esc 关闭" % _pretty_trace_type(event_type))
	call_deferred("_reset_trace_detail_scroll")


func _reset_trace_detail_scroll() -> void:
	if _trace_detail_scroll != null:
		_trace_detail_scroll.scroll_vertical = 0


func _hide_trace_details_popup() -> void:
	if _trace_detail_popup != null:
		_trace_detail_popup.visible = false


func _is_trace_detail_popup_visible() -> bool:
	return _trace_detail_popup != null and _trace_detail_popup.visible


func _decision_trace_agent_ids(entry: Dictionary) -> Array:
	var ids: Array = []
	_append_ids_from_value(ids, entry.get("agentId", null))
	_append_ids_from_value(ids, entry.get("targetIds", null))
	var details = entry.get("details", {})
	if details is Dictionary:
		var detail_dict := details as Dictionary
		_append_ids_from_value(ids, detail_dict.get("npcId", null))
		_append_ids_from_value(ids, detail_dict.get("targetNpcId", null))
	return _unique_ids(ids)


func _memory_observer_ids(entry: Dictionary) -> Array:
	var ids: Array = []
	var details = entry.get("details", {})
	if details is Dictionary:
		var detail_dict := details as Dictionary
		var scope = detail_dict.get("observerScope", {})
		if scope is Dictionary:
			var scope_dict := scope as Dictionary
			_append_ids_from_value(ids, scope_dict.get("observers", null))
			_append_ids_from_value(ids, scope_dict.get("observerIds", null))
		_append_ids_from_value(ids, detail_dict.get("observers", null))
	if ids.is_empty():
		_append_ids_from_value(ids, entry.get("targetIds", null))
	return _unique_ids(ids)


func _append_ids_from_value(ids: Array, value) -> void:
	if value == null:
		return
	if value is Array:
		var value_array := value as Array
		for item in value_array:
			_append_ids_from_value(ids, item)
		return
	var id_text := str(value).strip_edges()
	if id_text == "" or id_text == "<null>":
		return
	if not ids.has(id_text):
		ids.append(id_text)


func _unique_ids(ids: Array) -> Array:
	var unique: Array = []
	for item in ids:
		_append_ids_from_value(unique, item)
	return unique


func _trace_row_text(entry: Dictionary) -> String:
	var event_type := _trace_event_type(entry)
	var summary := _truncate_text(str(entry.get("summary", "")), 58)
	var world_time = entry.get("worldTime", {})
	var tick_text := "t?"
	if world_time is Dictionary:
		tick_text = "t%d" % int((world_time as Dictionary).get("tick", -1))
	return "%s %s%s · %s" % [
		tick_text,
		_pretty_trace_type(event_type),
		_trace_detail_hint(entry.get("details", {})),
		summary,
	]


func _trace_event_type(entry: Dictionary) -> String:
	return str(entry.get("eventType", entry.get("type", "trace")))


func _trace_detail_hint(details) -> String:
	if not (details is Dictionary):
		return ""
	var detail_dict := details as Dictionary
	var tool_id := str(detail_dict.get("selectedToolId", detail_dict.get("toolId", detail_dict.get("interruptedToolId", ""))))
	if tool_id != "":
		return " [%s]" % tool_id
	var observer_count := str(detail_dict.get("observerCount", ""))
	if observer_count != "":
		return " [%s observers]" % observer_count
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


func _section_text(summary: Dictionary, key: String) -> String:
	return _text_or_placeholder(summary.get(key, ""), key)


func _text_or_placeholder(value, key: String) -> String:
	var text := str(value).strip_edges()
	if text == "" or text == "-" or text == "[]" or text == "{}" or text == "<null>":
		return str(SECTION_EMPTY_TEXT.get(key, "暂无数据。"))
	return text


func _empty_trace_summary_dict() -> Dictionary:
	return {
		"all": str(SECTION_EMPTY_TEXT["recentTraceEvents"]),
		"decision": "暂无 decision trace：等待 NPC 完成动机决策。",
		"tool": "暂无 tool trace：等待工具执行结果。",
		"interrupt": "暂无 interrupt trace：当前没有工具中断。",
		"memory": "暂无 memory trace：等待观察者写入记忆。",
	}


func _empty_trace_event_group_dict() -> Dictionary:
	return {"all": [], "decision": [], "tool": [], "interrupt": [], "memory": []}


func _empty_trace_detail_group_dict() -> Dictionary:
	return {"all": [], "decision": [], "tool": [], "interrupt": [], "memory": []}


func _set_phase2_status(text: String, is_error: bool = false) -> void:
	if _phase2_status_value == null:
		return
	_phase2_status_value.text = text
	_phase2_status_value.add_theme_color_override("font_color", _error_status_color if is_error else _normal_status_color)


func _set_retry_visible(next_visible: bool) -> void:
	if _phase2_retry_button != null:
		_phase2_retry_button.visible = next_visible


func _truncate_text(value: String, max_chars: int) -> String:
	if value.length() <= max_chars:
		return value
	return "%s…" % value.substr(0, max(0, max_chars - 1))
