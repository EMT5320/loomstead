from __future__ import annotations

import json
import mimetypes
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from app.developer.developer_commands import apply_developer_command
from app.runtime.agent_runtime import AgentRuntime


class TownApplication:
    """应用外壳，隔离 HTTP 层和核心 Runtime。"""

    def __init__(self, provider_mode: str | None = None) -> None:
        self.runtime = AgentRuntime(provider_mode=provider_mode)

    def get_public_state(self) -> dict[str, Any]:
        return self.runtime.get_public_state()

    def get_game_state(self) -> dict[str, Any]:
        return self.runtime.get_game_state()

    def step_simulation(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.runtime.step(actor_id=(payload or {}).get("actorId", "developer"))

    def world_tick(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """按客户端提供的游戏时间步长推进世界。"""
        data = payload or {}
        delta_seconds = float(data.get("deltaSeconds", 0.0))
        speed = float(data.get("speed", 1.0))
        return self.runtime.tick(delta_seconds=delta_seconds, speed=speed)

    def command(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return apply_developer_command(self.runtime, payload or {})

    def player_action(self, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.runtime.handle_player_action(payload or {})

    def debug_snapshot(self, query: dict[str, Any] | None = None) -> dict[str, Any]:
        """Debug Console 总览查询入口。"""
        return self.runtime.get_debug_snapshot(query or {})

    def debug_director(self, query: dict[str, Any] | None = None) -> dict[str, Any]:
        """Director Beat 生命周期查询入口。"""
        return self.runtime.get_director_debug_snapshot(query or {})

    def debug_skills(self, query: dict[str, Any] | None = None) -> dict[str, Any]:
        """Event Skill 生命周期查询入口。"""
        return self.runtime.get_skill_lifecycle_snapshot(query or {})

    def debug_turns(self, query: dict[str, Any] | None = None) -> dict[str, Any]:
        """Provider Debug 记录查询入口。"""
        return self.runtime.get_debug_turns(query or {})

    def debug_influence(self, query: dict[str, Any] | None = None) -> dict[str, Any]:
        """首日玩家影响链查询入口。"""
        return self.runtime.get_influence_chain_debug(query or {})

    def debug_phase2(self, query: dict[str, Any] | None = None) -> dict[str, Any]:
        """Phase 2 可解释调试查询入口。"""
        return self.runtime.get_phase2_debug_snapshot(query or {})

    def showcase_starlight(self, query: dict[str, Any] | None = None) -> dict[str, Any]:
        """Showcase Mode v1 星灯祭只读聚合入口。"""
        return self.runtime.get_starlight_showcase_snapshot(query or {})

    def debug_skill_explain(self, query: dict[str, Any] | None = None) -> dict[str, Any]:
        """单个 Event Skill 可解释说明入口。"""
        return self.runtime.explain_event_skill(query or {})

    def reload_model_config(self) -> dict[str, Any]:
        """重新读取模型配置，供开发期 Web 面板热重载。"""
        return self.runtime.reload_model_config()

    def memory_summary(self, query: dict[str, Any] | None = None) -> dict[str, Any]:
        """Memory Summary 查询入口。"""
        return self.runtime.get_memory_debug(query or {})["summaries"]

    def memory_search(self, query: dict[str, Any] | None = None) -> dict[str, Any]:
        """RAG-lite 检索查询入口。"""
        return self.runtime.get_memory_debug(query or {})["retrieval"]


def create_town_app(provider_mode: str | None = None) -> TownApplication:
    """供测试和 HTTP 服务复用的应用工厂。"""
    return TownApplication(provider_mode=provider_mode)


def create_handler(app: TownApplication, project_root: Path):
    frontend_root = project_root / "frontend"

    class Handler(BaseHTTPRequestHandler):
        """轻量 HTTP 适配器，保持和前端一致的 REST/SSE API。"""

        def do_GET(self) -> None:  # noqa: N802 - http.server 约定方法名
            route, query = self.route_and_query()
            try:
                if route == "/api/state":
                    return self.write_json(app.get_public_state())
                if route == "/api/world/state":
                    return self.write_json(app.get_game_state())
                if route == "/api/model-config":
                    return self.write_json(app.runtime.model_config.public_config())
                if route == "/api/debug":
                    return self.write_json(app.debug_snapshot(query))
                if route == "/api/debug/director":
                    return self.write_json(app.debug_director(query))
                if route == "/api/debug/skills":
                    return self.write_json(app.debug_skills(query))
                if route == "/api/debug/turns":
                    return self.write_json(app.debug_turns(query))
                if route == "/api/debug/influence":
                    return self.write_json(app.debug_influence(query))
                if route == "/api/debug.phase2":
                    return self.write_json(app.debug_phase2(query))
                if route == "/api/showcase/starlight":
                    return self.write_json(app.showcase_starlight(query))
                if route == "/api/debug/skill":
                    return self.write_json(app.debug_skill_explain(query))
                if route == "/api/memory/summary":
                    return self.write_json(app.memory_summary(query))
                if route == "/api/memory/search":
                    return self.write_json(app.memory_search(query))
                if route == "/api/events":
                    return self.stream_events(app)
            except (KeyError, ValueError) as error:
                return self.write_json({"ok": False, "error": str(error)}, HTTPStatus.BAD_REQUEST)
            return self.serve_static(frontend_root)

        def do_POST(self) -> None:  # noqa: N802 - http.server 约定方法名
            payload = self.read_json()
            route = self.path.split("?", 1)[0]
            if route == "/api/step":
                return self.write_json(app.step_simulation(payload))
            if route == "/api/world/tick":
                try:
                    return self.write_json(app.world_tick(payload))
                except ValueError as error:
                    return self.write_json({"ok": False, "error": str(error)}, HTTPStatus.BAD_REQUEST)
            if route == "/api/player/action":
                try:
                    return self.write_json(app.player_action(payload))
                except ValueError as error:
                    return self.write_json({"ok": False, "error": str(error)}, HTTPStatus.BAD_REQUEST)
            if route == "/api/model-config/reload":
                return self.write_json(app.reload_model_config())
            if route == "/api/developer":
                return self.write_json(app.command(payload))
            return self.write_json({"error": "unknown endpoint"}, HTTPStatus.NOT_FOUND)

        def route_and_query(self) -> tuple[str, dict[str, str]]:
            """解析路径和查询参数，供 Debug / Memory API 复用。"""
            parsed = urlparse(self.path)
            query = {key: values[-1] for key, values in parse_qs(parsed.query, keep_blank_values=True).items()}
            return parsed.path, query

        def read_json(self) -> dict[str, Any]:
            length = int(self.headers.get("content-length", "0"))
            if length <= 0:
                return {}
            raw = self.rfile.read(length).decode("utf-8")
            return json.loads(raw) if raw else {}

        def write_json(self, data: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("content-type", "application/json; charset=utf-8")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def serve_static(self, root: Path) -> None:
            requested = "/index.html" if self.path == "/" else self.path.split("?", 1)[0]
            target = (root / requested.lstrip("/")).resolve()
            if not str(target).startswith(str(root.resolve())) or not target.exists():
                return self.write_json({"error": "file not found"}, HTTPStatus.NOT_FOUND)
            body = target.read_bytes()
            content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
            self.send_response(HTTPStatus.OK)
            self.send_header("content-type", f"{content_type}; charset=utf-8" if content_type.startswith("text/") or target.suffix == ".js" else content_type)
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def stream_events(self, app_ref: TownApplication) -> None:
            queue = app_ref.runtime.event_store.subscribe()
            self.send_response(HTTPStatus.OK)
            self.send_header("content-type", "text/event-stream; charset=utf-8")
            self.send_header("cache-control", "no-cache")
            self.end_headers()
            try:
                while True:
                    event = queue.get()
                    self.wfile.write(f"data: {json.dumps(event, ensure_ascii=False)}\n\n".encode("utf-8"))
                    self.wfile.flush()
            except Exception:
                app_ref.runtime.event_store.unsubscribe(queue)

        def log_message(self, format: str, *args: Any) -> None:
            # 开发期减少请求日志噪音，核心事件已进入 EventStore。
            if os.getenv("LOOMSTEAD_HTTP_LOG") == "1" or os.getenv("AGENT_TOWN_HTTP_LOG") == "1":
                super().log_message(format, *args)

    return Handler


def run_server(port: int = 8787) -> None:
    """启动本地开发服务器。"""
    project_root = Path(__file__).resolve().parents[2]
    app = create_town_app()
    server = ThreadingHTTPServer(("127.0.0.1", port), create_handler(app, project_root))
    print(f"Loomstead Python 后端已启动：http://localhost:{port}")
    print(f"模型配置：provider={app.runtime.provider_mode}, config={app.runtime.model_config.config_path}, local={app.runtime.model_config.local_config_path.exists()}")
    server.serve_forever()


if __name__ == "__main__":
    run_server(int(os.getenv("PORT", "8787")))
