"""
Fundamental data tools - balance sheet, income, cashflow, valuation, etc.
"""
import json
from typing import Optional
from server.mcp_server import mcp
from server.config import format_dataframe_response, format_list_response, audit_wrapper
from server.tools import tool_registry

# GM API imports
from gm.api import (
    stk_get_fundamentals_balance_pt as gm_stk_get_fundamentals_balance_pt,
    stk_get_fundamentals_income_pt as gm_stk_get_fundamentals_income_pt,
    stk_get_fundamentals_cashflow_pt as gm_stk_get_fundamentals_cashflow_pt,
    stk_get_finance_deriv_pt as gm_stk_get_finance_deriv_pt,
    stk_get_finance_prime_pt as gm_stk_get_finance_prime_pt,
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
    stk_get_dividend as gm_stk_get_dividend,
    stk_get_ration as gm_stk_get_ration,
    stk_get_shareholder_num as gm_stk_get_shareholder_num,
    stk_get_top_shareholder as gm_stk_get_top_shareholder,
    stk_get_share_change as gm_stk_get_share_change,
    stk_abnor_change_stocks as gm_stk_abnor_change_stocks,
    stk_abnor_change_detail as gm_stk_abnor_change_detail,
    stk_quota_shszhk_infos as gm_stk_quota_shszhk_infos,
    stk_hk_inst_holding_detail_info as gm_stk_hk_inst_holding_detail_info,
    stk_hk_inst_holding_info as gm_stk_hk_inst_holding_info,
    stk_active_stock_top10_shszhk_info as gm_stk_active_stock_top10_shszhk_info,
    stk_get_finance_audit as gm_stk_get_finance_audit,
    get_open_call_auction as gm_get_open_call_auction,
)


# Balance sheet
@mcp.tool()
@audit_wrapper
@tool_registry("stk_get_fundamentals_balance")
async def stk_get_fundamentals_balance(symbols: str, fields: str, date: Optional[str] = None) -> str:
    """资产负债表截面数据（point-in-time），对应 GM: stk_get_fundamentals_balance_pt。

    参数:
    - symbols: 股票代码，多个用英文逗号分隔，如 'SHSE.600000,SZSE.000001'
    - fields: 可用字段（逗号分隔）:
        资产: mny_cptl(货币资金), ttl_cur_ast(流动资产合计), fix_ast(固定资产), ttl_ncur_ast(非流动资产合计), ttl_ast(资产总计)
        负债: sht_ln(短期借款), ttl_cur_liab(流动负债合计), lt_ln(长期借款), ttl_ncur_liab(非流动负债合计), ttl_liab(负债合计)
        权益: paid_in_cptl(实收资本), cptl_rsv(资本公积), ret_prof(未分配利润), ttl_eqy_pcom(归母权益), ttl_eqy(股东权益合计)
    - date: 发布日期 'YYYY-MM-DD'，None 表示最新一期
    """
    res = gm_stk_get_fundamentals_balance_pt(
        symbols=symbols,
        fields=fields,
        date=date,
    )
    return format_dataframe_response(res) if hasattr(res, 'to_string') else format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)


# Income statement
@mcp.tool()
@audit_wrapper
@tool_registry("stk_get_fundamentals_income")
async def stk_get_fundamentals_income(symbols: str, fields: str, date: Optional[str] = None) -> str:
    """利润表截面数据（point-in-time），对应 GM: stk_get_fundamentals_income_pt。

    参数:
    - symbols: 股票代码，多个用英文逗号分隔，如 'SHSE.600000,SZSE.000001'
    - fields: 可用字段（逗号分隔）:
        收入: ttl_inc_oper(营业总收入), inc_oper(营业收入), inc_inv(投资收益), inc_fv_chg(公允价值变动收益)
        成本: ttl_cost_oper(营业总成本), cost_oper(营业成本), exp_sell(销售费用), exp_adm(管理费用), exp_rd(研发费用), exp_fin(财务费用)
        利润: oper_prof(营业利润), ttl_prof(利润总额), net_prof(净利润), net_prof_pcom(归母净利润)
    - date: 发布日期 'YYYY-MM-DD'，None 表示最新一期
    """
    res = gm_stk_get_fundamentals_income_pt(
        symbols=symbols,
        fields=fields,
        date=date,
    )
    return format_dataframe_response(res) if hasattr(res, 'to_string') else format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)


