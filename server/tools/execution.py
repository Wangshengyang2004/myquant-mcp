"""
Execution tools - positions, orders, cash, execution reports.
"""
import json
from server.mcp_server import mcp
from server.config import validate_auth, format_list_response, audit_wrapper, DEFAULT_ACCOUNT_ID
from server.tools import tool_registry

# GM API imports
from gm.api import (
    get_position as gm_get_position,
    get_orders as gm_get_orders,
    get_cash as gm_get_cash,
    get_execution_reports as gm_get_execution_reports,
)


# Account query tools (protected when REQUIRE_AUTH_TOKEN=true)
@mcp.tool()
@audit_wrapper
@tool_registry("get_positions")
async def get_positions(auth_token: str) -> str:
    """Get positions."""
    if not validate_auth(auth_token):
        raise ValueError("Error: Invalid authentication token")
    res = gm_get_position(account_id=DEFAULT_ACCOUNT_ID)
    return format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)


@mcp.tool()
@audit_wrapper
@tool_registry("get_orders")
async def get_orders(auth_token: str) -> str:
    """Get orders."""
    if not validate_auth(auth_token):
        raise ValueError("Error: Invalid authentication token")
    res = gm_get_orders()
    return format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)


@mcp.tool()
@audit_wrapper
@tool_registry("get_cash")
async def get_cash(auth_token: str) -> str:
    """Get cash balance."""
    if not validate_auth(auth_token):
        raise ValueError("Error: Invalid authentication token")
    res = gm_get_cash(account_id=DEFAULT_ACCOUNT_ID)
    return format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)


@mcp.tool()
@audit_wrapper
@tool_registry("get_execution_reports")
async def get_execution_reports(auth_token: str) -> str:
    """Get execution reports."""
    if not validate_auth(auth_token):
        raise ValueError("Error: Invalid authentication token")
    res = gm_get_execution_reports()
    return format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)
