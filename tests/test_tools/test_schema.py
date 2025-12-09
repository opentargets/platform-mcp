"""Tests for schema tool."""

from open_targets_platform_mcp.tools.schema.schema import get_open_targets_graphql_schema

# Access the underlying function
get_schema_fn = get_open_targets_graphql_schema


def test_get_open_targets_graphql_schema_returns_string() -> None:
    """Test that get_open_targets_graphql_schema returns a string."""
    result = get_schema_fn()
    assert isinstance(result, str)
    # Result should be non-empty
    assert len(result) > 0