# Cash flow
@mcp.tool()
@audit_wrapper
@tool_registry("stk_get_fundamentals_cashflow")
async def stk_get_fundamentals_cashflow(symbols: str, fields: str, date: Optional[str] = None) -> str:
    """现金流量表截面数据（point-in-time），对应 GM: stk_get_fundamentals_cashflow_pt。

    参数:
    - symbols: 股票代码，多个用英文逗号分隔，如 'SHSE.600000,SZSE.000001'
    - fields: 可用字段（逗号分隔）:
        经营: net_cf_oper(经营活动现金净额), cf_in_oper(经营现金流入), cf_out_oper(经营现金流出)
        投资: net_cf_inv(投资活动现金净额), cash_pay_inv(投资支付现金), pur_fix_intg_ast(购建固定资产)
        筹资: net_cf_fin(筹资活动现金净额), cash_rcv_cptl(吸收投资现金), cash_rpay_brw(偿还债务现金)
        其他: net_incr_cash_eq(现金净增加额), cash_cash_eq_end(期末现金余额)
    - date: 发布日期 'YYYY-MM-DD'，None 表示最新一期
    """
    res = gm_stk_get_fundamentals_cashflow_pt(
        symbols=symbols,
        fields=fields,
        date=date,
    )
    return format_dataframe_response(res) if hasattr(res, 'to_string') else format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)


# Financial derivatives
@mcp.tool()
@audit_wrapper
@tool_registry("stk_get_finance_deriv")
async def stk_get_finance_deriv(symbols: str, fields: str, date: Optional[str] = None) -> str:
    """财务衍生指标截面数据（每股指标），对应 GM: stk_get_finance_deriv_pt。

    参数:
    - symbols: 股票代码字符串，或逗号分隔多个代码
    - fields: 可用字段（逗号分隔）:
        每股: eps_basic(基本每股收益), eps_dil2(稀释每股收益), eps_dil(期末股本摊薄),
              bps(每股净资产BPS), net_cf_oper_ps(每股经营现金流), ttl_inc_oper_ps(每股营业总收入),
              inc_oper_ps(每股营业收入), ebit_ps(每股息税前利润), cptl_rsv_ps(每股资本公积),
              sur_rsv_ps(每股盈余公积), retain_prof_ps(每股未分配利润), net_cf_ps(每股现金流量净额),
              fcff_ps(每股企业自由现金流量), fcfe_ps(每股股东自由现金流量), ebitda_ps(每股EBITDA)
        收益率: roe(摊薄ROE), roe_weight(加权ROE), roe_avg(平均ROE), roe_cut(扣除/摊薄ROE),
                ocf_toi(经营性现金净流量/营业总收入)
        同比增长: eps_dil_yoy, net_cf_oper_ps_yoy, ttl_inc_oper_yoy, inc_oper_yoy, oper_prof_yoy,
                  ttl_prof_yoy, net_prof_pcom_yoy, net_cf_oper_yoy, roe_yoy, net_asset_yoy,
                  ttl_liab_yoy, ttl_asset_yoy, net_cash_flow_yoy
        其他: ebit, ebitda, ebit_inverse, ebitda_inverse, nr_prof_loss(非经常性损益),
              net_prof_cut(扣非净利润), gross_prof(毛利润), oper_net_inc, val_chg_net_inc,
              exp_rd(研发费用), ttl_inv_cptl, work_cptl
    - date: 发布日期 'YYYY-MM-DD'，None 表示最新一期
    """
    res = gm_stk_get_finance_deriv_pt(
        symbols=symbols,
        fields=fields,
        date=date,
    )
    return format_dataframe_response(res) if hasattr(res, 'to_string') else format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)


