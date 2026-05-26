class_name ObserverPanel
extends CanvasLayer

# Research Dock：取代旧 ObserverPanel + WorldPulsePanel 的右侧重排版本。
# 三 Tab：
#   1. 全景 Pulse        - 世界时钟 / 活跃事件 / 6 个 NPC 行动一览（取代旧 WorldPulsePanel）
#   2. 选中 NPC          - 身份 / Motivation / 主观记忆 / 关系边 / 启发式 五张卡
#   3. Trace 时间线       - 分类过滤 + trace 行 + key-value details + 复制完整
#
# 保留对外 API：
#   - signal highlight_npcs_requested / retry_requested
#   - signal select_npc_requested （新增，供 Tab 1 行点击切到 Tab 2）
#   - func toggle_panel_visible / set_panel_visible / is_panel_visible
#   - func show_empty_selection / set_selected_npc
#   - func show_phase2_loading / show_phase2_error / set_phase2_debug_summary
#   - func set_world_pulse_data （新增，由 TownMap 推数据进来）
#
# 设计目标：研究 / 可解释性主面板，深色半透明卡片 + 滚动 + 类型染色。

const ResearchThemeScript := preload("res://scripts/ui/research_theme.gd")

signal highlight_npcs_requested(npc_ids)
signal retry_requested(npc_id)
signal select_npc_requested(npc_id)
signal trace_source_requested(npc_id, event_id, trace_id)

const TRACE_FILTER_IDS := ["all", "decision", "tool", "interrupt", "memory"]
const TRACE_FILTER_LABELS := {
	"all": "全部",
	"decision": "决策",
	"tool": "工具",
	"interrupt": "中断",
	"memory": "记忆",
}
const DETAIL_POPUP_MAX_CHARS := 12000
const SECTION_EMPTY_TEXT := {
	"motivation": "暂无 motivation：等待下一次世界 tick。",
	"subjectiveMemory": "暂无 subjectiveMemory：该 NPC 尚未写入主观记忆。",
	"relationshipEdges": "暂无 relationshipEdges：该 NPC 暂无可解释关系边。",
	"heuristics": "暂无 heuristics：该 NPC 暂无启发式学习记录。",
	"recentTraceEvents": "暂无 recentTraceEvents：该 NPC 尚未产生可解释 trace。",
	"traceDetails": "暂无 traceDetails：先等待 trace 产生，再查看明细。",
}
const TAB_PULSE := 0
const TAB_INSPECTOR := 1
const TAB_TRACE := 2
const MEMORY_CARD_TOP_N := 4
const TAB_SCROLL_BOTTOM_PADDING := 40.0
const PULSE_NPC_ROW_MIN_HEIGHT := 84.0
const PULSE_NPC_NAME_MIN_WIDTH := 134.0

var _panel: PanelContainer
var _tab_buttons: Array[Button] = []
var _tab_pages: Array[Control] = []
var _current_tab: int = TAB_PULSE

# Tab 1 · Pulse
var _pulse_clock_label: Label
var _pulse_event_list: VBoxContainer
var _pulse_npc_list: VBoxContainer

# Tab 2 · Inspector
var _inspector_status_value: Label
var _phase2_retry_button: Button
var _identity_name_label: Label
var _identity_id_label: Label
var _identity_location_label: Label
var _identity_anchor_label: Label
var _motivation_need_label: Label
var _motivation_need_bar: ProgressBar
var _motivation_decision_label: Label
var _motivation_sources_box: HBoxContainer
var _memory_list: VBoxContainer
var _memory_summary_label: Label
var _relationship_list: VBoxContainer
var _relationship_summary_label: Label
var _heuristic_list: VBoxContainer
var _heuristic_summary_label: Label

# Tab 3 · Trace
var _trace_filter_buttons: Array[Button] = []
var _trace_index_label: Label
var _trace_prev_button: Button
var _trace_next_button: Button
var _trace_copy_button: Button
var _trace_rows_box: VBoxContainer
var _trace_summary_label: Label
var _trace_details_box: VBoxContainer
var _trace_details_status_label: Label

# Trace 弹层（保留旧版"巨幅 details popup"路径，方便 paper 截图复制完整 JSON）
var _trace_detail_popup: PanelContainer
var _trace_detail_popup_title: Label
var _trace_detail_scroll: ScrollContainer
var _trace_detail_popup_value: Label

# 缓存与状态
var _panel_visible := false
var _current_npc_id := ""
var _current_payload: Dictionary = {}
var _world_pulse_data: Dictionary = {}
var _recent_trace_event_groups: Dictionary = _empty_filter_dict()
var _recent_trace_copy_detail_groups: Dictionary = _empty_filter_dict()
var _recent_trace_summaries: Dictionary = _empty_summary_dict()
var _current_trace_focus: Dictionary = {}
var _current_trace_filter := "all"
var _current_trace_detail_index := 0


func _ready() -> void:
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
	# 1-5：切换 trace 过滤；自动跳 Tab 3，便于排查决策链。
	var filter_index := _trace_filter_index_for_key(key_event.keycode)
	if filter_index >= 0:
		_switch_tab(TAB_TRACE)
		_select_trace_filter_by_index(filter_index)
		get_viewport().set_input_as_handled()


# ---------------------------------------------------------------------------
# Public API（与旧 ObserverPanel 一致，新增 select_npc_requested / world pulse）
# ---------------------------------------------------------------------------

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
	_current_payload = {}
	_identity_id_label.text = "-"
	_identity_name_label.text = "未选择"
	_identity_location_label.text = "-"
	_identity_anchor_label.text = "-"
	_set_phase2_status("等待选择 NPC")
	_set_retry_visible(false)
	_render_empty_motivation()
	_render_empty_memory()
	_render_empty_relationships()
	_render_empty_heuristics()
	_reset_recent_trace_view()


func set_selected_npc(snapshot: Dictionary) -> void:
	var npc_id := str(snapshot.get("npcId", ""))
	var npc_name := str(snapshot.get("name", ""))
	var location_id := str(snapshot.get("location", ""))
	var anchor_id := str(snapshot.get("anchor", ""))
	var switched_npc := npc_id != _current_npc_id
	_current_npc_id = npc_id
	_identity_id_label.text = npc_id if npc_id != "" else "-"
	_identity_name_label.text = npc_name if npc_name != "" else "未命名"
	_identity_location_label.text = _pretty_location(location_id)
	_identity_anchor_label.text = _pretty_anchor(anchor_id)
	if switched_npc:
		_set_phase2_status("等待加载 Phase 2 Debug")
		_set_retry_visible(false)
		_render_empty_motivation()
		_render_empty_memory()
		_render_empty_relationships()
		_render_empty_heuristics()
		_reset_recent_trace_view()
	# 选中 NPC 时自动跳到 Inspector Tab，方便人工核对当前决策。
	if switched_npc and _current_tab == TAB_PULSE:
		_switch_tab(TAB_INSPECTOR)


func show_phase2_loading() -> void:
	_set_phase2_status("加载中…")
	_set_retry_visible(false)


func show_phase2_error(error_message: String) -> void:
	var text := error_message.strip_edges()
	if text == "":
		text = "unknown error"
	_set_phase2_status("错误：%s" % text, true)
	_set_retry_visible(_current_npc_id != "")
	_render_empty_motivation()
	_render_empty_memory()
	_render_empty_relationships()
	_render_empty_heuristics()
	_reset_recent_trace_view()


func set_phase2_debug_summary(summary: Dictionary) -> void:
	# summary 仍兼容旧 text 字段（供 check_godot_project 校验）；新版面板从 `payload`
	# 拿原始 phase2 debug 字典进行卡片渲染。
	_current_payload = summary.duplicate(true)
	_set_retry_visible(false)
	var payload = summary.get("payload", {})
	if not (payload is Dictionary):
		payload = {}
	_render_motivation(payload as Dictionary, summary)
	_render_memory(payload as Dictionary, summary)
	_render_relationships(payload as Dictionary, summary)
	_render_heuristics(payload as Dictionary, summary)

	# trace 数据已由 TownMap 预处理，直接消费。
	_recent_trace_event_groups = _trace_event_group_dict(summary)
	_recent_trace_copy_detail_groups = _trace_copy_detail_group_dict(summary)
	_recent_trace_summaries = _trace_summary_dict(summary)
	_current_trace_focus = _trace_focus_dict(summary)
	var focus_status := _trace_focus_status_text(_current_trace_focus)
	_set_phase2_status(focus_status if focus_status != "" else "已同步")
	_select_trace_focus_or_latest(true)
	_update_recent_trace_view()


func set_world_pulse_data(data: Dictionary) -> void:
	# TownMap 把世界 pulse 拼好后整体推到面板：clock / events / npcRows。
	_world_pulse_data = data.duplicate(true)
	_refresh_pulse_tab()


# ---------------------------------------------------------------------------
# 主面板布局
# ---------------------------------------------------------------------------

