class_name ResearchTheme
extends RefCounted

# 集中管理 Loomstead Godot UI 的颜色 / StyleBox / 字号 / 字体，避免散落的
# add_theme_*_override，并保证 Research Dock / HUD / Top Banner / VN 面板视觉一致。
#
# 设计风格：深色半透明卡片 + 蓝色 accent，与游戏暖色背景反差，
# 适合作为研究 / 可解释性主面板。
#
# 字体使用 Godot 4 `SystemFont`，按平台回退到本机 CJK 字体，
# 避免在仓库里塞 16MB 字体二进制。

const COLOR_BG_DEEP := Color(0.06, 0.08, 0.11, 0.94)
const COLOR_BG_CARD := Color(0.10, 0.12, 0.17, 0.92)
const COLOR_BG_CHIP := Color(0.16, 0.20, 0.28, 0.92)
const COLOR_BORDER := Color(0.36, 0.55, 0.86, 0.55)
const COLOR_BORDER_SOFT := Color(0.30, 0.38, 0.52, 0.45)
const COLOR_ACCENT := Color(0.36, 0.71, 1.00, 1.0)
const COLOR_ACCENT_SOFT := Color(0.36, 0.71, 1.00, 0.25)
const COLOR_TEXT_PRIMARY := Color(0.90, 0.94, 1.0, 1.0)
const COLOR_TEXT_MUTED := Color(0.62, 0.69, 0.80, 1.0)
const COLOR_TEXT_TITLE := Color(1.0, 0.94, 0.74, 1.0)
const COLOR_VALENCE_POS := Color(0.40, 0.86, 0.56, 1.0)
const COLOR_VALENCE_NEG := Color(0.95, 0.50, 0.50, 1.0)
const COLOR_VALENCE_NEUTRAL := Color(0.62, 0.69, 0.80, 1.0)
const COLOR_TYPE_DECISION := Color(0.45, 0.75, 1.0, 1.0)
const COLOR_TYPE_TOOL := Color(0.40, 0.86, 0.56, 1.0)
const COLOR_TYPE_INTERRUPT := Color(0.98, 0.70, 0.40, 1.0)
const COLOR_TYPE_MEMORY := Color(0.80, 0.62, 1.0, 1.0)
const COLOR_TYPE_DEFAULT := Color(0.74, 0.78, 0.86, 1.0)
const COLOR_STATUS_ERROR := Color(1.0, 0.60, 0.54, 1.0)
const COLOR_STATUS_OK := Color(0.68, 0.92, 0.74, 1.0)

const FONT_SIZE_TITLE := 20
const FONT_SIZE_SUBTITLE := 15
const FONT_SIZE_BODY := 13
const FONT_SIZE_SMALL := 11
const FONT_SIZE_CHIP := 11

const PANEL_CORNER_RADIUS := 14
const CARD_CORNER_RADIUS := 10
const CHIP_CORNER_RADIUS := 8

# 系统字体缓存，跨实例复用避免重复创建。
static var _system_font_cache: Font = null


static func get_system_font() -> Font:
	if _system_font_cache != null:
		return _system_font_cache
	var font := SystemFont.new()
	# Windows / macOS / Linux 常见 CJK 字体名，Godot 会按顺序回退。
	font.font_names = PackedStringArray([
		"Microsoft YaHei UI",
		"Microsoft YaHei",
		"PingFang SC",
		"Hiragino Sans GB",
		"Noto Sans CJK SC",
		"Source Han Sans SC",
		"WenQuanYi Micro Hei",
		"sans-serif",
	])
	font.allow_system_fallback = true
	font.subpixel_positioning = TextServer.SUBPIXEL_POSITIONING_AUTO
	_system_font_cache = font
	return font


static func make_panel_style(
	bg_color: Color = COLOR_BG_DEEP,
	border_color: Color = COLOR_BORDER,
	corner: int = PANEL_CORNER_RADIUS,
	border_width: int = 1
) -> StyleBoxFlat:
	var style := StyleBoxFlat.new()
	style.bg_color = bg_color
	style.border_color = border_color
	style.set_border_width_all(border_width)
	style.set_corner_radius_all(corner)
	style.shadow_color = Color(0.0, 0.0, 0.0, 0.45)
	style.shadow_size = 10
	style.content_margin_left = 12
	style.content_margin_right = 12
	style.content_margin_top = 10
	style.content_margin_bottom = 10
	return style


static func make_card_style(accent_color: Color = COLOR_BORDER_SOFT) -> StyleBoxFlat:
	var style := StyleBoxFlat.new()
	style.bg_color = COLOR_BG_CARD
	style.border_color = accent_color
	style.set_border_width_all(1)
	style.set_corner_radius_all(CARD_CORNER_RADIUS)
	style.content_margin_left = 12
	style.content_margin_right = 12
	style.content_margin_top = 10
	style.content_margin_bottom = 10
	return style


