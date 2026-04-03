#!/usr/bin/env python3
"""
MyQuant HTTP API Client

A self-contained client for connecting to the MyQuant HTTP API.
It can call every tool exposed by the server. Protected account and trading
operations use the same auth_token gate as MCP and should be passed explicitly
on the command line.

Usage:
    python skills/myquant-mcp/scripts/client.py --help
    python skills/myquant-mcp/scripts/client.py --list-tools
    python skills/myquant-mcp/scripts/client.py history --symbol SHSE.600000 --frequency 1d --start-time 2024-01-01 --end-time 2024-12-31
    python skills/myquant-mcp/scripts/client.py stk_get_fundamentals_balance --symbols SHSE.600000 --fields ttl_ast,ttl_liab --download-dir ./data

Requirements:
    - requests (pip install requests)
"""
import argparse
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional

# Try to import requests, provide helpful error if not available
try:
    import requests
except ImportError:
    print("Error: 'requests' library is required. Install with: pip install requests")
    sys.exit(1)


# =============================================================================
# Configuration
# =============================================================================

# Default local server URL. Override with --url when targeting another deployment.
DEFAULT_BASE_URL = "http://localhost:8001"
API_VERSION = "v1"
TOOLS_ENDPOINT = f"/api/{API_VERSION}/tools"
TOOL_CALL_ENDPOINT = f"/api/{API_VERSION}/tools/{{tool_name}}"

# Request timeout in seconds
DEFAULT_TIMEOUT = 60


# =============================================================================
# Tool Definitions (matching MCP server tools)
# =============================================================================

