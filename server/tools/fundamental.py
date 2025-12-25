"""
Fundamental data tools - balance sheet, income, cashflow, valuation, etc.
"""
import json
from server.mcp_server import mcp
from server.config import format_dataframe_response, format_list_response
from log_config import audit_logger

# GM API imports
# GM API imports
from gm.api import (
    stk_get_fundamentals_balance_pt as gm_stk_get_fundamentals_balance_pt,
    stk_get_fundamentals_income_pt as gm_stk_get_fundamentals_income_pt,
    stk_get_fundamentals_cashflow_pt as gm_stk_get_fundamentals_cashflow_pt,
    stk_get_finance_deriv_pt as gm_stk_get_finance_deriv_pt,
    stk_get_daily_mktvalue_pt as gm_stk_get_daily_mktvalue_pt,
    stk_get_daily_valuation_pt as gm_stk_get_daily_valuation_pt,
    stk_get_daily_basic_pt as gm_stk_get_daily_basic_pt,
    stk_get_money_flow as gm_stk_get_money_flow,
    stk_get_adj_factor as gm_stk_get_adj_factor,
    stk_get_finance_forecast as gm_stk_get_finance_forecast,
    stk_get_sector_category as gm_stk_get_sector_category,
    stk_get_sector_constituents as gm_stk_get_sector_constituents,
    stk_get_symbol_sector as gm_stk_get_symbol_sector,
    stk_get_industry_category as gm_stk_get_industry_category,
    stk_get_industry_constituents as gm_stk_get_industry_constituents,
    stk_get_symbol_industry as gm_stk_get_symbol_industry,
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


# Balance sheet
@mcp.tool()
@audit_wrapper
async def stk_get_fundamentals_balance(symbols: str, fields: str, date: str = None) -> str:
    """资产负债表截面数据（point-in-time），对应 GM: stk_get_fundamentals_balance_pt。

    参数:
    - symbols: 股票代码字符串，或用英文逗号分隔的多个代码，如 'SHSE.600000,SZSE.000001'
    - fields: 资产负债表字段名，逗号分隔，例如:
        mny_cptl(货币资金), ttl_ast(资产总计), ttl_liab(负债合计),
        ttl_eqy_pcom(归母权益合计), ttl_eqy(股东权益合计)
    - date: 发布日期 'YYYY-MM-DD'，None 表示最新一期
    """
    res = gm_stk_get_fundamentals_balance_pt(
        symbols=symbols,
        fields=fields,
        date=date,
    )
    return format_dataframe_response(res) if hasattr(res, 'to_string') else format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)
_tool_functions["stk_get_fundamentals_balance"] = stk_get_fundamentals_balance


# Income statement
@mcp.tool()
@audit_wrapper
async def stk_get_fundamentals_income(symbols: str, fields: str, date: str = None) -> str:
    """利润表截面数据（point-in-time），对应 GM: stk_get_fundamentals_income_pt。

    参数:
    - symbols: 股票代码字符串，或逗号分隔多个代码
    - fields: 利润表字段名，逗号分隔，例如:
        ttl_inc_oper(营业总收入), inc_oper(营业收入),
        net_prof(净利润), net_prof_pcom(归母净利润)
    - date: 发布日期 'YYYY-MM-DD'，None 表示最新一期
    """
    res = gm_stk_get_fundamentals_income_pt(
        symbols=symbols,
        fields=fields,
        date=date,
    )
    return format_dataframe_response(res) if hasattr(res, 'to_string') else format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)
_tool_functions["stk_get_fundamentals_income"] = stk_get_fundamentals_income


# Cash flow
@mcp.tool()
@audit_wrapper
async def stk_get_fundamentals_cashflow(symbols: str, fields: str, date: str = None) -> str:
    """现金流量表截面数据（point-in-time），对应 GM: stk_get_fundamentals_cashflow_pt。

    参数:
    - symbols: 股票代码字符串，或逗号分隔多个代码
    - fields: 现金流量表字段名，逗号分隔，例如:
        net_cf_oper(经营活动现金净额),
        net_cf_inv(投资活动现金净额),
        net_cf_fin(筹资活动现金净额),
        net_incr_cash_eq(现金及现金等价物净增加额)
    - date: 发布日期 'YYYY-MM-DD'，None 表示最新一期
    """
    res = gm_stk_get_fundamentals_cashflow_pt(
        symbols=symbols,
        fields=fields,
        date=date,
    )
    return format_dataframe_response(res) if hasattr(res, 'to_string') else format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)
_tool_functions["stk_get_fundamentals_cashflow"] = stk_get_fundamentals_cashflow


# Financial derivatives
@mcp.tool()
@audit_wrapper
async def stk_get_finance_deriv(symbols: str, fields: str, date: str = None) -> str:
    """财务衍生指标截面数据（每股指标），对应 GM: stk_get_finance_deriv_pt。

    参数:
    - symbols: 股票代码字符串，或逗号分隔多个代码
    - fields: 财务衍生字段名，逗号分隔，例如:
        eps_basic(每股收益EPS-基本),
        bps(每股净资产BPS),
        net_cf_oper_ps(每股经营现金流量净额),
        ttl_inc_oper_ps(每股营业总收入)
    - date: 发布日期 'YYYY-MM-DD'，None 表示最新一期
    """
    res = gm_stk_get_finance_deriv_pt(
        symbols=symbols,
        fields=fields,
        date=date,
    )
    return format_dataframe_response(res) if hasattr(res, 'to_string') else format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)
