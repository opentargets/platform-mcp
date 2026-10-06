"""Tool for executing GraphQL queries against the Open Targets Platform API."""

from typing import Annotated, Any

from fastmcp.exceptions import ToolError

from open_targets_platform_mcp.client import execute_graphql_query
from open_targets_platform_mcp.helper import clone_function_with_removed_parameter
from open_targets_platform_mcp.model.query_result import QueryResult, QueryResultStatus


async def _query_impl(
    query_string: str,
    variables: dict[str, Any] | None = None,
    jq_filter: str | None = None,
) -> QueryResult:
    result = await execute_graphql_query(query_string, variables, jq_filter=jq_filter)
    # Raise so the MCP response is flagged with isError; ToolError messages
    # are not masked.
    if result.status == QueryResultStatus.ERROR:
        raise ToolError(result.error_message())
    return result


async def query_with_jq(
    query_string: Annotated[
        str,
        "GraphQL query string starting with 'query' keyword.",
    ],
    variables: Annotated[
        dict[str, Any] | None,
        "Optional dict or JSON string with query variables.",
    ] = None,
    jq_filter: Annotated[
        str | None,
        "Optional jq filter to pre-filter the JSON response server-side. "
        "Always use null coalescing (`//`) to handle null or missing values gracefully, "
        'for example: `// empty`, `// []`, `// {}`, `// ""`, or any other sensible default.',
    ] = None,
) -> Annotated[
    QueryResult,
    "GraphQL response with data field containing targets, diseases, drugs, variants, studies. "
    "A failed query is returned as a tool error with the error message.",
]:
    return await _query_impl(query_string, variables, jq_filter)


query_without_jq = clone_function_with_removed_parameter(query_with_jq, "jq_filter")