# Market value
@mcp.tool()
@audit_wrapper
@tool_registry("stk_get_daily_mktvalue")
async def stk_get_daily_mktvalue(symbols: str, fields: str, trade_date: Optional[str] = None) -> str:
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


# Valuation
@mcp.tool()
@audit_wrapper
@tool_registry("get_valuation")
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


@mcp.tool()
@audit_wrapper
@tool_registry("stk_get_daily_valuation")
async def stk_get_daily_valuation(symbols: str, fields: str, trade_date: Optional[str] = None) -> str:
    """估值类单日截面指标（PE、PB 等），对应 GM: stk_get_daily_valuation_pt。

    参数:
    - symbols: 股票代码字符串，或逗号分隔多个代码
    - fields: 全部可用字段（逗号分隔，仅支持以下字段）:
        市盈率: pe_ttm(TTM), pe_lyr(最新年报), pe_mrq(最新报告期), pe_1q(一季*4), pe_2q(中报*2), pe_3q(三季*4/3)
        扣非市盈率: pe_ttm_cut, pe_lyr_cut, pe_mrq_cut, pe_1q_cut, pe_2q_cut, pe_3q_cut
        市净率: pb_lyr(最新年报), pb_mrq(最新报告期), pb_lyr_1(剔除其他权益), pb_mrq_1
        市现率: pcf_ttm_oper(经营现金流TTM), pcf_ttm_ncf(现金净流量TTM), pcf_lyr_oper, pcf_lyr_ncf
        市销率: ps_ttm, ps_lyr, ps_mrq, ps_1q, ps_2q, ps_3q
        PEG: peg_lyr, peg_mrq, peg_1q, peg_2q, peg_3q, peg_np_cgr, peg_npp_cgr
    - trade_date: 交易日 'YYYY-MM-DD'，None 表示最新交易日
    """
    res = gm_stk_get_daily_valuation_pt(
        symbols=symbols,
        fields=fields,
        trade_date=trade_date,
        df=False,
    )
    return format_dataframe_response(res) if hasattr(res, "to_string") else format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)


# Basic indicators
@mcp.tool()
@audit_wrapper
@tool_registry("stk_get_daily_basic")
async def stk_get_daily_basic(symbols: str, fields: str, trade_date: Optional[str] = None) -> str:
    """基础类单日截面指标（收盘价、换手率、股本等），对应 GM: stk_get_daily_basic_pt。

    参数:
    - symbols: 股票代码，多个用英文逗号分隔，如 'SHSE.600000,SZSE.000001'
    - fields: 全部可用字段（逗号分隔，仅支持以下字段）:
        tclose(收盘价), turnrate(换手率%), ttl_shr(总股本), circ_shr(流通股本),
        ttl_shr_unl(无限售流通股), ttl_shr_ltd(有限售股本), a_shr_unl(A股流通股), h_shr_unl(H股流通股)
    - trade_date: 交易日 'YYYY-MM-DD'，None 表示最新交易日
    """
    res = gm_stk_get_daily_basic_pt(
        symbols=symbols,
        fields=fields,
        trade_date=trade_date,
        df=False,
    )
    return format_dataframe_response(res) if hasattr(res, "to_string") else format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)


# Money flow
@mcp.tool()
@audit_wrapper
@tool_registry("stk_get_money_flow")
async def stk_get_money_flow(symbols: str, date: Optional[str] = None) -> str:
    """查询股票资金流向，对应 GM: stk_get_money_flow。

    参数:
    - symbols: 股票代码字符串，或逗号分隔多个代码，如 'SHSE.600820,SZSE.000538'
    - date: 查询日期 'YYYY-MM-DD'，None 或 "" 表示最新
    """
    res = gm_stk_get_money_flow(symbols=symbols, trade_date=date or None)
    return format_dataframe_response(res) if hasattr(res, "to_string") else format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)


