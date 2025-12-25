"""
Web UI API - serves the webui.html and provides tool list endpoint.
"""
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse

from server.config import WEBUI_HTML_PATH
from server.api.direct_call import _build_registered_tools

_WEBUI_HTML_CACHE = None


async def webui_home(request: Request) -> HTMLResponse:
    """Serve the Web UI.

    HTML template is located at `webui.html` in project root.
    """
    global _WEBUI_HTML_CACHE

    if _WEBUI_HTML_CACHE is None:
        try:
            _WEBUI_HTML_CACHE = WEBUI_HTML_PATH.read_text(encoding="utf-8")
        except FileNotFoundError:
            return HTMLResponse(
                "<h1>MyQuant MCP Web UI</h1><p>webui.html 文件未找到，请检查部署。</p>",
                status_code=500,
            )

    return HTMLResponse(content=_WEBUI_HTML_CACHE)


async def webui_api_tools(request: Request) -> JSONResponse:
    """Web UI API: Get tools list."""
    try:
        return JSONResponse({"tools": _build_registered_tools()})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


__all__ = ["webui_home", "webui_api_tools"]