_tool_functions["stk_get_finance_deriv"] = stk_get_finance_deriv


# Market value
@mcp.tool()
@audit_wrapper
async def stk_get_daily_mktvalue(symbols: str, fields: str, trade_date: str = None) -> str:
    """市值类单日截面指标（总市值、流通市值等），对应 GM: stk_get_daily_mktvalue_pt。

    参数:
    - symbols: 股票代码字符串，或逗号分隔多个代码
    - fields: 市值类字段名，逗号分隔，例如:
        tot_mv(总市值), a_mv(A股流通市值), a_mv_ex_ltd(A股流通市值不含限售股),
        ev(企业价值)
    - trade_date: 交易日 'YYYY-MM-DD'，None 表示最新交易日
    """
    res = gm_stk_get_daily_mktvalue_pt(
        symbols=symbols,
        fields=fields,
        trade_date=trade_date,
    )
    return format_dataframe_response(res) if hasattr(res, 'to_string') else format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)
_tool_functions["stk_get_daily_mktvalue"] = stk_get_daily_mktvalue


# Valuation
@mcp.tool()
@audit_wrapper
async def get_valuation(symbol: str) -> str:
    """获取单只股票的基础估值指标（pe_ttm, pe_mrq, pe_lyr）。

    参数:
    - symbol: 股票代码，例如 'SHSE.600820'

    返回的字段:
    - pe_ttm: 市盈率(TTM)
    - pe_mrq: 市盈率(最新报告期MRQ)
    - pe_lyr: 市盈率(最新年报LYR)
    """
    res = gm_stk_get_daily_valuation_pt(
        symbols=symbol,
        fields="pe_ttm,pe_mrq,pe_lyr",
        trade_date=None,
        df=False,
    )
    return format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)
_tool_functions["get_valuation"] = get_valuation


@mcp.tool()
@audit_wrapper
async def stk_get_daily_valuation(symbols: str, fields: str, trade_date: str = None) -> str:
    """估值类单日截面指标（PE、PB 等），对应 GM: stk_get_daily_valuation_pt。

    参数:
    - symbols: 股票代码字符串，或逗号分隔多个代码
    - fields: 估值字段名，逗号分隔，例如:
        pe_ttm(市盈率TTM), pe_lyr(市盈率-最新年报),
        pe_mrq(市盈率-最新报告期), pb_lyr/pb_mrq(市净率相关)
    - trade_date: 交易日 'YYYY-MM-DD'，None 表示最新交易日
    """
    res = gm_stk_get_daily_valuation_pt(
        symbols=symbols,
        fields=fields,
        trade_date=trade_date,
        df=False,
    )
    return format_dataframe_response(res) if hasattr(res, "to_string") else format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)
_tool_functions["stk_get_daily_valuation"] = stk_get_daily_valuation


# Basic indicators
@mcp.tool()
@audit_wrapper
async def stk_get_daily_basic(symbols: str, fields: str, trade_date: str = None) -> str:
    """基础类单日截面指标（收盘价、换手率、股本等），对应 GM: stk_get_daily_basic_pt。

    参数:
    - symbols: 股票代码字符串，或逗号分隔多个代码
    - fields: 基础指标字段名，逗号分隔，例如:
        tclose(收盘价), turnrate(当日换手率),
        ttl_shr(总股本), circ_shr(流通股本)
    - trade_date: 交易日 'YYYY-MM-DD'，None 表示最新交易日
    """
    res = gm_stk_get_daily_basic_pt(
        symbols=symbols,
        fields=fields,
        trade_date=trade_date,
        df=False,
    )
    return format_dataframe_response(res) if hasattr(res, "to_string") else format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)
_tool_functions["stk_get_daily_basic"] = stk_get_daily_basic


# Money flow
@mcp.tool()
@audit_wrapper
async def stk_get_money_flow(symbols: str, date: str = None) -> str:
    """查询股票资金流向，对应 GM: stk_get_money_flow。

    参数:
    - symbols: 股票代码字符串，或逗号分隔多个代码，如 'SHSE.600820,SZSE.000538'
    - date: 查询日期 'YYYY-MM-DD'，None 或 "" 表示最新
    """
    res = gm_stk_get_money_flow(symbols=symbols, trade_date=date or None)
    return format_dataframe_response(res) if hasattr(res, "to_string") else format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)
_tool_functions["stk_get_money_flow"] = stk_get_money_flow


