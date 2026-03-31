"""
Market data tools - history, current, symbols, etc.
"""
import json
from typing import Optional
from server.mcp_server import mcp
from server.config import format_dataframe_response, format_list_response, audit_wrapper
from server.tools import tool_registry

# GM API imports
from gm.api import (
    history as gm_history,
    history_n as gm_history_n,
    current as gm_current,
    current_price as gm_current_price,
    last_tick as gm_last_tick,
    get_symbols as gm_get_symbols,
    get_symbol_infos as gm_get_symbol_infos,
    get_trading_dates_by_year as gm_get_trading_dates_by_year,
    get_history_symbol as gm_get_history_symbol,
    get_next_n_trading_dates as gm_get_next_n_trading_dates,
    get_previous_n_trading_dates as gm_get_previous_n_trading_dates,
    stk_get_index_constituents as gm_stk_get_index_constituents,
)

# Market data tools
@tool_registry("history")
@mcp.tool()
@audit_wrapper
async def history(symbol: str, frequency: str, start_time: str, end_time: str) -> str:
    """查询历史行情数据，对应 GM: history。

    参数:
    - symbol: 标的代码，多个用逗号分隔，如 'SHSE.600000,SZSE.000001'
    - frequency: 可选值: 'tick'(逐笔), '60s'(1分钟), '300s'(5分钟), '900s'(15分钟), '1800s'(30分钟), '3600s'(60分钟), '1d'(日线)
    - start_time: 开始时间 'YYYY-MM-DD' 或 'YYYY-MM-DD HH:MM:SS'
    - end_time: 结束时间 'YYYY-MM-DD' 或 'YYYY-MM-DD HH:MM:SS'

    返回: DataFrame (eob, open, high, low, close, volume, amount 等)
    """
    res = gm_history(
        symbol=symbol,
        frequency=frequency,
        start_time=start_time,
        end_time=end_time,
        df=True,
    )
    return format_dataframe_response(res)


@tool_registry("history_n")
@mcp.tool()
@audit_wrapper
async def history_n(symbol: str, frequency: str, count: int) -> str:
    """查询最新N条历史行情数据，对应 GM: history_n。

    参数:
    - symbol: 标的代码（仅支持单个，如 "SHSE.600000"）
    - frequency: 频率 ('tick', '60s', '300s', '1d', '1w', '1m')
    - count: 返回条数（正整数）

    示例:
    - history_n(symbol="SHSE.600000", frequency="1d", count=100)
    - history_n(symbol="SZSE.000001", frequency="60s", count=50)

    返回: DataFrame (eob, open, high, low, close, volume, amount 等)，按时间升序
    """
    res = gm_history_n(symbol=symbol, frequency=frequency, count=count, df=True)
    return format_dataframe_response(res)


@tool_registry("current")
@mcp.tool()
@audit_wrapper
async def current(symbols: str) -> str:
    """查询最新行情数据，对应 GM: current。

    参数:
    - symbols: 标的代码，多个用逗号分隔 (如 "SHSE.600000,SZSE.000001")

    示例:
    - current(symbols="SHSE.600000,SZSE.000001")

    返回: DataFrame (symbol, eob, open, high, low, close, volume, amount 等)
    """
    res = gm_current(symbols=symbols)
    return format_list_response(res) if isinstance(res, list) else format_dataframe_response(res)


@tool_registry("current_price")
@mcp.tool()
@audit_wrapper
async def current_price(symbols: str) -> str:
    """查询最新价，对应 GM: current_price。

    参数:
    - symbols: 标的代码，多个用逗号分隔 (如 "SHSE.600000,SZSE.000001")

    示例:
    - current_price(symbols="SHSE.600000")
    - current_price(symbols="SHSE.600000,SZSE.000001")

    返回: list[dict] 包含 symbol, price, created_at
    """
    res = gm_current_price(symbols=symbols)
    return json.dumps(res, ensure_ascii=False, default=str)