func _build_panel() -> void:
	_panel = PanelContainer.new()
	_panel.name = "ObserverPanelRoot"
	# Research Dock：右侧固定宽度 460px，顶到底（避开 VN 面板高度）。
	_panel.anchor_left = 1.0
	_panel.anchor_top = 0.0
	_panel.anchor_right = 1.0
	_panel.anchor_bottom = 1.0
	_panel.offset_left = -520.0
	_panel.offset_top = 16.0
	_panel.offset_right = -16.0
	_panel.offset_bottom = -236.0
	_panel.mouse_filter = Control.MOUSE_FILTER_STOP
	_panel.add_theme_stylebox_override("panel", ResearchThemeScript.make_panel_style())
	add_child(_panel)

	var root_margin := MarginContainer.new()
	root_margin.add_theme_constant_override("margin_left", int(round(ResearchThemeScript.scale_px(14.0))))
	root_margin.add_theme_constant_override("margin_right", int(round(ResearchThemeScript.scale_px(14.0))))
	root_margin.add_theme_constant_override("margin_top", int(round(ResearchThemeScript.scale_px(12.0))))
	root_margin.add_theme_constant_override("margin_bottom", int(round(ResearchThemeScript.scale_px(12.0))))
	root_margin.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	root_margin.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_panel.add_child(root_margin)

	var root_vbox := VBoxContainer.new()
	root_vbox.add_theme_constant_override("separation", int(round(ResearchThemeScript.scale_px(10.0))))
	root_vbox.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	root_vbox.size_flags_vertical = Control.SIZE_EXPAND_FILL
	root_margin.add_child(root_vbox)

	_build_header(root_vbox)
	_build_tab_bar(root_vbox)
	_build_tab_pages(root_vbox)
	_build_trace_detail_popup()
	_switch_tab(TAB_PULSE)


func _setup_tab_scroll(scroll: ScrollContainer, content: VBoxContainer) -> void:
	scroll.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	scroll.vertical_scroll_mode = ScrollContainer.SCROLL_MODE_AUTO
	content.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	content.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.add_child(content)


func _append_tab_bottom_padding(content: VBoxContainer) -> void:
	var spacer := Control.new()
	spacer.mouse_filter = Control.MOUSE_FILTER_IGNORE
	spacer.custom_minimum_size = Vector2(0.0, ResearchThemeScript.scale_px(TAB_SCROLL_BOTTOM_PADDING))
	content.add_child(spacer)


func _build_header(parent: VBoxContainer) -> void:
	var header := HBoxContainer.new()
	header.add_theme_constant_override("separation", 8)
	parent.add_child(header)

	var title := Label.new()
	title.text = "Loomstead Observer"
	title.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	ResearchThemeScript.apply_label_style(title, ResearchThemeScript.FONT_SIZE_TITLE, ResearchThemeScript.COLOR_TEXT_TITLE)
	header.add_child(title)

	var hint := Label.new()
	hint.text = "[Tab]"
	ResearchThemeScript.apply_label_style(hint, ResearchThemeScript.FONT_SIZE_SMALL, ResearchThemeScript.COLOR_TEXT_MUTED)
	header.add_child(hint)


func _build_tab_bar(parent: VBoxContainer) -> void:
	var tab_row := HBoxContainer.new()
	tab_row.add_theme_constant_override("separation", 6)
	parent.add_child(tab_row)

	_tab_buttons.clear()
	var tab_titles := ["小镇全景", "选中 NPC", "Trace 时间线"]
	for i in range(tab_titles.size()):
		var button := Button.new()
		button.text = str(tab_titles[i])
		button.focus_mode = Control.FOCUS_NONE
		button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		button.toggle_mode = true
		ResearchThemeScript.apply_button_style(button, ResearchThemeScript.FONT_SIZE_BODY)
		button.pressed.connect(_switch_tab.bind(i))
		tab_row.add_child(button)
		_tab_buttons.append(button)


func _build_tab_pages(parent: VBoxContainer) -> void:
	var stack := Control.new()
	stack.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	stack.size_flags_vertical = Control.SIZE_EXPAND_FILL
	parent.add_child(stack)

	_tab_pages.clear()
	_tab_pages.append(_build_pulse_tab())
	_tab_pages.append(_build_inspector_tab())
	_tab_pages.append(_build_trace_tab())
	for page in _tab_pages:
		page.anchor_left = 0.0
		page.anchor_top = 0.0
		page.anchor_right = 1.0
		page.anchor_bottom = 1.0
		page.offset_left = 0
		page.offset_right = 0
		page.offset_top = 0
		page.offset_bottom = 0
		stack.add_child(page)


# ---------------------------------------------------------------------------
# Tab 1 · 全景 Pulse
# ---------------------------------------------------------------------------

func _build_pulse_tab() -> Control:
	var scroll := ScrollContainer.new()
	var page_vbox := VBoxContainer.new()
	page_vbox.add_theme_constant_override("separation", 10)
	_setup_tab_scroll(scroll, page_vbox)

	# 时钟卡
	var clock_card := _make_card("世界时钟")
	_pulse_clock_label = Label.new()
	_pulse_clock_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	ResearchThemeScript.apply_label_style(_pulse_clock_label, ResearchThemeScript.FONT_SIZE_BODY, ResearchThemeScript.COLOR_TEXT_PRIMARY)
	_pulse_clock_label.text = "等待 tick…"
	clock_card.body.add_child(_pulse_clock_label)
	page_vbox.add_child(clock_card.root)

	# 活跃事件卡
	var event_card := _make_card("活跃事件")
	_pulse_event_list = VBoxContainer.new()
	_pulse_event_list.add_theme_constant_override("separation", 4)
	event_card.body.add_child(_pulse_event_list)
	page_vbox.add_child(event_card.root)

	# NPC 一览卡
	var npc_card := _make_card("NPC 一览（点击切到 Inspector）")
	_pulse_npc_list = VBoxContainer.new()
	_pulse_npc_list.add_theme_constant_override("separation", 8)
	npc_card.body.add_child(_pulse_npc_list)
	page_vbox.add_child(npc_card.root)

	_append_tab_bottom_padding(page_vbox)
	return scroll


func _refresh_pulse_tab() -> void:
	if _pulse_clock_label == null:
		return
	_pulse_clock_label.text = _format_pulse_clock_text()
	_refresh_pulse_event_list()
	_refresh_pulse_npc_list()


func _format_pulse_clock_text() -> String:
	var clock = _world_pulse_data.get("clock", {})
	if not (clock is Dictionary) or (clock as Dictionary).is_empty():
		return "等待 tick…"
	var clock_dict := clock as Dictionary
	var day := int(clock_dict.get("day", 1))
	var hour := int(clock_dict.get("hour", 0))
	var minute := int(clock_dict.get("minute", 0))
	var phase := str(clock_dict.get("phase", "unknown"))
	var tick := int(clock_dict.get("tick", 0))
	return "Day %d · %02d:%02d · %s · tick %d" % [day, hour, minute, phase, tick]


func _refresh_pulse_event_list() -> void:
	if _pulse_event_list == null:
		return
	for child in _pulse_event_list.get_children():
		child.queue_free()
	var events = _world_pulse_data.get("activeEvents", [])
	if not (events is Array) or (events as Array).is_empty():
		var empty := Label.new()
		empty.text = "暂无活跃事件"
		empty.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		ResearchThemeScript.apply_label_style(empty, ResearchThemeScript.FONT_SIZE_SMALL, ResearchThemeScript.COLOR_TEXT_MUTED)
		_pulse_event_list.add_child(empty)
		return
	for item in events as Array:
		if not (item is Dictionary):
			continue
		var event_dict := item as Dictionary
		var row := HBoxContainer.new()
		row.add_theme_constant_override("separation", 6)
		var bullet := _make_dot(ResearchThemeScript.COLOR_TYPE_INTERRUPT, 8)
		row.add_child(bullet)
		var text_label := Label.new()
		text_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		text_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		var title := str(event_dict.get("title", event_dict.get("id", "event")))
		var location := _pretty_location(str(event_dict.get("locationId", "")))
		var phase := str(event_dict.get("phase", ""))
		text_label.text = "%s · %s%s" % [title, location, (" · " + phase) if phase != "" else ""]
		ResearchThemeScript.apply_label_style(text_label, ResearchThemeScript.FONT_SIZE_BODY, ResearchThemeScript.COLOR_TEXT_PRIMARY)
		row.add_child(text_label)
		_pulse_event_list.add_child(row)


func _refresh_pulse_npc_list() -> void:
	if _pulse_npc_list == null:
		return
	for child in _pulse_npc_list.get_children():
		child.queue_free()
	var rows = _world_pulse_data.get("npcRows", [])
	if not (rows is Array) or (rows as Array).is_empty():
		var empty := Label.new()
		empty.text = "等待 /api/world/state 返回 NPC 计划…"
		empty.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		ResearchThemeScript.apply_label_style(empty, ResearchThemeScript.FONT_SIZE_SMALL, ResearchThemeScript.COLOR_TEXT_MUTED)
		_pulse_npc_list.add_child(empty)
		return
	for item in rows as Array:
		if not (item is Dictionary):
			continue
		var entry := item as Dictionary
		_pulse_npc_list.add_child(_build_pulse_npc_row(entry))


