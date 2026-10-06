"""Module for starting the server using FastMCP CLI."""

import asyncio

from fastmcp import FastMCP

from open_targets_platform_mcp.create_server import create_server
from open_targets_platform_mcp.logging_config import configure_logging
from open_targets_platform_mcp.settings import settings

# Under `fastmcp run`, the FastMCP CLI applies uvicorn's own log config; only
# the application, FastMCP and MCP loggers are switched to JSON here.
configure_logging(settings.log_format)

mcp: FastMCP = asyncio.run(create_server())
