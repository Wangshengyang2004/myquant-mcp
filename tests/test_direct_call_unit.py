import asyncio
import json

from starlette.requests import Request

from server.api import direct_call as direct_call_module


def make_request(body):
    payload = json.dumps(body).encode("utf-8")
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
        "method": "POST",
        "scheme": "http",
        "path": "/api/direct_call",
        "raw_path": b"/api/direct_call",
        "query_string": b"",
        "headers": [(b"content-type", b"application/json")],
        "client": ("127.0.0.1", 1234),
        "server": ("testserver", 80),
        "path_params": {},
    }
    return Request(scope, receive)


def parse_response(response):
    return json.loads(response.body.decode("utf-8"))


def test_python_type_to_json_type():
    assert direct_call_module._python_type_to_json_type(int) == "number"
    assert direct_call_module._python_type_to_json_type(bool) == "boolean"
    assert direct_call_module._python_type_to_json_type(list[str]) == "array"
    assert direct_call_module._python_type_to_json_type(dict[str, str]) == "object"
    assert direct_call_module._python_type_to_json_type(str) == "string"


def test_build_tool_schema_marks_required_and_defaults():
    def tool(symbol: str, count: int = 10, enabled: bool = False):
        """Example tool."""

    schema = direct_call_module._build_tool_schema(tool)

    assert schema["properties"]["symbol"]["type"] == "string"
    assert schema["properties"]["count"]["default"] == 10
    assert schema["properties"]["enabled"]["type"] == "boolean"
    assert schema["required"] == ["symbol"]


def test_build_registered_tools_uses_first_doc_line(monkeypatch):
    async def tool_a(symbol: str):
        """First line.\nSecond line."""

    monkeypatch.setattr(direct_call_module, "_tool_functions", {"tool_a": tool_a})

    tools = direct_call_module._build_registered_tools()

    assert tools == [
        {
            "name": "tool_a",
            "description": "First line.",
            "inputSchema": {
                "type": "object",
                "properties": {"symbol": {"type": "string"}},
                "required": ["symbol"],
            },
        }
    ]


def test_direct_call_tools_list(monkeypatch):
    async def tool_a(symbol: str):
        """First line."""

    monkeypatch.setattr(direct_call_module, "_tool_functions", {"tool_a": tool_a})

    response = asyncio.run(direct_call_module.direct_call_endpoint(make_request({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})))
    body = parse_response(response)

    assert body["id"] == 1
    assert body["result"]["tools"][0]["name"] == "tool_a"


def test_direct_call_tools_call_supports_nested_arguments(monkeypatch):
    async def tool_a(symbol: str, count: int = 1):
        return f"{symbol}:{count}"

    monkeypatch.setattr(direct_call_module, "_tool_functions", {"tool_a": tool_a})
    request = make_request(
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "tool_a", "params": {"arguments": {"symbol": "SHSE.600000", "count": 3}}},
        }
    )

    response = asyncio.run(direct_call_module.direct_call_endpoint(request))
    body = parse_response(response)

    assert body["result"]["content"][0]["text"] == "SHSE.600000:3"


def test_direct_call_unknown_tool(monkeypatch):
    monkeypatch.setattr(direct_call_module, "_tool_functions", {})
    request = make_request(
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "missing", "arguments": {}}}
    )

    response = asyncio.run(direct_call_module.direct_call_endpoint(request))
    body = parse_response(response)

    assert body["error"]["code"] == -32601
    assert "Unknown tool" in body["error"]["message"]


def test_direct_call_tool_error(monkeypatch):
    async def boom():
        raise ValueError("bad args")

    monkeypatch.setattr(direct_call_module, "_tool_functions", {"boom": boom})
    request = make_request({"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "boom"}})

    response = asyncio.run(direct_call_module.direct_call_endpoint(request))
    body = parse_response(response)

    assert body["error"]["code"] == -32000
    assert body["error"]["message"] == "bad args"


def test_direct_call_bad_json_request():
    async def receive():
        return {"type": "http.request", "body": b"not-json", "more_body": False}

    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/api/direct_call",
        "raw_path": b"/api/direct_call",
        "query_string": b"",
        "headers": [(b"content-type", b"application/json")],
        "client": ("127.0.0.1", 1234),
        "server": ("testserver", 80),
        "path_params": {},
    }

    response = asyncio.run(direct_call_module.direct_call_endpoint(Request(scope, receive)))
    body = parse_response(response)

    assert body["error"]["code"] == -32603
    assert "Request error" in body["error"]["message"]