DATA_TOOLS = {
    # -------------------------------------------------------------------------
    # Market Data Tools (市场数据)
    # -------------------------------------------------------------------------
    "history": {
        "description": "查询历史行情数据，对应 GM: history。",
        "params": {
            "symbol": "标的代码，多个用逗号分隔，如 'SHSE.600000,SZSE.000001'",
            "frequency": "可选值: 'tick'(逐笔), '60s'(1分钟), '300s'(5分钟), '900s'(15分钟), '1800s'(30分钟), '3600s'(60分钟), '1d'(日线)",
            "start_time": "开始时间 'YYYY-MM-DD' 或 'YYYY-MM-DD HH:MM:SS'",
            "end_time": "结束时间 'YYYY-MM-DD' 或 'YYYY-MM-DD HH:MM:SS'",
        },
        "required": ["symbol", "frequency", "start_time", "end_time"],
        "returns": "DataFrame (eob, open, high, low, close, volume, amount 等)",
    },
    "history_n": {
        "description": "查询最新N条历史行情数据，对应 GM: history_n。",
        "params": {
            "symbol": "标的代码（仅支持单个，如 'SHSE.600000'）",
            "frequency": "频率 ('tick', '60s', '300s', '1d', '1w', '1m')",
            "count": "返回条数（正整数）",
        },
        "required": ["symbol", "frequency", "count"],
        "returns": "DataFrame (eob, open, high, low, close, volume, amount 等)，按时间升序",
    },
    "current": {
        "description": "查询最新行情数据，对应 GM: current。",
        "params": {
            "symbols": "标的代码，多个用逗号分隔 (如 'SHSE.600000,SZSE.000001')",
        },
        "required": ["symbols"],
        "returns": "DataFrame (symbol, eob, open, high, low, close, volume, amount 等)",
    },
    "current_price": {
        "description": "查询最新价，对应 GM: current_price。",
        "params": {
            "symbols": "标的代码，多个用逗号分隔 (如 'SHSE.600000,SZSE.000001')",
        },
        "required": ["symbols"],
        "returns": "list[dict] 包含 symbol, price, created_at",
    },
    "last_tick": {
        "description": "查询已订阅的最新tick数据，对应 GM: last_tick。",
        "params": {
            "symbols": "标的代码，多个用逗号分隔 (如 'SHSE.600000,SZSE.000001')",
            "fields": "查询字段，默认所有字段",
            "include_call_auction": "是否支持集合竞价取数，默认False",
        },
        "required": ["symbols"],
        "returns": "list[dict] 最新tick数据",
    },
    "get_symbols": {
        "description": "查询指定交易日多标的交易信息，对应 GM: get_symbols。",
        "params": {
            "sec_type1": "证券品种大类 (必填，1010=股票, 1020=基金, 1030=债券, 1040=期货, 1050=期权, 1060=指数, 1070=板块)",
            "sec_type2": "证券品种细类 (如 101001=A股, 102001=ETF)",
            "exchanges": "交易所代码，多个用逗号分隔 (SHSE, SZSE, CFFEX, SHFE, DCE, CZCE, INE, GFEX)",
            "symbols": "标的代码，多个用逗号分隔",
            "skip_suspended": "是否跳过停牌，默认True",
            "skip_st": "是否跳过ST，默认True",
            "trade_date": "交易日期 'YYYY-MM-DD'，默认最新",
        },
        "required": ["sec_type1"],
        "returns": "DataFrame (symbol, sec_name, exchange, pre_close, upper_limit, lower_limit, etc.)",
    },
    "get_symbol_infos": {
        "description": "查询标的基本信息(与时间无关)，对应 GM: get_symbol_infos。",
        "params": {
            "sec_type1": "证券品种大类 (必填，1010=股票, 1020=基金, 1030=债券, 1040=期货, 1050=期权, 1060=指数, 1070=板块)",
            "sec_type2": "证券品种细类 (如 101001=A股, 102001=ETF)",
            "exchanges": "交易所代码，多个用逗号分隔 (SHSE, SZSE, CFFEX, SHFE, DCE, CZCE, INE, GFEX)",
            "symbols": "标的代码，多个用逗号分隔 (如 'SHSE.600000,SZSE.000001')",
        },
        "required": ["sec_type1"],
        "returns": "DataFrame (symbol, sec_name, exchange, listed_date, delisted_date, etc.)",
    },
    "get_trading_dates_by_year": {
        "description": "查询年度交易日历，对应 GM: get_trading_dates_by_year。",
        "params": {
            "exchange": "交易所代码 (SHSE, SZSE, CFFEX, SHFE, DCE, CZCE, INE, GFEX)",
            "start_year": "开始年份 (如 2024)",
            "end_year": "结束年份 (如 2024)",
        },
        "required": ["exchange", "start_year", "end_year"],
        "returns": "DataFrame (date, trade_date, next_trade_date, pre_trade_date)",
    },
    "get_history_symbol": {
        "description": "查询指定标的多日交易信息，对应 GM: get_history_symbol。",
        "params": {
            "symbol": "标的代码 (必填，只能输入一个，如 'SZSE.000002')",
            "start_date": "开始日期 'YYYY-MM-DD'，默认当前时间",
            "end_date": "结束日期 'YYYY-MM-DD'，默认当前时间",
        },
        "required": ["symbol"],
        "returns": "DataFrame (trade_date, symbol, pre_close, upper_limit, lower_limit, etc.)",
    },
    "get_next_n_trading_dates": {
        "description": "查询指定日期的后n个交易日，对应 GM: get_next_n_trading_dates。",
        "params": {
            "exchange": "交易所代码 (SHSE, SZSE, CFFEX, SHFE, DCE, CZCE, INE, GFEX)",
            "date": "基准日期 'YYYY-MM-DD'",
            "n": "获取数量，默认1",
        },
        "required": ["exchange", "date"],
        "returns": "list of dates (不包含基准日期)",
    },
    "get_previous_n_trading_dates": {
        "description": "查询指定日期的前n个交易日，对应 GM: get_previous_n_trading_dates。",
        "params": {
            "exchange": "交易所代码 (SHSE, SZSE, CFFEX, SHFE, DCE, CZCE, INE, GFEX)",
            "date": "基准日期 'YYYY-MM-DD'",
            "n": "获取数量，默认1",
        },
        "required": ["exchange", "date"],
        "returns": "list of dates (不包含基准日期)",
    },
    "stk_get_index_constituents": {
        "description": "查询指数成分股，对应 GM: stk_get_index_constituents。",
        "params": {
            "index": "指数代码 (如 'SHSE.000300' 沪深300)",
            "trade_date": "交易日期 'YYYY-MM-DD'，默认最新交易日",
        },
        "required": ["index"],
        "returns": "DataFrame (index, symbol, weight, trade_date, market_value_total, market_value_circ)",
    },

    # -------------------------------------------------------------------------
    # Fundamental Data Tools (基本面数据)
    # -------------------------------------------------------------------------
    "stk_get_fundamentals_balance": {
        "description": "资产负债表截面数据（point-in-time），对应 GM: stk_get_fundamentals_balance_pt。",
        "params": {
            "symbols": "股票代码，多个用英文逗号分隔，如 'SHSE.600000,SZSE.000001'",
            "fields": "可用字段（逗号分隔）: 资产: mny_cptl(货币资金), ttl_cur_ast(流动资产合计), fix_ast(固定资产), ttl_ncur_ast(非流动资产合计), ttl_ast(资产总计); 负债: sht_ln(短期借款), ttl_cur_liab(流动负债合计), lt_ln(长期借款), ttl_ncur_liab(非流动负债合计), ttl_liab(负债合计); 权益: paid_in_cptl(实收资本), cptl_rsv(资本公积), ret_prof(未分配利润), ttl_eqy_pcom(归母权益), ttl_eqy(股东权益合计)",
            "date": "发布日期 'YYYY-MM-DD'，None 表示最新一期",
        },
        "required": ["symbols", "fields"],
        "returns": "DataFrame 资产负债表数据",
    },
    "stk_get_fundamentals_income": {
        "description": "利润表截面数据（point-in-time），对应 GM: stk_get_fundamentals_income_pt。",
        "params": {
            "symbols": "股票代码，多个用英文逗号分隔，如 'SHSE.600000,SZSE.000001'",
            "fields": "可用字段（逗号分隔）: 收入: ttl_inc_oper(营业总收入), inc_oper(营业收入), inc_inv(投资收益), inc_fv_chg(公允价值变动收益); 成本: ttl_cost_oper(营业总成本), cost_oper(营业成本), exp_sell(销售费用), exp_adm(管理费用), exp_rd(研发费用), exp_fin(财务费用); 利润: oper_prof(营业利润), ttl_prof(利润总额), net_prof(净利润), net_prof_pcom(归母净利润)",
            "date": "发布日期 'YYYY-MM-DD'，None 表示最新一期",
        },
        "required": ["symbols", "fields"],
        "returns": "DataFrame 利润表数据",
    },
    "stk_get_fundamentals_cashflow": {
        "description": "现金流量表截面数据（point-in-time），对应 GM: stk_get_fundamentals_cashflow_pt。",
        "params": {
            "symbols": "股票代码，多个用英文逗号分隔，如 'SHSE.600000,SZSE.000001'",
            "fields": "可用字段（逗号分隔）: 经营: net_cf_oper(经营活动现金净额), cf_in_oper(经营现金流入), cf_out_oper(经营现金流出); 投资: net_cf_inv(投资活动现金净额), cash_pay_inv(投资支付现金), pur_fix_intg_ast(购建固定资产); 筹资: net_cf_fin(筹资活动现金净额), cash_rcv_cptl(吸收投资现金), cash_rpay_brw(偿还债务现金); 其他: net_incr_cash_eq(现金净增加额), cash_cash_eq_end(期末现金余额)",
            "date": "发布日期 'YYYY-MM-DD'，None 表示最新一期",
        },
        "required": ["symbols", "fields"],
        "returns": "DataFrame 现金流量表数据",
    },
    "stk_get_finance_deriv": {
        "description": "财务衍生指标截面数据（每股指标），对应 GM: stk_get_finance_deriv_pt。",
        "params": {
            "symbols": "股票代码字符串，或逗号分隔多个代码",
            "fields": "可用字段: 每股(eps_basic/eps_dil2/eps_dil/bps/net_cf_oper_ps/ttl_inc_oper_ps); 收益率(roe/roe_weight/roe_avg/roe_cut); 同比(eps_dil_yoy/ttl_inc_oper_yoy/net_prof_pcom_yoy); 其他(ebit/ebitda/nr_prof_loss/net_prof_cut)",
            "date": "发布日期 'YYYY-MM-DD'，None 表示最新一期",
        },
        "required": ["symbols", "fields"],
        "returns": "DataFrame 财务衍生指标数据",
    },
    "stk_get_daily_mktvalue": {
        "description": "市值类单日截面指标（总市值、流通市值等），对应 GM: stk_get_daily_mktvalue_pt。",
        "params": {
            "symbols": "股票代码字符串，或逗号分隔多个代码",
            "fields": "市值类字段名，逗号分隔，例如: tot_mv(总市值), a_mv(A股流通市值), a_mv_ex_ltd(A股流通市值不含限售股), ev(企业价值)",
            "trade_date": "交易日 'YYYY-MM-DD'，None 表示最新交易日",
        },
        "required": ["symbols", "fields"],
        "returns": "DataFrame 市值数据",
    },
    "get_valuation": {
        "description": "获取单只股票的基础估值指标（pe_ttm, pe_mrq, pe_lyr）。",
        "params": {
            "symbol": "股票代码，例如 'SHSE.600820'",
        },
        "required": ["symbol"],
        "returns": "dict (pe_ttm, pe_mrq, pe_lyr)",
    },
    "stk_get_daily_valuation": {
        "description": "估值类单日截面指标（PE、PB 等），对应 GM: stk_get_daily_valuation_pt。",
        "params": {
            "symbols": "股票代码字符串，或逗号分隔多个代码",
            "fields": "可用字段: 市盈率(pe_ttm/pe_lyr/pe_mrq/pe_1q/pe_2q/pe_3q); 扣非(pe_ttm_cut/pe_lyr_cut/pe_mrq_cut); 市净率(pb_lyr/pb_mrq); 市现率(pcf_ttm_oper/pcf_ttm_ncf); 市销率(ps_ttm/ps_lyr/ps_mrq); PEG(peg_lyr/peg_mrq)",
            "trade_date": "交易日 'YYYY-MM-DD'，None 表示最新交易日",
        },
        "required": ["symbols", "fields"],
        "returns": "DataFrame 估值数据",
    },
    "stk_get_daily_basic": {
        "description": "基础类单日截面指标（收盘价、换手率、股本等），对应 GM: stk_get_daily_basic_pt。",
        "params": {
            "symbols": "股票代码，多个用英文逗号分隔，如 'SHSE.600000,SZSE.000001'",
            "fields": "可用字段（逗号分隔）: tclose(收盘价), turnrate(换手率%), ttl_shr(总股本), circ_shr(流通股本), ttl_shr_unl(无限售流通股), ttl_shr_ltd(有限售股本), a_shr_unl(A股流通股), h_shr_unl(H股流通股)",
            "trade_date": "交易日 'YYYY-MM-DD'，None 表示最新交易日",
        },
        "required": ["symbols", "fields"],
        "returns": "DataFrame 基础指标数据",
    },
    "stk_get_money_flow": {
        "description": "查询股票资金流向，对应 GM: stk_get_money_flow。",
        "params": {
            "symbols": "股票代码字符串，或逗号分隔多个代码，如 'SHSE.600820,SZSE.000538'",
            "date": "查询日期 'YYYY-MM-DD'，None 或 '' 表示最新",
        },
        "required": ["symbols"],
        "returns": "DataFrame 资金流向数据",
    },
    "stk_get_adj_factor": {
        "description": "查询股票复权因子，对应 GM: stk_get_adj_factor。",
        "params": {
            "symbols": "股票代码字符串（只能传入单只股票，例如 'SHSE.600820'）",
            "start_date": "开始日期 'YYYY-MM-DD'，None 表示不限制",
            "end_date": "结束日期 'YYYY-MM-DD'，None 表示不限制",
        },
        "required": ["symbols"],
        "returns": "DataFrame 复权因子数据",
    },
    "stk_get_finance_forecast": {
        "description": "查询股票业绩预告，对应 GM: stk_get_finance_forecast。",
        "params": {
            "symbols": "股票代码字符串，或逗号分隔多个代码",
            "date": "查询日期 'YYYY-MM-DD'，默认 '' 表示最新",
        },
        "required": ["symbols"],
        "returns": "DataFrame 业绩预告数据",
    },
    "stk_get_sector_category": {
        "description": "查询板块分类，对应 GM: stk_get_sector_category。",
        "params": {
            "sector_type": "板块类型: '1001' 市场类, '1002' 地域类, '1003' 概念类",
        },
        "required": ["sector_type"],
        "returns": "DataFrame 板块分类数据",
    },
    "stk_get_sector_constituents": {
        "description": "查询板块成分股，对应 GM: stk_get_sector_constituents。",
        "params": {
            "sector_code": "板块代码，可通过 stk_get_sector_category 获取",
        },
        "required": ["sector_code"],
        "returns": "DataFrame 板块成分股数据",
    },
    "stk_get_symbol_sector": {
        "description": "查询股票所属板块，对应 GM: stk_get_symbol_sector。",
        "params": {
            "symbols": "股票代码，多个用英文逗号分隔，如 'SHSE.600000,SZSE.000001'",
            "sector_type": "可选值: '1001'(市场类), '1002'(地域类), '1003'(概念类)",
        },
        "required": ["symbols", "sector_type"],
        "returns": "DataFrame 股票所属板块数据",
    },
    "stk_get_industry_category": {
        "description": "查询行业分类，对应 GM: stk_get_industry_category。",
        "params": {
            "source": "行业来源，'zjh2012'（证监会 2012，默认）或 'sw2021'(申万 2021)",
            "level": "行业分级，1=一级行业(默认)，2=二级，3=三级(部分来源不支持)",
        },
        "required": [],
        "returns": "DataFrame 行业分类数据",
    },
    "stk_get_industry_constituents": {
        "description": "查询行业成分股，对应 GM: stk_get_industry_constituents。",
        "params": {
            "industry_code": "行业代码，可通过 stk_get_industry_category 获取",
            "date": "查询日期 'YYYY-MM-DD'，默认 '' 表示最新",
        },
        "required": ["industry_code"],
        "returns": "DataFrame 行业成分股数据",
    },
    "stk_get_symbol_industry": {
        "description": "查询股票所属行业，对应 GM: stk_get_symbol_industry。",
        "params": {
            "symbols": "股票代码字符串，或用英文逗号分隔的多个代码，如 'SHSE.600820,SZSE.000002'",
            "source": "行业来源，'zjh2012'(证监会 2012，默认) 或 'sw2021'(申万 2021)",
            "level": "行业分级，1=一级行业(默认)，2=二级，3=三级",
            "date": "查询日期 'YYYY-MM-DD'，默认 '' 表示最新",
        },
        "required": ["symbols"],
        "returns": "DataFrame 股票所属行业数据",
    },
    "stk_get_finance_prime": {
        "description": "查询财务主要指标截面数据（多标的），对应 GM: stk_get_finance_prime_pt。",
        "params": {
            "symbols": "股票代码，多个用英文逗号分隔，如 'SHSE.600000,SZSE.000001'",
            "fields": "可用字段: 每股(eps_basic/eps_dil/eps_basic_cut/net_cf_oper_ps/bps_pcom_ps); 利润(oper_prof/ttl_prof/net_prof_pcom/net_prof/net_prof_pcom_cut); 资产(ttl_ast/ttl_liab/ttl_eqy_pcom/share_cptl/net_asset); 收入(ttl_inc_oper/inc_oper); 收益率(roe/roe_weight_avg/roe_cut/roe_weight_avg_cut); 现金流(net_cf_oper); 同比(eps_yoy/inc_oper_yoy/ttl_inc_oper_yoy/net_prof_pcom_yoy)",
            "date": "发布日期 'YYYY-MM-DD'，None 表示最新一期",
            "rpt_type": "报表类型，1=一季报, 6=中报, 9=前三季报, 12=年报，None=不限",
            "data_type": "数据类型，None=默认, 100=合并最初, 101=合并原始, 102=合并调整",
        },
        "required": ["symbols", "fields"],
        "returns": "DataFrame 财务主要指标数据",
    },
    "stk_get_dividend": {
        "description": "查询股票分红送股信息，对应 GM: stk_get_dividend。",
        "params": {
            "symbol": "股票代码（只能填一个股票标的）",
            "start_date": "开始时间（除权除息日），格式 'YYYY-MM-DD'",
            "end_date": "结束时间（除权除息日），格式 'YYYY-MM-DD'",
        },
        "required": ["symbol", "start_date", "end_date"],
        "returns": "DataFrame 分红送股数据",
    },
    "stk_get_ration": {
        "description": "查询股票配股信息，对应 GM: stk_get_ration。",
        "params": {
            "symbol": "股票代码（只能填一个股票标的）",
            "start_date": "开始时间（除权除息日），格式 'YYYY-MM-DD'",
            "end_date": "结束时间（除权除息日），格式 'YYYY-MM-DD'",
        },
        "required": ["symbol", "start_date", "end_date"],
        "returns": "DataFrame 配股数据",
    },
    "stk_get_shareholder_num": {
        "description": "查询股东户数，对应 GM: stk_get_shareholder_num。",
        "params": {
            "symbol": "股票代码（只能填一个股票标的）",
            "start_date": "开始时间（公告日期），格式 'YYYY-MM-DD'，默认 '' 表示最新时间",
            "end_date": "结束时间（公告日期），格式 'YYYY-MM-DD'，默认 '' 表示最新时间",
        },
        "required": ["symbol"],
        "returns": "DataFrame 股东户数数据",
    },
    "stk_get_top_shareholder": {
        "description": "查询十大股东，对应 GM: stk_get_top_shareholder。",
        "params": {
            "symbol": "股票代码（只能填一个股票标的）",
            "start_date": "开始时间（公告日期），格式 'YYYY-MM-DD'，默认 '' 表示最新时间",
            "end_date": "结束时间（公告日期），格式 'YYYY-MM-DD'，默认 '' 表示最新时间",
            "tradable_holder": "是否流通股东，False=十大股东（默认），True=十大流通股东",
        },
        "required": ["symbol"],
        "returns": "DataFrame 十大股东数据",
    },
    "stk_get_share_change": {
        "description": "查询股本变动，对应 GM: stk_get_share_change。",
        "params": {
            "symbol": "股票代码（只能填一个股票标的）",
            "start_date": "开始时间（发布日期），格式 'YYYY-MM-DD'，默认 '' 表示最新时间",
            "end_date": "结束时间（发布日期），格式 'YYYY-MM-DD'，默认 '' 表示最新时间",
        },
        "required": ["symbol"],
        "returns": "DataFrame 股本变动数据",
    },
    "stk_abnor_change_stocks": {
        "description": "查询龙虎榜股票数据，对应 GM: stk_abnor_change_stocks。",
        "params": {
            "symbols": "股票代码（可输入多个，用英文逗号分隔），默认 None 表示所有标的",
            "change_types": "异动类型（可输入多个，用英文逗号分隔），默认 None 表示所有类型",
            "trade_date": "交易日期，格式 'YYYY-MM-DD'，默认 None 表示最新交易日期",
            "fields": "返回字段，默认 None 返回所有字段",
            "df": "是否返回 dataframe 格式，默认 False 返回 list[dict]",
        },
        "required": [],
        "returns": "DataFrame 或 list[dict] 龙虎榜股票数据",
    },
    "stk_abnor_change_detail": {
        "description": "查询龙虎榜营业部数据，对应 GM: stk_abnor_change_detail。",
        "params": {
            "symbols": "股票代码（可输入多个，用英文逗号分隔），默认 None 表示所有标的",
            "change_types": "异动类型（可输入多个，用英文逗号分隔），默认 None 表示所有类型",
            "trade_date": "交易日期，格式 'YYYY-MM-DD'，默认 None 表示最新交易日期",
            "fields": "返回字段，默认 None 返回所有字段",
            "df": "是否返回 dataframe 格式，默认 False 返回 list[dict]",
        },
        "required": [],
        "returns": "DataFrame 或 list[dict] 龙虎榜营业部数据",
    },
    "stk_quota_shszhk_infos": {
        "description": "查询沪深港通额度数据，对应 GM: stk_quota_shszhk_infos。",
        "params": {
            "types": "类型（可输入多个，用英文逗号分隔），如 'SH,SHHK,SZ,SZHK'",
            "start_date": "开始日期，格式 'YYYY-MM-DD'",
            "end_date": "结束日期，格式 'YYYY-MM-DD'",
            "count": "查询数量",
            "df": "是否返回 dataframe 格式，默认 False 返回 list[dict]",
        },
        "required": [],
        "returns": "DataFrame 或 list[dict] 沪深港通额度数据",
    },
    "stk_hk_inst_holding_detail_info": {
        "description": "查询沪深港通标的港股机构持股明细数据，对应 GM: stk_hk_inst_holding_detail_info。",
        "params": {
            "symbols": "股票代码（如 'SHSE.600008'），None=所有标的",
            "trade_date": "交易日期（%Y-%m-%d 格式，None=最新）",
        },
        "required": [],
        "returns": "DataFrame 机构持股明细（symbol, sec_name, trade_date, participant_name, share_holding, shares_rate）",
    },
    "stk_hk_inst_holding_info": {
        "description": "查询沪深港通标的港股机构持股数据，对应 GM: stk_hk_inst_holding_info。",
        "params": {
            "symbols": "股票代码（如 'SHSE.600008,SZSE.000002'），None=所有标的",
            "trade_date": "交易日期（%Y-%m-%d 格式，None=最新）",
            "limit": "返回结果数量限制（可选）",
        },
        "required": [],
        "returns": "DataFrame 机构持股数据",
    },
    "stk_active_stock_top10_shszhk_info": {
        "description": "查询沪深港通十大活跃成交股数据，对应 GM: stk_active_stock_top10_shszhk_info。",
        "params": {
            "types": "类型（SH=沪股通, SHHK=沪港股通, SZ=深股通, SZHK=深港股通, NF=北向资金）可传入多个用逗号分隔（如 'SZ,SHHK'），None=全部",
            "trade_date": "交易日期（%Y-%m-%d 格式，None=最新）",
        },
        "required": [],
        "returns": "DataFrame 活跃成交股数据（symbol, sec_name, trade_type, rank, buy_amount, sell_amount, total_amount 等）",
    },
    "stk_get_finance_audit": {
        "description": "查询财务审计意见，对应 GM: stk_get_finance_audit。",
        "params": {
            "symbols": "股票代码 (如 'SHSE.600000' 或 'SHSE.600000,SZSE.000001')",
            "date": "查询日期（最新公告日期，%Y-%m-%d 格式，None=最新）",
            "rpt_date": "报告日期（%Y-%m-%d 格式，如 '2023-12-31' 表示年报）",
        },
        "required": ["symbols"],
        "returns": "DataFrame 审计意见（acct_agency, cpa, audit_opinion, audit_opinion_text, audit_no 等）",
    },
    "get_open_call_auction": {
        "description": "查询集合竞价开盘成交，对应 GM: get_open_call_auction。",
        "params": {
            "symbols": "股票代码，可输入多个，用英文逗号分隔，如 'SHSE.600000,SZSE.000001'",
            "trade_date": "交易日期，格式 'YYYY-MM-DD'，默认 None 表示最新交易日",
        },
        "required": ["symbols"],
        "returns": "DataFrame 集合竞价数据",
    },
}

