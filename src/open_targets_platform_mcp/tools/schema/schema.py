"""Tool for fetching the Open Targets Platform GraphQL schema."""

from typing import Annotated

from graphql import print_schema
from pydantic import Field

from open_targets_platform_mcp.client.graphql import fetch_graphql_schema
from open_targets_platform_mcp.tools.schema.subschema import (
    _types_to_sdl,
    get_categories_for_docstring,
    get_category_subschemas,
)
from open_targets_platform_mcp.tools.schema.type_graph import get_cached_schema

# Module-level cache for schema (pre-fetched at startup)
_cached_schema: str | None = None


async def prefetch_schema() -> None:
    """Pre-fetch and cache the GraphQL schema at server startup.

    This function should be called once during server initialization
    to ensure the schema is available immediately when requested.
    """
    global _cached_schema  # noqa: PLW0603
    schema_obj = await fetch_graphql_schema()
    _cached_schema = print_schema(schema_obj)


async def get_open_targets_graphql_schema(
    categories: Annotated[
        list[str],
        Field(
            description="List of category names to filter the schema. "
            "Returns only types relevant to the specified categories.",
        ),
    ],
) -> str:
    """Retrieve the Open Targets Platform GraphQL schema by category."""
    if _cached_schema is None:
        msg = "Schema not initialized. Call prefetch_schema() at server startup."
        raise RuntimeError(msg)

    # Get subschemas for requested categories
    subschemas = get_category_subschemas()
    available_categories = sorted(subschemas.subschemas.keys())

    # Validate category names
    invalid_categories = [c for c in categories if c not in subschemas.subschemas]
    if invalid_categories:
        msg = (
            f"Invalid category name(s): {', '.join(invalid_categories)}. "
            f"Available categories: {', '.join(available_categories)}"
        )
        raise ValueError(msg)

    # Collect all types from requested categories
    all_types: set[str] = set()
    for category_name in categories:
        all_types.update(subschemas.subschemas[category_name].types)

    # Generate combined SDL
    schema_obj = get_cached_schema()
    return _types_to_sdl(all_types, schema_obj)


# Dynamically set the docstring with the categories list
get_open_targets_graphql_schema.__doc__ = f"""\
Retrieve the Open Targets Platform GraphQL schema filtered by category.

You MUST specify one or more categories to retrieve the relevant schema subset.
Categories group related GraphQL types into coherent subschemas
(e.g., 'drug-mechanisms', 'genetic-associations', 'target-safety').

Returns deduplicated GraphQL types in SDL format with their annotations.

Args:
    categories: List of category names to filter the schema.

Returns:
    str: Merged, deduplicated types in SDL (Schema Definition Language) format.

{get_categories_for_docstring()}
"""
