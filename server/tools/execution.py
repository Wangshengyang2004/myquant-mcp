"""
Execution tools - positions, orders, cash, execution reports, code execution.
"""
import io
import json
from contextlib import redirect_stdout
from datetime import datetime, date
from server.mcp_server import mcp
from server.config import validate_auth, format_list_response
from log_config import audit_logger

# GM API imports
# GM API imports
from gm.api import (
    get_position as gm_get_position,
    get_orders as gm_get_orders,
    get_cash as gm_get_cash,
    get_execution_reports as gm_get_execution_reports,
)

# Config
from server.config import DEFAULT_ACCOUNT_ID

# Tool functions mapping
_tool_functions = {}


def audit_wrapper(func):
    """Audit logging decorator"""
    import functools
    import time

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        tool_name = func.__name__
        try:
            arguments = kwargs.copy()
            log_args = {k: v for k, v in arguments.items() if k != "auth_token"}
            if "auth_token" in arguments:
                log_args["auth_token"] = "***"

            result = await func(*args, **kwargs)
            duration_ms = (time.time() - start_time) * 1000
            audit_logger.log_tool_call(tool_name, log_args, "success", duration_ms=duration_ms)
            return result
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            log_args = {k: v for k, v in kwargs.items() if k != "auth_token"}
            if "auth_token" in kwargs:
                log_args["auth_token"] = "***"
            audit_logger.log_tool_call(tool_name, log_args, "error", error=str(e), duration_ms=duration_ms)
            raise
    return wrapper


# Code execution tool
@mcp.tool()
@audit_wrapper
async def exec_code(auth_token: str, code: str) -> str:
    """Execute Python on server."""
    if not validate_auth(auth_token):
        raise ValueError("Error: Invalid authentication token")

    stdout_buffer = io.StringIO()
    with redirect_stdout(stdout_buffer):
        exec(code, {
            "__builtins__": __builtins__,
            "datetime": datetime,
            "date": date,
            "json": json,
            "math": __import__('math'),
            "gm": __import__('gm.api')
        }, {})
    output = stdout_buffer.getvalue().strip()
    return f"STDOUT:\n{output}" if output else "Done."
_tool_functions["exec_code"] = exec_code


# Query tools (public, no authentication required)
@mcp.tool()
@audit_wrapper
async def get_positions() -> str:
    """Get positions."""
    res = gm_get_position(account_id=DEFAULT_ACCOUNT_ID)
    return format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)
_tool_functions["get_positions"] = get_positions


@mcp.tool()
@audit_wrapper
async def get_orders() -> str:
    """Get orders."""
    res = gm_get_orders()
    return format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)
_tool_functions["get_orders"] = get_orders


@mcp.tool()
@audit_wrapper
async def get_cash() -> str:
    """Get cash balance."""
    res = gm_get_cash(account_id=DEFAULT_ACCOUNT_ID)
    return format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)
_tool_functions["get_cash"] = get_cash


@mcp.tool()
@audit_wrapper
async def get_execution_reports() -> str:
    """Get execution reports."""
    res = gm_get_execution_reports()
    return format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)
_tool_functions["get_execution_reports"] = get_execution_reports