# =============================================================================
# API Client
# =============================================================================

class MyQuantClient:
    """Client for MyQuant MCP HTTP API."""

    def __init__(self, base_url: str = DEFAULT_BASE_URL, timeout: int = DEFAULT_TIMEOUT):
        """
        Initialize the client.

        Args:
            base_url: Base URL of the MyQuant MCP server
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()

    def _get_url(self, endpoint: str) -> str:
        """Build full URL from endpoint."""
        return f"{self.base_url}{endpoint}"

    def list_tools(self) -> Dict[str, Any]:
        """
        Get list of all available tools from the server.

        Returns:
            Dict with 'success', 'count', and 'tools' keys
        """
        url = self._get_url(TOOLS_ENDPOINT)
        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def get_tool_info(self, tool_name: str) -> Dict[str, Any]:
        """
        Get information about a specific tool.

        Args:
            tool_name: Name of the tool

        Returns:
            Dict with tool information
        """
        url = self._get_url(f"{TOOLS_ENDPOINT}/{tool_name}")
        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def call_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """
        Call a tool with the given arguments.

        Args:
            tool_name: Name of the tool to call
            **kwargs: Tool arguments

        Returns:
            Dict with 'success' and 'data' or 'error' keys

        Raises:
            requests.HTTPError: If HTTP request fails
        """
        url = self._get_url(TOOL_CALL_ENDPOINT.format(tool_name=tool_name))
        response = self.session.post(url, json=kwargs, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def call_tool_get(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """
        Call a tool using GET request with query parameters.

        Args:
            tool_name: Name of the tool to call
            **kwargs: Tool arguments (converted to query params)

        Returns:
            Dict with 'success' and 'data' or 'error' keys
        """
        url = self._get_url(f"{TOOLS_ENDPOINT}/{tool_name}/call")
        response = self.session.get(url, params=kwargs, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def close(self):
        """Close the client session."""
        self.session.close()


def _server_tool_from_response(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Extract the tool object from a REST tool-info response."""
    tool = payload.get("tool")
    return tool if isinstance(tool, dict) else None