static func make_chip_style(accent_color: Color = COLOR_BORDER_SOFT) -> StyleBoxFlat:
	var style := StyleBoxFlat.new()
	style.bg_color = COLOR_BG_CHIP
	style.border_color = accent_color
	style.set_border_width_all(1)
	style.set_corner_radius_all(CHIP_CORNER_RADIUS)
	style.content_margin_left = 8
	style.content_margin_right = 8
	style.content_margin_top = 3
	style.content_margin_bottom = 3
	return style


static func make_tab_style(active: bool) -> StyleBoxFlat:
	var style := StyleBoxFlat.new()
	if active:
		style.bg_color = COLOR_ACCENT_SOFT
		style.border_color = COLOR_ACCENT
	else:
		style.bg_color = Color(0.0, 0.0, 0.0, 0.18)
		style.border_color = COLOR_BORDER_SOFT
	style.set_border_width_all(1)
	style.border_width_bottom = 2 if active else 1
	style.set_corner_radius_all(8)
	style.content_margin_left = 10
	style.content_margin_right = 10
	style.content_margin_top = 5
	style.content_margin_bottom = 5
	return style


static func apply_label_style(
	label: Label,
	font_size: int = FONT_SIZE_BODY,
	color: Color = COLOR_TEXT_PRIMARY,
	shadow: bool = false
) -> void:
	label.add_theme_font_override("font", get_system_font())
	label.add_theme_font_size_override("font_size", font_size)
	label.add_theme_color_override("font_color", color)
	if shadow:
		label.add_theme_color_override("font_shadow_color", Color(0.0, 0.0, 0.0, 0.88))
		label.add_theme_constant_override("shadow_offset_x", 1)
		label.add_theme_constant_override("shadow_offset_y", 1)


static func apply_button_style(button: BaseButton, font_size: int = FONT_SIZE_BODY) -> void:
	button.add_theme_font_override("font", get_system_font())
	button.add_theme_font_size_override("font_size", font_size)
	button.add_theme_color_override("font_color", COLOR_TEXT_PRIMARY)
	button.add_theme_color_override("font_hover_color", COLOR_ACCENT)
	button.add_theme_color_override("font_pressed_color", COLOR_ACCENT)
	button.add_theme_color_override("font_disabled_color", COLOR_TEXT_MUTED)
	var normal := _make_button_box(false)
	var hover := _make_button_box(false)
	hover.bg_color = Color(0.16, 0.22, 0.32, 0.96)
	hover.border_color = COLOR_ACCENT
	var pressed := _make_button_box(true)
	var disabled := _make_button_box(false)
	disabled.bg_color = Color(0.08, 0.10, 0.14, 0.55)
	disabled.border_color = COLOR_BORDER_SOFT
	button.add_theme_stylebox_override("normal", normal)
	button.add_theme_stylebox_override("hover", hover)
	button.add_theme_stylebox_override("pressed", pressed)
	button.add_theme_stylebox_override("disabled", disabled)
	button.add_theme_stylebox_override("focus", _make_button_box(false))


static func _make_button_box(pressed: bool) -> StyleBoxFlat:
	var box := StyleBoxFlat.new()
	box.bg_color = COLOR_ACCENT_SOFT if pressed else Color(0.12, 0.16, 0.24, 0.92)
	box.border_color = COLOR_ACCENT if pressed else COLOR_BORDER_SOFT
	box.set_border_width_all(1)
	box.set_corner_radius_all(8)
	box.content_margin_left = 10
	box.content_margin_right = 10
	box.content_margin_top = 4
	box.content_margin_bottom = 4
	return box


static func valence_color(value: float) -> Color:
	if value >= 0.15:
		return COLOR_VALENCE_POS
	if value <= -0.15:
		return COLOR_VALENCE_NEG
	return COLOR_VALENCE_NEUTRAL


static func trace_type_color(event_type: String) -> Color:
	match event_type:
		"motivation.decision_made":
			return COLOR_TYPE_DECISION
		"tool.execution_completed", "tool.execution_failed":
			return COLOR_TYPE_TOOL
		"tool.execution_interrupted":
			return COLOR_TYPE_INTERRUPT
		"memory.result_observed":
			return COLOR_TYPE_MEMORY
		_:
			return COLOR_TYPE_DEFAULT


static func contributing_source_color(source_type: String) -> Color:
	if source_type.find("relationship") >= 0:
		return Color(1.0, 0.74, 0.84, 1.0)
	if source_type.find("subjective_memory") >= 0:
		return Color(0.80, 0.62, 1.0, 1.0)
	if source_type.find("heuristic") >= 0:
		return Color(1.0, 0.86, 0.50, 1.0)
	if source_type.find("trace") >= 0 or source_type.find("decision") >= 0:
		return COLOR_TYPE_DECISION
	return COLOR_TEXT_MUTED


static func make_separator(color: Color = COLOR_BORDER_SOFT, height: int = 1) -> Control:
	var rect := ColorRect.new()
	rect.color = color
	rect.custom_minimum_size = Vector2(0, height)
	rect.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	rect.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return rect
