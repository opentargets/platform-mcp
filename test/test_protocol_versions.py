"""Protocol-era tests over the stateless Streamable HTTP transport.

The server must serve both MCP protocol eras from the same endpoint:

- 2026-07-28 ("modern"): no handshake; every request is a self-contained POST
  carrying its protocol version and client info in ``params._meta``, and
  clients open with ``server/discover``.
- 2025-era ("legacy"): ``initialize`` handshake followed by regular requests.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import httpx2
import pytest

MODERN = "2026-07-28"
LEGACY = "2025-06-18"

# Mirrors the probe Claude Code sends when it opens a connection.
MODERN_META = {
    "io.modelcontextprotocol/protocolVersion": MODERN,
    "io.modelcontextprotocol/clientInfo": {"name": "pytest", "version": "0.0.0"},
    "io.modelcontextprotocol/clientCapabilities": {
        "roots": {"listChanged": True},
        "elicitation": {"form": {}, "url": {}},
    },
}

EXPECTED_TOOLS = {
    "batch_query_open_targets_graphql",
    "get_open_targets_graphql_schema",
    "get_type_dependencies",
    "query_open_targets_graphql",
    "search_entities",
}


def _parse(response: httpx2.Response) -> dict[str, Any]:
    """Parse a JSON-RPC response sent either as plain JSON or as SSE."""
    text = response.text.strip()
    if text.startswith("{"):
        return json.loads(text)
    for line in text.splitlines():
        if line.startswith("data:"):
            return json.loads(line.removeprefix("data:"))
    msg = f"Unparseable MCP response: {text!r}"
    raise AssertionError(msg)


@pytest.fixture
async def http_app(mock_gql_session, mock_schema_caches):
    """Build the stateless HTTP app, as served in production."""
    from open_targets_platform_mcp.create_server import create_server

    server = await create_server()
    return server.http_app(stateless_http=True)


@asynccontextmanager
async def _serve(app: Any) -> AsyncIterator[httpx2.AsyncClient]:
    """Run the app lifespan and yield an in-process HTTP client.

    Kept out of the fixture: the lifespan opens an anyio task group, which must
    be entered and exited in the same task (pytest-asyncio runs async fixture
    setup and teardown in different tasks).
    """
    async with app.router.lifespan_context(app):
        transport = httpx2.ASGITransport(app=app)
        async with httpx2.AsyncClient(transport=transport, base_url="http://testserver") as client:
            yield client


async def _post(
    client: httpx2.AsyncClient,
    body: dict[str, Any],
    version: str,
    *,
    modern_headers: bool = False,
) -> httpx2.Response:
    headers = {
        "content-type": "application/json",
        "accept": "application/json, text/event-stream",
        "mcp-protocol-version": version,
    }
    if modern_headers:
        headers["mcp-method"] = body["method"]
        if body["method"] == "tools/call":
            headers["mcp-name"] = body["params"]["name"]
    return await client.post("/mcp", json=body, headers=headers)


class TestModernProtocol:
    async def test_server_discover_succeeds(self, http_app):
        async with _serve(http_app) as http_client:
            response = await _post(
                http_client,
                {
                    "jsonrpc": "2.0",
                    "id": "server-discover-probe-1",
                    "method": "server/discover",
                    "params": {"_meta": MODERN_META},
                },
                MODERN,
                modern_headers=True,
            )

            assert response.status_code == 200
            payload = _parse(response)
            assert "error" not in payload
            result = payload["result"]
            assert MODERN in result["supportedVersions"]
            assert "tools" in result["capabilities"]
            server_info = result["_meta"]["io.modelcontextprotocol/serverInfo"]
            assert server_info["name"].startswith("Model Context Protocol server for Open Targets Platform")

    async def test_tools_list_and_call_without_handshake(self, http_app):
        async with _serve(http_app) as http_client:
            response = await _post(
                http_client,
                {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {"_meta": MODERN_META}},
                MODERN,
                modern_headers=True,
            )
            assert response.status_code == 200
            tools = _parse(response)["result"]["tools"]
            assert {t["name"] for t in tools} == EXPECTED_TOOLS

            response = await _post(
                http_client,
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {
                        "_meta": MODERN_META,
                        "name": "search_entities",
                        "arguments": {"query_strings": ["BRCA1"]},
                    },
                },
                MODERN,
                modern_headers=True,
            )
            assert response.status_code == 200
            result = _parse(response)["result"]
            assert result["isError"] is False
            data = json.loads(result["content"][0]["text"])
            assert data["BRCA1"][0]["id"] == "ENSG00000012048"


class TestLegacyProtocol:
    async def test_initialize_handshake_then_tool_call(self, http_app):
        async with _serve(http_app) as http_client:
            response = await _post(
                http_client,
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": LEGACY,
                        "capabilities": {},
                        "clientInfo": {"name": "pytest-legacy", "version": "0.0.0"},
                    },
                },
                LEGACY,
            )
            assert response.status_code == 200
            result = _parse(response)["result"]
            assert result["protocolVersion"] == LEGACY
            assert result["serverInfo"]["name"].startswith("Model Context Protocol server for Open Targets Platform")

            response = await _post(http_client, {"jsonrpc": "2.0", "method": "notifications/initialized"}, LEGACY)
            assert response.status_code == 202

            response = await _post(
                http_client, {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}, LEGACY
            )
            assert response.status_code == 200
            assert {t["name"] for t in _parse(response)["result"]["tools"]} == EXPECTED_TOOLS

            response = await _post(
                http_client,
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {"name": "search_entities", "arguments": {"query_strings": ["BRCA1"]}},
                },
                LEGACY,
            )
            assert response.status_code == 200
            result = _parse(response)["result"]
            assert result["isError"] is False
            assert json.loads(result["content"][0]["text"])["BRCA1"][0]["id"] == "ENSG00000012048"


@pytest.fixture
def strict_rate_limit():
    """Enable rate limiting with a single token that practically never refills."""
    from open_targets_platform_mcp.settings import settings

    previous = (
        settings.rate_limiting_enabled,
        settings.rate_limiting_max_requests_per_second,
        settings.rate_limiting_burst_capacity,
    )
    settings.rate_limiting_enabled = True
    settings.rate_limiting_max_requests_per_second = 0.0001
    settings.rate_limiting_burst_capacity = 1
    try:
        yield
    finally:
        (
            settings.rate_limiting_enabled,
            settings.rate_limiting_max_requests_per_second,
            settings.rate_limiting_burst_capacity,
        ) = previous


class TestRateLimitingExemptions:
    async def test_negotiation_requests_are_never_rate_limited(self, strict_rate_limit, http_app):
        async with _serve(http_app) as http_client:
            discover = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "server/discover",
                "params": {"_meta": MODERN_META},
            }
            initialize = {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "initialize",
                "params": {
                    "protocolVersion": LEGACY,
                    "capabilities": {},
                    "clientInfo": {"name": "pytest-legacy", "version": "0.0.0"},
                },
            }
            for _ in range(3):
                assert "result" in _parse(await _post(http_client, discover, MODERN, modern_headers=True))
                assert "result" in _parse(await _post(http_client, initialize, LEGACY))

            call = {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"_meta": MODERN_META, "name": "search_entities", "arguments": {"query_strings": ["BRCA1"]}},
            }
            # The single token admits one call; the next one is rate limited.
            assert "result" in _parse(await _post(http_client, call, MODERN, modern_headers=True))
            limited = _parse(await _post(http_client, call, MODERN, modern_headers=True))
            assert "Rate limit exceeded" in json.dumps(limited)