# Adjustment factor
@mcp.tool()
@audit_wrapper
@tool_registry("stk_get_adj_factor")
async def stk_get_adj_factor(symbols: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> str:
    """查询股票复权因子，对应 GM: stk_get_adj_factor。

    参数:
    - symbols: 股票代码字符串（只能传入单只股票，例如 'SHSE.600820'）
    - start_date: 开始日期 'YYYY-MM-DD'，None 表示不限制
    - end_date: 结束日期 'YYYY-MM-DD'，None 表示不限制
    """
    res = gm_stk_get_adj_factor(symbol=symbols, start_date=start_date or "", end_date=end_date or "")
    return format_dataframe_response(res) if hasattr(res, "to_string") else format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)


# Finance forecast
@mcp.tool()
@audit_wrapper
@tool_registry("stk_get_finance_forecast")
async def stk_get_finance_forecast(symbols: str, date: str = "") -> str:
    """查询股票业绩预告，对应 GM: stk_get_finance_forecast。

    参数:
    - symbols: 股票代码字符串，或逗号分隔多个代码
    - date: 查询日期 'YYYY-MM-DD'，默认 "" 表示最新
    """
    res = gm_stk_get_finance_forecast(symbols=symbols, date=date)
    return format_dataframe_response(res) if hasattr(res, "to_string") else format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)


# Sector/Industry
@mcp.tool()
@audit_wrapper
@tool_registry("stk_get_sector_category")
async def stk_get_sector_category(sector_type: str) -> str:
    """查询板块分类，对应 GM: stk_get_sector_category。

    参数:
    - sector_type: 板块类型:
        '1001' 市场类, '1002' 地域类, '1003' 概念类
    """
    res = gm_stk_get_sector_category(sector_type=sector_type)
    return format_dataframe_response(res) if hasattr(res, "to_string") else format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)


@mcp.tool()
@audit_wrapper
@tool_registry("stk_get_sector_constituents")
async def stk_get_sector_constituents(sector_code: str) -> str:
    """查询板块成分股，对应 GM: stk_get_sector_constituents。

    参数:
    - sector_code: 板块代码，可通过 stk_get_sector_category 获取
    """
    res = gm_stk_get_sector_constituents(sector_code=sector_code)
    return format_dataframe_response(res) if hasattr(res, "to_string") else format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)


@mcp.tool()
@audit_wrapper
@tool_registry("stk_get_symbol_sector")
async def stk_get_symbol_sector(symbols: str, sector_type: str) -> str:
    """查询股票所属板块，对应 GM: stk_get_symbol_sector。

    参数:
    - symbols: 股票代码，多个用英文逗号分隔，如 'SHSE.600000,SZSE.000001'
    - sector_type: 可选值: '1001'(市场类), '1002'(地域类), '1003'(概念类)
    """
    res = gm_stk_get_symbol_sector(symbols=symbols, sector_type=sector_type)
    return format_dataframe_response(res) if hasattr(res, "to_string") else format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)


@mcp.tool()
@audit_wrapper
@tool_registry("stk_get_industry_category")
async def stk_get_industry_category(source: str = "zjh2012", level: Optional[int] = 1) -> str:
    """查询行业分类，对应 GM: stk_get_industry_category。

    参数:
    - source: 行业来源，'zjh2012'（证监会 2012，默认）或 'sw2021'(申万 2021)
    - level: 行业分级，1=一级行业(默认)，2=二级，3=三级(部分来源不支持)
    """
    res = gm_stk_get_industry_category(source=source, level=level)
    return format_dataframe_response(res) if hasattr(res, "to_string") else format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)


@mcp.tool()
@audit_wrapper
@tool_registry("stk_get_industry_constituents")
async def stk_get_industry_constituents(industry_code: str, date: str = "") -> str:
    """查询行业成分股，对应 GM: stk_get_industry_constituents。

    参数:
    - industry_code: 行业代码，可通过 stk_get_industry_category 获取
    - date: 查询日期 'YYYY-MM-DD'，默认 "" 表示最新
    """
    res = gm_stk_get_industry_constituents(industry_code=industry_code, date=date)
    return format_dataframe_response(res) if hasattr(res, "to_string") else format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)


