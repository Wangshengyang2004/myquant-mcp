"""
API package for server endpoints.
"""
from server.api.direct_call import direct_call_endpoint
from server.api.webui import webui_home, webui_api_tools
from server.api.rest import (
    rest_api_tools_list,
    rest_api_tool_info,
    rest_api_tool_call,
    rest_api_tool_call_get,
)

__all__ = [
    "direct_call_endpoint",
    "webui_home",
    "webui_api_tools",
    "rest_api_tools_list",
    "rest_api_tool_info",
    "rest_api_tool_call",
    "rest_api_tool_call_get",
]
