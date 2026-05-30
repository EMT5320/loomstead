class_name ConnectionStatusBanner
extends CanvasLayer

# 后端不可达指示横幅（R2.4 / R2.5）。
#
# 当客户端在 5 秒连接尝试内无法连到后端时，TownMap 调用 show_unreachable()
# 在 HUD 顶部居中显示一条「后端不可达」可见提示；窗口保持响应、不崩溃、不关闭。
# 这是一个独立的 CanvasLayer 横幅，不依赖 ObserverPanel，避免与同步失败逻辑耦合。
#
# 设计为表现层只读提示：不写回权威世界状态，仅在连接恢复后由 TownMap 调用
# hide_unreachable() 收起。真实窗口表现仍需人工复验（Manual_Verification_Gate）。

const ResearchThemeScript := preload("res://scripts/ui/research_theme.gd")

const UNREACHABLE_TITLE := "后端不可达"
const DEFAULT_DETAIL := "5 秒连接尝试未连到后端运行时，已停止重试。窗口仍可操作，恢复后端后请重启或等待重连。"

var _panel: PanelContainer
var _title_label: Label
var _detail_label: Label


func _ready() -> void:
	layer = 24
	_build_panel()
	hide_unreachable()


func show_unreachable(detail: String = "") -> void:
	# 显示「后端不可达」可见指示。detail 为可选的可读原因（如连接超时文案）。
	if _title_label != null:
		_title_label.text = "⚠ %s" % UNREACHABLE_TITLE
	if _detail_label != null:
		var trimmed := detail.strip_edges()
		_detail_label.text = trimmed if trimmed != "" else DEFAULT_DETAIL
	if _panel != null:
		_panel.visible = true


func hide_unreachable() -> void:
	if _panel != null:
		_panel.visible = false


func is_showing() -> bool:
	return _panel != null and _panel.visible


func _build_panel() -> void:
	_panel = PanelContainer.new()
	_panel.name = "ConnectionStatusPanel"
	# 顶部居中横幅，宽度留出左右空间，避免遮挡 TopBanner。
	_panel.anchor_left = 0.5
	_panel.anchor_top = 0.0
	_panel.anchor_right = 0.5
	_panel.anchor_bottom = 0.0
	_panel.offset_left = -ResearchThemeScript.scale_px(360.0)
	_panel.offset_top = ResearchThemeScript.scale_px(96.0)
	_panel.offset_right = ResearchThemeScript.scale_px(360.0)
	_panel.offset_bottom = ResearchThemeScript.scale_px(168.0)
	# 提示不拦截输入，保证窗口对操作者输入保持响应（R2.5）。
	_panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_panel.add_theme_stylebox_override(
		"panel",
		ResearchThemeScript.make_panel_style(
			ResearchThemeScript.COLOR_BG_DEEP,
			ResearchThemeScript.COLOR_STATUS_ERROR
		)
	)
	add_child(_panel)

	var margin := MarginContainer.new()
	margin.add_theme_constant_override("margin_left", int(round(ResearchThemeScript.scale_px(14.0))))
	margin.add_theme_constant_override("margin_right", int(round(ResearchThemeScript.scale_px(14.0))))
	margin.add_theme_constant_override("margin_top", int(round(ResearchThemeScript.scale_px(8.0))))
	margin.add_theme_constant_override("margin_bottom", int(round(ResearchThemeScript.scale_px(8.0))))
	margin.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_panel.add_child(margin)

	var column := VBoxContainer.new()
	column.add_theme_constant_override("separation", int(round(ResearchThemeScript.scale_px(4.0))))
	column.mouse_filter = Control.MOUSE_FILTER_IGNORE
	margin.add_child(column)

	_title_label = Label.new()
	_title_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_title_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	ResearchThemeScript.apply_label_style(
		_title_label,
		ResearchThemeScript.FONT_SIZE_SUBTITLE,
		ResearchThemeScript.COLOR_STATUS_ERROR,
		true
	)
	column.add_child(_title_label)

	_detail_label = Label.new()
	_detail_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_detail_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_detail_label.custom_minimum_size = Vector2(ResearchThemeScript.scale_px(680.0), 0)
	_detail_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	ResearchThemeScript.apply_label_style(
		_detail_label,
		ResearchThemeScript.FONT_SIZE_SMALL,
		ResearchThemeScript.COLOR_TEXT_MUTED
	)
	column.add_child(_detail_label)