@mcp.tool()
@audit_wrapper
@tool_registry("stk_get_symbol_industry")
async def stk_get_symbol_industry(symbols: str, source: str = "zjh2012", level: Optional[int] = 1, date: Optional[str] = None) -> str:
    """查询股票所属行业，对应 GM: stk_get_symbol_industry。

    参数:
    - symbols: 股票代码字符串，或用英文逗号分隔的多个代码，如 'SHSE.600820,SZSE.000002'
    - source: 行业来源，'zjh2012'(证监会 2012，默认) 或 'sw2021'(申万 2021)
    - level: 行业分级，1=一级行业(默认)，2=二级，3=三级
    - date: 查询日期 'YYYY-MM-DD'，默认 "" 表示最新
    """
    res = gm_stk_get_symbol_industry(symbols=symbols, source=source, level=level, date=date)
    return format_dataframe_response(res) if hasattr(res, "to_string") else format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)


# Financial prime indicators (财务主要指标)
@mcp.tool()
@audit_wrapper
@tool_registry("stk_get_finance_prime")
async def stk_get_finance_prime(symbols: str, fields: str, date: Optional[str] = None, rpt_type: Optional[int] = None, data_type: Optional[int] = None) -> str:
    """查询财务主要指标截面数据（多标的），对应 GM: stk_get_finance_prime_pt。

    参数:
    - symbols: 股票代码，多个用英文逗号分隔，如 'SHSE.600000,SZSE.000001'
    - fields: 可用字段（逗号分隔）:
        每股: eps_basic(基本每股收益), eps_dil(稀释每股收益), eps_basic_cut(扣非基本), eps_dil_cut(扣非稀释),
              net_cf_oper_ps(每股经营现金流), bps_pcom_ps(归母每股净资产), bps_sh(普通股东每股净资产)
        利润: oper_prof(营业利润), ttl_prof(利润总额), net_prof_pcom(归母净利润), net_prof(普通股东净利润),
              net_prof_pcom_cut(扣非归母净利润), net_prof_cut(扣非普通股东净利润)
        资产: ttl_ast(总资产), ttl_liab(总负债), ttl_eqy_pcom(归母权益), share_cptl(股本), net_asset(普通股东净资产)
        收入: ttl_inc_oper(营业总收入), inc_oper(营业收入)
        收益率: roe(摊薄ROE), roe_weight_avg(加权ROE), roe_cut(扣非摊薄ROE), roe_weight_avg_cut(扣非加权ROE)
        现金流: net_cf_oper(经营活动现金流量净额)
        同比: eps_yoy, inc_oper_yoy, ttl_inc_oper_yoy, net_prof_pcom_yoy
    - date: 发布日期 'YYYY-MM-DD'，None 表示最新一期
    - rpt_type: 报表类型，1=一季报, 6=中报, 9=前三季报, 12=年报，None=不限
    - data_type: 数据类型，None=默认, 100=合并最初, 101=合并原始, 102=合并调整
    """
    res = gm_stk_get_finance_prime_pt(
        symbols=symbols,
        fields=fields,
        date=date,
        rpt_type=rpt_type,
        data_type=data_type,
    )
    return format_dataframe_response(res) if hasattr(res, "to_string") else format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)


# Dividend (分红送股)
@mcp.tool()
@audit_wrapper
@tool_registry("stk_get_dividend")
async def stk_get_dividend(symbol: str, start_date: str, end_date: str) -> str:
    """查询股票分红送股信息，对应 GM: stk_get_dividend。

    参数:
    - symbol: 股票代码（只能填一个股票标的）
    - start_date: 开始时间（除权除息日），格式 'YYYY-MM-DD'
    - end_date: 结束时间（除权除息日），格式 'YYYY-MM-DD'
    """
    res = gm_stk_get_dividend(symbol=symbol, start_date=start_date, end_date=end_date)
    return format_dataframe_response(res) if hasattr(res, "to_string") else format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)