@tool_registry("last_tick")
@mcp.tool()
@audit_wrapper
async def last_tick(symbols: str, fields: str = "", include_call_auction: bool = False) -> str:
    """查询已订阅的最新tick数据，对应 GM: last_tick。

    参数:
    - symbols: 标的代码，多个用逗号分隔 (如 "SHSE.600000,SZSE.000001")
    - fields: 查询字段，默认所有字段
    - include_call_auction: 是否支持集合竞价取数，默认False

    示例:
    - last_tick(symbols="SHSE.600000")
    - last_tick(symbols="SHSE.600000,SZSE.000001", fields="symbol,price,created_at")

    返回: list[dict] 最新tick数据
    """
    res = gm_last_tick(symbols=symbols, fields=fields, include_call_auction=include_call_auction)
    return json.dumps(res, ensure_ascii=False, default=str)


@tool_registry("get_symbols")
@mcp.tool()
@audit_wrapper
async def get_symbols(sec_type1: int, sec_type2: Optional[int] = None, exchanges: Optional[str] = None, symbols: Optional[str] = None, skip_suspended: bool = True, skip_st: bool = True, trade_date: Optional[str] = None) -> str:
    """查询指定交易日多标的交易信息，对应 GM: get_symbols。

    参数:
    - sec_type1: 证券品种大类 (必填，1010=股票, 1020=基金, 1030=债券, 1040=期货, 1050=期权, 1060=指数, 1070=板块)
    - sec_type2: 证券品种细类 (如 101001=A股, 102001=ETF)
    - exchanges: 交易所代码，多个用逗号分隔 (SHSE, SZSE, CFFEX, SHFE, DCE, CZCE, INE, GFEX)
    - symbols: 标的代码，多个用逗号分隔
    - skip_suspended: 是否跳过停牌，默认True
    - skip_st: 是否跳过ST，默认True
    - trade_date: 交易日期 'YYYY-MM-DD'，默认最新

    示例:
    - get_symbols(sec_type1=1010, exchanges="SHSE")
    - get_symbols(sec_type1=1010, sec_type2=101001, skip_st=False)

    返回: DataFrame (symbol, sec_name, exchange, pre_close, upper_limit, lower_limit, etc.)
    """
    res = gm_get_symbols(
        sec_type1=sec_type1,
        sec_type2=sec_type2,
        exchanges=exchanges,
        symbols=symbols,
        skip_suspended=skip_suspended,
        skip_st=skip_st,
        trade_date=trade_date,
        df=True
    )
    return format_dataframe_response(res)


@tool_registry("get_symbol_infos")
@mcp.tool()
@audit_wrapper
async def get_symbol_infos(sec_type1: int, sec_type2: Optional[int] = None, exchanges: Optional[str] = None, symbols: Optional[str] = None) -> str:
    """查询标的基本信息(与时间无关)，对应 GM: get_symbol_infos。

    参数:
    - sec_type1: 证券品种大类 (必填，1010=股票, 1020=基金, 1030=债券, 1040=期货, 1050=期权, 1060=指数, 1070=板块)
    - sec_type2: 证券品种细类 (如 101001=A股, 102001=ETF)
    - exchanges: 交易所代码，多个用逗号分隔 (SHSE, SZSE, CFFEX, SHFE, DCE, CZCE, INE, GFEX)
    - symbols: 标的代码，多个用逗号分隔 (如 "SHSE.600000,SZSE.000001")

    示例:
    - get_symbol_infos(sec_type1=1010, symbols="SHSE.600000,SZSE.000002")
    - get_symbol_infos(sec_type1=1010, sec_type2=101001, exchanges="SHSE")

    返回: DataFrame (symbol, sec_name, exchange, listed_date, delisted_date, etc.)
    """
    res = gm_get_symbol_infos(sec_type1=sec_type1, sec_type2=sec_type2, exchanges=exchanges, symbols=symbols, df=True)
    return format_dataframe_response(res)


