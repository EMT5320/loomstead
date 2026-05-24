class_name ApiClient
extends Node

var base_url: String = "http://127.0.0.1:8787"
var request_timeout_seconds: float = 10.0
var _http: HTTPRequest


func get_world_state() -> Dictionary:
	# Godot 客户端只读取后端权威状态。
	return await _request_json("GET", "/api/world/state", {})


func post_player_action(action: Dictionary) -> Dictionary:
	# 玩家动作统一进入后端，由后端负责事件、关系、记忆和 Debug 记录。
	return await _request_json("POST", "/api/player/action", action)


func tick(delta_seconds: float, speed: float = 1.0) -> Dictionary:
	# 世界时钟通过 tick 推进后端权威状态。
	return await _request_json("POST", "/api/world/tick", {
		"deltaSeconds": delta_seconds,
		"speed": speed,
	})


func get_phase2_debug(agent_id: String) -> Dictionary:
	var trimmed_id := agent_id.strip_edges()
	if trimmed_id == "":
		return {"ok": false, "error": "agentId 不能为空"}
	var encoded_agent_id := trimmed_id.uri_encode()

	# 优先调用 Phase 2 专用调试入口。
	var primary := await _request_json("GET", "/api/debug.phase2?agentId=%s" % encoded_agent_id, {})
	if bool(primary.get("ok", false)):
		return primary

	# 兼容总览入口：后端若暂时未暴露专用路由，可从 /api/debug 的 phase2 字段读取。
	var fallback := await _request_json("GET", "/api/debug?agentId=%s" % encoded_agent_id, {})
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


func _request_json(method: String, path: String, payload: Dictionary) -> Dictionary:
	_ensure_http()
	if _http.get_http_client_status() != HTTPClient.STATUS_DISCONNECTED:
		_http.cancel_request()

	var request_method := HTTPClient.METHOD_GET
	var body := ""
	if method == "POST":
		request_method = HTTPClient.METHOD_POST
		body = JSON.stringify(payload)

	var error := _http.request(base_url + path, PackedStringArray(["Content-Type: application/json"]), request_method, body)
	if error != OK:
		return {"ok": false, "error": "HTTPRequest 启动失败：%s" % error}

	var result: Array = await _http.request_completed
	var request_result: int = result[0]
	var response_code: int = result[1]
	var raw_body: PackedByteArray = result[3]

	if request_result != HTTPRequest.RESULT_SUCCESS:
		return {
			"ok": false,
			"error": "HTTP 请求失败：%s" % _http_request_result_reason(request_result),
			"requestResult": request_result,
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
