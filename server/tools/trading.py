"""
Trading tools - order_volume, order_value, order_cancel, etc.
"""
import json
from typing import Optional
from server.mcp_server import mcp
from server.config import validate_auth, format_list_response, audit_wrapper, DEFAULT_ACCOUNT_ID
from server.tools import tool_registry

# GM API imports
from gm.api import (
    order_volume as gm_order_volume,
    order_value as gm_order_value,
    order_target_volume as gm_order_target_volume,
    order_percent as gm_order_percent,
    order_target_value as gm_order_target_value,
    order_target_percent as gm_order_target_percent,
    order_batch as gm_order_batch,
    get_unfinished_orders as gm_get_unfinished_orders,
    order_cancel as gm_order_cancel,
    order_cancel_all as gm_order_cancel_all,
    order_close_all as gm_order_close_all,
    set_account_id as gm_set_account_id,
    OrderType_Limit,
    PositionEffect_Open,
    PositionEffect_Close,
    PositionSide_Long,
)


# Trading tools (require authentication)
@mcp.tool()
@audit_wrapper
@tool_registry("order_volume")
async def order_volume(auth_token: str, symbol: str, volume: int, side: int, price: Optional[float] = None) -> str:
    """按指定数量买入或卖出股票，对应 GM: order_volume。

    参数:
    - auth_token: 认证令牌
    - symbol: 标的代码 (如 "SZSE.002236")
    - volume: 委托数量（股数）
    - side: 委托方向 (1=买入, 2=卖出)
    - price: 委托价格（可选）

    示例:
    - order_volume(auth_token="admin", symbol="SZSE.002236", volume=100, side=1, price=10.5)
    - order_volume(auth_token="admin", symbol="SZSE.002236", volume=100, side=2, price=11.0)
    """
    if not validate_auth(auth_token):
        raise ValueError("Error: Invalid authentication token")
    # Set account context before placing orders
    gm_set_account_id(DEFAULT_ACCOUNT_ID)
    # Map side to position_effect: 1=buy→Open, 2=sell→Close
    position_effect = PositionEffect_Open if side == 1 else PositionEffect_Close
    res = gm_order_volume(
        symbol=symbol,
        volume=int(volume),
        side=side,
        order_type=OrderType_Limit,
        position_effect=position_effect,
        price=float(price) if price is not None else 0,
    )
    return format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)


@mcp.tool()
@audit_wrapper
@tool_registry("order_value")
async def order_value(auth_token: str, symbol: str, value: float, side: int, price: Optional[float] = None) -> str:
    """按指定金额买入或卖出股票，对应 GM: order_value。

    参数:
    - auth_token: 认证令牌
    - symbol: 标的代码 (如 "SZSE.002236")
    - value: 委托金额（元）
    - side: 委托方向 (1=买入, 2=卖出)
    - price: 委托价格（可选）

    示例:
    - order_value(auth_token="admin", symbol="SZSE.002236", value=10000, side=1, price=10.5)
    - order_value(auth_token="admin", symbol="SZSE.002236", value=10000, side=2, price=11.0)

    注意: 系统根据 value/price 计算数量，最小单位100股
    """
    if not validate_auth(auth_token):
        raise ValueError("Error: Invalid authentication token")
    # Set account context before placing orders
    gm_set_account_id(DEFAULT_ACCOUNT_ID)
    # Map side to position_effect: 1=buy→Open, 2=sell→Close
    position_effect = PositionEffect_Open if side == 1 else PositionEffect_Close
    res = gm_order_value(
        symbol=symbol,
        value=float(value),
        side=side,
        order_type=OrderType_Limit,
        position_effect=position_effect,
        price=float(price) if price is not None else 0,
    )
    return format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)


@mcp.tool()
@audit_wrapper
@tool_registry("order_target_volume")
async def order_target_volume(auth_token: str, symbol: str, volume: int) -> str:
    """调仓到目标持仓量，对应 GM: order_target_volume。

    参数:
    - auth_token: 认证令牌
    - symbol: 标的代码 (如 "SZSE.002236")
    - volume: 目标持仓数量（股数）

    示例:
    - order_target_volume(auth_token="admin", symbol="SZSE.002236", volume=0)  # 清仓
    - order_target_volume(auth_token="admin", symbol="SZSE.002236", volume=1000)  # 调整到1000股

    注意: 系统自动判断买入或卖出，volume=0表示全部卖出
    """
    if not validate_auth(auth_token):
        raise ValueError("Error: Invalid authentication token")
    # Set account context before placing orders
    gm_set_account_id(DEFAULT_ACCOUNT_ID)
    res = gm_order_target_volume(
        symbol=symbol,
        volume=int(volume),
        position_side=PositionSide_Long,
        order_type=OrderType_Limit,
    )
    return format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)


@mcp.tool()
@audit_wrapper
@tool_registry("order_cancel")
async def order_cancel(auth_token: str, wait_cancel_orders: list) -> str:
    """撤销指定委托单，对应 GM: order_cancel。

    参数:
    - auth_token: 认证令牌
    - wait_cancel_orders: 要撤销的订单列表 (每项包含 cl_ord_id 和 account_id)

    示例:
    - order_cancel(auth_token="admin", wait_cancel_orders=[{'cl_ord_id': '123', 'account_id': 'acc_id'}])

    提示: 可先使用 get_unfinished_orders() 查询未成交订单
    """
    if not validate_auth(auth_token):
        raise ValueError("Error: Invalid authentication token")
    res = gm_order_cancel(wait_cancel_orders=wait_cancel_orders)
    return format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)