func _build_pulse_npc_row(entry: Dictionary) -> Button:
	var npc_id := str(entry.get("npcId", ""))
	var npc_name := str(entry.get("name", npc_id))
	var status := str(entry.get("status", ""))
	var location := str(entry.get("location", ""))
	var accent_color := ResearchThemeScript.COLOR_ACCENT
	if entry.has("color") and entry["color"] is Color:
		accent_color = entry["color"]
	var button := Button.new()
	button.focus_mode = Control.FOCUS_NONE
	button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	button.custom_minimum_size = Vector2(0.0, ResearchThemeScript.scale_px(PULSE_NPC_ROW_MIN_HEIGHT))
	button.toggle_mode = false
	button.text = ""
	ResearchThemeScript.apply_button_style(button, ResearchThemeScript.FONT_SIZE_BODY)

	# 双层布局：第一行显示 NPC 与地点，第二行显示状态，非全屏也能完整阅读 6 个 NPC。
	var inner := VBoxContainer.new()
	inner.add_theme_constant_override("separation", 4)
	inner.mouse_filter = Control.MOUSE_FILTER_IGNORE
	inner.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	button.add_child(inner)
	# 把 inner 居中显示在 Button 内部。
	inner.anchor_left = 0.0
	inner.anchor_top = 0.0
	inner.anchor_right = 1.0
	inner.anchor_bottom = 1.0
	inner.offset_left = 8
	inner.offset_right = -8
	inner.offset_top = 6
	inner.offset_bottom = -6
	var head_row := HBoxContainer.new()
	head_row.add_theme_constant_override("separation", 8)
	inner.add_child(head_row)
	var dot := _make_dot(accent_color, 10)
	head_row.add_child(dot)
	var name_label := Label.new()
	name_label.text = npc_name
	name_label.custom_minimum_size = Vector2(ResearchThemeScript.scale_px(PULSE_NPC_NAME_MIN_WIDTH), 0)
	name_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	name_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	ResearchThemeScript.apply_label_style(name_label, ResearchThemeScript.FONT_SIZE_BODY, ResearchThemeScript.COLOR_TEXT_PRIMARY)
	head_row.add_child(name_label)
	var filler := Control.new()
	filler.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	filler.mouse_filter = Control.MOUSE_FILTER_IGNORE
	head_row.add_child(filler)
	if location != "":
		var loc_chip := _make_chip(_pretty_location(location), ResearchThemeScript.COLOR_BORDER_SOFT)
		head_row.add_child(loc_chip)
	var status_label := Label.new()
	status_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	status_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	status_label.text = status if status != "" else "—"
	status_label.max_lines_visible = 3
	ResearchThemeScript.apply_label_style(status_label, ResearchThemeScript.FONT_SIZE_SMALL, ResearchThemeScript.COLOR_TEXT_MUTED)
	inner.add_child(status_label)
	if npc_id != "":
		button.pressed.connect(func(): select_npc_requested.emit(npc_id))
	return button


# ---------------------------------------------------------------------------
# Tab 2 · 选中 NPC（Inspector）
# ---------------------------------------------------------------------------

func _build_inspector_tab() -> Control:
	var scroll := ScrollContainer.new()
	var vbox := VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 10)
	_setup_tab_scroll(scroll, vbox)

	# 身份卡
	var identity_card := _make_card("身份")
	var grid := GridContainer.new()
	grid.columns = 2
	grid.add_theme_constant_override("h_separation", 14)
	grid.add_theme_constant_override("v_separation", 4)
	identity_card.body.add_child(grid)
	_identity_name_label = _add_identity_row(grid, "名称", "未选择")
	_identity_id_label = _add_identity_row(grid, "npcId", "-")
	_identity_location_label = _add_identity_row(grid, "location", "-")
	_identity_anchor_label = _add_identity_row(grid, "anchor", "-")
	var status_row := HBoxContainer.new()
	status_row.add_theme_constant_override("separation", 8)
	identity_card.body.add_child(status_row)
	_inspector_status_value = Label.new()
	_inspector_status_value.text = "状态：等待"
	_inspector_status_value.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_inspector_status_value.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	ResearchThemeScript.apply_label_style(_inspector_status_value, ResearchThemeScript.FONT_SIZE_SMALL, ResearchThemeScript.COLOR_STATUS_OK)
	status_row.add_child(_inspector_status_value)
	_phase2_retry_button = Button.new()
	_phase2_retry_button.text = "重试"
	_phase2_retry_button.focus_mode = Control.FOCUS_NONE
	_phase2_retry_button.visible = false
	ResearchThemeScript.apply_button_style(_phase2_retry_button, ResearchThemeScript.FONT_SIZE_SMALL)
	_phase2_retry_button.pressed.connect(_on_retry_pressed)
	status_row.add_child(_phase2_retry_button)
	vbox.add_child(identity_card.root)

	# Motivation 卡
	var motivation_card := _make_card("Motivation")
	_motivation_need_label = Label.new()
	_motivation_need_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	ResearchThemeScript.apply_label_style(_motivation_need_label, ResearchThemeScript.FONT_SIZE_BODY, ResearchThemeScript.COLOR_TEXT_PRIMARY)
	_motivation_need_label.text = "需求：等待数据"
	motivation_card.body.add_child(_motivation_need_label)
	_motivation_need_bar = ProgressBar.new()
	_motivation_need_bar.min_value = 0.0
	_motivation_need_bar.max_value = 1.0
	_motivation_need_bar.value = 0.0
	_motivation_need_bar.show_percentage = false
	_motivation_need_bar.custom_minimum_size = Vector2(0, 8)
	var bar_bg := StyleBoxFlat.new()
	bar_bg.bg_color = Color(0.12, 0.16, 0.22, 0.92)
	bar_bg.set_corner_radius_all(4)
	var bar_fg := StyleBoxFlat.new()
	bar_fg.bg_color = ResearchThemeScript.COLOR_ACCENT
	bar_fg.set_corner_radius_all(4)
	_motivation_need_bar.add_theme_stylebox_override("background", bar_bg)
	_motivation_need_bar.add_theme_stylebox_override("fill", bar_fg)
	motivation_card.body.add_child(_motivation_need_bar)
	_motivation_decision_label = Label.new()
	_motivation_decision_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	ResearchThemeScript.apply_label_style(_motivation_decision_label, ResearchThemeScript.FONT_SIZE_BODY, ResearchThemeScript.COLOR_ACCENT)
	_motivation_decision_label.text = "决策：—"
	motivation_card.body.add_child(_motivation_decision_label)
	var sources_title := Label.new()
	sources_title.text = "contributingSources"
	ResearchThemeScript.apply_label_style(sources_title, ResearchThemeScript.FONT_SIZE_SMALL, ResearchThemeScript.COLOR_TEXT_MUTED)
	motivation_card.body.add_child(sources_title)
	_motivation_sources_box = HBoxContainer.new()
	_motivation_sources_box.add_theme_constant_override("separation", 6)
	motivation_card.body.add_child(_motivation_sources_box)
	vbox.add_child(motivation_card.root)

	# 主观记忆卡（subjectiveMemory）
	var memory_card := _make_card("subjectiveMemory")
	_memory_summary_label = Label.new()
	_memory_summary_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	ResearchThemeScript.apply_label_style(_memory_summary_label, ResearchThemeScript.FONT_SIZE_SMALL, ResearchThemeScript.COLOR_TEXT_MUTED)
	_memory_summary_label.text = SECTION_EMPTY_TEXT["subjectiveMemory"]
	memory_card.body.add_child(_memory_summary_label)
	_memory_list = VBoxContainer.new()
	_memory_list.add_theme_constant_override("separation", 6)
	memory_card.body.add_child(_memory_list)
	vbox.add_child(memory_card.root)

	# 关系边卡（relationshipEdges）
	var relationship_card := _make_card("relationshipEdges（点击 chip 高亮地图 NPC）")
	_relationship_summary_label = Label.new()
	_relationship_summary_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	ResearchThemeScript.apply_label_style(_relationship_summary_label, ResearchThemeScript.FONT_SIZE_SMALL, ResearchThemeScript.COLOR_TEXT_MUTED)
	_relationship_summary_label.text = SECTION_EMPTY_TEXT["relationshipEdges"]
	relationship_card.body.add_child(_relationship_summary_label)
	_relationship_list = VBoxContainer.new()
	_relationship_list.add_theme_constant_override("separation", 4)
	relationship_card.body.add_child(_relationship_list)
	vbox.add_child(relationship_card.root)

	# 启发式卡（heuristics）
	var heuristic_card := _make_card("heuristics")
	_heuristic_summary_label = Label.new()
	_heuristic_summary_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	ResearchThemeScript.apply_label_style(_heuristic_summary_label, ResearchThemeScript.FONT_SIZE_SMALL, ResearchThemeScript.COLOR_TEXT_MUTED)
	_heuristic_summary_label.text = SECTION_EMPTY_TEXT["heuristics"]
	heuristic_card.body.add_child(_heuristic_summary_label)
	_heuristic_list = VBoxContainer.new()
	_heuristic_list.add_theme_constant_override("separation", 4)
	heuristic_card.body.add_child(_heuristic_list)
	vbox.add_child(heuristic_card.root)

	_append_tab_bottom_padding(vbox)
	return scroll


func _add_identity_row(grid: GridContainer, key: String, default_text: String) -> Label:
	var key_label := Label.new()
	key_label.text = key
	ResearchThemeScript.apply_label_style(key_label, ResearchThemeScript.FONT_SIZE_SMALL, ResearchThemeScript.COLOR_TEXT_MUTED)
	grid.add_child(key_label)
	var value_label := Label.new()
	value_label.text = default_text
	value_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	value_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	ResearchThemeScript.apply_label_style(value_label, ResearchThemeScript.FONT_SIZE_BODY, ResearchThemeScript.COLOR_TEXT_PRIMARY)
	grid.add_child(value_label)
	return value_label


func _render_empty_motivation() -> void:
	if _motivation_need_label == null:
		return
	_motivation_need_label.text = "需求：等待 motivation 数据"
	_motivation_need_bar.value = 0.0
	_motivation_decision_label.text = "决策：—"
	for child in _motivation_sources_box.get_children():
		child.queue_free()


