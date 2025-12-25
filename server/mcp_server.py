"""
FastMCP server initialization.
"""
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

# Security settings - disable DNS rebinding protection for local network access
security_settings = TransportSecuritySettings(
    enable_dns_rebinding_protection=False,
)

# Create FastMCP server
mcp = FastMCP(
    "myquant-windows-gateway",
    stateless_http=True,
    json_response=True,
    streamable_http_path="/",
    transport_security=security_settings,
)


def get_mcp_app():
    """Get the FastMCP streamable HTTP app"""
    return mcp.streamable_http_app()
