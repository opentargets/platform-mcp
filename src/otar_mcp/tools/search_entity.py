"""Tool for executing entity search queries using SearchAnnotation."""

from pathlib import Path
from typing import Annotated

from pydantic import Field

from otar_mcp.client import execute_graphql_query
from otar_mcp.config import config
from otar_mcp.mcp_instance import mcp


def _get_search_annotation_query() -> str:
    """Load the SearchAnnotation.gql file."""
    current_file = Path(__file__)
    project_root = current_file.parent.parent.parent.parent
    query_file = project_root / "extracted_queries" / "search" / "SearchAnnotation.gql"

    if not query_file.exists():
        msg = f"SearchAnnotation.gql not found at {query_file}"
        raise FileNotFoundError(msg)

    with open(query_file, encoding="utf-8") as f:
        return f.read()


@mcp.tool(name="search_entity")
def search_entity(
    query_string: Annotated[
        str,
        Field(description="Search query string to find entities (e.g., 'BRCA1', 'breast cancer', 'aspirin')"),
    ],
) -> dict:
    """Search for entities across multiple types using the Open Targets search API.

    This tool performs a streamlined entity search that returns the id and entity type
    for up to 3 matching entities across targets, diseases, drugs, variants, and studies.

    Args:
        query_string: The search query (e.g., "BRCA1", "breast cancer", "aspirin")

    Returns:
        list: Array of up to 3 matching entities with id and entity fields,
              or dict with error message if the query fails.
    """
    try:
        # Load the query
        query = _get_search_annotation_query()

        # Build variables
        variables = {
            "queryString": query_string,
        }

        # Hardcoded jq filter to return only id and entity from first 3 results
        jq_filter = ".data.search.hits[:3] | map({id, entity})"

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