func _render_motivation(payload: Dictionary, summary: Dictionary) -> void:
	var items := _payload_items(payload.get("motivation", {}))
	if items.is_empty():
		_render_empty_motivation()
		# fallback 用 town_map 拼好的文本，保证字段在面板里至少能看到。
		_motivation_decision_label.text = _section_summary_text(summary, "motivation")
		return
	var focus = items[0]
	if not (focus is Dictionary):
		_render_empty_motivation()
		return
	var focus_dict := focus as Dictionary
	var primary_need = focus_dict.get("primaryNeed", {})
	var need_id := ""
	var urgency := 0.0
	var current := 0.0
	if primary_need is Dictionary:
		need_id = str((primary_need as Dictionary).get("needId", "unknown"))
		urgency = float((primary_need as Dictionary).get("urgency", 0.0))
		current = float((primary_need as Dictionary).get("current", 0.0))
	_motivation_need_label.text = "%s · urgency %.2f · current %.2f" % [_need_label(need_id), urgency, current]
	_motivation_need_bar.value = clampf(urgency, 0.0, 1.0)

	var decision = focus_dict.get("decision", {})
	var tool_id := ""
	if decision is Dictionary:
		tool_id = str((decision as Dictionary).get("selectedToolId", ""))
	if tool_id == "":
		tool_id = "—"
	_motivation_decision_label.text = "selectedToolId · %s" % tool_id

	for child in _motivation_sources_box.get_children():
		child.queue_free()
	var sources := []
	if decision is Dictionary:
		var raw_sources = (decision as Dictionary).get("contributingSources", [])
		if raw_sources is Array:
			sources = raw_sources as Array
	if sources.is_empty():
		var empty_chip := _make_chip("无 contributing source", ResearchThemeScript.COLOR_BORDER_SOFT)
		_motivation_sources_box.add_child(empty_chip)
	else:
		var count: int = mini(sources.size(), 4)
		for i in range(count):
			var source = sources[i]
			if not (source is Dictionary):
				continue
			var source_type := str((source as Dictionary).get("type", "source"))
			var chip := _make_chip(_short_source_label(source_type), ResearchThemeScript.contributing_source_color(source_type))
			_motivation_sources_box.add_child(chip)
		if sources.size() > 4:
			_motivation_sources_box.add_child(_make_chip("+%d" % (sources.size() - 4), ResearchThemeScript.COLOR_BORDER_SOFT))


func _render_empty_memory() -> void:
	if _memory_list == null:
		return
	for child in _memory_list.get_children():
		child.queue_free()
	_memory_summary_label.text = SECTION_EMPTY_TEXT["subjectiveMemory"]


func _render_memory(payload: Dictionary, summary: Dictionary) -> void:
	var items := _payload_items(payload.get("subjectiveMemory", {}))
	for child in _memory_list.get_children():
		child.queue_free()
	if items.is_empty():
		_memory_summary_label.text = _section_summary_text(summary, "subjectiveMemory")
		return
	# 按 effectiveSalience 排序取 top N。
	var sortable: Array = []
	for item in items:
		if item is Dictionary:
			sortable.append((item as Dictionary).duplicate(true))
	sortable.sort_custom(func(a, b):
		return float(a.get("effectiveSalience", a.get("salience", 0.0))) > float(b.get("effectiveSalience", b.get("salience", 0.0))))
	var shown: int = mini(sortable.size(), MEMORY_CARD_TOP_N)
	_memory_summary_label.text = "共 %d 条，显示 salience 最高 %d 条" % [items.size(), shown]
	for i in range(shown):
		_memory_list.add_child(_build_memory_row(sortable[i]))


func _build_memory_row(entry: Dictionary) -> Control:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 8)
	var valence := float(entry.get("emotionalValence", 0.0))
	var dot := _make_dot(ResearchThemeScript.valence_color(valence), 9)
	row.add_child(dot)
	var inner_vbox := VBoxContainer.new()
	inner_vbox.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	inner_vbox.add_theme_constant_override("separation", 2)
	row.add_child(inner_vbox)
	var text_label := Label.new()
	text_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	text_label.text = _truncate_text(str(entry.get("text", "")), 110)
	ResearchThemeScript.apply_label_style(text_label, ResearchThemeScript.FONT_SIZE_BODY, ResearchThemeScript.COLOR_TEXT_PRIMARY)
	inner_vbox.add_child(text_label)
	var meta_row := HBoxContainer.new()
	meta_row.add_theme_constant_override("separation", 6)
	inner_vbox.add_child(meta_row)
	var valence_chip := _make_chip("valence %.2f" % valence, ResearchThemeScript.valence_color(valence))
	meta_row.add_child(valence_chip)
	var salience := float(entry.get("effectiveSalience", entry.get("salience", 0.0)))
	meta_row.add_child(_make_chip("salience %.2f" % salience, ResearchThemeScript.COLOR_BORDER_SOFT))
	var tick := int(entry.get("createdTick", -1))
	if tick >= 0:
		meta_row.add_child(_make_chip("t%d" % tick, ResearchThemeScript.COLOR_BORDER_SOFT))
	return row


func _render_empty_relationships() -> void:
	if _relationship_list == null:
		return
	for child in _relationship_list.get_children():
		child.queue_free()
	_relationship_summary_label.text = SECTION_EMPTY_TEXT["relationshipEdges"]


func _render_relationships(payload: Dictionary, summary: Dictionary) -> void:
	var items := _payload_items(payload.get("relationshipEdges", {}))
	for child in _relationship_list.get_children():
		child.queue_free()
	if items.is_empty():
		_relationship_summary_label.text = _section_summary_text(summary, "relationshipEdges")
		return
	var sortable: Array = []
	for item in items:
		if item is Dictionary:
			sortable.append((item as Dictionary).duplicate(true))
	sortable.sort_custom(func(a, b):
		return absf(float(a.get("strength", 0.0))) > absf(float(b.get("strength", 0.0))))
	var shown: int = mini(sortable.size(), 6)
	_relationship_summary_label.text = "共 %d 条，按 |strength| 排序" % items.size()
	var chip_row := HBoxContainer.new()
	chip_row.add_theme_constant_override("separation", 6)
	_relationship_list.add_child(chip_row)
	var current_row := chip_row
	var row_chip_count := 0
	for i in range(shown):
		var edge := sortable[i] as Dictionary
		var target_id := str(edge.get("targetAgentId", "?"))
		var edge_type := str(edge.get("edgeType", "edge"))
		var strength := float(edge.get("strength", 0.0))
		var sign_text := "+" if strength >= 0.0 else ""
		var label_text := "%s · %s · %s%.2f" % [edge_type, target_id, sign_text, strength]
		var color := ResearchThemeScript.contributing_source_color("relationship_edge_refs")
		var chip_button := _make_chip_button(label_text, color)
		var captured_id := target_id
		chip_button.pressed.connect(func(): highlight_npcs_requested.emit([captured_id]))
		current_row.add_child(chip_button)
		row_chip_count += 1
		if row_chip_count >= 2:
			current_row = HBoxContainer.new()
			current_row.add_theme_constant_override("separation", 6)
			_relationship_list.add_child(current_row)
			row_chip_count = 0


func _render_empty_heuristics() -> void:
	if _heuristic_list == null:
		return
	for child in _heuristic_list.get_children():
		child.queue_free()
	_heuristic_summary_label.text = SECTION_EMPTY_TEXT["heuristics"]


func _render_heuristics(payload: Dictionary, summary: Dictionary) -> void:
	var items := _payload_items(payload.get("heuristics", {}))
	for child in _heuristic_list.get_children():
		child.queue_free()
	if items.is_empty():
		_heuristic_summary_label.text = _section_summary_text(summary, "heuristics")
		return
	var sortable: Array = []
	for item in items:
		if item is Dictionary:
			sortable.append((item as Dictionary).duplicate(true))
	sortable.sort_custom(func(a, b):
		return float(a.get("effectiveConfidence", a.get("confidence", 0.0))) > float(b.get("effectiveConfidence", b.get("confidence", 0.0))))
	var shown: int = mini(sortable.size(), 5)
	_heuristic_summary_label.text = "共 %d 条，按 effectiveConfidence 排序" % items.size()
	for i in range(shown):
		_heuristic_list.add_child(_build_heuristic_row(sortable[i]))


func _build_heuristic_row(entry: Dictionary) -> Control:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 8)
	var trigger := str(entry.get("triggerPattern", entry.get("heuristicId", "heuristic")))
	var confidence := float(entry.get("effectiveConfidence", entry.get("confidence", 0.0)))
	var status_text := str(entry.get("status", ""))
	var status_color := ResearchThemeScript.COLOR_VALENCE_POS if status_text == "active" else ResearchThemeScript.COLOR_TEXT_MUTED
	var dot := _make_dot(status_color, 8)
	row.add_child(dot)
	var label := Label.new()
	label.text = trigger
	label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	ResearchThemeScript.apply_label_style(label, ResearchThemeScript.FONT_SIZE_BODY, ResearchThemeScript.COLOR_TEXT_PRIMARY)
	row.add_child(label)
	var bar := ProgressBar.new()
	bar.min_value = 0.0
	bar.max_value = 1.0
	bar.value = clampf(confidence, 0.0, 1.0)
	bar.show_percentage = false
	bar.custom_minimum_size = Vector2(72, 6)
	var bar_bg := StyleBoxFlat.new()
	bar_bg.bg_color = Color(0.12, 0.16, 0.22, 0.92)
	bar_bg.set_corner_radius_all(3)
	var bar_fg := StyleBoxFlat.new()
	bar_fg.bg_color = ResearchThemeScript.contributing_source_color("heuristic_refs")
	bar_fg.set_corner_radius_all(3)
	bar.add_theme_stylebox_override("background", bar_bg)
	bar.add_theme_stylebox_override("fill", bar_fg)
	row.add_child(bar)
	var conf_label := Label.new()
	conf_label.text = "%.2f" % confidence
	conf_label.custom_minimum_size = Vector2(36, 0)
	ResearchThemeScript.apply_label_style(conf_label, ResearchThemeScript.FONT_SIZE_SMALL, ResearchThemeScript.COLOR_TEXT_MUTED)
	row.add_child(conf_label)
	return row