def _tool_requires_auth(tool: Optional[Dict[str, Any]]) -> bool:
    """Check whether a tool schema requires auth_token."""
    if not tool:
        return False
    schema = tool.get("inputSchema", {}) or {}
    properties = schema.get("properties", {}) or {}
    required = schema.get("required", []) or []
    return "auth_token" in properties or "auth_token" in required


def _mask_sensitive_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """Hide auth_token in CLI logging."""
    masked = dict(params)
    if "auth_token" in masked:
        masked["auth_token"] = "***"
    return masked


def _print_server_tool_info(tool: Dict[str, Any]) -> None:
    """Print tool details using live schema returned by the server."""
    schema = tool.get("inputSchema", {}) or {}
    properties = schema.get("properties", {}) or {}
    required = schema.get("required", []) or []

    print(f"\n{'='*60}")
    print(f"Tool: {tool.get('name', 'unknown')}")
    print(f"{'='*60}")
    print(f"\nDescription:\n  {tool.get('description', 'No description')}")
    print("\nParameters:")
    if properties:
        for param, info in properties.items():
            req_marker = "*" if param in required else " "
            type_name = info.get("type", "any")
            default = f", default={info['default']}" if "default" in info else ""
            print(f"  {req_marker} {param}: type={type_name}{default}")
    else:
        print("  None")
    print(f"\nRequired parameters: {', '.join(required) if required else 'None'}")
    print()