# Ration (配股)
@mcp.tool()
@audit_wrapper
@tool_registry("stk_get_ration")
async def stk_get_ration(symbol: str, start_date: str, end_date: str) -> str:
    """查询股票配股信息，对应 GM: stk_get_ration。

    参数:
    - symbol: 股票代码（只能填一个股票标的）
    - start_date: 开始时间（除权除息日），格式 'YYYY-MM-DD'
    - end_date: 结束时间（除权除息日），格式 'YYYY-MM-DD'
    """
    res = gm_stk_get_ration(symbol=symbol, start_date=start_date, end_date=end_date)
    return format_dataframe_response(res) if hasattr(res, "to_string") else format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)


# Shareholder number (股东户数)
@mcp.tool()
@audit_wrapper
@tool_registry("stk_get_shareholder_num")
async def stk_get_shareholder_num(symbol: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> str:
    """查询股东户数，对应 GM: stk_get_shareholder_num。

    参数:
    - symbol: 股票代码（只能填一个股票标的）
    - start_date: 开始时间（公告日期），格式 'YYYY-MM-DD'，默认 "" 表示最新时间
    - end_date: 结束时间（公告日期），格式 'YYYY-MM-DD'，默认 "" 表示最新时间
    """
    res = gm_stk_get_shareholder_num(symbol=symbol, start_date=start_date or "", end_date=end_date or "")
    return format_dataframe_response(res) if hasattr(res, "to_string") else format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)


# Top shareholder (十大股东)
@mcp.tool()
@audit_wrapper
@tool_registry("stk_get_top_shareholder")
async def stk_get_top_shareholder(symbol: str, start_date: Optional[str] = None, end_date: Optional[str] = None, tradable_holder: bool = False) -> str:
    """查询十大股东，对应 GM: stk_get_top_shareholder。

    参数:
    - symbol: 股票代码（只能填一个股票标的）
    - start_date: 开始时间（公告日期），格式 'YYYY-MM-DD'，默认 "" 表示最新时间
    - end_date: 结束时间（公告日期），格式 'YYYY-MM-DD'，默认 "" 表示最新时间
    - tradable_holder: 是否流通股东，False=十大股东（默认），True=十大流通股东
    """
    res = gm_stk_get_top_shareholder(symbol=symbol, start_date=start_date or "", end_date=end_date or "", tradable_holder=tradable_holder)
    return format_dataframe_response(res) if hasattr(res, "to_string") else format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)


# Share change (股本变动)
@mcp.tool()
@audit_wrapper
@tool_registry("stk_get_share_change")
async def stk_get_share_change(symbol: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> str:
    """查询股本变动，对应 GM: stk_get_share_change。

    参数:
    - symbol: 股票代码（只能填一个股票标的）
    - start_date: 开始时间（发布日期），格式 'YYYY-MM-DD'，默认 "" 表示最新时间
    - end_date: 结束时间（发布日期），格式 'YYYY-MM-DD'，默认 "" 表示最新时间
    """
    res = gm_stk_get_share_change(symbol=symbol, start_date=start_date or "", end_date=end_date or "")
    return format_dataframe_response(res) if hasattr(res, "to_string") else format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)


# Abnormal change stocks (龙虎榜股票数据)
@mcp.tool()
@audit_wrapper
@tool_registry("stk_abnor_change_stocks")
async def stk_abnor_change_stocks(symbols: Optional[str] = None, change_types: Optional[str] = None, trade_date: Optional[str] = None, fields: Optional[str] = None, df: bool = False) -> str:
    """查询龙虎榜股票数据，对应 GM: stk_abnor_change_stocks。

    参数:
    - symbols: 股票代码（可输入多个，用英文逗号分隔），默认 None 表示所有标的
    - change_types: 异动类型（可输入多个，用英文逗号分隔），默认 None 表示所有类型
    - trade_date: 交易日期，格式 'YYYY-MM-DD'，默认 None 表示最新交易日期
    - fields: 返回字段，默认 None 返回所有字段
    - df: 是否返回 dataframe 格式，默认 False 返回 list[dict]
    """
    res = gm_stk_abnor_change_stocks(symbols=symbols, change_types=change_types, trade_date=trade_date, fields=fields, df=df)
    return format_dataframe_response(res) if hasattr(res, "to_string") else format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)


