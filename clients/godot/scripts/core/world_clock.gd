class_name WorldClock
extends Node

signal tick_requested(delta_seconds: float, speed: float)
signal tick_received(payload: Dictionary)
signal tick_failed(error_message: String)
signal paused_changed(is_paused: bool)
signal speed_changed(new_speed: float)

@export var tick_interval_seconds: float = 1.0
@export var auto_start: bool = true
@export var default_speed: float = 1.0
@export var tick_request_timeout_seconds: float = 12.0

var paused: bool = false
var speed: float = 1.0
var _tick_accumulator: float = 0.0
var _tick_in_flight: bool = false
var _tick_request_started_msec: int = 0
var _tick_request_sequence: int = 0
var _active_tick_request_id: int = 0
var _api_client: ApiClient


func _ready() -> void:
	# 时钟节点自己持有 ApiClient，避免和旧 main.gd 绑定。
	_api_client = ApiClient.new()
	_api_client.name = "ClockApiClient"
	add_child(_api_client)

	speed = max(default_speed, 0.1)
	paused = not auto_start
	paused_changed.emit(paused)
	speed_changed.emit(speed)


func _process(delta: float) -> void:
	if paused:
		return
	if _tick_in_flight:
		_recover_stale_tick_request()
		return

	_tick_accumulator += delta
	if _tick_accumulator < tick_interval_seconds:
		return

	var step_count := int(floor(_tick_accumulator / tick_interval_seconds))
	_tick_accumulator -= float(step_count) * tick_interval_seconds

	var delta_seconds := float(step_count) * tick_interval_seconds
	if delta_seconds <= 0.0:
		return

	_request_tick(delta_seconds)


func set_paused(next_paused: bool) -> void:
	paused = next_paused
	paused_changed.emit(paused)


func toggle_paused() -> void:
	set_paused(not paused)


func set_speed(next_speed: float) -> void:
	speed = clamp(next_speed, 0.1, 8.0)
	speed_changed.emit(speed)


func request_tick_once(delta_seconds: float) -> void:
	if delta_seconds <= 0.0:
		return
	_request_tick(delta_seconds)


func _request_tick(delta_seconds: float) -> void:
	if _tick_in_flight:
		return

	_tick_request_sequence += 1
	var request_id := _tick_request_sequence
	_active_tick_request_id = request_id
	_tick_request_started_msec = Time.get_ticks_msec()
	_tick_in_flight = true
	tick_requested.emit(delta_seconds, speed)
	var response := await _api_client.tick(delta_seconds, speed)
	if request_id != _active_tick_request_id:
		return
	_tick_in_flight = false
	_active_tick_request_id = 0
	_tick_request_started_msec = 0

	if not bool(response.get("ok", false)):
		tick_failed.emit(str(response.get("error", "tick 请求失败")))
		return

	var payload = response.get("data", {})
	if payload is Dictionary:
		tick_received.emit(payload)
		return

	tick_failed.emit("tick 响应不是字典")


func _recover_stale_tick_request() -> void:
	if tick_request_timeout_seconds <= 0.0 or _tick_request_started_msec <= 0:
		return
	var elapsed_seconds := float(Time.get_ticks_msec() - _tick_request_started_msec) / 1000.0
	if elapsed_seconds < tick_request_timeout_seconds:
		return
	_active_tick_request_id = 0
	_tick_request_started_msec = 0
	_tick_in_flight = false
	if _api_client != null:
		_api_client.cancel_current_request()
	tick_failed.emit("tick 请求超时，已恢复自动推进")
