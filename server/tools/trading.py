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


def _normalize_gm_batch_orders(orders: list) -> list:
    """为每条批量委托补全与 order_volume 一致的默认字段，避免柜台因缺 position_effect / order_type 拒单。"""
    normalized = []
    for raw in orders:
        if not isinstance(raw, dict):
            normalized.append(raw)
            continue
        item = dict(raw)
        side = item.get("side")
        if side is not None:
            try:
                side_int = int(side)
            except (TypeError, ValueError):
                side_int = None
            if side_int in (1, 2) and "position_effect" not in item:
                item["position_effect"] = (
                    PositionEffect_Open if side_int == 1 else PositionEffect_Close
                )
        if "order_type" not in item:
            item["order_type"] = OrderType_Limit
        normalized.append(item)
    return normalized


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
    - price: 委托价格。本工具固定使用 GM 限价单（OrderType_Limit）；若省略，会向底层传 price=0。
      A 股多数模拟/实盘柜台对限价单要求有效价格，省略时常报「委托价格不可以为0」。实盘/模拟盘建议始终传入挂单价。

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
    - price: 用于把金额折算为股数的限价。本工具固定为限价单；若省略则传 price=0，与「按金额自动用市价/最新价」的常见框架语义不同，
      A 股柜台通常会直接拒绝。按金额下单时务必传入与折算一致的有效限价（或改用自算股数 + order_volume）。

    示例:
    - order_value(auth_token="admin", symbol="SZSE.002236", value=10000, side=1, price=10.5)
    - order_value(auth_token="admin", symbol="SZSE.002236", value=10000, side=2, price=11.0)

    注意: 系统根据 value/price 计算数量，最小单位 100 股（以柜台规则为准）。
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
    - price: 限价单委托价。省略时传 price=0；A 股限价场景下柜台通常要求非零价格，建议显式传入。
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
    - orders: 委托列表，每项为 dict。字段以 GM 柜台要求为准；常见包括:
        - symbol: 标的代码
        - volume: 委托数量（按数量委托时必填）
        - value: 委托金额（按金额委托时必填）
        - side: 委托方向，1=买入，2=卖出
        - price: 限价单价格（A 股限价场景下通常必填，否则易与单笔接口同样被拒）
        - order_type: 委托类型；若省略，服务端会默认补为限价单（与 order_volume 一致）
        - position_effect: 开平标志；若省略，服务端会按 side 补全（1→开仓，2→平仓），与单笔封装一致

    说明: GM 的 order_batch 不会自动填充与 order_volume 相同的默认值；本工具在调用前会为缺省项补上 order_type、position_effect，
    但若柜台仍要求其它字段或合法 price，需调用方在每条 order 中写全。
    """
    if not validate_auth(auth_token):
        raise ValueError("Error: Invalid authentication token")
    # Set account context before placing orders
    gm_set_account_id(DEFAULT_ACCOUNT_ID)
    # Pass orders as positional argument (GM API doesn't accept keyword argument 'orders')
    res = gm_order_batch(_normalize_gm_batch_orders(orders))
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
