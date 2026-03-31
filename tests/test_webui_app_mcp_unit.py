import asyncio
import json

from starlette.requests import Request

from server.api import webui as webui_module
from server import app as app_module
from server import mcp_server as mcp_server_module


def make_request(path="/"):
    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("utf-8"),
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 1234),
        "server": ("testserver", 80),
        "path_params": {},
    }
    return Request(scope, receive)


def test_webui_home_reads_and_caches_file(monkeypatch):
    class FakePath:
        def __init__(self, value):
            self.value = value

        def read_text(self, encoding="utf-8"):
            return self.value

    html_path = FakePath("<h1>Hello</h1>")

    monkeypatch.setattr(webui_module, "WEBUI_HTML_PATH", html_path)
    monkeypatch.setattr(webui_module, "_WEBUI_HTML_CACHE", None)

    first = asyncio.run(webui_module.webui_home(make_request()))
    html_path.value = "<h1>Changed</h1>"
    second = asyncio.run(webui_module.webui_home(make_request()))

    assert first.body.decode("utf-8") == "<h1>Hello</h1>"
    assert second.body.decode("utf-8") == "<h1>Hello</h1>"


def test_webui_home_missing_file_returns_500(monkeypatch):
    class MissingPath:
        def read_text(self, encoding="utf-8"):
            raise FileNotFoundError

    monkeypatch.setattr(webui_module, "WEBUI_HTML_PATH", MissingPath())
    monkeypatch.setattr(webui_module, "_WEBUI_HTML_CACHE", None)

    response = asyncio.run(webui_module.webui_home(make_request()))

    assert response.status_code == 500
    assert "webui.html 文件未找到" in response.body.decode("utf-8")


def test_webui_api_tools_success_and_error(monkeypatch):
    monkeypatch.setattr(webui_module, "_build_registered_tools", lambda: [{"name": "history"}])
    ok = asyncio.run(webui_module.webui_api_tools(make_request("/api/tools")))

    monkeypatch.setattr(webui_module, "_build_registered_tools", lambda: (_ for _ in ()).throw(RuntimeError("boom")))
    error = asyncio.run(webui_module.webui_api_tools(make_request("/api/tools")))

    assert json.loads(ok.body.decode("utf-8")) == {"tools": [{"name": "history"}]}
    assert error.status_code == 500
    assert json.loads(error.body.decode("utf-8")) == {"error": "boom"}


def test_create_app_has_expected_routes_and_middleware():
    app = app_module.create_app()
    route_paths = {route.path for route in app.routes}

    assert "/" in route_paths
    assert "/webui" in route_paths
    assert "/mcp" in route_paths
    assert "/api/direct_call" in route_paths
    assert "/api/v1/tools" in route_paths
    assert any(middleware.cls.__name__ == "CORSMiddleware" for middleware in app.user_middleware)
    assert any(middleware.cls.__name__ == "LoggingMiddleware" for middleware in app.user_middleware)


def test_mcp_server_uses_dns_rebinding_override():
    assert mcp_server_module.security_settings.enable_dns_rebinding_protection is False
    assert mcp_server_module.get_mcp_app() == {"app": "dummy-mcp"}
