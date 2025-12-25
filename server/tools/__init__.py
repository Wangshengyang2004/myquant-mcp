"""
MCP Tools package.

Exports tool functions and the _tool_functions mapping table.
"""
from server.tools.market import *  # noqa: F401, F403
from server.tools.fundamental import *  # noqa: F401, F403
from server.tools.trading import *  # noqa: F401, F403
from server.tools.execution import *  # noqa: F401, F403

# Tool function mapping for direct access
_tool_functions = {}

# Register all tools from submodules
for module in [market, fundamental, trading, execution]:
    for name in getattr(module, "_tool_functions", {}):
        _tool_functions[name] = getattr(module, "_tool_functions")[name]

__all__ = ["_tool_functions"]
