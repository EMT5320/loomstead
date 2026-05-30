class_name ApiClient
extends Node

var base_url: String = "http://127.0.0.1:8787"
var request_timeout_seconds: float = 10.0
# 启动期连接尝试上限：R2.4 要求 5 秒内无法连到后端即视为不可达。
# 区别于常规请求的 10 秒超时，避免不可达时迟迟不回退到可见提示。
var connect_attempt_timeout_seconds: float = 5.0
var _http: HTTPRequest


func get_world_state() -> Dictionary:
	# Godot 客户端只读取后端权威状态。
	return await _request_json("GET", "/api/world/state", {})


func get_world_state_initial_connect() -> Dictionary:
	# 启动期可达性探测：用 5 秒连接尝试上限对齐 R2.4。
	return await _request_json("GET", "/api/world/state", {}, connect_attempt_timeout_seconds)


func get_showcase_starlight() -> Dictionary:
	# Showcase Mode v1 只读聚合接口：摘要层不直接拼接 Director / Skill / Trace 原始 API。
	return await _request_json("GET", "/api/showcase/starlight", {})


func post_player_action(action: Dictionary) -> Dictionary:
	# 玩家动作统一进入后端，由后端负责事件、关系、记忆和 Debug 记录。
	return await _request_json("POST", "/api/player/action", action)


func tick(delta_seconds: float, speed: float = 1.0) -> Dictionary:
	# 世界时钟通过 tick 推进后端权威状态。
	return await _request_json("POST", "/api/world/tick", {
		"deltaSeconds": delta_seconds,
		"speed": speed,
	})


func get_phase2_debug(agent_id: String, focus_event_id: String = "", focus_trace_id: String = "") -> Dictionary:
	var trimmed_id := agent_id.strip_edges()
	if trimmed_id == "":
		return {"ok": false, "error": "agentId 不能为空"}
	var encoded_agent_id := trimmed_id.uri_encode()
	var query_parts: Array[String] = ["agentId=%s" % encoded_agent_id]
	var trimmed_focus_event := focus_event_id.strip_edges()
	if trimmed_focus_event != "":
		query_parts.append("focusEventId=%s" % trimmed_focus_event.uri_encode())
	var trimmed_focus_trace := focus_trace_id.strip_edges()
	if trimmed_focus_trace != "":
		query_parts.append("focusTraceId=%s" % trimmed_focus_trace.uri_encode())
	var query := "&".join(query_parts)

	# 优先调用 Phase 2 专用调试入口。
	var primary := await _request_json("GET", "/api/debug.phase2?%s" % query, {})
	if bool(primary.get("ok", false)):
		return primary

	# 兼容总览入口：后端若暂时未暴露专用路由，可从 /api/debug 的 phase2 字段读取。
	var fallback := await _request_json("GET", "/api/debug?%s" % query, {})
	if not bool(fallback.get("ok", false)):
		return primary
	var fallback_data = fallback.get("data", {})
	if fallback_data is Dictionary:
		var phase2_data = (fallback_data as Dictionary).get("phase2", null)
		if phase2_data is Dictionary:
			return {"ok": true, "data": phase2_data}
	return {"ok": false, "error": "缺少 phase2 调试数据"}


func _ensure_http() -> void:
	if _http == null:
		_http = HTTPRequest.new()
		_http.timeout = request_timeout_seconds
		add_child(_http)


func cancel_current_request() -> void:
	if _http != null and _http.get_http_client_status() != HTTPClient.STATUS_DISCONNECTED:
		_http.cancel_request()


