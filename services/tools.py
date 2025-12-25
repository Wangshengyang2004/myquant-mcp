"""
SDK Tools creation service.

Wraps windows_server tool functions for use with Claude Agent SDK.
"""
import inspect
from log_config import logger


def create_sdk_tools_from_functions():
    """Create SDK tools from windows_server._tool_functions"""
    from server.tools import _tool_functions

    # Import tool decorator only if SDK is available
    try:
        from claude_agent_sdk import tool
    except ImportError as e:
        logger.warning(f"Claude Agent SDK not available, tools will not be created. Error: {e}")
        return []

    sdk_tools = []
    for tool_name, tool_func in _tool_functions.items():
        # Get docstring and parameters from the function
        doc = tool_func.__doc__ or f"Tool: {tool_name}"

        # Get function signature to extract parameters
        sig = inspect.signature(tool_func)
        params = {}
        for param_name, param in sig.parameters.items():
            # Keep auth_token parameter - user will provide it
            # Map Python types to SDK types
            param_type = param.annotation if param.annotation != inspect.Parameter.empty else str
            if param_type == int:
                params[param_name] = int
            elif param_type == float:
                params[param_name] = float
            else:
                params[param_name] = str

        # Create SDK tool wrapper with closure to capture tool_func
        def make_tool_wrapper(f):
            @tool(tool_name, doc.strip(), params)
            async def tool_wrapper(args: dict):
                try:
                    result = await f(**args)
                    return {"content": [{"type": "text", "text": result}]}
                except Exception as e:
                    return {"content": [{"type": "text", "text": f"Error: {str(e)}"}]}
            return tool_wrapper

        sdk_tools.append(make_tool_wrapper(tool_func))

    logger.info(f"Created {len(sdk_tools)} SDK tools from windows_server")
    return sdk_tools


# Create SDK tools once at module import
_ALL_SDK_TOOLS = create_sdk_tools_from_functions()
