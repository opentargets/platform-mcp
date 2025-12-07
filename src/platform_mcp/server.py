"""Server setup and configuration for OpenTargets MCP."""

from fastmcp import FastMCP

from platform_mcp.mcp_instance import mcp


def setup_server() -> FastMCP:
    """
    Set up the MCP server with all tools.

    This function registers tools based on current configuration.
    Must be called after config.jq_enabled is set.

    Returns:
        FastMCP: Configured MCP server instance with all tools registered
    """
    # Import tool modules that don't need conditional registration
    # These imports trigger the @mcp.tool() decorators
    from platform_mcp.tools import schema, search_entity  # noqa: F401

    # Conditionally register query tools based on jq_enabled config
    from platform_mcp.tools.register import register_query_tools

    register_query_tools()

    return mcp
