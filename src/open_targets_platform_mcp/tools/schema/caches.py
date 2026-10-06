from graphql import GraphQLSchema, print_schema

from open_targets_platform_mcp.cache import AsyncCache
from open_targets_platform_mcp.client.graphql import fetch_graphql_schema
from open_targets_platform_mcp.settings import settings
from open_targets_platform_mcp.tools.schema.helper import build_type_graph, load_categories
from open_targets_platform_mcp.tools.schema.helper.graph import TypeGraph
from open_targets_platform_mcp.tools.schema.helper.subschema import (
    CategorySubschema,
    CategorySubschemas,
    build_category_subschema,
)

# Caches backing the schema tools are eager: they are warmed at server startup
# (see warm_schema_caches) so the first tool call on a fresh instance does not
# block the event loop while the schema is fetched and processed.
schema_cache = AsyncCache[GraphQLSchema](is_eager=True)
type_graph_cache = AsyncCache[TypeGraph](is_eager=True)
category_subschemas_cache = AsyncCache[CategorySubschemas](is_eager=True)
serialised_schema_cache = AsyncCache[str]()


async def type_graph_cache_factory() -> TypeGraph:
    """Factory to build the type graph cache."""
    return build_type_graph(await schema_cache.get())


async def serialised_schema_cache_factory() -> str:
    """Factory to build the serialised schema cache."""
    schema = await schema_cache.get()
    return print_schema(schema)


async def category_subschemas_cache_factory() -> CategorySubschemas:
    """Factory to build subschemas for all categories."""
    graph = await type_graph_cache.get()
    schema = await schema_cache.get()
    categories = load_categories()

    subschemas: dict[str, CategorySubschema] = {}
    depth = settings.subschema_depth

    for category_name, category_data in categories.items():
        subschemas[category_name] = build_category_subschema(
            category_name,
            category_data,
            graph,
            schema,
            depth,
        )

    return CategorySubschemas(subschemas=subschemas, depth=depth)


schema_cache.set_factory(fetch_graphql_schema)
type_graph_cache.set_factory(type_graph_cache_factory)
serialised_schema_cache.set_factory(serialised_schema_cache_factory)
category_subschemas_cache.set_factory(category_subschemas_cache_factory)


async def warm_schema_caches() -> None:
    """Populate all eager schema caches."""
    for cache in (schema_cache, type_graph_cache, category_subschemas_cache, serialised_schema_cache):
        await cache.warm()
