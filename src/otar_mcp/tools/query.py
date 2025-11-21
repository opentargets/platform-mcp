"""Tool for executing GraphQL queries against the OpenTargets API."""

import json
from typing import Annotated, Optional, Union

from pydantic import Field

from otar_mcp.client import execute_graphql_query
from otar_mcp.config import config
from otar_mcp.mcp_instance import mcp


@mcp.tool(name="query_open_targets_graphql")
def query_open_targets_graphql(
    query_string: Annotated[str, Field(description="GraphQL query string starting with 'query' keyword")],
    variables: Annotated[
        Optional[Union[dict, str]],
        Field(description="Optional variables for the GraphQL query"),
    ] = None,
    jq_filter: Annotated[
        Optional[str],
        Field(description="Optional jq filter to pre-filter the JSON response server-side"),
    ] = None,
) -> dict:
    """Execute GraphQL queries against the Open Targets API.

    IMPORTANT: Before writing any query, you MUST first call the `get_open_targets_query_examples`
    tool with relevant categories (e.g., ["target", "disease", "drug"]) to learn the proper
    query syntax, available fields, required variables, and structure. Use the examples as
    templates for constructing your queries.

    If the examples don't provide sufficient information about available fields, types, or
    query structure, use the `get_open_targets_graphql_schema` tool to retrieve the full
    GraphQL schema for more detailed type definitions and field information.

    CRITICAL IDENTIFIER REQUIREMENTS:
    Open Targets queries require specific standardized identifiers, NOT common names:

    - Targets/Genes: ENSEMBL IDs (e.g., "ENSG00000139618" not "BRCA2")
    - Diseases: EFO IDs (e.g., "EFO_0000305") or MONDO IDs (e.g., "MONDO_0007254")
                NOT disease names like "breast cancer"
    - Drugs: ChEMBL IDs (e.g., "CHEMBL1201583" not "aspirin" or "Bayer Aspirin")
    - Variants: Variant IDs in "chr_pos_ref_alt" format (e.g., "19_44908822_C_T")
                or rsIDs (e.g., "rs7412")
    - Studies: Study IDs (e.g., "GCST90002357")
    - Credible Sets: Study Locus IDs (e.g., "7d68cc9c70351c9dbd2a2c0c145e555d")

    WHEN USER PROVIDES COMMON NAMES:
    If the user asks about entities using common language (gene symbols like "BRCA2",
    disease names like "breast cancer", drug trade names like "aspirin"), you MUST
    first use the `search_entity` tool to find the proper identifiers before
    constructing your GraphQL query.

    Example workflow:
    1. User asks: "What are the associations for BRCA2 and breast cancer?"
    2. Call: search_entity(query_string="BRCA2", entity_names=["target"])
       → Get ENSEMBL ID: "ENSG00000139618"
    3. Call: search_entity(query_string="breast cancer", entity_names=["disease"])
       → Get EFO/MONDO ID: "MONDO_0007254"
    4. Use these IDs in your GraphQL query variables

    ALWAYS use a jq filter to return ONLY the specific information requested by the user.
    This achieves parsimony by reducing token consumption and response size. Never return
    the full API response when only specific fields are needed.

    Args:
        query_string: GraphQL query starting with 'query' keyword
        variables: Optional dict or JSON string with query variables
        jq_filter: Optional jq expression to filter the response server-side

    Returns:
        dict: GraphQL response with data field containing targets, diseases, drugs, variants,
              studies or error message.
    """
    try:
        # Parse variables if provided as a JSON string
        parsed_variables: Optional[dict] = variables if isinstance(variables, dict) else None
        if isinstance(variables, str):
            try:
                parsed_variables = json.loads(variables)
            except json.JSONDecodeError as e:
                return {"error": f"Failed to parse variables JSON string: {e!s}"}

        return execute_graphql_query(config.api_endpoint, query_string, parsed_variables, jq_filter=jq_filter)
    except Exception as e:
        return {"error": f"Failed to execute GraphQL query: {e!s}"}