# ---------------------------------------------------------------------------
# Tab 3 · Trace 时间线
# ---------------------------------------------------------------------------

func _build_trace_tab() -> Control:
	var scroll := ScrollContainer.new()
	var vbox := VBoxContainer.new()
	vbox.add_theme_constant_override("separation", 10)
	_setup_tab_scroll(scroll, vbox)

	# 过滤 + 分页 + 复制条
	var control_card := _make_card("traceFilter（1-5 切换）")
	var filter_row := HBoxContainer.new()
	filter_row.add_theme_constant_override("separation", 4)
	control_card.body.add_child(filter_row)
	_trace_filter_buttons.clear()
	for i in range(TRACE_FILTER_IDS.size()):
		var filter_id := str(TRACE_FILTER_IDS[i])
		var button := Button.new()
		button.text = "%d %s" % [i + 1, str(TRACE_FILTER_LABELS.get(filter_id, filter_id))]
		button.focus_mode = Control.FOCUS_NONE
		button.toggle_mode = true
		button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		ResearchThemeScript.apply_button_style(button, ResearchThemeScript.FONT_SIZE_SMALL)
		button.pressed.connect(_select_trace_filter_by_index.bind(i))
		filter_row.add_child(button)
		_trace_filter_buttons.append(button)

	var nav_row := HBoxContainer.new()
	nav_row.add_theme_constant_override("separation", 6)
	control_card.body.add_child(nav_row)
	_trace_prev_button = Button.new()
	_trace_prev_button.text = "◀ Prev"
	_trace_prev_button.focus_mode = Control.FOCUS_NONE
	ResearchThemeScript.apply_button_style(_trace_prev_button, ResearchThemeScript.FONT_SIZE_SMALL)
	_trace_prev_button.pressed.connect(_on_trace_prev_pressed)
	nav_row.add_child(_trace_prev_button)
	_trace_next_button = Button.new()
	_trace_next_button.text = "Next ▶"
	_trace_next_button.focus_mode = Control.FOCUS_NONE
	ResearchThemeScript.apply_button_style(_trace_next_button, ResearchThemeScript.FONT_SIZE_SMALL)
	_trace_next_button.pressed.connect(_on_trace_next_pressed)
	nav_row.add_child(_trace_next_button)
	_trace_index_label = Label.new()
	_trace_index_label.text = "0/0"
	_trace_index_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_trace_index_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	ResearchThemeScript.apply_label_style(_trace_index_label, ResearchThemeScript.FONT_SIZE_SMALL, ResearchThemeScript.COLOR_TEXT_MUTED)
	nav_row.add_child(_trace_index_label)
	_trace_copy_button = Button.new()
	_trace_copy_button.text = "Copy trace"
	_trace_copy_button.focus_mode = Control.FOCUS_NONE
	ResearchThemeScript.apply_button_style(_trace_copy_button, ResearchThemeScript.FONT_SIZE_SMALL)
	_trace_copy_button.pressed.connect(_on_trace_copy_pressed)
	nav_row.add_child(_trace_copy_button)
	vbox.add_child(control_card.root)

	# 时间线（recentTraceEvents）
	var rows_card := _make_card("recentTraceEvents")
	_trace_summary_label = Label.new()
	_trace_summary_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	ResearchThemeScript.apply_label_style(_trace_summary_label, ResearchThemeScript.FONT_SIZE_SMALL, ResearchThemeScript.COLOR_TEXT_MUTED)
	_trace_summary_label.text = _trace_interaction_hint()
	rows_card.body.add_child(_trace_summary_label)
	_trace_rows_box = VBoxContainer.new()
	_trace_rows_box.add_theme_constant_override("separation", 4)
	rows_card.body.add_child(_trace_rows_box)
	vbox.add_child(rows_card.root)

	# Trace 详情（key-value 表）
	var details_card := _make_card("trace details")
	_trace_details_status_label = Label.new()
	_trace_details_status_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	ResearchThemeScript.apply_label_style(_trace_details_status_label, ResearchThemeScript.FONT_SIZE_SMALL, ResearchThemeScript.COLOR_TEXT_MUTED)
	_trace_details_status_label.text = SECTION_EMPTY_TEXT["traceDetails"]
	details_card.body.add_child(_trace_details_status_label)
	_trace_details_box = VBoxContainer.new()
	_trace_details_box.add_theme_constant_override("separation", 4)
	details_card.body.add_child(_trace_details_box)
	vbox.add_child(details_card.root)

	_update_trace_filter_button_states()
	_append_tab_bottom_padding(vbox)
	return scroll


func _select_trace_filter_by_index(index: int) -> void:
	if index < 0 or index >= TRACE_FILTER_IDS.size():
		return
	_current_trace_filter = str(TRACE_FILTER_IDS[index])
	_select_trace_focus_or_latest(false)
	_update_recent_trace_view()


func _update_trace_filter_button_states() -> void:
	if _trace_filter_buttons.is_empty():
		return
	for i in range(_trace_filter_buttons.size()):
		var button := _trace_filter_buttons[i]
		var filter_id := str(TRACE_FILTER_IDS[i])
		var active := filter_id == _current_trace_filter
		button.button_pressed = active
		var style := ResearchThemeScript.make_tab_style(active)
		button.add_theme_stylebox_override("normal", style)
		button.add_theme_stylebox_override("pressed", style)
		button.add_theme_stylebox_override("hover", style)


func _reset_recent_trace_view() -> void:
	_recent_trace_event_groups = _empty_filter_dict()
	_recent_trace_copy_detail_groups = _empty_filter_dict()
	_recent_trace_summaries = _empty_summary_dict()
	_current_trace_focus = {}
	_current_trace_detail_index = 0
	_current_trace_filter = "all"
	_hide_trace_details_popup()
	_update_recent_trace_view()


func _update_recent_trace_view() -> void:
	_update_trace_filter_button_states()
	var rows := _trace_events_for_filter()
	_rebuild_recent_trace_rows(rows)
	_update_recent_trace_detail_view()
	if _trace_summary_label != null:
		if rows.is_empty():
			_trace_summary_label.text = _trace_summary_text_for_filter()
		else:
			_trace_summary_label.text = _trace_interaction_hint()
	if _trace_prev_button != null:
		_trace_prev_button.disabled = rows.is_empty()
	if _trace_next_button != null:
		_trace_next_button.disabled = rows.is_empty()
	if _trace_copy_button != null:
		_trace_copy_button.disabled = rows.is_empty()


func _rebuild_recent_trace_rows(rows: Array) -> void:
	if _trace_rows_box == null:
		return
	for child in _trace_rows_box.get_children():
		child.queue_free()
	if rows.is_empty():
		return
	for i in range(rows.size()):
		if not (rows[i] is Dictionary):
			continue
		var entry := (rows[i] as Dictionary).duplicate(true)
		_trace_rows_box.add_child(_build_trace_row_button(entry, i))


func _build_trace_row_button(entry: Dictionary, row_index: int) -> Button:
	var event_type := _trace_event_type(entry)
	var tick_text := _trace_tick_text(entry)
	var summary := _truncate_text(str(entry.get("summary", "")), 64)
	var hint := _trace_detail_hint(entry.get("details", {}))
	var source_badge := _trace_source_badge(entry)
	var color := ResearchThemeScript.trace_type_color(event_type)
	var label_text := "%s  %s%s%s · %s" % [tick_text, _trace_row_type_label(event_type), hint, source_badge, summary]

	var button := Button.new()
	button.focus_mode = Control.FOCUS_NONE
	button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	button.custom_minimum_size = Vector2(0, 32)
	button.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	button.clip_text = true
	button.alignment = HORIZONTAL_ALIGNMENT_LEFT
	button.text = ("▶ " if row_index == _current_trace_detail_index else "• ") + label_text
	button.tooltip_text = _trace_row_tooltip(entry)
	button.add_theme_color_override("font_color", color)
	button.add_theme_color_override("font_hover_color", color)
	button.add_theme_font_override("font", ResearchThemeScript.get_system_font())
	button.add_theme_font_size_override("font_size", ResearchThemeScript.scaled_size(ResearchThemeScript.FONT_SIZE_BODY))
	# Trace 行使用极简 stylebox，避免按钮厚边压挤行高。
	var row_box := StyleBoxFlat.new()
	row_box.bg_color = Color(0.0, 0.0, 0.0, 0.12) if row_index != _current_trace_detail_index else Color(color.r, color.g, color.b, 0.20)
	row_box.set_corner_radius_all(6)
	row_box.content_margin_left = 8
	row_box.content_margin_right = 8
	row_box.content_margin_top = 4
	row_box.content_margin_bottom = 4
	row_box.border_color = color if row_index == _current_trace_detail_index else Color(0.0, 0.0, 0.0, 0.0)
	row_box.set_border_width_all(1 if row_index == _current_trace_detail_index else 0)
	button.add_theme_stylebox_override("normal", row_box)
	button.add_theme_stylebox_override("hover", row_box)
	button.add_theme_stylebox_override("pressed", row_box)
	button.add_theme_stylebox_override("focus", row_box)
	button.pressed.connect(_on_trace_row_pressed.bind(entry, row_index))
	return button


