"""Server setup and configuration for OpenTargets MCP."""

from fastmcp import FastMCP
from mcp.types import Icon

from open_targets_platform_mcp.settings import settings
from open_targets_platform_mcp.tools import (
    batch_query_with_jq,
    batch_query_without_jq,
    get_open_targets_graphql_schema,
    query_with_jq,
    query_without_jq,
    search_entity,
)


def create_server() -> FastMCP:
    """Set up the MCP server and register all tools.

    This function registers tools based on current configuration.

    Returns:
        FastMCP: Configured MCP server instance with all tools registered
    """
    mcp = FastMCP(
        settings.server_name,
        icons=[
            Icon(
                src="https://raw.githubusercontent.com/opentargets/ot-ui-apps/main/apps/platform/public/favicon.png",
                mimeType="image/png",
            ),
        ],
    )

    mcp.tool(batch_query_with_jq)
    mcp.tool(batch_query_without_jq)
    mcp.tool(get_open_targets_graphql_schema)
    mcp.tool(query_with_jq)
    mcp.tool(query_without_jq)
    mcp.tool(search_entity)

    return mcp
