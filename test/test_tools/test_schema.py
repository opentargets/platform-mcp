"""Tests for schema tool."""

from unittest.mock import AsyncMock, patch

import pytest
from graphql import GraphQLSchema, build_schema

from open_targets_platform_mcp.tools.schema import schema


@pytest.fixture
def clear_cache():
    """Clear the schema cache before and after each test."""
    schema._cached_schema = None
    yield
    schema._cached_schema = None


@pytest.fixture
def mock_graphql_schema() -> GraphQLSchema:
    """Create a mock GraphQL schema for testing."""
    return build_schema(
        """
        type Query {
            target(ensemblId: String!): Target
        }
        type Target {
            id: String!
            approvedSymbol: String
        }
        """,
    )


@pytest.mark.asyncio
async def test_prefetch_schema_populates_cache(clear_cache, mock_graphql_schema) -> None:
    """Test that prefetch_schema fetches and caches the schema."""
    with patch(
        "open_targets_platform_mcp.tools.schema.schema.fetch_graphql_schema",
        new_callable=AsyncMock,
    ) as mock_fetch:
        mock_fetch.return_value = mock_graphql_schema

        await schema.prefetch_schema()

    assert schema._cached_schema is not None
    assert isinstance(schema._cached_schema, str)
    assert len(schema._cached_schema) > 0
    assert "type Query" in schema._cached_schema or "type Query {" in schema._cached_schema
    mock_fetch.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_open_targets_graphql_schema_returns_cached_schema(clear_cache, mock_graphql_schema) -> None:
    """Test that get_open_targets_graphql_schema returns the pre-fetched schema."""
    with patch(
        "open_targets_platform_mcp.tools.schema.schema.fetch_graphql_schema",
        new_callable=AsyncMock,
    ) as mock_fetch:
        mock_fetch.return_value = mock_graphql_schema

        # Pre-fetch the schema first
        await schema.prefetch_schema()

        # Now get the schema - should return cached value
        result = await schema.get_open_targets_graphql_schema()

    assert isinstance(result, str)
    assert len(result) > 0
    assert "type Query" in result or "type Query {" in result
    assert "target" in result.lower()
    # Should only be called once (during prefetch)
    mock_fetch.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_open_targets_graphql_schema_raises_if_not_prefetched(clear_cache) -> None:
    """Test that get_open_targets_graphql_schema raises error if schema not pre-fetched."""
    with pytest.raises(RuntimeError, match="Schema not initialized"):
        await schema.get_open_targets_graphql_schema()


@pytest.mark.asyncio
async def test_multiple_calls_return_same_cached_schema(clear_cache, mock_graphql_schema) -> None:
    """Test that multiple calls return the same cached schema."""
    with patch(
        "open_targets_platform_mcp.tools.schema.schema.fetch_graphql_schema",
        new_callable=AsyncMock,
    ) as mock_fetch:
        mock_fetch.return_value = mock_graphql_schema

        await schema.prefetch_schema()

        result1 = await schema.get_open_targets_graphql_schema()
        result2 = await schema.get_open_targets_graphql_schema()

        assert result1 == result2
        # Should only be called once during prefetch
        assert mock_fetch.await_count == 1
