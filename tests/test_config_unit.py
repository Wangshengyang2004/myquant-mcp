import asyncio
import importlib
import json


def reload_config(monkeypatch, require_auth="true", auth_token="", slow_threshold="100"):
    import dotenv

    monkeypatch.setenv("REQUIRE_AUTH_TOKEN", require_auth)
    monkeypatch.setenv("MCP_AUTH_TOKEN", auth_token)
    monkeypatch.setenv("SLOW_THRESHOLD_MS", slow_threshold)
    monkeypatch.setattr(dotenv, "load_dotenv", lambda *args, **kwargs: None)
    import server.config as config
    return importlib.reload(config)


def test_validate_auth_requires_matching_token(monkeypatch):
    config = reload_config(monkeypatch, require_auth="true", auth_token="secret-token")

    assert config.validate_auth("secret-token") is True
    assert config.validate_auth("wrong-token") is False


def test_validate_auth_fails_closed_when_token_missing(monkeypatch):
    config = reload_config(monkeypatch, require_auth="true", auth_token="")

    assert config.validate_auth("anything") is False


def test_validate_auth_allows_when_auth_disabled(monkeypatch):
    config = reload_config(monkeypatch, require_auth="false", auth_token="")

    assert config.validate_auth("anything") is True


def test_formatters_cover_empty_and_non_empty(monkeypatch):
    config = reload_config(monkeypatch)

    class FakeDf:
        empty = False

        def to_string(self, index=False):
            return "col\n1"

    class EmptyDf:
        empty = True

    assert config.format_dataframe_response(None) == "No data available"
    assert config.format_dataframe_response(EmptyDf()) == "No data available"
    assert config.format_dataframe_response(FakeDf()) == "col\n1"
    assert config.format_list_response([]) == "No data available"
    assert json.loads(config.format_list_response([{"symbol": "SHSE.600000"}])) == [{"symbol": "SHSE.600000"}]
    assert config.format_gm_response(None) == "No data available"
    assert json.loads(config.format_gm_response({"ok": True})) == {"ok": True}


def test_result_summary_handles_common_shapes(monkeypatch):
    config = reload_config(monkeypatch)

    assert config._result_summary(None) == "None"
    assert config._result_summary("No data available") == "empty"
    assert config._result_summary("header\nrow1\nrow2") == "2 rows"
    assert config._result_summary("single line") == "single line"


def test_audit_wrapper_masks_auth_and_logs_success(monkeypatch):
    config = reload_config(monkeypatch, slow_threshold="0")
    audit_entries = []
    info_messages = []

    monkeypatch.setattr(
        config.audit_logger,
        "log_tool_call",
        lambda *args, **kwargs: audit_entries.append((args, kwargs)),
    )
    monkeypatch.setattr(config.RequestContext, "get", classmethod(lambda cls: {"request_id": "req-1"}))
    monkeypatch.setattr(config.console_logger, "info", lambda message: info_messages.append(message))

    times = iter([10.0, 10.25])
    monkeypatch.setattr(config.time, "time", lambda: next(times))

    @config.audit_wrapper
    async def sample_tool(auth_token: str, symbol: str):
        return "header\nrow"

    result = asyncio.run(sample_tool(auth_token="secret", symbol="SHSE.600000"))

    assert result == "header\nrow"
    assert audit_entries[0][0][0] == "sample_tool"
    assert audit_entries[0][0][1]["auth_token"] == "***"
    assert "req-1" in info_messages[0]
    assert "SLOW" in info_messages[0]


def test_audit_wrapper_logs_error(monkeypatch):
    config = reload_config(monkeypatch)
    audit_entries = []
    error_messages = []

    monkeypatch.setattr(
        config.audit_logger,
        "log_tool_call",
        lambda *args, **kwargs: audit_entries.append((args, kwargs)),
    )
    monkeypatch.setattr(config.RequestContext, "get", classmethod(lambda cls: {"request_id": "req-2"}))
    monkeypatch.setattr(config.console_logger, "error", lambda message: error_messages.append(message))

    times = iter([20.0, 20.1])
    monkeypatch.setattr(config.time, "time", lambda: next(times))

    @config.audit_wrapper
    async def failing_tool(auth_token: str):
        raise RuntimeError("boom")

    try:
        asyncio.run(failing_tool(auth_token="secret"))
    except RuntimeError as exc:
        assert str(exc) == "boom"
    else:
        raise AssertionError("RuntimeError should have been raised")

    assert audit_entries[0][0][0] == "failing_tool"
    assert audit_entries[0][0][1]["auth_token"] == "***"
    assert "ERR: boom" in error_messages[0]
