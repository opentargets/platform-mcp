"""Tool for executing entity search queries using SearchPageQuery."""

from pathlib import Path
from typing import Annotated, Optional

from pydantic import Field

from otar_mcp.client import execute_graphql_query
from otar_mcp.config import config
from otar_mcp.mcp_instance import mcp


def _get_search_page_query() -> str:
    """Load the SearchPageQuery.gql file."""
    current_file = Path(__file__)
    project_root = current_file.parent.parent.parent.parent
    query_file = project_root / "extracted_queries" / "search" / "SearchPageQuery.gql"

    if not query_file.exists():
        msg = f"SearchPageQuery.gql not found at {query_file}"
        raise FileNotFoundError(msg)

    with open(query_file, encoding="utf-8") as f:
        return f.read()


@mcp.tool(name="search_entity")
def search_entity(
    query_string: Annotated[
        str,
        Field(description="Search query string to find entities"),
    ],
    entity_names: Annotated[
        list[str],
        Field(description="List of entity types to search (e.g., ['target', 'disease', 'drug', 'variant', 'study'])"),
    ],
    index: Annotated[
        int,
        Field(description="Page index for pagination (0-based)", ge=0),
    ] = 0,
    jq_filter: Annotated[
        Optional[str],
        Field(description="Optional jq filter to pre-filter the JSON response server-side"),
    ] = None,
) -> dict:
    """Search for entities across multiple types using the Open Targets search API.

    This tool performs a multi-entity search that returns paginated results across
    targets, diseases, drugs, variants, and studies. It also fetches the top hit
    for each entity type to display as a detail panel.

    The results include:
    - Total number of results
    - Aggregations by entity type
    - Paginated search hits (10 per page)
    - Top hit with detailed information

    ALWAYS use a jq filter to return ONLY the specific information requested by the user.
    This achieves parsimony by reducing token consumption and response size.

    Args:
        query_string: The search query (e.g., "BRCA1", "breast cancer", "aspirin")
        entity_names: Entity types to search across (e.g., ["target", "disease", "drug"])
        index: Page number for pagination (default: 0, returns results 1-10)
        jq_filter: Optional jq expression to filter the response server-side

    Returns:
        dict: Search results with data field containing search hits, aggregations,
              and top hit details, or error message.
    """
    try:
        # Load the query
        query = _get_search_page_query()

        # Build variables
        variables = {
            "queryString": query_string,
            "index": index,
            "entityNames": entity_names,
        }

        # Execute query
        return execute_graphql_query(
            config.api_endpoint,
            query,
            variables,
            jq_filter=jq_filter,
        )
    except FileNotFoundError as e:
        return {"error": str(e)}
    except Exception as e:
        return {"error": f"Failed to execute search query: {e!s}"}
