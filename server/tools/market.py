"""
Market data tools - history, current, symbols, etc.
"""
import json
from server.mcp_server import mcp
from server.config import format_dataframe_response, format_list_response
from log_config import audit_logger

# GM API imports
# GM API imports
from gm.api import (
    history as gm_history,
    history_n as gm_history_n,
    current as gm_current,
    get_symbols as gm_get_symbols,
    get_symbol_infos as gm_get_symbol_infos,
    get_trading_dates_by_year as gm_get_trading_dates_by_year,
    fut_get_continuous_contracts as gm_fut_get_continuous_contracts,
    get_history_symbol as gm_get_history_symbol,
    get_next_n_trading_dates as gm_get_next_n_trading_dates,
    get_previous_n_trading_dates as gm_get_previous_n_trading_dates,
    stk_get_index_constituents as gm_stk_get_index_constituents,
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


# Market data tools
@mcp.tool()
@audit_wrapper
async def history(symbol: str, frequency: str, start_time: str, end_time: str) -> str:
    """Query history."""
    res = gm_history(
        symbol=symbol,
        frequency=frequency,
        start_time=start_time,
        end_time=end_time,
        df=True,
    )
    return format_dataframe_response(res)
_tool_functions["history"] = history


@mcp.tool()
@audit_wrapper
async def history_n(symbol: str, frequency: str, count: int) -> str:
    """Query latest N bars."""
    res = gm_history_n(symbol=symbol, frequency=frequency, count=count, df=True)
    return format_dataframe_response(res)
_tool_functions["history_n"] = history_n


@mcp.tool()
@audit_wrapper
async def current(symbols: str) -> str:
    """Market snapshot."""
    res = gm_current(symbols=symbols)
    return format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)
_tool_functions["current"] = current


@mcp.tool()
@audit_wrapper
async def get_symbols(sec_type1: int, trade_date: str = None) -> str:
    """查询指定交易日多标的交易信息，对应 GM: get_symbols。

    参数:
    - sec_type1: 证券品种大类（必填），如:
        1010: 股票, 1020: 基金, 1030: 债券, 1040: 期货,
        1050: 期权, 1060: 指数, 1070: 板块
    - trade_date: 交易日期 'YYYY-MM-DD'，None 表示最新截面
    """
    res = gm_get_symbols(sec_type1=sec_type1, trade_date=trade_date)
    return format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)
_tool_functions["get_symbols"] = get_symbols


@mcp.tool()
@audit_wrapper
async def get_symbol_infos(sec_type1: int) -> str:
    """Basic symbol info."""
    res = gm_get_symbol_infos(sec_type1=sec_type1)
    return format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)
_tool_functions["get_symbol_infos"] = get_symbol_infos


@mcp.tool()
@audit_wrapper
async def get_trading_dates(exchange: str, start_year: int, end_year: int) -> str:
    """Get trading dates."""
    res = gm_get_trading_dates_by_year(
        exchange=exchange,
        start_year=start_year,
        end_year=end_year,
    )
    return format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)
_tool_functions["get_trading_dates"] = get_trading_dates


@mcp.tool()
@audit_wrapper
async def fut_get_continuous(csymbol: str) -> str:
    """Continuous futures symbols."""
    res = gm_fut_get_continuous_contracts(csymbol=csymbol)
    return format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)
_tool_functions["fut_get_continuous"] = fut_get_continuous


@mcp.tool()
@audit_wrapper
async def get_history_symbol(symbol: str, start_date: str = None, end_date: str = None) -> str:
    """查询指定标的多日交易信息，对应 GM: get_history_symbol。

    参数:
    - symbol: 标的代码（必填），只能输入一个，如 'SHSE.600820'
    - start_date: 开始时间 'YYYY-MM-DD'，默认 None 表示当前时间
    - end_date: 结束时间 'YYYY-MM-DD'，默认 None 表示当前时间
    """
    res = gm_get_history_symbol(
        symbol=symbol,
        start_date=start_date,
        end_date=end_date,
    )
    return format_dataframe_response(res) if hasattr(res, "to_string") else format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)
_tool_functions["get_history_symbol"] = get_history_symbol


@mcp.tool()
@audit_wrapper
async def get_next_n_trading_dates(exchange: str, date: str, count: int = 1) -> str:
    """查询指定日期的后n个交易日，对应 GM: get_next_n_trading_dates。

    参数:
    - exchange: 交易所代码，如 'SHSE'(上交所), 'SZSE'(深交所)
    - date: 指定日期 'YYYY-MM-DD'
    - count: 查询数量，默认 1
    """
    res = gm_get_next_n_trading_dates(
        exchange=exchange,
        date=date,
        n=count,
    )
    return format_dataframe_response(res) if hasattr(res, "to_string") else format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)
_tool_functions["get_next_n_trading_dates"] = get_next_n_trading_dates


@mcp.tool()
@audit_wrapper
async def get_previous_n_trading_dates(exchange: str, date: str, count: int = 1) -> str:
    """查询指定日期的前n个交易日，对应 GM: get_previous_n_trading_dates。

    参数:
    - exchange: 交易所代码，如 'SHSE'(上交所), 'SZSE'(深交所)
    - date: 指定日期 'YYYY-MM-DD'
    - count: 查询数量，默认 1
    """
    res = gm_get_previous_n_trading_dates(
        exchange=exchange,
        date=date,
        n=count,
    )
    return format_dataframe_response(res) if hasattr(res, "to_string") else format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)
_tool_functions["get_previous_n_trading_dates"] = get_previous_n_trading_dates


@mcp.tool()
@audit_wrapper
async def stk_get_index_constituents(index: str, trade_date: str = None) -> str:
    """查询指数成分股，对应 GM: stk_get_index_constituents。

    参数:
    - index: 指数代码（必填），只能输入一个指数，如 'SHSE.000300'(沪深300), 'SHSE.000905'(中证500)
    - trade_date: 交易日期 'YYYY-MM-DD'，默认 None 表示最新交易日
    """
    res = gm_stk_get_index_constituents(
        index=index,
        trade_date=trade_date,
    )
    return format_dataframe_response(res) if hasattr(res, "to_string") else format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)
_tool_functions["stk_get_index_constituents"] = stk_get_index_constituents