func _update_recent_trace_detail_view() -> void:
	if _trace_details_box == null or _trace_details_status_label == null:
		return
	for child in _trace_details_box.get_children():
		child.queue_free()
	var rows := _trace_events_for_filter()
	var item_count := rows.size()
	_update_trace_index_label(item_count)
	if item_count <= 0:
		_trace_details_status_label.text = SECTION_EMPTY_TEXT["traceDetails"]
		return
	_current_trace_detail_index = int(clamp(_current_trace_detail_index, 0, item_count - 1))
	var entry := rows[_current_trace_detail_index] as Dictionary
	var event_type := _trace_event_type(entry)
	_trace_details_status_label.text = "%s · trace=%s · span=%s" % [
		_trace_detail_type_label(event_type),
		str(entry.get("traceId", "-")),
		str(entry.get("spanId", "-")),
	]
	if event_type == "memory.result_observed":
		_trace_details_box.add_child(_make_trace_callout(
			"当前选中行：memory.result_observed（观察记忆）。这就是人工验收里的 memory.result_observed 行；点击上方紫色 trace 行会高亮观察者。"
		))
	_trace_details_box.add_child(_make_detail_kv("tick", _trace_tick_text(entry)))
	_trace_details_box.add_child(_make_detail_kv("type", event_type))
	_trace_details_box.add_child(_make_detail_kv("agentId", str(entry.get("agentId", "-"))))
	var target_ids = entry.get("targetIds", [])
	if target_ids is Array and not (target_ids as Array).is_empty():
		_trace_details_box.add_child(_make_detail_kv("targetIds", ", ".join((target_ids as Array).map(func(x): return str(x)))))
	var summary := str(entry.get("summary", ""))
	if summary != "":
		_trace_details_box.add_child(_make_detail_kv("summary", summary))
	# 证据链放在 details 前面，避免被较长 key-value 列表挤到视野外。
	_append_trace_source_links_section(entry)
	# details 折叠为多行 key-value
	var details = entry.get("details", {})
	if details is Dictionary:
		for key in (details as Dictionary).keys():
			var key_text := str(key)
			var value = (details as Dictionary)[key]
			_trace_details_box.add_child(_make_detail_kv(key_text, _value_to_text(value)))
	# 提供"展开完整 JSON"按钮
	var expand_row := HBoxContainer.new()
	expand_row.add_theme_constant_override("separation", 6)
	_trace_details_box.add_child(expand_row)
	var expand_btn := Button.new()
	expand_btn.text = "展开完整 JSON"
	expand_btn.focus_mode = Control.FOCUS_NONE
	ResearchThemeScript.apply_button_style(expand_btn, ResearchThemeScript.FONT_SIZE_SMALL)
	expand_btn.pressed.connect(_show_trace_details_popup.bind(entry))
	expand_row.add_child(expand_btn)


func _make_detail_kv(key: String, value_text: String) -> Control:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 8)
	var key_label := Label.new()
	key_label.text = key
	key_label.custom_minimum_size = Vector2(110, 0)
	ResearchThemeScript.apply_label_style(key_label, ResearchThemeScript.FONT_SIZE_SMALL, ResearchThemeScript.COLOR_TEXT_MUTED)
	row.add_child(key_label)
	var value_label := Label.new()
	value_label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	value_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	value_label.text = _truncate_text(value_text, 320)
	ResearchThemeScript.apply_label_style(value_label, ResearchThemeScript.FONT_SIZE_SMALL, ResearchThemeScript.COLOR_TEXT_PRIMARY)
	row.add_child(value_label)
	return row


func _make_trace_callout(text: String) -> Control:
	# 真实窗口验收要能一眼确认当前 trace 类型，避免只在 key-value 里找字段。
	var panel := PanelContainer.new()
	panel.add_theme_stylebox_override("panel", ResearchThemeScript.make_chip_style(ResearchThemeScript.COLOR_ACCENT))
	var label := Label.new()
	label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	label.text = text
	ResearchThemeScript.apply_label_style(label, ResearchThemeScript.FONT_SIZE_SMALL, ResearchThemeScript.COLOR_TEXT_PRIMARY)
	panel.add_child(label)
	return panel


func _append_trace_source_links_section(entry: Dictionary) -> void:
	var title := Label.new()
	title.text = "证据链"
	ResearchThemeScript.apply_label_style(title, ResearchThemeScript.FONT_SIZE_SMALL, ResearchThemeScript.COLOR_ACCENT)
	_trace_details_box.add_child(title)
	var links = entry.get("sourceLinks", [])
	if not (links is Array) or (links as Array).is_empty():
		var empty := Label.new()
		empty.text = "无直接来源事件"
		ResearchThemeScript.apply_label_style(empty, ResearchThemeScript.FONT_SIZE_SMALL, ResearchThemeScript.COLOR_TEXT_MUTED)
		_trace_details_box.add_child(empty)
		return
	var hint := Label.new()
	hint.text = "下方是可点击按钮；点击后会重新拉取并聚焦直接来源事件。"
	ResearchThemeScript.apply_label_style(hint, ResearchThemeScript.FONT_SIZE_SMALL, ResearchThemeScript.COLOR_TEXT_MUTED)
	_trace_details_box.add_child(hint)
	var current_row := HBoxContainer.new()
	current_row.add_theme_constant_override("separation", 6)
	_trace_details_box.add_child(current_row)
	var row_chip_count := 0
	for index in range((links as Array).size()):
		var item = (links as Array)[index]
		if not (item is Dictionary):
			continue
		var link := item as Dictionary
		var event_id := str(link.get("eventId", ""))
		var label := "点击跳转来源事件 · %s" % _trace_row_type_label(str(link.get("eventType", "trace")))
		if event_id != "":
			label = "%s · %s" % [label, event_id.substr(0, min(10, event_id.length()))]
		var chip := _make_chip_button(label, ResearchThemeScript.trace_type_color(str(link.get("eventType", ""))))
		chip.tooltip_text = "%s\n%s" % [str(link.get("summary", "")), event_id]
		chip.pressed.connect(_on_trace_source_link_pressed.bind(link))
		current_row.add_child(chip)
		row_chip_count += 1
		if row_chip_count >= 2 and index < (links as Array).size() - 1:
			current_row = HBoxContainer.new()
			current_row.add_theme_constant_override("separation", 6)
			_trace_details_box.add_child(current_row)
			row_chip_count = 0


func _value_to_text(value) -> String:
	if value == null:
		return "null"
	if value is Dictionary or value is Array:
		return JSON.stringify(value)
	return str(value)


func _select_latest_trace_detail() -> void:
	var rows := _trace_events_for_filter()
	_current_trace_detail_index = max(0, rows.size() - 1)


func _select_trace_focus_or_latest(allow_filter_switch: bool = false) -> void:
	var rows := _trace_events_for_filter()
	if rows.is_empty():
		_current_trace_detail_index = 0
	var focus_event_id := str(_current_trace_focus.get("eventId", ""))
	var focus_trace_id := str(_current_trace_focus.get("traceId", ""))
	var requested = _current_trace_focus.get("requested", {})
	if requested is Dictionary:
		var requested_dict := requested as Dictionary
		if focus_event_id == "":
			focus_event_id = str(requested_dict.get("eventId", ""))
		if focus_trace_id == "":
			focus_trace_id = str(requested_dict.get("traceId", ""))
	if allow_filter_switch and (focus_event_id != "" or focus_trace_id != ""):
		var all_rows = _recent_trace_event_groups.get("all", [])
		if all_rows is Array:
			for item in all_rows as Array:
				if not (item is Dictionary):
					continue
				var focus_entry := item as Dictionary
				var entry_event_id := str(focus_entry.get("eventId", ""))
				var entry_trace_id := str(focus_entry.get("traceId", ""))
				if (focus_event_id != "" and entry_event_id == focus_event_id) or (focus_trace_id != "" and entry_trace_id == focus_trace_id):
					_current_trace_filter = _trace_filter_for_event_type(_trace_event_type(focus_entry))
					rows = _trace_events_for_filter()
					break
	if rows.is_empty():
		_current_trace_detail_index = 0
		return
	if focus_event_id != "" or focus_trace_id != "":
		for i in range(rows.size()):
			if not (rows[i] is Dictionary):
				continue
			var entry := rows[i] as Dictionary
			if focus_event_id != "" and str(entry.get("eventId", "")) == focus_event_id:
				_current_trace_detail_index = i
				return
			if focus_trace_id != "" and str(entry.get("traceId", "")) == focus_trace_id:
				_current_trace_detail_index = i
				return
	_select_latest_trace_detail()


