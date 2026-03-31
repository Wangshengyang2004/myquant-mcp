#!/usr/bin/env python3
"""
MyQuant MCP Server - Main entry point

FastMCP + Streamable HTTP transport with modular architecture.

This is the main entry point that imports from the refactored `server/` package.
Run this file to start the server:

    python server.py

The server will listen on http://0.0.0.0:8001
"""
import logging
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

import uvicorn
from gm.api import set_token, set_serv_addr
from dotenv import load_dotenv

# Import log_config first to initialize logging suppression
from server.log_config import console_logger, suppress_mcp_sdk_logging
from server.app import create_app


def init_gm_token():
    """Initialize GM API access (token + optional service address)"""
    load_dotenv(override=True)
    token = os.getenv("GM_TOKEN", "")
    if token:
        set_token(token)
        console_logger.info("GM API token initialized successfully")
    else:
        console_logger.warning("GM_TOKEN not found in environment")

    serv_addr = os.getenv("GM_SERV_ADDR", "").strip()
    if serv_addr:
        try:
            set_serv_addr(serv_addr)
            console_logger.info(f"GM service address set to {serv_addr}")
        except Exception as exc:
            console_logger.error(f"Failed to set GM service address '{serv_addr}': {exc}")
    else:
        console_logger.info("GM_SERV_ADDR not set, defaulting to local GM terminal")


def configure_uvicorn_logging():
    """Configure uvicorn logging to be cleaner."""
    # Get uvicorn loggers
    uvicorn_logger = logging.getLogger("uvicorn")
    uvicorn_error_logger = logging.getLogger("uvicorn.error")
    uvicorn_access_logger = logging.getLogger("uvicorn.access")
    
    # Set levels
    uvicorn_logger.setLevel(logging.INFO)
    uvicorn_error_logger.setLevel(logging.INFO)
    uvicorn_access_logger.setLevel(logging.WARNING)  # Reduce access log verbosity
    
    # Don't propagate to root logger
    uvicorn_logger.propagate = False
    uvicorn_error_logger.propagate = False
    uvicorn_access_logger.propagate = False


def main():
    """Run the server."""
    # Configure logging early
    suppress_mcp_sdk_logging()
    configure_uvicorn_logging()
    
    # Initialize GM token
    init_gm_token()
    
    # Port configuration
    port = int(os.getenv("PORT", "8001"))
    host = os.getenv("HOST", "0.0.0.0")

    # Get app
    app = create_app()

    console_logger.info(f"Starting MyQuant MCP Server on http://{host}:{port}")
    console_logger.info(f"Web UI: http://{host}:{port}/")
    console_logger.info(f"MCP endpoint: http://{host}:{port}/mcp/")
    console_logger.info(f"API docs: http://{host}:{port}/api/v1/tools")

    # Run server
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="warning",  # Reduce uvicorn's own logging verbosity
        access_log=False,  # Disable default access log (we have our own middleware)
    )


if __name__ == "__main__":
    main()
