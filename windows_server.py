#!/usr/bin/env python3
"""
MyQuant MCP Server - Main entry point

FastMCP + Streamable HTTP transport with modular architecture.

This is the main entry point that imports from the refactored `server/` package.
Run this file to start the server:

    python windows_server.py

The server will listen on http://0.0.0.0:8001
"""
import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

import uvicorn
from server.app import create_app


def main():
    """Run the server."""
    # Port configuration
    port = int(os.getenv("PORT", "8001"))
    host = os.getenv("HOST", "0.0.0.0")

    # Get app
    app = create_app()

    print(f"Starting MyQuant MCP Server on http://{host}:{port}")
    print(f"Web UI: http://{host}:{port}/")
    print(f"MCP endpoint: http://{host}:{port}/mcp/")
    print(f"API docs: http://{host}:{port}/api/v1/tools")

    # Run server
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )


if __name__ == "__main__":
    main()