func _trace_copy_payload_for_current() -> Dictionary:
	var rows := _trace_events_for_filter()
	if rows.is_empty() or _current_trace_detail_index >= rows.size():
		return {}
	if not (rows[_current_trace_detail_index] is Dictionary):
		return {}
	var payload := (rows[_current_trace_detail_index] as Dictionary).duplicate(true)
	if not _current_trace_focus.is_empty():
		payload["traceFocus"] = _current_trace_focus.duplicate(true)
	return payload


func _update_trace_index_label(item_count: int) -> void:
	if _trace_index_label == null:
		return
	if item_count <= 0:
		_trace_index_label.text = "0/0"
		return
	_trace_index_label.text = "%d/%d" % [_current_trace_detail_index + 1, item_count]


func _on_trace_prev_pressed() -> void:
	var item_count := _trace_events_for_filter().size()
	if item_count <= 0:
		return
	_current_trace_detail_index = max(0, _current_trace_detail_index - 1)
	_update_recent_trace_view()


func _on_trace_next_pressed() -> void:
	var item_count := _trace_events_for_filter().size()
	if item_count <= 0:
		return
	_current_trace_detail_index = min(item_count - 1, _current_trace_detail_index + 1)
	_update_recent_trace_view()


func _on_trace_copy_pressed() -> void:
	var copy_payload := _trace_copy_payload_for_current()
	if copy_payload.is_empty():
		return
	var copy_text := JSON.stringify(copy_payload, "\t")
	if copy_text == "":
		return
	DisplayServer.clipboard_set(copy_text)
	_set_phase2_status("已复制当前 trace JSON")


func _on_trace_row_pressed(entry: Dictionary, row_index: int) -> void:
	_current_trace_detail_index = row_index
	_update_recent_trace_view()
	var event_type := _trace_event_type(entry)
	if event_type == "motivation.decision_made":
		_hide_trace_details_popup()
		_emit_highlight(_decision_trace_agent_ids(entry), "decision trace")
		return
	if event_type == "memory.result_observed":
		_hide_trace_details_popup()
		_emit_highlight(_memory_observer_ids(entry), "memory observers")
		return
	if event_type in ["tool.execution_completed", "tool.execution_failed", "tool.execution_interrupted"]:
		_hide_trace_details_popup()
		_emit_highlight(_decision_trace_agent_ids(entry), "tool trace")
		return
	# 其它类型直接展开完整 JSON 弹层
	_show_trace_details_popup(entry)


func _on_trace_source_link_pressed(link: Dictionary) -> void:
	var event_id := str(link.get("eventId", ""))
	var trace_id := str(link.get("traceId", ""))
	if event_id == "" and trace_id == "":
		_set_phase2_status("source link 缺少 eventId / traceId")
		return
	_hide_trace_details_popup()
	_emit_highlight(_source_link_agent_ids(link), "source trace")
	trace_source_requested.emit(_current_npc_id, event_id, trace_id)
	_set_phase2_status("跳转 source：%s" % (event_id if event_id != "" else trace_id))


func _on_retry_pressed() -> void:
	if _current_npc_id == "":
		return
	_set_phase2_status("重试加载中…")
	_set_retry_visible(false)
	retry_requested.emit(_current_npc_id)


# ---------------------------------------------------------------------------
# Trace details 弹层（旧"完整 JSON 弹层"路径，便于 paper 截图）
# ---------------------------------------------------------------------------

func _build_trace_detail_popup() -> void:
	_trace_detail_popup = PanelContainer.new()
	_trace_detail_popup.name = "TraceDetailsPopup"
	_trace_detail_popup.visible = false
	_trace_detail_popup.anchor_left = 0.0
	_trace_detail_popup.anchor_top = 0.0
	_trace_detail_popup.anchor_right = 1.0
	_trace_detail_popup.anchor_bottom = 1.0
	_trace_detail_popup.offset_left = 16.0
	_trace_detail_popup.offset_top = 84.0
	_trace_detail_popup.offset_right = -16.0
	_trace_detail_popup.offset_bottom = -16.0
	_trace_detail_popup.mouse_filter = Control.MOUSE_FILTER_STOP
	_trace_detail_popup.z_index = 60
	_trace_detail_popup.add_theme_stylebox_override("panel", ResearchThemeScript.make_panel_style(Color(0.02, 0.04, 0.06, 0.97), ResearchThemeScript.COLOR_ACCENT))
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
	ResearchThemeScript.apply_label_style(_trace_detail_popup_title, ResearchThemeScript.FONT_SIZE_SUBTITLE, ResearchThemeScript.COLOR_ACCENT)
	title_row.add_child(_trace_detail_popup_title)
	var close_btn := Button.new()
	close_btn.text = "关闭 [Esc]"
	close_btn.focus_mode = Control.FOCUS_NONE
	ResearchThemeScript.apply_button_style(close_btn, ResearchThemeScript.FONT_SIZE_SMALL)
	close_btn.pressed.connect(_hide_trace_details_popup)
	title_row.add_child(close_btn)
	_trace_detail_scroll = ScrollContainer.new()
	_trace_detail_scroll.focus_mode = Control.FOCUS_NONE
	_trace_detail_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	_trace_detail_scroll.custom_minimum_size = Vector2(0.0, 280.0)
	column.add_child(_trace_detail_scroll)
	_trace_detail_popup_value = Label.new()
	_trace_detail_popup_value.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	ResearchThemeScript.apply_label_style(_trace_detail_popup_value, ResearchThemeScript.FONT_SIZE_SMALL, Color(0.93, 0.97, 1.0, 1.0))
	_trace_detail_scroll.add_child(_trace_detail_popup_value)


func _show_trace_details_popup(entry: Dictionary) -> void:
	if _trace_detail_popup == null:
		return
	var event_type := _trace_event_type(entry)
	var trace_id := str(entry.get("traceId", entry.get("id", "-")))
	_trace_detail_popup_title.text = "%s · %s" % [_pretty_trace_type(event_type), trace_id]
	var details = entry.get("details", {})
	var detail_text := "{}"
	if details is Dictionary or details is Array:
		detail_text = JSON.stringify(details, "\t")
	else:
		detail_text = str(details)
	if detail_text.length() > DETAIL_POPUP_MAX_CHARS:
		detail_text = "%s\n... 已截断，Copy trace 可复制完整。" % detail_text.substr(0, DETAIL_POPUP_MAX_CHARS)
	_trace_detail_popup_value.text = detail_text
	_trace_detail_popup.visible = true
	call_deferred("_reset_trace_detail_scroll")


func _reset_trace_detail_scroll() -> void:
	if _trace_detail_scroll != null:
		_trace_detail_scroll.scroll_vertical = 0


func _hide_trace_details_popup() -> void:
	if _trace_detail_popup != null:
		_trace_detail_popup.visible = false


func _is_trace_detail_popup_visible() -> bool:
	return _trace_detail_popup != null and _trace_detail_popup.visible


# ---------------------------------------------------------------------------
# 公共小工具
# ---------------------------------------------------------------------------

func _switch_tab(next_tab: int) -> void:
	_current_tab = int(clamp(next_tab, 0, _tab_pages.size() - 1))
	for i in range(_tab_pages.size()):
		_tab_pages[i].visible = i == _current_tab
	for i in range(_tab_buttons.size()):
		var button := _tab_buttons[i]
		var active := i == _current_tab
		button.button_pressed = active
		var style := ResearchThemeScript.make_tab_style(active)
		button.add_theme_stylebox_override("normal", style)
		button.add_theme_stylebox_override("pressed", style)
		button.add_theme_stylebox_override("hover", style)


func _make_card(title_text: String) -> Dictionary:
	var card := PanelContainer.new()
	card.add_theme_stylebox_override("panel", ResearchThemeScript.make_card_style())
	var margin := MarginContainer.new()
	margin.add_theme_constant_override("margin_left", int(round(ResearchThemeScript.scale_px(12.0))))
	margin.add_theme_constant_override("margin_right", int(round(ResearchThemeScript.scale_px(12.0))))
	margin.add_theme_constant_override("margin_top", int(round(ResearchThemeScript.scale_px(10.0))))
	margin.add_theme_constant_override("margin_bottom", int(round(ResearchThemeScript.scale_px(10.0))))
	card.add_child(margin)
	var column := VBoxContainer.new()
	column.add_theme_constant_override("separation", int(round(ResearchThemeScript.scale_px(6.0))))
	margin.add_child(column)
	var title := Label.new()
	title.text = title_text
	ResearchThemeScript.apply_label_style(title, ResearchThemeScript.FONT_SIZE_SUBTITLE, ResearchThemeScript.COLOR_TEXT_TITLE)
	column.add_child(title)
	var body := VBoxContainer.new()
	body.add_theme_constant_override("separation", int(round(ResearchThemeScript.scale_px(6.0))))
	column.add_child(body)
	return {"root": card, "body": body}


func _make_chip(text: String, accent: Color) -> Control:
	var chip := PanelContainer.new()
	chip.add_theme_stylebox_override("panel", ResearchThemeScript.make_chip_style(accent))
	var label := Label.new()
	label.text = text
	ResearchThemeScript.apply_label_style(label, ResearchThemeScript.FONT_SIZE_CHIP, accent)
	chip.add_child(label)
	return chip


