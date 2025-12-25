"""
Direct call API - JSON-RPC style endpoint for tool invocation.
"""
import json
from starlette.requests import Request
from starlette.responses import JSONResponse

from server.tools import _tool_functions


def _python_type_to_json_type(anno) -> str:
    """Map Python type annotations to JSON Schema types."""
    origin = getattr(anno, "__origin__", None)
    if origin is list or origin is list:
        return "array"
    if origin is dict or origin is dict:
        return "object"
    if anno in (int, float):
        return "number"
    if anno is bool:
        return "boolean"
    return "string"


def _build_tool_schema(func) -> dict:
    """Generate input schema from function signature."""
    import inspect
    sig = inspect.signature(func)
    properties = {}
    required = []

    for name, param in sig.parameters.items():
        if name == "self":
            continue
        anno = param.annotation
        json_type = _python_type_to_json_type(anno)
        field = {"type": json_type}
        if param.default is not inspect._empty:
            field["default"] = param.default
        else:
            required.append(name)
        properties[name] = field

    schema = {"type": "object", "properties": properties}
    if required:
        schema["required"] = required
    return schema


def _build_registered_tools() -> list:
    """Build tool list from _tool_functions for JSON-RPC tools/list."""
    import inspect
    tools = []
    for name, func in _tool_functions.items():
        doc = inspect.getdoc(func) or ""
        first_line = doc.strip().splitlines()[0] if doc.strip() else ""
        tools.append({
            "name": name,
            "description": first_line,
            "inputSchema": _build_tool_schema(func),
        })
    return tools


async def direct_call_endpoint(request: Request) -> JSONResponse:
    """Direct call endpoint for JSON-RPC style tool invocation.

    Supported methods:
    - tools/list: Return available tools list
    - tools/call: Invoke tool with params = {"name": tool_name, "arguments": {...}}
    """
    try:
        body = await request.json()
        method = body.get("method")
        request_id = body.get("id")

        # Tools list
        if method == "tools/list":
            try:
                return JSONResponse({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {"tools": _build_registered_tools()},
                })
            except Exception as e:
                return JSONResponse({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32603,
                        "message": f"Internal error: {str(e)}",
                    },
                })

        # Call tool
        if method == "tools/call":
            params = body.get("params", {}) or {}
            tool_name = params.get("name")
            arguments = params.get("params", {}).get("arguments", {}) or {}

            if tool_name not in _tool_functions:
                return JSONResponse({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": f"Unknown tool: {tool_name}",
                    },
                })

            try:
                tool_func = _tool_functions[tool_name]
                result_text = await tool_func(**arguments)

                return JSONResponse({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": {
                        "content": [{"type": "text", "text": str(result_text)}]
                    },
                })
            except Exception as e:
                return JSONResponse({
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "error": {"code": -32000, "message": str(e)},
                })

        # Unknown method
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32601, "message": "Method not found"},
        })
    except Exception as e:
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": body.get("id") if "body" in locals() else None,
            "error": {"code": -32603, "message": f"Request error: {str(e)}"},
        })


# Export for use in other modules
__all__ = ["direct_call_endpoint", "_build_registered_tools"]
