"""
MCP Tools package.

Exports tool functions and the _tool_functions mapping table.
"""
# Tool registry must be defined BEFORE submodule imports (decorators use it)
_tool_functions = {}

def tool_registry(name: str):
    """Decorator to register a function in _tool_functions.

    Usage:
        @tool_registry("history")
        @mcp.tool()
        async def history(...):
            ...
    """
    def decorator(func):
        _tool_functions[name] = func
        return func
    return decorator

# Import all tools from submodules (decorators register functions during import)
from server.tools.market import *  # noqa: F401, F403
from server.tools.fundamental import *  # noqa: F401, F403
from server.tools.trading import *  # noqa: F401, F403
from server.tools.do_t import *  # noqa: F401, F403
from server.tools.execution import *  # noqa: F401, F403

__all__ = ["_tool_functions", "tool_registry"]