# =============================================================================
# CLI Interface
# =============================================================================

def save_result(data: Any, tool_name: str, download_dir: str, format: str = "json"):
    """
    Save result to file.

    Args:
        data: Data to save
        tool_name: Name of the tool (used in filename)
        download_dir: Directory to save to
        format: Output format ('json' or 'csv')
    """
    os.makedirs(download_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if format == "csv" and isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
        import csv

        filename = f"{tool_name}_{timestamp}.csv"
        filepath = os.path.join(download_dir, filename)

        with open(filepath, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)

        print(f"Saved to: {filepath}")
    else:
        filename = f"{tool_name}_{timestamp}.json"
        filepath = os.path.join(download_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, default=str)

        print(f"Saved to: {filepath}")


def print_tool_info(tool_name: str, client: Optional[MyQuantClient] = None):
    """Print detailed information about a tool."""
    if client is not None:
        try:
            payload = client.get_tool_info(tool_name)
            tool = _server_tool_from_response(payload)
            if payload.get("success") and tool:
                _print_server_tool_info(tool)
                return
        except requests.RequestException as exc:
            print(f"Warning: failed to fetch live tool info, falling back to local docs: {exc}")

    if tool_name not in DATA_TOOLS:
        print(f"Error: Unknown tool '{tool_name}'")
        print("Tip: run --list-tools against a live server to inspect the full tool set.")
        return

    tool = DATA_TOOLS[tool_name]
    print(f"\n{'='*60}")
    print(f"Tool: {tool_name}")
    print(f"{'='*60}")
    print(f"\nDescription:\n  {tool['description']}")
    print("\nParameters:")
    for param, desc in tool["params"].items():
        req_marker = "*" if param in tool["required"] else " "
        print(f"  {req_marker} {param}: {desc}")
    print(f"\nReturns:\n  {tool['returns']}")
    print(f"\nRequired parameters: {', '.join(tool['required']) if tool['required'] else 'None'}")
    print()


def list_all_tools(client: Optional[MyQuantClient] = None):
    """List all available tools."""
    if client is not None:
        try:
            payload = client.list_tools()
            tools = payload.get("tools", []) if payload.get("success") else []
            if tools:
                public_tools = sorted((t for t in tools if not _tool_requires_auth(t)), key=lambda item: item["name"])
                protected_tools = sorted((t for t in tools if _tool_requires_auth(t)), key=lambda item: item["name"])

                print("\n" + "="*60)
                print("MyQuant HTTP API - Available Tools")
                print("="*60)

                print("\n[Public Tools]")
                for tool in public_tools:
                    print(f"  {tool['name']:<35} - {tool.get('description', '')}")

                if protected_tools:
                    print("\n[Protected Tools]")
                    for tool in protected_tools:
                        print(f"  {tool['name']:<35} - {tool.get('description', '')}")
                    print("\nProtected tools require --auth-token <MCP_AUTH_TOKEN>.")

                print(f"\nTotal: {len(tools)} tools available")
                print("\nUse: python skills/myquant-mcp/scripts/client.py --info <tool_name> for details")
                print()
                return
        except requests.RequestException as exc:
            print(f"Warning: failed to fetch live tool list, falling back to built-in data catalog: {exc}")

    print("\n" + "="*60)
    print("MyQuant HTTP API - Built-in Data Tool Catalog")
    print("="*60)

    market_tools = ["history", "history_n", "current", "current_price", "last_tick",
                    "get_symbols", "get_symbol_infos", "get_trading_dates_by_year",
                    "get_history_symbol", "get_next_n_trading_dates",
                    "get_previous_n_trading_dates", "stk_get_index_constituents"]

    print("\n[Market Data Tools]")
    for name in market_tools:
        if name in DATA_TOOLS:
            desc = DATA_TOOLS[name]["description"].split("，")[0]
            print(f"  {name:<35} - {desc}")

    print("\n[Fundamental Data Tools]")
    for name in sorted(DATA_TOOLS.keys()):
        if name not in market_tools:
            desc = DATA_TOOLS[name]["description"].split("，")[0]
            print(f"  {name:<35} - {desc}")

    print(f"\nTotal: {len(DATA_TOOLS)} built-in data tools documented")
    print("\nTip: connect to a live server to inspect protected trading/account tools as well.")
    print()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="MyQuant HTTP API Client - Access public and protected tools",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  List all tools:
    python skills/myquant-mcp/scripts/client.py --list-tools

  Get tool info:
    python skills/myquant-mcp/scripts/client.py --info history

  Call a tool:
    python skills/myquant-mcp/scripts/client.py history --symbol SHSE.600000 --frequency 1d --start-time 2024-01-01 --end-time 2024-12-31

  Call a protected account tool:
    python skills/myquant-mcp/scripts/client.py --auth-token YOUR_TOKEN get_positions

  Call a protected trading tool:
    python skills/myquant-mcp/scripts/client.py --auth-token YOUR_TOKEN order_volume --symbol SZSE.000001 --volume 100 --side 1 --price 10.50

  Save result to file:
    python skills/myquant-mcp/scripts/client.py history --symbol SHSE.600000 --frequency 1d --start-time 2024-01-01 --end-time 2024-12-31 --download-dir ./data

  Use custom server:
    python skills/myquant-mcp/scripts/client.py --url http://your-server:8001 history --symbol SHSE.600000 ...

  Use GET method:
    python skills/myquant-mcp/scripts/client.py --get history --symbol SHSE.600000 --frequency 1d --start-time 2024-01-01 --end-time 2024-12-31
        """,
    )

    # Global options
    parser.add_argument(
        "--url", "-u",
        default=DEFAULT_BASE_URL,
        help=f"Server base URL (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--timeout", "-t",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"Request timeout in seconds (default: {DEFAULT_TIMEOUT})",
    )
    parser.add_argument(
        "--list-tools", "-l",
        action="store_true",
        help="List all available tools",
    )
    parser.add_argument(
        "--info", "-i",
        metavar="TOOL_NAME",
        help="Show detailed info for a tool",
    )
    parser.add_argument(
        "--download-dir", "-d",
        metavar="DIR",
        help="Directory to save results (if specified)",
    )
    parser.add_argument(
        "--format", "-f",
        choices=["json", "csv"],
        default="json",
        help="Output format for saved files (default: json)",
    )
    parser.add_argument(
        "--get", "-g",
        action="store_true",
        help="Use GET request instead of POST",
    )
    parser.add_argument(
        "--output", "-o",
        action="store_true",
        help="Print full output (not truncated)",
    )
    parser.add_argument(
        "--auth-token",
        help="Auth token for protected tools. Pass the same value as MCP_AUTH_TOKEN.",
    )

    # Tool name as positional argument
    parser.add_argument(
        "tool_name",
        nargs="?",
        help="Name of the tool to call",
    )

    # Tool arguments (all remaining args)
    parser.add_argument(
        "tool_args",
        nargs=argparse.REMAINDER,
        help="Tool arguments as --key value pairs",
    )

    args = parser.parse_args()

    client = MyQuantClient(base_url=args.url, timeout=args.timeout) if (args.list_tools or args.info or args.tool_name) else None

    # Handle list tools
    if args.list_tools:
        try:
            list_all_tools(client)
        finally:
            if client is not None:
                client.close()
        return

    # Handle tool info
    if args.info:
        try:
            print_tool_info(args.info, client)
        finally:
            if client is not None:
                client.close()
        return

    # Handle tool call
    if args.tool_name:
        tool_name = args.tool_name

        # Parse tool arguments
        tool_params = {}
        i = 0
        while i < len(args.tool_args):
            arg = args.tool_args[i]
            if arg.startswith("--"):
                key = arg[2:].replace("-", "_")
                if i + 1 < len(args.tool_args) and not args.tool_args[i + 1].startswith("--"):
                    value = args.tool_args[i + 1]
                    # Try to convert to appropriate type
                    if value.lower() == "true":
                        value = True
                    elif value.lower() == "false":
                        value = False
                    elif value.lower() == "none" or value.lower() == "null":
                        value = None
                    elif value.isdigit():
                        value = int(value)
                    else:
                        try:
                            value = float(value)
                        except ValueError:
                            pass
                    tool_params[key] = value
                    i += 2
                else:
                    # Boolean flag
                    tool_params[key] = True
                    i += 1
            else:
                i += 1

        try:
            live_tool = None
            try:
                payload = client.get_tool_info(tool_name)
                live_tool = _server_tool_from_response(payload)
            except requests.RequestException:
                live_tool = None

            if live_tool is None and tool_name not in DATA_TOOLS:
                print(f"Warning: Tool '{tool_name}' is not in the built-in data catalog.")
                print("Proceeding with the live server call anyway...\n")

            if args.auth_token and "auth_token" not in tool_params and _tool_requires_auth(live_tool):
                tool_params["auth_token"] = args.auth_token

            if _tool_requires_auth(live_tool) and "auth_token" not in tool_params:
                print(
                    "Error: this tool requires auth_token. Pass --auth-token <MCP_AUTH_TOKEN> "
                    "before the tool name, or provide --auth-token after the tool name as a tool argument."
                )
                return

            print(f"Calling tool: {tool_name}")
            print(f"Parameters: {json.dumps(_mask_sensitive_params(tool_params), ensure_ascii=False)}")

            if args.get:
                result = client.call_tool_get(tool_name, **tool_params)
            else:
                result = client.call_tool(tool_name, **tool_params)

            # Check result
            if result.get("success"):
                data = result.get("data")

                # Print result
                if args.output:
                    print(f"\nResult:\n{json.dumps(data, ensure_ascii=False, indent=2, default=str)}")
                else:
                    # Truncate output for display
                    output = json.dumps(data, ensure_ascii=False, indent=2, default=str)
                    if len(output) > 500:
                        print(f"\nResult (truncated, use --output for full):\n{output[:500]}...")
                    else:
                        print(f"\nResult:\n{output}")

                # Save if requested
                if args.download_dir:
                    save_result(data, tool_name, args.download_dir, args.format)
            else:
                print(f"\nError: {result.get('error', 'Unknown error')}")

        except requests.HTTPError as e:
            print(f"\nHTTP Error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    print(f"Server response: {json.dumps(error_data, ensure_ascii=False, indent=2)}")
                except:
                    print(f"Server response: {e.response.text}")
        except Exception as e:
            print(f"\nError: {e}")
        finally:
            if client is not None:
                client.close()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
