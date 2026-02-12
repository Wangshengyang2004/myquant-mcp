#!/usr/bin/env python3
"""
MyQuant MCP Server - Main entry point

Modular architecture with FastMCP + Streamable HTTP transport.
"""
import os
import uvicorn

from server.app import create_app
from gm.api import set_token


def init_gm_token():
    """Initialize GM API token"""
    from dotenv import load_dotenv
    load_dotenv(override=True)
    token = os.getenv("GM_TOKEN", "")
    if token:
        set_token(token)
        print(f"GM API token initialized successfully")
    else:
        print("Warning: GM_TOKEN not found in environment")


def main():
    """Run the server"""
    # Initialize GM token
    init_gm_token()
    
    # Port configuration
    port = int(os.getenv("PORT", "8001"))
    host = os.getenv("HOST", "0.0.0.0")

    # Get app
    app = create_app()

    # Run server
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )


if __name__ == "__main__":
    main()
