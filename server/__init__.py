#!/usr/bin/env python3
"""
MyQuant MCP Server - Main entry point

Modular architecture with FastMCP + Streamable HTTP transport.
"""
import os
import uvicorn

from server.app import create_app


def main():
    """Run the server"""
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