# Abnormal change detail (龙虎榜营业部数据)
@mcp.tool()
@audit_wrapper
@tool_registry("stk_abnor_change_detail")
async def stk_abnor_change_detail(symbols: Optional[str] = None, change_types: Optional[str] = None, trade_date: Optional[str] = None, fields: Optional[str] = None, df: bool = False) -> str:
    """查询龙虎榜营业部数据，对应 GM: stk_abnor_change_detail。

    参数:
    - symbols: 股票代码（可输入多个，用英文逗号分隔），默认 None 表示所有标的
    - change_types: 异动类型（可输入多个，用英文逗号分隔），默认 None 表示所有类型
    - trade_date: 交易日期，格式 'YYYY-MM-DD'，默认 None 表示最新交易日期
    - fields: 返回字段，默认 None 返回所有字段
    - df: 是否返回 dataframe 格式，默认 False 返回 list[dict]
    """
    res = gm_stk_abnor_change_detail(symbols=symbols, change_types=change_types, trade_date=trade_date, fields=fields, df=df)
    return format_dataframe_response(res) if hasattr(res, "to_string") else format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)


# Shanghai-Shenzhen-Hong Kong Stock Connect quota (沪深港通额度数据)
@mcp.tool()
@audit_wrapper
@tool_registry("stk_quota_shszhk_infos")
async def stk_quota_shszhk_infos(types: Optional[str] = None, start_date: Optional[str] = None, end_date: Optional[str] = None, count: Optional[int] = None, df: bool = False) -> str:
    """查询沪深港通额度数据，对应 GM: stk_quota_shszhk_infos。

    参数:
    - types: 类型（可输入多个，用英文逗号分隔），如 'SH,SHHK,SZ,SZHK'
    - start_date: 开始日期，格式 'YYYY-MM-DD'
    - end_date: 结束日期，格式 'YYYY-MM-DD'
    - count: 查询数量
    - df: 是否返回 dataframe 格式，默认 False 返回 list[dict]
    """
    res = gm_stk_quota_shszhk_infos(types=types, start_date=start_date, end_date=end_date, count=count, df=df)
    return format_dataframe_response(res) if hasattr(res, "to_string") else format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)


# Hong Kong institutional holding detail (沪深港通标的港股机构持股明细数据)
@mcp.tool()
@audit_wrapper
@tool_registry("stk_hk_inst_holding_detail_info")
async def stk_hk_inst_holding_detail_info(symbols: Optional[str] = None, trade_date: Optional[str] = None) -> str:
    """查询沪深港通标的港股机构持股明细数据，对应 GM: stk_hk_inst_holding_detail_info。

    参数:
    - symbols: 股票代码（如 'SHSE.600008'），None=所有标的
    - trade_date: 交易日期（%Y-%m-%d 格式，None=最新）

    示例:
    - stk_hk_inst_holding_detail_info()  # 所有标的最新数据
    - stk_hk_inst_holding_detail_info(symbols="SHSE.600008")  # 指定股票
    - stk_hk_inst_holding_detail_info(symbols="SHSE.600008", trade_date="2024-12-01")

    返回: 机构持股明细（symbol, sec_name, trade_date, participant_name, share_holding, shares_rate）
    """
    res = gm_stk_hk_inst_holding_detail_info(symbols=symbols, trade_date=trade_date, df=True)
    return format_dataframe_response(res) if hasattr(res, "to_string") else format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)


# Hong Kong institutional holding (沪深港通标的港股机构持股数据)
@mcp.tool()
@audit_wrapper
@tool_registry("stk_hk_inst_holding_info")
async def stk_hk_inst_holding_info(symbols: Optional[str] = None, trade_date: Optional[str] = None, limit: Optional[int] = None) -> str:
    """查询沪深港通标的港股机构持股数据，对应 GM: stk_hk_inst_holding_info。

    参数:
    - symbols: 股票代码（如 'SHSE.600008,SZSE.000002'），None=所有标的
    - trade_date: 交易日期（%Y-%m-%d 格式，None=最新）
    - limit: 返回结果数量限制（可选）
        - 默认None: 有symbols过滤时返回全部，否则限制50条
        - 设定数值: 强制限制返回条数
    """
    res = gm_stk_hk_inst_holding_info(symbols=symbols, trade_date=trade_date, df=True)

    # Intelligent limiting
    has_filters = symbols is not None or trade_date is not None

    if limit is not None:
        if res is not None and len(res) > 0:
            if hasattr(res, 'head'):  # DataFrame
                res = res.head(limit)
            elif isinstance(res, list):  # List
                res = res[:limit]
    elif not has_filters:
        # No filters and no explicit limit - apply default 50
        if res is not None and len(res) > 50:
            if hasattr(res, 'head'):  # DataFrame
                res = res.head(50)
            elif isinstance(res, list):  # List
                res = res[:50]

    return format_dataframe_response(res) if hasattr(res, "to_string") else format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)