func _request_json(method: String, path: String, payload: Dictionary, timeout_override: float = -1.0) -> Dictionary:
	_ensure_http()
	if _http.get_http_client_status() != HTTPClient.STATUS_DISCONNECTED:
		_http.cancel_request()

	# 允许单次请求覆盖默认超时（启动期连接尝试用 5 秒上限，对齐 R2.4）。
	var previous_timeout := _http.timeout
	if timeout_override > 0.0:
		_http.timeout = timeout_override

	var request_method := HTTPClient.METHOD_GET
	var body := ""
	if method == "POST":
		request_method = HTTPClient.METHOD_POST
		body = JSON.stringify(payload)

	var error := _http.request(base_url + path, PackedStringArray(["Content-Type: application/json"]), request_method, body)
	if error != OK:
		_http.timeout = previous_timeout
		return {"ok": false, "error": "HTTPRequest 启动失败：%s" % error, "unreachable": true}

	var result: Array = await _http.request_completed
	_http.timeout = previous_timeout
	var request_result: int = result[0]
	var response_code: int = result[1]
	var raw_body: PackedByteArray = result[3]

	if request_result != HTTPRequest.RESULT_SUCCESS:
		return {
			"ok": false,
			"error": "HTTP 请求失败：%s" % _http_request_result_reason(request_result),
			"requestResult": request_result,
			"unreachable": _is_unreachable_result(request_result),
		}

	var text := raw_body.get_string_from_utf8()
	var parsed = JSON.parse_string(text)
	if typeof(parsed) != TYPE_DICTIONARY:
		return {"ok": false, "error": "响应需为 JSON 对象", "httpCode": response_code, "raw": text}

	if response_code < 200 or response_code >= 300:
		return {
			"ok": false,
			"error": "HTTP %d %s" % [response_code, _http_status_reason(response_code)],
			"httpCode": response_code,
			"data": parsed,
		}

	return {"ok": true, "data": parsed}


func _is_unreachable_result(result_code: int) -> bool:
	# 判定哪些 transport 结果码代表「后端整体不可达」（连不上/解析不到/无响应/超时），
	# 供启动期连接尝试在 5 秒内回退到 HUD 可见的「后端不可达」提示（R2.4）。
	match result_code:
		HTTPRequest.RESULT_CANT_CONNECT, \
		HTTPRequest.RESULT_CANT_RESOLVE, \
		HTTPRequest.RESULT_CONNECTION_ERROR, \
		HTTPRequest.RESULT_NO_RESPONSE, \
		HTTPRequest.RESULT_TIMEOUT:
			return true
		_:
			return false


func _http_request_result_reason(result_code: int) -> String:
	# 把 Godot 原始请求结果转为可读文案，ObserverPanel 错误态会直接展示。
	match result_code:
		HTTPRequest.RESULT_CANT_CONNECT:
			return "无法连接后端 (%d)" % result_code
		HTTPRequest.RESULT_CANT_RESOLVE:
			return "无法解析后端地址 (%d)" % result_code
		HTTPRequest.RESULT_CONNECTION_ERROR:
			return "连接中断 (%d)" % result_code
		HTTPRequest.RESULT_TLS_HANDSHAKE_ERROR:
			return "TLS 握手失败 (%d)" % result_code
		HTTPRequest.RESULT_NO_RESPONSE:
			return "后端无响应 (%d)" % result_code
		HTTPRequest.RESULT_REQUEST_FAILED:
			return "请求失败 (%d)" % result_code
		HTTPRequest.RESULT_REDIRECT_LIMIT_REACHED:
			return "重定向次数过多 (%d)" % result_code
		HTTPRequest.RESULT_TIMEOUT:
			return "请求超时 (%d)" % result_code
		_:
			return "结果码 %d" % result_code


func _http_status_reason(response_code: int) -> String:
	match response_code:
		400:
			return "Bad Request"
		401:
			return "Unauthorized"
		403:
			return "Forbidden"
		404:
			return "Not Found"
		408:
			return "Request Timeout"
		429:
			return "Too Many Requests"
		500:
			return "Internal Server Error"
		502:
			return "Bad Gateway"
		503:
			return "Service Unavailable"
		504:
			return "Gateway Timeout"
		_:
			return "状态码异常"
