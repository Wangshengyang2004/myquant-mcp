"""
SDK Tools creation service.

Wraps windows_server tool functions for use with Claude Agent SDK.
"""
from server.log_config import logger


def create_sdk_tools_from_functions():
    """Create SDK tools from windows_server._tool_functions"""
    from server.tools import _tool_functions
    from claude_agent_sdk import tool

    sdk_tools = []
    for tool_name, tool_func in _tool_functions.items():
        # Get docstring and parameters from the function
        doc = tool_func.__doc__ or f"Tool: {tool_name}"

        # Get function signature to extract parameters
        sig = tool_func.__code__
        param_names = sig.co_varnames[:sig.co_argcount]
        params = {name: str for name in param_names}

        # Create SDK tool wrapper with default arg to capture value (avoids late binding closure)
        def make_tool_wrapper(f=tool_func, name=tool_name, description=doc.strip(), param_schema=params):
            @tool(name, description, param_schema)
            async def tool_wrapper(args: dict):
                try:
                    result = await f(**args)
                    return {"content": [{"type": "text", "text": result}]}
                except Exception as e:
                    return {"content": [{"type": "text", "text": f"Error: {str(e)}"}], "is_error": True}
            return tool_wrapper

        sdk_tools.append(make_tool_wrapper())

    logger.info(f"Created {len(sdk_tools)} SDK tools from windows_server")
    return sdk_tools


# Create SDK tools once at module import
_ALL_SDK_TOOLS = create_sdk_tools_from_functions()