# Shanghai-Shenzhen-Hong Kong active stocks (沪深港通十大活跃成交股数据)
@mcp.tool()
@audit_wrapper
@tool_registry("stk_active_stock_top10_shszhk_info")
async def stk_active_stock_top10_shszhk_info(types: Optional[str] = None, trade_date: Optional[str] = None) -> str:
    """查询沪深港通十大活跃成交股数据，对应 GM: stk_active_stock_top10_shszhk_info。

    参数:
    - types: 类型（SH=沪股通, SHHK=沪港股通, SZ=深股通, SZHK=深港股通, NF=北向资金）
        可传入多个用逗号分隔（如 'SZ,SHHK'），None=全部
    - trade_date: 交易日期（%Y-%m-%d 格式，None=最新）

    示例:
    - stk_active_stock_top10_shszhk_info()  # 全部类型最新数据
    - stk_active_stock_top10_shszhk_info(types="SZ")  # 深股通最新数据
    - stk_active_stock_top10_shszhk_info(types="NF", trade_date="2024-12-01")

    返回: 活跃成交股数据（symbol, sec_name, trade_type, rank, buy_amount, sell_amount, total_amount 等）
    """
    res = gm_stk_active_stock_top10_shszhk_info(types=types, trade_date=trade_date, df=True)
    return format_dataframe_response(res) if hasattr(res, "to_string") else format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)


# Finance audit (财务审计意见)
@mcp.tool()
@audit_wrapper
@tool_registry("stk_get_finance_audit")
async def stk_get_finance_audit(symbols: str, date: Optional[str] = None, rpt_date: Optional[str] = None) -> str:
    """查询财务审计意见，对应 GM: stk_get_finance_audit。

    参数:
    - symbols: 股票代码 (如 'SHSE.600000' 或 'SHSE.600000,SZSE.000001')
    - date: 查询日期（最新公告日期，%Y-%m-%d 格式，None=最新）
    - rpt_date: 报告日期（%Y-%m-%d 格式，如 '2023-12-31' 表示年报）

    示例:
    - stk_get_finance_audit(symbols="SHSE.600000")
    - stk_get_finance_audit(symbols="SHSE.600000", rpt_date="2023-12-31")

    返回: 审计意见（acct_agency, cpa, audit_opinion, audit_opinion_text, audit_no 等）
    """
    res = gm_stk_get_finance_audit(symbols=symbols, date=date, rpt_date=rpt_date, df=True)
    return format_dataframe_response(res) if hasattr(res, "to_string") else format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)


# Open call auction (集合竞价开盘成交)
@mcp.tool()
@audit_wrapper
@tool_registry("get_open_call_auction")
async def get_open_call_auction(symbols: str, trade_date: Optional[str] = None) -> str:
    """查询集合竞价开盘成交，对应 GM: get_open_call_auction。

    参数:
    - symbols: 股票代码，可输入多个，用英文逗号分隔，如 'SHSE.600000,SZSE.000001'
    - trade_date: 交易日期，格式 'YYYY-MM-DD'，默认 None 表示最新交易日
    """
    res = gm_get_open_call_auction(symbols=symbols, trade_date=trade_date)
    return format_dataframe_response(res) if hasattr(res, "to_string") else format_list_response(res) if isinstance(res, list) else json.dumps(res, indent=2, default=str)
