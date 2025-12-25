"""
Trading tools - order_volume, order_value, order_cancel, etc.
"""
import json
from server.mcp_server import mcp
from server.config import validate_auth, format_list_response
from log_config import audit_logger

# GM API imports
# GM API imports
from gm.api import (
    order_volume as gm_order_volume,
    order_value as gm_order_value,
    order_target_volume as gm_order_target_volume,
    order_cancel as gm_order_cancel,
    order_cancel_all as gm_order_cancel_all,
    order_close_all as gm_order_close_all,
    OrderType_Limit,
    PositionSide_Long,
)

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


# Trading tools (require authentication)
@mcp.tool()
@audit_wrapper
async def order_volume(auth_token: str, symbol: str, volume: int, side: int, price: float = None) -> str:
    """Order by volume."""
    if not validate_auth(auth_token):
        raise ValueError("Error: Invalid authentication token")
    res = gm_order_volume(
        symbol=symbol,
        volume=volume,
        side=side,
        order_type=OrderType_Limit,
        price=price or 0,
    )
    return format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)
_tool_functions["order_volume"] = order_volume


@mcp.tool()
@audit_wrapper
async def order_value(auth_token: str, symbol: str, value: float, side: int, price: float = None) -> str:
    """Order by value."""
    if not validate_auth(auth_token):
        raise ValueError("Error: Invalid authentication token")
    res = gm_order_value(
        symbol=symbol,
        value=value,
        side=side,
        order_type=OrderType_Limit,
        price=price,
    )
    return format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)
_tool_functions["order_value"] = order_value


@mcp.tool()
@audit_wrapper
async def order_target_volume(auth_token: str, symbol: str, volume: int) -> str:
    """Target volume."""
    if not validate_auth(auth_token):
        raise ValueError("Error: Invalid authentication token")
    res = gm_order_target_volume(
        symbol=symbol,
        volume=volume,
        position_side=PositionSide_Long,
        order_type=OrderType_Limit,
    )
    return format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)
_tool_functions["order_target_volume"] = order_target_volume


@mcp.tool()
@audit_wrapper
async def order_cancel(auth_token: str, wait_cancel_orders: list) -> str:
    """Cancel specific orders."""
    if not validate_auth(auth_token):
        raise ValueError("Error: Invalid authentication token")
    res = gm_order_cancel(wait_cancel_orders=wait_cancel_orders)
    return format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)
_tool_functions["order_cancel"] = order_cancel


@mcp.tool()
@audit_wrapper
async def order_cancel_all(auth_token: str) -> str:
    """Cancel all."""
    if not validate_auth(auth_token):
        raise ValueError("Error: Invalid authentication token")
    res = gm_order_cancel_all()
    return format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)
_tool_functions["order_cancel_all"] = order_cancel_all


@mcp.tool()
@audit_wrapper
async def order_close_all(auth_token: str) -> str:
    """Close all."""
    if not validate_auth(auth_token):
        raise ValueError("Error: Invalid authentication token")
    res = gm_order_close_all()
    return format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)
_tool_functions["order_close_all"] = order_close_all
