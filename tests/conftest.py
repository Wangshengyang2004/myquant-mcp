import contextlib
import sys
import types


def _build_dummy_gm_api():
    module = types.ModuleType("gm.api")

    def _dummy_function(*args, **kwargs):
        return []

    def _dummy_getattr(name):
        if name in {
            "OrderType_Limit",
            "PositionEffect_Open",
            "PositionEffect_Close",
            "PositionSide_Long",
        }:
            return 0
        return _dummy_function

    module.__getattr__ = _dummy_getattr
    module.set_token = lambda *args, **kwargs: None
    module.set_serv_addr = lambda *args, **kwargs: None
    return module


def _install_gm_stub():
    gm_module = types.ModuleType("gm")
    gm_api_module = _build_dummy_gm_api()
    gm_module.api = gm_api_module
    sys.modules.setdefault("gm", gm_module)
    sys.modules.setdefault("gm.api", gm_api_module)


def _install_mcp_stub():
    mcp_module = types.ModuleType("mcp")
    mcp_server_module = types.ModuleType("mcp.server")
    mcp_fastmcp_module = types.ModuleType("mcp.server.fastmcp")
    mcp_transport_module = types.ModuleType("mcp.server.transport_security")

    class DummySessionManager:
        @contextlib.asynccontextmanager
        async def run(self):
            yield

    class FastMCP:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs
            self.session_manager = DummySessionManager()

        def tool(self):
            def decorator(func):
                return func
            return decorator

        def streamable_http_app(self):
            return {"app": "dummy-mcp"}

    class TransportSecuritySettings:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

    mcp_fastmcp_module.FastMCP = FastMCP
    mcp_transport_module.TransportSecuritySettings = TransportSecuritySettings
    mcp_server_module.fastmcp = mcp_fastmcp_module
    mcp_server_module.transport_security = mcp_transport_module
    mcp_module.server = mcp_server_module

    sys.modules.setdefault("mcp", mcp_module)
    sys.modules.setdefault("mcp.server", mcp_server_module)
    sys.modules.setdefault("mcp.server.fastmcp", mcp_fastmcp_module)
    sys.modules.setdefault("mcp.server.transport_security", mcp_transport_module)


_install_gm_stub()
_install_mcp_stub()
