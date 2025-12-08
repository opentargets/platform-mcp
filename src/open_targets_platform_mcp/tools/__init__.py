"""MCP tools for OpenTargets API."""

# Import all tools to make them available when this package is imported
from open_targets_platform_mcp.tools.batch_query import batch_query_with_jq, batch_query_without_jq
from open_targets_platform_mcp.tools.query import query_with_jq, query_without_jq
from open_targets_platform_mcp.tools.schema import get_open_targets_graphql_schema
from open_targets_platform_mcp.tools.search_entity import search_entity

__all__ = [
    "batch_query_with_jq",
    "batch_query_without_jq",
    "get_open_targets_graphql_schema",
    "query_with_jq",
    "query_without_jq",
    "search_entity",
]
