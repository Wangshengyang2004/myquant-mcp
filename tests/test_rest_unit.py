import asyncio
import json

from starlette.requests import Request

from server.api import rest as rest_module


def make_request(method="GET", path="/api/v1/tools", body=None, query_string="", path_params=None):
    payload = json.dumps(body).encode("utf-8") if body is not None else b""
    delivered = False

    async def receive():
        nonlocal delivered
        if delivered:
            return {"type": "http.request", "body": b"", "more_body": False}
        delivered = True
        return {"type": "http.request", "body": payload, "more_body": False}

    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("utf-8"),
        "query_string": query_string.encode("utf-8"),
        "headers": [(b"content-type", b"application/json")],
        "client": ("127.0.0.1", 1234),
        "server": ("testserver", 80),
        "path_params": path_params or {},
    }
    return Request(scope, receive)


def parse_response(response):
    return json.loads(response.body.decode("utf-8"))


def test_rest_tools_list_filters_blocked(monkeypatch):
    monkeypatch.setattr(
        rest_module,
        "_build_registered_tools",
        lambda: [{"name": "history"}, {"name": "get_positions"}, {"name": "order_volume"}],
    )
    monkeypatch.setattr(rest_module, "BLOCKED_TOOLS_HTTP", {"get_positions", "order_volume"})

    response = asyncio.run(rest_module.rest_api_tools_list(make_request()))
    body = parse_response(response)

    assert body["success"] is True
    assert body["count"] == 1
    assert body["tools"] == [{"name": "history"}]


def test_rest_tool_info_blocked_and_missing(monkeypatch):
    monkeypatch.setattr(rest_module, "_tool_functions", {"history": object()})
    monkeypatch.setattr(rest_module, "BLOCKED_TOOLS_HTTP", {"get_positions"})

    blocked = asyncio.run(
        rest_module.rest_api_tool_info(make_request(path="/api/v1/tools/get_positions", path_params={"tool_name": "get_positions"}))
    )
    missing = asyncio.run(
        rest_module.rest_api_tool_info(make_request(path="/api/v1/tools/missing", path_params={"tool_name": "missing"}))
    )

    assert blocked.status_code == 403
    assert parse_response(blocked)["success"] is False
    assert missing.status_code == 404


def test_rest_tools_list_exposes_protected_tools_by_default(monkeypatch):
    monkeypatch.setattr(
        rest_module,
        "_build_registered_tools",
        lambda: [{"name": "history"}, {"name": "get_positions"}, {"name": "order_volume"}],
    )
    monkeypatch.setattr(rest_module, "BLOCKED_TOOLS_HTTP", set())

    response = asyncio.run(rest_module.rest_api_tools_list(make_request()))
    body = parse_response(response)

    assert body["success"] is True
    assert body["count"] == 3
    assert body["tools"] == [{"name": "history"}, {"name": "get_positions"}, {"name": "order_volume"}]


def test_rest_tool_info_success(monkeypatch):
    monkeypatch.setattr(rest_module, "_tool_functions", {"history": object()})
    monkeypatch.setattr(
        rest_module,
        "_build_registered_tools",
        lambda: [{"name": "history", "description": "desc", "inputSchema": {"type": "object"}}],
    )

    response = asyncio.run(
        rest_module.rest_api_tool_info(make_request(path="/api/v1/tools/history", path_params={"tool_name": "history"}))
    )
    body = parse_response(response)

    assert body["success"] is True
    assert body["tool"]["name"] == "history"


def test_rest_tool_info_exposes_protected_tool_when_not_blocked(monkeypatch):
    monkeypatch.setattr(rest_module, "_tool_functions", {"get_positions": object()})
    monkeypatch.setattr(
        rest_module,
        "_build_registered_tools",
        lambda: [{"name": "get_positions", "description": "desc", "inputSchema": {"type": "object"}}],
    )
    monkeypatch.setattr(rest_module, "BLOCKED_TOOLS_HTTP", set())

    response = asyncio.run(
        rest_module.rest_api_tool_info(
            make_request(path="/api/v1/tools/get_positions", path_params={"tool_name": "get_positions"})
        )
    )
    body = parse_response(response)

    assert body["success"] is True
    assert body["tool"]["name"] == "get_positions"


def test_rest_tool_call_parses_json_result(monkeypatch):
    async def history(symbol: str):
        return json.dumps({"symbol": symbol})

    monkeypatch.setattr(rest_module, "_tool_functions", {"history": history})

    response = asyncio.run(
        rest_module.rest_api_tool_call(
            make_request(
                method="POST",
                path="/api/v1/tools/history",
                body={"symbol": "SHSE.600000"},
                path_params={"tool_name": "history"},
            )
        )
    )
    body = parse_response(response)

    assert body == {"success": True, "data": {"symbol": "SHSE.600000"}}


def test_rest_tool_call_returns_plain_text_and_type_error(monkeypatch):
    async def plain():
        return "ok"

    async def needs_arg(symbol: str):
        return symbol

    monkeypatch.setattr(rest_module, "_tool_functions", {"plain": plain, "needs_arg": needs_arg})

    ok_response = asyncio.run(
        rest_module.rest_api_tool_call(
            make_request(method="POST", path="/api/v1/tools/plain", body={}, path_params={"tool_name": "plain"})
        )
    )
    error_response = asyncio.run(
        rest_module.rest_api_tool_call(
            make_request(method="POST", path="/api/v1/tools/needs_arg", body={}, path_params={"tool_name": "needs_arg"})
        )
    )

    assert parse_response(ok_response) == {"success": True, "data": "ok"}
    assert error_response.status_code == 400
    assert "Invalid arguments" in parse_response(error_response)["error"]


def test_rest_tool_call_get_converts_types(monkeypatch):
    seen = {}

    async def history(enabled: bool, count: int, price: float, symbol: str):
        seen.update(
            {
                "enabled": enabled,
                "count": count,
                "price": price,
                "symbol": symbol,
            }
        )
        return json.dumps({"ok": True})

    monkeypatch.setattr(rest_module, "_tool_functions", {"history": history})

    response = asyncio.run(
        rest_module.rest_api_tool_call_get(
            make_request(
                path="/api/v1/tools/history/call",
                query_string="enabled=true&count=3&price=10.5&symbol=SHSE.600000",
                path_params={"tool_name": "history"},
            )
        )
    )

    assert parse_response(response) == {"success": True, "data": {"ok": True}}
    assert seen == {"enabled": True, "count": 3, "price": 10.5, "symbol": "SHSE.600000"}