# Adjustment factor
@mcp.tool()
@audit_wrapper
async def stk_get_adj_factor(symbols: str, start_date: str = None, end_date: str = None) -> str:
    """查询股票复权因子，对应 GM: stk_get_adj_factor。

    参数:
    - symbols: 股票代码字符串（只能传入单只股票，例如 'SHSE.600820'）
    - start_date: 开始日期 'YYYY-MM-DD'，None 表示不限制
    - end_date: 结束日期 'YYYY-MM-DD'，None 表示不限制
    """
    res = gm_stk_get_adj_factor(symbol=symbols, start_date=start_date or "", end_date=end_date or "")
    return format_dataframe_response(res) if hasattr(res, "to_string") else format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)
_tool_functions["stk_get_adj_factor"] = stk_get_adj_factor


# Finance forecast
@mcp.tool()
@audit_wrapper
async def stk_get_finance_forecast(symbols: str, date: str = "") -> str:
    """查询股票业绩预告，对应 GM: stk_get_finance_forecast。

    参数:
    - symbols: 股票代码字符串，或逗号分隔多个代码
    - date: 查询日期 'YYYY-MM-DD'，默认 "" 表示最新
    """
    res = gm_stk_get_finance_forecast(symbols=symbols, date=date)
    return format_dataframe_response(res) if hasattr(res, "to_string") else format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)
_tool_functions["stk_get_finance_forecast"] = stk_get_finance_forecast


# Sector/Industry
@mcp.tool()
@audit_wrapper
async def stk_get_sector_category(sector_type: str) -> str:
    """查询板块分类，对应 GM: stk_get_sector_category。

    参数:
    - sector_type: 板块类型:
        '1001' 市场类, '1002' 地域类, '1003' 概念类
    """
    res = gm_stk_get_sector_category(sector_type=sector_type)
    return format_dataframe_response(res) if hasattr(res, "to_string") else format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)
_tool_functions["stk_get_sector_category"] = stk_get_sector_category


@mcp.tool()
@audit_wrapper
async def stk_get_sector_constituents(sector_code: str) -> str:
    """查询板块成分股，对应 GM: stk_get_sector_constituents。

    参数:
    - sector_code: 板块代码，可通过 stk_get_sector_category 获取
    """
    res = gm_stk_get_sector_constituents(sector_code=sector_code)
    return format_dataframe_response(res) if hasattr(res, "to_string") else format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)
_tool_functions["stk_get_sector_constituents"] = stk_get_sector_constituents


@mcp.tool()
@audit_wrapper
async def stk_get_symbol_sector(symbols: str, sector_type: str) -> str:
    """查询股票所属板块，对应 GM: stk_get_symbol_sector。

    参数:
    - symbols: 股票代码字符串，或逗号分隔多个代码
    - sector_type: 板块类型 '1001' 市场类 / '1002' 地域类 / '1003' 概念类
    """
    res = gm_stk_get_symbol_sector(symbols=symbols, sector_type=sector_type)
    return format_dataframe_response(res) if hasattr(res, "to_string") else format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)
_tool_functions["stk_get_symbol_sector"] = stk_get_symbol_sector


@mcp.tool()
@audit_wrapper
async def stk_get_industry_category(source: str = "zjh2012", level: int = 1) -> str:
    """查询行业分类，对应 GM: stk_get_industry_category。

    参数:
    - source: 行业来源，'zjh2012'（证监会 2012，默认）或 'sw2021'(申万 2021)
    - level: 行业分级，1=一级行业(默认)，2=二级，3=三级(部分来源不支持)
    """
    res = gm_stk_get_industry_category(source=source, level=level)
    return format_dataframe_response(res) if hasattr(res, "to_string") else format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)
_tool_functions["stk_get_industry_category"] = stk_get_industry_category


@mcp.tool()
@audit_wrapper
async def stk_get_industry_constituents(industry_code: str, date: str = "") -> str:
    """查询行业成分股，对应 GM: stk_get_industry_constituents。

    参数:
    - industry_code: 行业代码，可通过 stk_get_industry_category 获取
    - date: 查询日期 'YYYY-MM-DD'，默认 "" 表示最新
    """
    res = gm_stk_get_industry_constituents(industry_code=industry_code, date=date)
    return format_dataframe_response(res) if hasattr(res, "to_string") else format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)
_tool_functions["stk_get_industry_constituents"] = stk_get_industry_constituents


@mcp.tool()
@audit_wrapper
async def stk_get_symbol_industry(symbols: str, source: str = "zjh2012", level: int = 1, date: str = "") -> str:
    """查询股票所属行业，对应 GM: stk_get_symbol_industry。

    参数:
    - symbols: 股票代码字符串，或用英文逗号分隔的多个代码，如 'SHSE.600820,SZSE.000002'
    - source: 行业来源，'zjh2012'(证监会 2012，默认) 或 'sw2021'(申万 2021)
    - level: 行业分级，1=一级行业(默认)，2=二级，3=三级
    - date: 查询日期 'YYYY-MM-DD'，默认 "" 表示最新
    """
    res = gm_stk_get_symbol_industry(symbols=symbols, source=source, level=level, date=date)
    return format_dataframe_response(res) if hasattr(res, "to_string") else format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)
_tool_functions["stk_get_symbol_industry"] = stk_get_symbol_industry
