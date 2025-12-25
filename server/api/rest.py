"""
RESTful API endpoints for tool invocation.
"""
import json
from starlette.requests import Request
from starlette.responses import JSONResponse

from server.tools import _tool_functions
from server.api.direct_call import _build_registered_tools, _build_tool_schema


async def rest_api_tools_list(request: Request) -> JSONResponse:
    """RESTful API: Get all available tools.

    GET /api/v1/tools
    Returns: {"success": true, "count": N, "tools": [...]}
    """
    try:
        tools = _build_registered_tools()
        return JSONResponse({
            "success": True,
            "count": len(tools),
            "tools": tools
        })
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


async def rest_api_tool_info(request: Request) -> JSONResponse:
    """RESTful API: Get specific tool information.

    GET /api/v1/tools/{tool_name}
    Returns: {"success": true, "tool": {...}}
    """
    tool_name = request.path_params.get("tool_name")
    if not tool_name:
        return JSONResponse({"success": False, "error": "Tool name is required"}, status_code=400)

    if tool_name not in _tool_functions:
        return JSONResponse({"success": False, "error": f"Tool '{tool_name}' not found"}, status_code=404)

    try:
        tools = _build_registered_tools()
        tool_info = next((t for t in tools if t["name"] == tool_name), None)
        if not tool_info:
            return JSONResponse({"success": False, "error": f"Tool '{tool_name}' not found"}, status_code=404)
        return JSONResponse({"success": True, "tool": tool_info})
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


async def rest_api_tool_call(request: Request) -> JSONResponse:
    """RESTful API: Invoke tool via POST.

    POST /api/v1/tools/{tool_name}
    Body: JSON object with tool parameters
    Returns: {"success": true, "data": ...} or {"success": false, "error": "..."}
    """
    tool_name = request.path_params.get("tool_name")
    if not tool_name:
        return JSONResponse({"success": False, "error": "Tool name is required"}, status_code=400)

    if tool_name not in _tool_functions:
        return JSONResponse({"success": False, "error": f"Tool '{tool_name}' not found"}, status_code=404)

    try:
        body = await request.json()
        arguments = body if isinstance(body, dict) else {}

        tool_func = _tool_functions[tool_name]
        result_text = await tool_func(**arguments)

        # Try to parse JSON result
        try:
            result_data = json.loads(result_text)
            return JSONResponse({"success": True, "data": result_data})
        except (json.JSONDecodeError, TypeError):
            return JSONResponse({"success": True, "data": result_text})
    except TypeError as e:
        return JSONResponse({"success": False, "error": f"Invalid arguments: {str(e)}"}, status_code=400)
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


async def rest_api_tool_call_get(request: Request) -> JSONResponse:
    """RESTful API: Invoke tool via GET with query params.

    GET /api/v1/tools/{tool_name}/call?param1=value1&param2=value2
    Returns: {"success": true, "data": ...} or {"success": false, "error": "..."}
    """
    tool_name = request.path_params.get("tool_name")
    if not tool_name:
        return JSONResponse({"success": False, "error": "Tool name is required"}, status_code=400)

    if tool_name not in _tool_functions:
        return JSONResponse({"success": False, "error": f"Tool '{tool_name}' not found"}, status_code=404)

    try:
        arguments = dict(request.query_params)

        # Convert types (string -> number/bool)
        for key, value in arguments.items():
            if value.lower() == "true":
                arguments[key] = True
            elif value.lower() == "false":
                arguments[key] = False
            elif value.isdigit():
                arguments[key] = int(value)
            elif value.replace(".", "", 1).isdigit():
                arguments[key] = float(value)

        tool_func = _tool_functions[tool_name]
        result_text = await tool_func(**arguments)

        try:
            result_data = json.loads(result_text)
            return JSONResponse({"success": True, "data": result_data})
        except (json.JSONDecodeError, TypeError):
            return JSONResponse({"success": True, "data": result_text})
    except TypeError as e:
        return JSONResponse({"success": False, "error": f"Invalid arguments: {str(e)}"}, status_code=400)
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


__all__ = [
    "rest_api_tools_list",
    "rest_api_tool_info",
    "rest_api_tool_call",
    "rest_api_tool_call_get",
]