@mcp.tool()
@audit_wrapper
@tool_registry("order_cancel_all")
async def order_cancel_all(auth_token: str) -> str:
    """撤销所有未成交的委托单，对应 GM: order_cancel_all。

    参数:
    - auth_token: 认证令牌

    示例:
    - order_cancel_all(auth_token="admin")
    """
    if not validate_auth(auth_token):
        raise ValueError("Error: Invalid authentication token")
    res = gm_order_cancel_all()
    return format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)


@mcp.tool()
@audit_wrapper
@tool_registry("order_close_all")
async def order_close_all(auth_token: str) -> str:
    """平仓所有持仓（卖出所有股票），对应 GM: order_close_all。

    参数:
    - auth_token: 认证令牌

    示例:
    - order_close_all(auth_token="admin")

    ⚠️ 警告: 此操作会卖出所有持仓，不可撤销！
    """
    if not validate_auth(auth_token):
        raise ValueError("Error: Invalid authentication token")
    res = gm_order_close_all()
    return format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)


# Order percent (按总资产指定比例委托)
@mcp.tool()
@audit_wrapper
@tool_registry("order_percent")
async def order_percent(auth_token: str, symbol: str, percent: float, side: int, price: Optional[float] = None) -> str:
    """按总资产指定比例委托，对应 GM: order_percent。

    参数:
    - auth_token: 认证令牌
    - symbol: 标的代码
    - percent: 委托数量占总资产的比例（0-100）
    - side: 委托方向，1=买入，2=卖出
    - price: 委托价格（限价单必须），默认 None
    """
    if not validate_auth(auth_token):
        raise ValueError("Error: Invalid authentication token")
    # Set account context before placing orders
    gm_set_account_id(DEFAULT_ACCOUNT_ID)
    # Map side to position_effect: 1=buy→Open, 2=sell→Close
    position_effect = PositionEffect_Open if side == 1 else PositionEffect_Close
    res = gm_order_percent(
        symbol=symbol,
        percent=float(percent),
        side=side,
        order_type=OrderType_Limit,
        position_effect=position_effect,
        price=float(price) if price is not None else 0,
    )
    return format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)


# Order target value (调仓到目标持仓额)
@mcp.tool()
@audit_wrapper
@tool_registry("order_target_value")
async def order_target_value(auth_token: str, symbol: str, value: float) -> str:
    """调仓到目标持仓额，对应 GM: order_target_value。

    参数:
    - auth_token: 认证令牌
    - symbol: 标的代码 (如 "SZSE.002236")
    - value: 目标持仓金额（元）

    示例:
    - order_target_value(auth_token="admin", symbol="SZSE.002236", value=0)  # 清仓
    - order_target_value(auth_token="admin", symbol="SZSE.002236", value=100000)  # 调整到10万元

    注意: 系统自动判断买入或卖出，value=0表示全部卖出
    """
    if not validate_auth(auth_token):
        raise ValueError("Error: Invalid authentication token")
    # Set account context before placing orders
    gm_set_account_id(DEFAULT_ACCOUNT_ID)
    res = gm_order_target_value(
        symbol=symbol,
        value=float(value),
        position_side=PositionSide_Long,
        order_type=OrderType_Limit,
    )
    return format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)


# Order target percent (调仓到目标持仓比例)
@mcp.tool()
@audit_wrapper
@tool_registry("order_target_percent")
async def order_target_percent(auth_token: str, symbol: str, percent: float) -> str:
    """调仓到目标持仓比例（总资产比例），对应 GM: order_target_percent。

    参数:
    - auth_token: 认证令牌
    - symbol: 标的代码 (如 "SZSE.002236")
    - percent: 目标持仓比例占总资产的比例（0-100）

    示例:
    - order_target_percent(auth_token="admin", symbol="SZSE.002236", percent=0)  # 清仓
    - order_target_percent(auth_token="admin", symbol="SZSE.002236", percent=10)  # 调整到10%

    注意: 系统自动判断买入或卖出，percent=0表示全部卖出
    """
    if not validate_auth(auth_token):
        raise ValueError("Error: Invalid authentication token")
    # Set account context before placing orders
    gm_set_account_id(DEFAULT_ACCOUNT_ID)
    res = gm_order_target_percent(
        symbol=symbol,
        percent=float(percent),
        position_side=PositionSide_Long,
        order_type=OrderType_Limit,
    )
    return format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)


# Order batch (批量委托接口)
@mcp.tool()
@audit_wrapper
@tool_registry("order_batch")
async def order_batch(auth_token: str, orders: list) -> str:
    """批量委托接口，对应 GM: order_batch。

    参数:
    - auth_token: 认证令牌
    - orders: 委托列表，每项包含:
        - symbol: 标的代码
        - volume: 委托数量（按数量委托时必填）
        - value: 委托金额（按金额委托时必填）
        - side: 委托方向，1=买入，2=卖出
        - price: 委托价格（可选）
        - order_type: 委托类型（可选）
    """
    if not validate_auth(auth_token):
        raise ValueError("Error: Invalid authentication token")
    # Set account context before placing orders
    gm_set_account_id(DEFAULT_ACCOUNT_ID)
    # Pass orders as positional argument (GM API doesn't accept keyword argument 'orders')
    res = gm_order_batch(orders)
    return format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)


# Get unfinished orders (查询日内全部未结委托)
@mcp.tool()
@audit_wrapper
@tool_registry("get_unfinished_orders")
async def get_unfinished_orders(auth_token: str) -> str:
    """查询日内全部未结委托，对应 GM: get_unfinished_orders。

    参数:
    - auth_token: 认证令牌
    """
    if not validate_auth(auth_token):
        raise ValueError("Error: Invalid authentication token")
    res = gm_get_unfinished_orders()
    return format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)
