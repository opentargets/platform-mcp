import asyncio
from importlib import metadata
from typing import Annotated

import typer
from pydantic import HttpUrl

from open_targets_platform_mcp.create_server import create_server
from open_targets_platform_mcp.settings import TransportType, settings

PACKAGE_NAME = "open_targets_platform_mcp"
PACKAGE_VERSION = metadata.version(PACKAGE_NAME)

app = typer.Typer(
    help=f"Model Context Protocol server for Open Targets Platform version {PACKAGE_VERSION}",
)


def _version_callback(value: bool) -> None:
    """Show the package version and exit."""
    if value:
        typer.echo(f"{PACKAGE_NAME} {PACKAGE_VERSION}")
        raise typer.Exit


def _list_tools_callback(value: bool) -> None:
    """List all available MCP tools."""
    if value:
        mcp = create_server()
        tools = asyncio.run(mcp.get_tools())
        for name, tool in tools.items():
            # Extract first line of description from the tool's description field
            description = tool.description or "No description available"
            first_line = description.split("\n")[0].strip()
            typer.echo(f"  - {name}: {first_line}")
        raise typer.Exit


@app.callback(invoke_without_command=True)
def root(
    version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            help=_version_callback.__doc__,
            is_eager=True,
            callback=_version_callback,
        ),
    ] = None,
    list_tools: Annotated[
        bool | None,
        typer.Option(
            "--list-tools",
            help=_list_tools_callback.__doc__,
            is_eager=True,
            callback=_list_tools_callback,
        ),
    ] = None,
    transport: Annotated[
        TransportType | None,
        typer.Option(
            help="Protocol the server to use",
            show_default=True,
        ),
    ] = settings.transport,
    host: Annotated[
        str | None,
        typer.Option(
            help="Host to bind the HTTP server to",
            show_default=True,
        ),
    ] = settings.http_host,
    port: Annotated[
        int | None,
        typer.Option(
            help="Port to bind the HTTP server to",
            show_default=True,
        ),
    ] = settings.http_port,
    jq: Annotated[
        bool | None,
        typer.Option(
            help="Enable/Disable jq filtering support for query tools",
            show_default=True,
        ),
    ] = settings.jq_enabled,
    api: Annotated[
        str | None,
        typer.Option(
            help="Open Targets Platform API endpoint to use",
            show_default=True,
        ),
    ] = str(settings.api_endpoint),
    timeout: Annotated[
        int | None,
        typer.Option(
            help="Request timeout (in seconds) for calls to the Open Targets Platform API.",
            show_default=True,
        ),
    ] = settings.api_call_timeout,
) -> None:
    """Entry point of CLI."""
    settings.transport = settings.transport if transport is None else transport
    settings.http_host = settings.http_host if host is None else host
    settings.http_port = settings.http_port if port is None else port
    settings.jq_enabled = settings.jq_enabled if jq is None else jq
    settings.api_endpoint = settings.api_endpoint if api is None else HttpUrl(api)
    settings.api_call_timeout = settings.api_call_timeout if timeout is None else timeout

    mcp = create_server()

    if settings.transport == TransportType.HTTP:
        mcp.run(
            transport=settings.transport.value,
            host=settings.http_host,
            port=settings.http_port,
        )
    else:
        mcp.run(
            transport=settings.transport.value,
        )


def main() -> None:
    """Entry point of the application."""
    app()


if __name__ == "__main__":
    main()