func _make_chip_button(text: String, accent: Color) -> Button:
	var button := Button.new()
	button.text = text
	button.focus_mode = Control.FOCUS_NONE
	button.custom_minimum_size = Vector2(0, 28)
	button.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	button.add_theme_font_override("font", ResearchThemeScript.get_system_font())
	button.add_theme_font_size_override("font_size", ResearchThemeScript.scaled_size(ResearchThemeScript.FONT_SIZE_CHIP))
	button.add_theme_color_override("font_color", accent)
	button.add_theme_color_override("font_hover_color", ResearchThemeScript.COLOR_TEXT_PRIMARY)
	var style := ResearchThemeScript.make_chip_style(accent)
	var hover_style := ResearchThemeScript.make_chip_style(accent)
	hover_style.bg_color = Color(accent.r * 0.4, accent.g * 0.4, accent.b * 0.4, 0.85)
	button.add_theme_stylebox_override("normal", style)
	button.add_theme_stylebox_override("hover", hover_style)
	button.add_theme_stylebox_override("pressed", hover_style)
	button.add_theme_stylebox_override("focus", style)
	return button


func _make_dot(color: Color, size_px: int) -> Control:
	var dot := ColorRect.new()
	dot.color = color
	dot.custom_minimum_size = Vector2(size_px, size_px)
	dot.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	dot.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return dot


func _set_phase2_status(text: String, is_error: bool = false) -> void:
	if _inspector_status_value == null:
		return
	_inspector_status_value.text = "状态：%s" % text
	_inspector_status_value.add_theme_color_override("font_color", ResearchThemeScript.COLOR_STATUS_ERROR if is_error else ResearchThemeScript.COLOR_STATUS_OK)


func _set_retry_visible(next_visible: bool) -> void:
	if _phase2_retry_button != null:
		_phase2_retry_button.visible = next_visible


# ---------------------------------------------------------------------------
# 数据辅助
# ---------------------------------------------------------------------------

func _payload_items(section) -> Array:
	if section is Array:
		return section as Array
	if section is Dictionary:
		var items = (section as Dictionary).get("items", [])
		if items is Array:
			return items as Array
	return []


func _section_summary_text(summary: Dictionary, key: String) -> String:
	var text := str(summary.get(key, "")).strip_edges()
	if text == "" or text == "-" or text == "[]" or text == "{}" or text == "<null>":
		return str(SECTION_EMPTY_TEXT.get(key, "暂无数据。"))
	return text


func _trace_summary_dict(summary: Dictionary) -> Dictionary:
	var groups = summary.get("recentTraceEventGroups", {})
	if groups is Dictionary:
		return (groups as Dictionary).duplicate(true)
	return _empty_summary_dict()


func _trace_event_group_dict(summary: Dictionary) -> Dictionary:
	var groups = summary.get("recentTraceEventRows", {})
	if groups is Dictionary:
		return (groups as Dictionary).duplicate(true)
	return _empty_filter_dict()


func _trace_copy_detail_group_dict(summary: Dictionary) -> Dictionary:
	var groups = summary.get("recentTraceCopyDetailGroups", {})
	if groups is Dictionary:
		return (groups as Dictionary).duplicate(true)
	return _empty_filter_dict()


func _trace_focus_dict(summary: Dictionary) -> Dictionary:
	var focus = summary.get("traceFocus", {})
	if focus is Dictionary:
		return (focus as Dictionary).duplicate(true)
	return {}


func _trace_events_for_filter() -> Array:
	var rows = _recent_trace_event_groups.get(_current_trace_filter, _recent_trace_event_groups.get("all", []))
	if rows is Array:
		return rows as Array
	return []


func _trace_copy_details_for_filter() -> Array:
	var details = _recent_trace_copy_detail_groups.get(_current_trace_filter, _recent_trace_copy_detail_groups.get("all", []))
	if details is Array:
		return details as Array
	return []


func _trace_summary_text_for_filter() -> String:
	var fallback := str(_recent_trace_summaries.get(_current_trace_filter, _recent_trace_summaries.get("all", "")))
	if fallback.strip_edges() == "":
		fallback = str(SECTION_EMPTY_TEXT["recentTraceEvents"])
	return fallback


func _trace_interaction_hint() -> String:
	# 文案直接写出验收关键词，减少 Research Dock 的交互猜测成本。
	return "点击 trace 行：memory.result_observed 行会高亮观察者；证据链里的橙色“点击跳转来源事件”按钮会聚焦来源。"


func _trace_focus_status_text(focus: Dictionary) -> String:
	if focus.is_empty():
		return ""
	var requested = focus.get("requested", {})
	var requested_event_id := ""
	var requested_trace_id := ""
	if requested is Dictionary:
		requested_event_id = str((requested as Dictionary).get("eventId", ""))
		requested_trace_id = str((requested as Dictionary).get("traceId", ""))
	var focus_event_id := str(focus.get("eventId", requested_event_id))
	var focus_trace_id := str(focus.get("traceId", requested_trace_id))
	var focus_label := focus_event_id if focus_event_id != "" else focus_trace_id
	if bool(focus.get("matched", false)):
		return "已聚焦来源事件：%s" % (focus_label if focus_label != "" else "matched")
	if str(focus.get("status", "")) == "missing":
		return "未找到来源事件：%s" % (focus_label if focus_label != "" else "unknown")
	return ""


static func _empty_filter_dict() -> Dictionary:
	return {"all": [], "decision": [], "tool": [], "interrupt": [], "memory": []}


static func _empty_summary_dict() -> Dictionary:
	return {
		"all": "暂无 recentTraceEvents：该 NPC 尚未产生可解释 trace。",
		"decision": "暂无 decision trace。",
		"tool": "暂无 tool trace。",
		"interrupt": "暂无 interrupt trace。",
		"memory": "暂无 memory trace。",
	}


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


func _trace_event_type(entry: Dictionary) -> String:
	return str(entry.get("eventType", entry.get("type", "trace")))


func _trace_row_type_label(event_type: String) -> String:
	if event_type == "memory.result_observed":
		return "memory.result_observed"
	return _pretty_trace_type(event_type)


func _trace_detail_type_label(event_type: String) -> String:
	if event_type == "memory.result_observed":
		return "memory.result_observed（观察记忆）"
	return "%s · %s" % [_pretty_trace_type(event_type), event_type] if event_type != _pretty_trace_type(event_type) else event_type


func _trace_row_tooltip(entry: Dictionary) -> String:
	var event_type := _trace_event_type(entry)
	if event_type == "memory.result_observed":
		return "memory.result_observed 行：点击后高亮观察者；在 details 的证据链里点击来源按钮。"
	if event_type == "motivation.decision_made":
		return "decision 行：点击后高亮决策 NPC。"
	if event_type in ["tool.execution_completed", "tool.execution_failed", "tool.execution_interrupted"]:
		return "tool 行：点击后高亮相关 NPC。"
	return "点击查看 trace details。"


func _trace_tick_text(entry: Dictionary) -> String:
	var world_time = entry.get("worldTime", {})
	if world_time is Dictionary:
		return "t%d" % int((world_time as Dictionary).get("tick", -1))
	return "t?"


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


func _trace_source_badge(entry: Dictionary) -> String:
	var links = entry.get("sourceLinks", [])
	if links is Array and not (links as Array).is_empty():
		return " [有来源按钮]"
	return ""


func _trace_filter_for_event_type(event_type: String) -> String:
	match event_type:
		"motivation.decision_made":
			return "decision"
		"tool.execution_completed", "tool.execution_failed":
			return "tool"
		"tool.execution_interrupted":
			return "interrupt"
		"memory.result_observed":
			return "memory"
		_:
			return "all"


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


func _source_link_agent_ids(link: Dictionary) -> Array:
	var ids: Array = []
	_append_ids_from_value(ids, link.get("agentId", null))
	_append_ids_from_value(ids, link.get("targetIds", null))
	return _unique_ids(ids)


func _emit_highlight(npc_ids: Array, label_text: String) -> void:
	var normalized := _unique_ids(npc_ids)
	if normalized.is_empty():
		_set_phase2_status("%s 未提供可高亮 NPC" % label_text)
		return
	highlight_npcs_requested.emit(normalized)
	_set_phase2_status("已高亮 %s：%s" % [label_text, ", ".join(normalized)])


func _append_ids_from_value(ids: Array, value) -> void:
	if value == null:
		return
	if value is Array:
		for item in value as Array:
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


func _short_source_label(source_type: String) -> String:
	match source_type:
		"relationship_edge_refs":
			return "关系"
		"subjective_memory_refs":
			return "主观记忆"
		"heuristic_refs":
			return "启发式"
		"motivation_decision_trace":
			return "decision"
		"llm_social_strategic_layer":
			return "LLM"
		_:
			return source_type.replace("_", " ")


func _need_label(need_id: String) -> String:
	match need_id:
		"energy":
			return "energy 恢复体力"
		"money_anxiety":
			return "money_anxiety 稳定收入"
		"affiliation":
			return "affiliation 建立联结"
		"recognition":
			return "recognition 获得认可"
		"":
			return "等待动机"
		_:
			return need_id


func _pretty_location(location_id: String) -> String:
	if location_id == "":
		return "-"
	match location_id:
		"farm":
			return "Farm 农场"
		"plaza":
			return "Plaza 广场"
		"tavern":
			return "Tavern 酒馆"
		_:
			return location_id


func _pretty_anchor(anchor_id: String) -> String:
	if anchor_id == "":
		return "-"
	return anchor_id.replace("_", " ")


func _truncate_text(value: String, max_chars: int) -> String:
	if value.length() <= max_chars:
		return value
	return "%s…" % value.substr(0, max(0, max_chars - 1))
