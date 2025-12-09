"""Tests for GraphQL client module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from open_targets_platform_mcp.client.graphql import execute_graphql_query
from open_targets_platform_mcp.model.result import QueryResult, QueryResultStatus

# ============================================================================
# execute_graphql_query Tests - Unit Tests with Mocks
# ============================================================================


class TestExecuteGraphQLQuery:
    """Tests for execute_graphql_query function."""

    @pytest.mark.asyncio
    async def test_execute_query_success(self, sample_query_string, sample_graphql_response):
        """Test successful query execution."""
        mock_client = MagicMock()
        mock_client.execute_async = AsyncMock(return_value=sample_graphql_response)

        with patch("open_targets_platform_mcp.client.graphql.gql", return_value="parsed_query"):
            with patch("open_targets_platform_mcp.client.graphql.Client", return_value=mock_client):
                result = await execute_graphql_query(sample_query_string)

        assert result.status == QueryResultStatus.SUCCESS
        assert result.result == sample_graphql_response

    @pytest.mark.asyncio
    async def test_execute_query_with_variables(
        self, sample_query_string, sample_variables, sample_graphql_response
    ):
        """Test query execution with variables."""
        mock_client = MagicMock()
        mock_client.execute_async = AsyncMock(return_value=sample_graphql_response)

        with patch("open_targets_platform_mcp.client.graphql.gql", return_value="parsed_query"):
            with patch("open_targets_platform_mcp.client.graphql.Client", return_value=mock_client):
                result = await execute_graphql_query(sample_query_string, variables=sample_variables)

        assert result.status == QueryResultStatus.SUCCESS
        mock_client.execute_async.assert_called_once_with("parsed_query", variable_values=sample_variables)

    @pytest.mark.asyncio
    async def test_execute_query_default_headers(self, sample_query_string):
        """Test that default headers are set when none provided."""
        with patch("open_targets_platform_mcp.client.graphql.AIOHTTPTransport") as mock_transport:
            with patch("open_targets_platform_mcp.client.graphql.gql", return_value="parsed_query"):
                with patch("open_targets_platform_mcp.client.graphql.Client"):
                    await execute_graphql_query(sample_query_string)

        call_kwargs = mock_transport.call_args[1]
        assert call_kwargs["headers"] == {"Content-Type": "application/json"}

    @pytest.mark.asyncio
    async def test_execute_query_invalid_query_string(self):
        """Test handling of invalid GraphQL query string."""
        invalid_query = "this is not valid graphql"

        with patch("open_targets_platform_mcp.client.graphql.gql", side_effect=Exception("Parse error")):
            result = await execute_graphql_query(invalid_query)

        assert result.status == QueryResultStatus.ERROR
        assert "Parse error" in str(result.message)

    @pytest.mark.asyncio
    async def test_execute_query_execution_error(self, sample_query_string):
        """Test handling of query execution errors."""
        mock_client = MagicMock()
        mock_client.execute_async = AsyncMock(side_effect=Exception("Network error"))

        with patch("open_targets_platform_mcp.client.graphql.gql", return_value="parsed_query"):
            with patch("open_targets_platform_mcp.client.graphql.Client", return_value=mock_client):
                result = await execute_graphql_query(sample_query_string)

        assert result.status == QueryResultStatus.ERROR
        assert "Network error" in str(result.message)


# ============================================================================
# JQ Filter Tests
# ============================================================================


class TestJQFiltering:
    """Tests for jq filter functionality."""

    @pytest.mark.asyncio
    async def test_execute_query_with_simple_jq_filter(self, sample_query_string):
        """Test query execution with simple jq filter."""
        mock_response = {
            "target": {"id": "ENSG00000141510", "approvedSymbol": "TP53", "approvedName": "tumor protein p53"}
        }

        mock_client = MagicMock()
        mock_client.execute_async = AsyncMock(return_value=mock_response)

        with patch("open_targets_platform_mcp.client.graphql.gql", return_value="parsed_query"):
            with patch("open_targets_platform_mcp.client.graphql.Client", return_value=mock_client):
                result = await execute_graphql_query(sample_query_string, jq_filter=".target.id")

        # jq filter should extract just the ID
        assert result.status == QueryResultStatus.SUCCESS
        assert result.result == "ENSG00000141510"

    @pytest.mark.asyncio
    async def test_execute_query_with_complex_jq_filter(self, sample_query_string):
        """Test query execution with object-building jq filter."""
        mock_response = {
            "target": {"id": "ENSG00000141510", "approvedSymbol": "TP53", "approvedName": "tumor protein p53"}
        }

        mock_client = MagicMock()
        mock_client.execute_async = AsyncMock(return_value=mock_response)

        with patch("open_targets_platform_mcp.client.graphql.gql", return_value="parsed_query"):
            with patch("open_targets_platform_mcp.client.graphql.Client", return_value=mock_client):
                result = await execute_graphql_query(
                    sample_query_string, jq_filter=".target | {id, symbol: .approvedSymbol}"
                )

        # jq filter returns a single dict
        assert result.status == QueryResultStatus.SUCCESS
        assert isinstance(result.result, dict)
        assert "id" in result.result
        assert "symbol" in result.result
        assert result.result["id"] == "ENSG00000141510"
        assert result.result["symbol"] == "TP53"

    @pytest.mark.asyncio
    async def test_execute_query_with_array_jq_filter(self, sample_query_string):
        """Test query execution with jq filter that returns multiple results."""
        mock_response = {
            "targets": [
                {"id": "ENSG00000141510", "approvedSymbol": "TP53"},
                {"id": "ENSG00000012048", "approvedSymbol": "BRCA1"},
            ]
        }

        mock_client = MagicMock()
        mock_client.execute_async = AsyncMock(return_value=mock_response)

        with patch("open_targets_platform_mcp.client.graphql.gql", return_value="parsed_query"):
            with patch("open_targets_platform_mcp.client.graphql.Client", return_value=mock_client):
                result = await execute_graphql_query(sample_query_string, jq_filter=".targets[] | .approvedSymbol")

        # Multiple results should be in result list
        assert result.status == QueryResultStatus.SUCCESS
        assert isinstance(result.result, list)
        assert result.result == ["TP53", "BRCA1"]

    @pytest.mark.asyncio
    async def test_execute_query_jq_filter_error_handling(self, sample_query_string):
        """Test that jq filter errors are handled gracefully."""
        mock_response = {"target": {"id": "ENSG00000141510"}}

        mock_client = MagicMock()
        mock_client.execute_async = AsyncMock(return_value=mock_response)

        # Mock jq to raise an error
        with patch("open_targets_platform_mcp.client.graphql.gql", return_value="parsed_query"):
            with patch("open_targets_platform_mcp.client.graphql.Client", return_value=mock_client):
                with patch("open_targets_platform_mcp.client.graphql.jq.compile") as mock_jq:
                    # Make jq filter raise an error
                    mock_jq.side_effect = Exception("jq compilation error")

                    result = await execute_graphql_query(sample_query_string, jq_filter=".invalid_filter")

        # Should return warning with original data
        assert result.status == QueryResultStatus.WARNING
        assert result.result == mock_response
        assert "jq filter failed" in str(result.message)
        assert "// empty" in str(result.message)  # Should suggest null handling

    @pytest.mark.asyncio
    async def test_execute_query_no_jq_filter(self, sample_query_string, sample_graphql_response):
        """Test query execution without jq filter returns full response."""
        mock_client = MagicMock()
        mock_client.execute_async = AsyncMock(return_value=sample_graphql_response)

        with patch("open_targets_platform_mcp.client.graphql.gql", return_value="parsed_query"):
            with patch("open_targets_platform_mcp.client.graphql.Client", return_value=mock_client):
                result = await execute_graphql_query(sample_query_string)

        assert result.status == QueryResultStatus.SUCCESS
        assert result.result == sample_graphql_response


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.integration
class TestGraphQLIntegration:
    """Integration tests with real API calls."""

    @pytest.mark.asyncio
    async def test_real_query_execution(self):
        """Test real query execution against OpenTargets API."""
        query = """
        query {
            target(ensemblId: "ENSG00000141510") {
                id
                approvedSymbol
            }
        }
        """

        result = await execute_graphql_query(query)

        assert result.status == QueryResultStatus.SUCCESS
        assert "target" in result.result
        assert result.result["target"]["id"] == "ENSG00000141510"
        assert result.result["target"]["approvedSymbol"] == "TP53"

    @pytest.mark.asyncio
    async def test_real_query_with_variables(self):
        """Test real query with variables."""
        query = """
        query GetTarget($ensemblId: String!) {
            target(ensemblId: $ensemblId) {
                id
                approvedSymbol
            }
        }
        """
        variables = {"ensemblId": "ENSG00000012048"}

        result = await execute_graphql_query(query, variables=variables)

        assert result.status == QueryResultStatus.SUCCESS
        assert result.result["target"]["id"] == "ENSG00000012048"
        assert result.result["target"]["approvedSymbol"] == "BRCA1"

    @pytest.mark.asyncio
    async def test_real_query_with_jq_filter(self):
        """Test real query with jq filter."""
        query = """
        query {
            target(ensemblId: "ENSG00000141510") {
                id
                approvedSymbol
                approvedName
            }
        }
        """

        result = await execute_graphql_query(query, jq_filter=".target.approvedSymbol")

        assert result.status == QueryResultStatus.SUCCESS
        assert result.result == "TP53"

    @pytest.mark.asyncio
    async def test_real_invalid_query(self):
        """Test that invalid query returns error."""
        invalid_query = """
        query {
            nonexistentField {
                id
            }
        }
        """

        result = await execute_graphql_query(invalid_query)

        assert result.status == QueryResultStatus.ERROR
