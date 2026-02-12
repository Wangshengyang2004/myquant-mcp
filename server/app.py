"""
Starlette application setup - creates and configures the app.
"""
import contextlib
import logging

from starlette.applications import Starlette
from starlette.routing import Mount, Route
from starlette.middleware.cors import CORSMiddleware
from server.log_config import LoggingMiddleware

from server.mcp_server import get_mcp_app, mcp
from server.api import (
    direct_call_endpoint,
    webui_home,
    webui_api_tools,
    rest_api_tools_list,
    rest_api_tool_info,
    rest_api_tool_call,
    rest_api_tool_call_get,
)

logger = logging.getLogger("server")

# Try to import agent page routes (optional)
try:
    from server.agent_page import ROUTES as AGENT_ROUTES
    AGENT_PAGE_ENABLED = True
except ImportError:
    AGENT_PAGE_ENABLED = False
    AGENT_ROUTES = []


@contextlib.asynccontextmanager
async def lifespan(app: Starlette):
    """Lifespan context manager."""
    # Agent page startup - load conversations from storage
    if AGENT_PAGE_ENABLED:
        try:
            from server.agent_page import startup as agent_startup
            await agent_startup()
        except Exception as e:
            logger.error(f"Agent page startup failed: {e}")

    async with mcp.session_manager.run():
        yield


def create_app() -> Starlette:
    """Create and configure the Starlette application."""

    # Build routes list
    routes = [
        # Web UI
        Route("/", webui_home, methods=["GET"]),
        Route("/webui", webui_home, methods=["GET"]),

        # MCP Streamable HTTP endpoint (includes /direct_call via custom_route)
        Mount("/mcp", app=get_mcp_app()),

        # Direct call (JSON-RPC) - backward compatibility
        Route("/api/direct_call", direct_call_endpoint, methods=["POST"]),

        # Web UI API
        Route("/api/tools", webui_api_tools, methods=["GET"]),

        # RESTful API endpoints
        Route("/api/v1/tools", rest_api_tools_list, methods=["GET"]),
        Route("/api/v1/tools/{tool_name}", rest_api_tool_info, methods=["GET"]),
        Route("/api/v1/tools/{tool_name}", rest_api_tool_call, methods=["POST"]),
        Route("/api/v1/tools/{tool_name}/call", rest_api_tool_call_get, methods=["GET"]),
    ]

    # Add agent page routes if available
    if AGENT_PAGE_ENABLED:
        for path, handler, methods in AGENT_ROUTES:
            routes.append(Route(path, handler, methods=methods))

    # Create app
    app = Starlette(
        routes=routes,
        lifespan=lifespan,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["*"],
        expose_headers=["Mcp-Session-Id"],
    )

    # Add logging middleware
    app.add_middleware(LoggingMiddleware)

    return app


__all__ = ["create_app"]
