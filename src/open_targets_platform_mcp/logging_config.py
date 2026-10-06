"""Log output: Rich console output or Cloud Logging structured JSON.

In ``rich`` mode nothing is changed: FastMCP's Rich handlers and uvicorn's
default log config are used, which is pleasant for local interactive use.

In ``json`` mode every log record is written to stderr as exactly one JSON
object per line, using the field names Cloud Logging understands for
structured logs (see
https://cloud.google.com/run/docs/logging#writing_structured_logs).
Tracebacks are embedded in the ``message`` field of the same entry, so an
event is never split across several log entries.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from collections.abc import Mapping

LogFormat = Literal["auto", "rich", "json"]
ResolvedLogFormat = Literal["rich", "json"]

# Loggers that get their own handlers (FastMCP installs Rich handlers at
# import time, uvicorn via its default dictConfig). In json mode their
# handlers are removed and records propagate to the root JSON handler.
_MANAGED_LOGGERS = (
    "fastmcp",
    "mcp",
    "uvicorn",
    "uvicorn.error",
    "uvicorn.access",
    "uvicorn.asgi",
)


def resolve_log_format(
    log_format: LogFormat,
    environ: Mapping[str, str] | None = None,
) -> ResolvedLogFormat:
    """Resolve ``auto`` to a concrete format.

    ``auto`` selects ``json`` on Cloud Run (detected via ``K_SERVICE``, which
    Cloud Run always sets) and ``rich`` otherwise. An explicit ``rich`` or
    ``json`` always wins.
    """
    if log_format != "auto":
        return log_format
    env = os.environ if environ is None else environ
    return "json" if env.get("K_SERVICE") else "rich"


def cloud_logging_severity(levelno: int) -> str:
    """Map a Python logging level number to a Cloud Logging severity."""
    if levelno >= logging.CRITICAL:
        return "CRITICAL"
    if levelno >= logging.ERROR:
        return "ERROR"
    if levelno >= logging.WARNING:
        return "WARNING"
    if levelno >= logging.INFO:
        return "INFO"
    if levelno >= logging.DEBUG:
        return "DEBUG"
    return "DEFAULT"


class CloudLoggingJsonFormatter(logging.Formatter):
    """Format a record as a single-line JSON object for Cloud Logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Return the record as one line of JSON, traceback included."""
        message = record.getMessage()
        if record.exc_info and not record.exc_text:
            record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            message = f"{message}\n{record.exc_text}"
        if record.stack_info:
            message = f"{message}\n{self.formatStack(record.stack_info)}"

        created = datetime.fromtimestamp(record.created, tz=timezone.utc)
        entry: dict[str, Any] = {
            "severity": cloud_logging_severity(record.levelno),
            "message": message,
            "logger": record.name,
            "time": created.isoformat(),
            "logging.googleapis.com/sourceLocation": {
                "file": record.pathname,
                "line": str(record.lineno),
                "function": record.funcName,
            },
        }
        # json.dumps escapes newlines, so the output is always one line.
        return json.dumps(entry, default=str, ensure_ascii=False)


def configure_logging(log_format: LogFormat) -> ResolvedLogFormat:
    """Configure log output for ``log_format``; return the resolved format.

    Call after ``fastmcp`` is imported (it installs Rich handlers at import
    time) and before the server starts.
    """
    resolved = resolve_log_format(log_format)
    if resolved == "rich":
        return resolved

    import fastmcp  # noqa: PLC0415 - only needed in json mode

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(CloudLoggingJsonFormatter())

    # Keep the levels that apply in rich mode, so only the format changes:
    # other loggers (e.g. ``mcp``) had no handler and only reached stderr at
    # WARNING+ via Python's last-resort handler; FastMCP and uvicorn log at
    # FastMCP's configured level (INFO by default).
    root = logging.getLogger()
    for existing in root.handlers[:]:
        root.removeHandler(existing)
    root.addHandler(handler)
    root.setLevel(logging.WARNING)

    for name in _MANAGED_LOGGERS:
        logger = logging.getLogger(name)
        for existing in logger.handlers[:]:
            logger.removeHandler(existing)
        logger.propagate = True
    for name in ("fastmcp", "uvicorn"):
        logging.getLogger(name).setLevel(fastmcp.settings.log_level)

    # FastMCP re-runs its Rich ``configure_logging`` when a temporary log
    # level is requested; with ``log_enabled`` off that is a no-op, so the
    # Rich handlers cannot come back. Our handlers ignore this flag.
    fastmcp.settings.log_enabled = False

    # Route ``warnings.warn`` output through logging, so it is JSON too.
    logging.captureWarnings(capture=True)
    return resolved


def uvicorn_config(
    log_format: ResolvedLogFormat,
    *,
    access_log: bool | None,
) -> dict[str, Any]:
    """Extra uvicorn settings for ``log_format``.

    In json mode uvicorn must not apply its own ``dictConfig``
    (``log_config=None``), so its loggers keep propagating to the root JSON
    handler. Access logs default to off in json mode because Cloud Run
    already records every request in its request log; ``access_log``
    overrides that default in either mode.
    """
    if log_format == "rich":
        return {} if access_log is None else {"access_log": access_log}
    return {"log_config": None, "access_log": bool(access_log)}
