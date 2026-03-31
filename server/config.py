"""
Server configuration and constants.
"""
import functools
import json
import os
import time
from pathlib import Path
from dotenv import load_dotenv

from server.log_config import audit_logger, console_logger, RequestContext

load_dotenv(override=True)

BASE_DIR = Path(__file__).resolve().parent.parent
WEBUI_HTML_PATH = BASE_DIR / "server" / "webui.html"

# Authentication
REQUIRE_AUTH_TOKEN = os.getenv("REQUIRE_AUTH_TOKEN", "true").lower() == "true"
AUTH_TOKEN = os.getenv("MCP_AUTH_TOKEN", "").strip()
GM_TOKEN = os.getenv("GM_TOKEN", "")

# GM API
DEFAULT_ACCOUNT_ID = os.getenv("GM_ACCOUNT_ID", "")


def validate_auth(auth_token: str) -> bool:
    """Validate authentication token"""
    if not REQUIRE_AUTH_TOKEN:
        return True
    if not AUTH_TOKEN:
        console_logger.warning("Protected tool access denied because MCP_AUTH_TOKEN is not configured")
        return False
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

SLOW_THRESHOLD_MS = float(os.getenv("SLOW_THRESHOLD_MS", "100"))


def _result_summary(result) -> str:
    if result is None:
        return "None"
    s = str(result).strip()
    if not s or s == "No data available":
        return "empty"
    lines = s.splitlines()
    if len(lines) > 1:
        return f"{len(lines) - 1} rows"
    return s[:20].replace("\n", " ")


def audit_wrapper(func):
    """Audit logging decorator for tool functions"""

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        tool_name = func.__name__
        
        arg_preview = ", ".join(f"{k}={repr(v)[:50]}" for k, v in list(kwargs.items())[:3] if k != "auth_token")

        try:
            arguments = kwargs.copy()
            log_args = {k: v for k, v in arguments.items() if k != "auth_token"}
            if "auth_token" in arguments:
                log_args["auth_token"] = "***"

            result = await func(*args, **kwargs)
            duration_ms = (time.time() - start_time) * 1000
            audit_logger.log_tool_call(tool_name, log_args, "success", duration_ms=duration_ms)

            ctx = RequestContext.get()
            req_id = ctx.get("request_id", "-")
            slow_tag = " SLOW" if duration_ms > SLOW_THRESHOLD_MS else ""
            summary = _result_summary(result)
            console_logger.info(f"[{req_id}] TOOL: {tool_name}({arg_preview}) → {duration_ms:.1f}ms{slow_tag} OK ({summary})")
            return result
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            log_args = {k: v for k, v in kwargs.items() if k != "auth_token"}
            if "auth_token" in kwargs:
                log_args["auth_token"] = "***"
            audit_logger.log_tool_call(tool_name, log_args, "error", error=str(e), duration_ms=duration_ms)

            ctx = RequestContext.get()
            req_id = ctx.get("request_id", "-")
            console_logger.error(f"[{req_id}] TOOL: {tool_name}({arg_preview}) → {duration_ms:.1f}ms ERR: {e}")
            raise
    return wrapper
