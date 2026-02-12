"""
Server configuration and constants.
"""
import functools
import json
import os
import time
from pathlib import Path
from dotenv import load_dotenv

from server.log_config import audit_logger, console_logger

load_dotenv(override=True)

BASE_DIR = Path(__file__).resolve().parent.parent
WEBUI_HTML_PATH = BASE_DIR / "server" / "webui.html"

# Authentication
REQUIRE_AUTH_TOKEN = os.getenv("REQUIRE_AUTH_TOKEN", "true").lower() == "true"
AUTH_TOKEN = os.getenv("MCP_AUTH_TOKEN", "admin")
GM_TOKEN = os.getenv("GM_TOKEN", "")

# GM API
DEFAULT_ACCOUNT_ID = os.getenv("GM_ACCOUNT_ID", "")


def validate_auth(auth_token: str) -> bool:
    """Validate authentication token"""
    if not REQUIRE_AUTH_TOKEN:
        return True
    return auth_token == AUTH_TOKEN


def format_dataframe_response(df) -> str:
    """Format DataFrame response"""
    if df is None or (hasattr(df, 'empty') and df.empty):
        return "No data available"
    return df.to_string(index=False) if hasattr(df, 'to_string') else str(df)


def format_list_response(data: list) -> str:
    """Format list response"""
    if not data:
        return "No data available"
    return json.dumps(data, indent=2, default=str, ensure_ascii=False)


def format_gm_response(res) -> str:
    """Format response from GM API (unified formatter for all response types)."""
    if res is None:
        return "No data available"
    if hasattr(res, 'to_string'):  # DataFrame
        return res.to_string(index=False)
    if isinstance(res, list):
        return json.dumps(res, indent=2, default=str, ensure_ascii=False)
    return json.dumps(res, indent=2, default=str, ensure_ascii=False)


# Security types for get_symbols/get_symbol_infos
SEC_TYPE_STOCK = 1010
SEC_TYPE_FUND = 1020
SEC_TYPE_BOND = 1030
SEC_TYPE_FUTURE = 1040
SEC_TYPE_OPTION = 1050
SEC_TYPE_INDEX = 1060
SEC_TYPE_SECTOR = 1070

# Claude Agent System Prompt
CLAUDE_AGENT_SYSTEM_PROMPT = """You are a helpful quantitative trading and financial analysis assistant with access to:

**MyQuant Tools** (Chinese Stock Market):
- history/history_n: Historical OHLCV data
- current: Real-time market snapshot
- get_symbols: List stocks/funds/indices
- stk_get_daily_valuation: PE/PB/PS valuation metrics
  - fields: 'pe_ttm,pe_mrq,pe_lyr,pb_lyr,pb_mrq,ps_ttm,ps_lyr'
- stk_get_daily_basic: Price, turnover, shares data
  - fields: 'tclose,turnrate,ttl_shr,circ_shr'
- stk_get_fundamentals_balance: Balance sheet (assets, liabilities, equity)
  - fields: 'mny_cptl,ttl_ast,ttl_liab,ttl_eqy_pcom,ttl_eqy'
- stk_get_fundamentals_income: Income statement (revenue, profit)
  - fields: 'ttl_inc_oper,inc_oper,net_prof,net_prof_pcom'
- stk_get_money_flow: Money flow analysis
- get_positions: Current trading positions
- get_cash: Account cash balance

**IMPORTANT - Field Names**: Use exact field names as shown above. Common errors:
- Use 'pb_lyr' NOT 'pb'
- Use 'tclose,turnrate,ttl_shr,circ_shr' NOT 'turnover_ratio,volume_ratio,total_share,float_share,total_mv,circ_mv'
- Use 'ttl_ast' NOT 'total_assets'
- Use 'ttl_inc_oper,net_prof' NOT 'total_revenue'

**Chrome DevTools** (Browser Automation):
- Navigate to websites, take screenshots, extract content

You can help users analyze stocks, get market data, evaluate fundamentals, and scrape financial websites."""

# Chrome DevTools MCP Server Configuration
CHROME_DEVTOOLS_MCP_CONFIG = {
    "type": "stdio",
    "command": "npx",
    "args": ["-y", "chrome-devtools-mcp@latest"]
}


def audit_wrapper(func):
    """Audit logging decorator for tool functions"""

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        tool_name = func.__name__
        
        # Log tool call start to console
        arg_preview = ", ".join(f"{k}={repr(v)[:50]}" for k, v in list(kwargs.items())[:3] if k != "auth_token")
        console_logger.info(f"TOOL CALL: {tool_name}({arg_preview})")
        
        try:
            arguments = kwargs.copy()
            log_args = {k: v for k, v in arguments.items() if k != "auth_token"}
            if "auth_token" in arguments:
                log_args["auth_token"] = "***"

            result = await func(*args, **kwargs)
            duration_ms = (time.time() - start_time) * 1000
            audit_logger.log_tool_call(tool_name, log_args, "success", duration_ms=duration_ms)
            
            # Log success to console
            console_logger.info(f"TOOL DONE: {tool_name} [{duration_ms:.1f}ms]")
            return result
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            log_args = {k: v for k, v in kwargs.items() if k != "auth_token"}
            if "auth_token" in kwargs:
                log_args["auth_token"] = "***"
            audit_logger.log_tool_call(tool_name, log_args, "error", error=str(e), duration_ms=duration_ms)
            
            # Log error to console
            console_logger.error(f"TOOL ERROR: {tool_name} - {e}")
            raise
    return wrapper
