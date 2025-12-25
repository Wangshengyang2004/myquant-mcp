"""
Server configuration and constants.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(override=True)

BASE_DIR = Path(__file__).resolve().parent.parent
WEBUI_HTML_PATH = BASE_DIR / "webui.html"

# Authentication
REQUIRE_AUTH_TOKEN = os.getenv("REQUIRE_AUTH_TOKEN", "true").lower() == "true"
AUTH_TOKEN = os.getenv("MCP_AUTH_TOKEN", "admin")
GM_TOKEN = os.getenv("GM_TOKEN", "")

# GM API
DEFAULT_ACCOUNT_ID = os.getenv(
    "GM_ACCOUNT_ID", "92c6b4e1-f4c8-46a0-9314-b9ef8acc33bc"
)


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
    import json
    if not data:
        return "No data available"
    return json.dumps(data, indent=2, default=str, ensure_ascii=False)