@tool_registry("get_trading_dates_by_year")
@mcp.tool()
@audit_wrapper
async def get_trading_dates_by_year(exchange: str, start_year: int, end_year: int) -> str:
    """查询年度交易日历，对应 GM: get_trading_dates_by_year。

    参数:
    - exchange: 交易所代码 (SHSE, SZSE, CFFEX, SHFE, DCE, CZCE, INE, GFEX)
    - start_year: 开始年份 (如 2024)
    - end_year: 结束年份 (如 2024)

    示例:
    - get_trading_dates_by_year(exchange="SHSE", start_year=2024, end_year=2024)
    - get_trading_dates_by_year(exchange="SZSE", start_year=2020, end_year=2023)

    返回: DataFrame (date, trade_date, next_trade_date, pre_trade_date)
    """
    res = gm_get_trading_dates_by_year(exchange=exchange, start_year=start_year, end_year=end_year)
    return format_dataframe_response(res)


@tool_registry("get_history_symbol")
@mcp.tool()
@audit_wrapper
async def get_history_symbol(symbol: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> str:
    """查询指定标的多日交易信息，对应 GM: get_history_symbol。

    参数:
    - symbol: 标的代码 (必填，只能输入一个，如 "SZSE.000002")
    - start_date: 开始日期 'YYYY-MM-DD'，默认当前时间
    - end_date: 结束日期 'YYYY-MM-DD'，默认当前时间

    示例:
    - get_history_symbol(symbol="SZSE.000002", start_date="2024-01-01", end_date="2024-12-31")

    返回: DataFrame (trade_date, symbol, pre_close, upper_limit, lower_limit, etc.)
    """
    res = gm_get_history_symbol(symbol=symbol, start_date=start_date, end_date=end_date, df=True)
    return format_dataframe_response(res)


@tool_registry("get_next_n_trading_dates")
@mcp.tool()
@audit_wrapper
async def get_next_n_trading_dates(exchange: str, date: str, n: int = 1) -> str:
    """查询指定日期的后n个交易日，对应 GM: get_next_n_trading_dates。

    参数:
    - exchange: 交易所代码 (SHSE, SZSE, CFFEX, SHFE, DCE, CZCE, INE, GFEX)
    - date: 基准日期 'YYYY-MM-DD'
    - n: 获取数量，默认1

    示例:
    - get_next_n_trading_dates(exchange="SHSE", date="2024-01-01", n=5)

    返回: list of dates (不包含基准日期)
    """
    res = gm_get_next_n_trading_dates(exchange=exchange, date=date, n=n)
    return format_list_response(res)


@tool_registry("get_previous_n_trading_dates")
@mcp.tool()
@audit_wrapper
async def get_previous_n_trading_dates(exchange: str, date: str, n: int = 1) -> str:
    """查询指定日期的前n个交易日，对应 GM: get_previous_n_trading_dates。

    参数:
    - exchange: 交易所代码 (SHSE, SZSE, CFFEX, SHFE, DCE, CZCE, INE, GFEX)
    - date: 基准日期 'YYYY-MM-DD'
    - n: 获取数量，默认1

    示例:
    - get_previous_n_trading_dates(exchange="SHSE", date="2024-01-10", n=5)

    返回: list of dates (不包含基准日期)
    """
    res = gm_get_previous_n_trading_dates(exchange=exchange, date=date, n=n)
    return format_list_response(res)


@tool_registry("stk_get_index_constituents")
@mcp.tool()
@audit_wrapper
async def stk_get_index_constituents(index: str, trade_date: Optional[str] = None) -> str:
    """查询指数成分股，对应 GM: stk_get_index_constituents。

    参数:
    - index: 指数代码 (如 "SHSE.000300" 沪深300)
    - trade_date: 交易日期 'YYYY-MM-DD'，默认最新交易日

    示例:
    - stk_get_index_constituents(index="SHSE.000300")
    - stk_get_index_constituents(index="SHSE.000300", trade_date="2024-01-01")

    返回: DataFrame (index, symbol, weight, trade_date, market_value_total, market_value_circ)
    """
    res = gm_stk_get_index_constituents(index=index, trade_date=trade_date)
    return format_dataframe_response(res)
