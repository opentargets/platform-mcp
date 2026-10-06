"""Tests for warming the schema caches at server startup."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock

import pytest
from fastmcp import Client

from open_targets_platform_mcp.cache import AsyncCache
from open_targets_platform_mcp.client.graphql import fetch_graphql_schema
from open_targets_platform_mcp.create_server import create_server
from open_targets_platform_mcp.settings import TransportType, settings
from open_targets_platform_mcp.tools.schema import caches

ALL_SCHEMA_CACHES = (
    caches.schema_cache,
    caches.type_graph_cache,
    caches.category_subschemas_cache,
    caches.serialised_schema_cache,
)


@pytest.fixture
def schema_factory():
    """Replace the schema fetch with a mock and leave all schema caches empty afterwards."""
    factory = AsyncMock()
    caches.schema_cache.set_factory(factory)
    for cache in ALL_SCHEMA_CACHES:
        cache.clear()
    yield factory
    caches.schema_cache.set_factory(fetch_graphql_schema)
    for cache in ALL_SCHEMA_CACHES:
        cache.clear()


@pytest.fixture
def stdio_transport():
    original = settings.transport
    settings.transport = TransportType.STDIO
    yield
    settings.transport = original


class TestAsyncCacheWarm:
    async def test_eager_cache_is_populated(self):
        factory = AsyncMock(return_value="value")
        cache = AsyncCache[str](factory, is_eager=True)
        await cache.warm()
        factory.assert_awaited_once()
        assert await cache.get() == "value"
        factory.assert_awaited_once()

    async def test_lazy_cache_is_not_populated(self):
        factory = AsyncMock(return_value="value")
        cache = AsyncCache[str](factory)
        await cache.warm()
        factory.assert_not_awaited()


class TestWarmSchemaCaches:
    async def test_populates_schema_tool_caches(self, schema_factory, graphql_schema):
        schema_factory.return_value = graphql_schema
        await caches.warm_schema_caches()
        schema_factory.assert_awaited_once()
        assert caches.schema_cache._value is graphql_schema
        assert caches.type_graph_cache._value is not None
        assert caches.category_subschemas_cache._value is not None
        # Not used by any tool, so it stays lazy.
        assert caches.serialised_schema_cache._value is None


class TestServerLifespan:
    async def test_http_server_warms_caches_before_serving(self, schema_factory, graphql_schema):
        schema_factory.return_value = graphql_schema
        server = await create_server()
        async with Client(server):
            schema_factory.assert_awaited_once()
            assert caches.category_subschemas_cache._value is not None

    async def test_warm_up_failure_does_not_prevent_startup(self, schema_factory, graphql_schema, caplog):
        schema_factory.side_effect = ConnectionError("Platform API unreachable")
        server = await create_server()
        with caplog.at_level(logging.WARNING):
            async with Client(server) as client:
                assert caches.schema_cache._value is None
                assert any("Failed to warm schema caches" in r.message for r in caplog.records)

                # Falls back to lazy population once the API is reachable again.
                schema_factory.side_effect = None
                schema_factory.return_value = graphql_schema
                result = await client.call_tool("get_type_dependencies", {"type_names": ["Target"]})
                assert "Target" in result.data

    async def test_stdio_server_does_not_warm_caches(self, schema_factory, stdio_transport):
        server = await create_server()
        async with Client(server):
            schema_factory.assert_not_awaited()
