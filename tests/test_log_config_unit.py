import asyncio
import logging

from starlette.requests import Request
from starlette.responses import Response

from server import log_config as log_config_module


def test_request_context_round_trip():
    log_config_module.RequestContext.set(ip="1.2.3.4", request_id="req-1")
    assert log_config_module.RequestContext.get()["ip"] == "1.2.3.4"
    log_config_module.RequestContext.clear()
    assert log_config_module.RequestContext.get() == {}


def test_context_formatter_includes_request_context():
    log_config_module.RequestContext.set(ip="1.2.3.4", request_id="req-2", path="/demo")
    formatter = log_config_module.ContextFormatter("%(ip)s %(request_id)s %(path)s %(message)s")
    record = logging.LogRecord("test", logging.INFO, __file__, 1, "hello", args=(), exc_info=None)

    formatted = formatter.format(record)

    log_config_module.RequestContext.clear()
    assert formatted == "1.2.3.4 req-2 /demo hello"


def test_filter_sensitive_args_masks_nested_values():
    filtered = log_config_module.audit_logger._filter_sensitive_args(
        {"auth_token": "secret", "nested": {"password": "hidden"}, "symbol": "SHSE.600000"}
    )

    assert filtered["auth_token"] == "***"
    assert filtered["nested"]["password"] == "***"
    assert filtered["symbol"] == "SHSE.600000"


def test_logging_middleware_sets_and_clears_context(monkeypatch):
    access_messages = []
    middleware = log_config_module.LoggingMiddleware(app=lambda scope, receive, send: None)
    monkeypatch.setattr(log_config_module.access_logger, "info", lambda message: access_messages.append(message))

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/health",
        "raw_path": b"/health",
        "query_string": b"",
        "headers": [(b"user-agent", b"pytest-agent")],
        "client": ("127.0.0.1", 1234),
        "server": ("testserver", 80),
        "path_params": {},
    }
    request = Request(scope, receive)

    async def call_next(req):
        context = log_config_module.RequestContext.get()
        assert context["path"] == "/health"
        return Response("ok")

    response = asyncio.run(middleware.dispatch(request, call_next))

    assert response.status_code == 200
    assert access_messages == ["GET /health"]
    assert log_config_module.RequestContext.get() == {}


def test_monitor_performance_wraps_sync_and_async(monkeypatch):
    calls = []
    monkeypatch.setattr(
        log_config_module.PerformanceMonitor,
        "log",
        classmethod(lambda cls, operation, duration_ms, metadata=None: calls.append((operation, duration_ms))),
    )

    @log_config_module.monitor_performance("sync-op")
    def sync_func():
        return "sync"

    @log_config_module.monitor_performance("async-op")
    async def async_func():
        return "async"

    assert sync_func() == "sync"
    assert asyncio.run(async_func()) == "async"
    assert calls[0][0] == "sync-op"
    assert calls[1][0] == "async-op"


def test_get_debug_info_contains_expected_keys():
    info = log_config_module.get_debug_info()

    assert "debug_mode" in info
    assert "log_files" in info
    assert "request_context" in info
