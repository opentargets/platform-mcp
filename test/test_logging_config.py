"""Tests for the rich/json log output configuration."""

from __future__ import annotations

import json
import logging
import sys

import fastmcp
import pytest
from rich.logging import RichHandler

from open_targets_platform_mcp.logging_config import (
    CloudLoggingJsonFormatter,
    cloud_logging_severity,
    configure_logging,
    resolve_log_format,
    uvicorn_config,
)
from open_targets_platform_mcp.settings import Settings

_LOGGER_NAMES = ("", "fastmcp", "mcp", "uvicorn", "uvicorn.error", "uvicorn.access", "uvicorn.asgi")


@pytest.fixture
def restore_logging():
    """Snapshot and restore the logger state that configure_logging touches."""
    saved = {
        name: (logging.getLogger(name).handlers[:], logging.getLogger(name).level, logging.getLogger(name).propagate)
        for name in _LOGGER_NAMES
    }
    log_enabled = fastmcp.settings.log_enabled
    yield
    for name, (handlers, level, propagate) in saved.items():
        logger = logging.getLogger(name)
        logger.handlers[:] = handlers
        logger.setLevel(level)
        logger.propagate = propagate
    fastmcp.settings.log_enabled = log_enabled
    logging.captureWarnings(capture=False)


def _record(level: int, msg: str, *, exc_info=None) -> logging.LogRecord:
    return logging.LogRecord("fastmcp.tools", level, "/app/tool.py", 42, msg, None, exc_info, func="call_tool")


class TestJsonFormatter:
    def test_record_with_traceback_is_one_json_line(self):
        try:
            raise ValueError("bad argument 'type_name'")  # noqa: TRY301
        except ValueError:
            record = _record(logging.ERROR, "Error validating tool 'get_type_dependencies'", exc_info=sys.exc_info())

        line = CloudLoggingJsonFormatter().format(record)

        assert "\n" not in line
        entry = json.loads(line)
        assert entry["severity"] == "ERROR"
        assert entry["logger"] == "fastmcp.tools"
        assert entry["message"].startswith("Error validating tool 'get_type_dependencies'\n")
        assert "Traceback (most recent call last):" in entry["message"]
        assert "ValueError: bad argument 'type_name'" in entry["message"]
        assert entry["time"].endswith("+00:00")
        assert entry["logging.googleapis.com/sourceLocation"] == {
            "file": "/app/tool.py",
            "line": "42",
            "function": "call_tool",
        }

    def test_multiline_message_stays_on_one_line(self):
        line = CloudLoggingJsonFormatter().format(_record(logging.INFO, "first\nsecond"))
        assert "\n" not in line
        assert json.loads(line)["message"] == "first\nsecond"

    @pytest.mark.parametrize(
        ("level", "severity"),
        [
            (logging.DEBUG, "DEBUG"),
            (logging.INFO, "INFO"),
            (logging.WARNING, "WARNING"),
            (logging.ERROR, "ERROR"),
            (logging.CRITICAL, "CRITICAL"),
            (5, "DEFAULT"),
        ],
    )
    def test_severity_mapping(self, level, severity):
        assert cloud_logging_severity(level) == severity
        assert json.loads(CloudLoggingJsonFormatter().format(_record(level, "x")))["severity"] == severity


class TestFormatSelection:
    def test_auto_is_rich_locally(self):
        assert resolve_log_format("auto", environ={}) == "rich"

    def test_auto_is_json_on_cloud_run(self):
        assert resolve_log_format("auto", environ={"K_SERVICE": "open-targets-platform-mcp"}) == "json"

    @pytest.mark.parametrize("explicit", ["rich", "json"])
    def test_explicit_setting_overrides_detection(self, explicit):
        assert resolve_log_format(explicit, environ={"K_SERVICE": "svc"}) == explicit
        assert resolve_log_format(explicit, environ={}) == explicit

    def test_setting_default_and_env_var(self, monkeypatch):
        monkeypatch.delenv("OTP_MCP_LOG_FORMAT", raising=False)
        assert Settings().log_format == "auto"
        monkeypatch.setenv("OTP_MCP_LOG_FORMAT", "json")
        assert Settings().log_format == "json"

    def test_invalid_setting_is_rejected(self, monkeypatch):
        monkeypatch.setenv("OTP_MCP_LOG_FORMAT", "xml")
        with pytest.raises(ValueError, match="log_format"):
            Settings()


class TestConfigureLogging:
    @pytest.mark.usefixtures("restore_logging")
    def test_json_mode_routes_fastmcp_and_uvicorn_through_one_json_handler(self, capsys):
        assert configure_logging("json") == "json"

        fastmcp_logger = logging.getLogger("fastmcp")
        assert not any(isinstance(h, RichHandler) for h in fastmcp_logger.handlers)
        assert fastmcp_logger.propagate
        assert fastmcp.settings.log_enabled is False

        try:
            raise RuntimeError("boom")  # noqa: TRY301
        except RuntimeError:
            logging.getLogger("fastmcp.tools.tool_manager").exception("Error calling tool 'x'")
        logging.getLogger("uvicorn.error").warning("uvicorn warning")
        logging.getLogger("fastmcp.timing.detailed").info("Tool 'x' completed in 1.00ms")
        # Levels are unchanged from rich mode: mcp INFO stays hidden, WARNING shows.
        logging.getLogger("mcp.server").info("mcp info")
        logging.getLogger("mcp.server").warning("mcp warning")

        lines = capsys.readouterr().err.strip().splitlines()
        entries = [json.loads(line) for line in lines]
        assert [(e["logger"], e["severity"]) for e in entries] == [
            ("fastmcp.tools.tool_manager", "ERROR"),
            ("uvicorn.error", "WARNING"),
            ("fastmcp.timing.detailed", "INFO"),
            ("mcp.server", "WARNING"),
        ]
        assert "RuntimeError: boom" in entries[0]["message"]

    @pytest.mark.usefixtures("restore_logging")
    def test_rich_mode_leaves_fastmcp_handlers_alone(self):
        before = logging.getLogger("fastmcp").handlers[:]
        root_before = logging.getLogger().handlers[:]

        assert configure_logging("rich") == "rich"

        assert logging.getLogger("fastmcp").handlers == before
        assert logging.getLogger().handlers == root_before
        assert fastmcp.settings.log_enabled is True


class TestUvicornConfig:
    def test_rich_mode_default_changes_nothing(self):
        assert uvicorn_config("rich", access_log=None) == {}

    def test_json_mode_disables_uvicorn_log_config_and_access_log(self):
        assert uvicorn_config("json", access_log=None) == {"log_config": None, "access_log": False}

    def test_access_log_can_be_forced(self):
        assert uvicorn_config("json", access_log=True)["access_log"] is True
        assert uvicorn_config("rich", access_log=False) == {"access_log": False}
