"""Rate limiting middleware with workarounds for FastMCP quirks."""

from fastmcp.server.middleware.middleware import CallNext, MiddlewareContext
from fastmcp.server.middleware.rate_limiting import RateLimitingMiddleware

# "initialize" (2025-era handshake) and "server/discover" (2026-07-28 era) are
# the protocol negotiation requests. "ping" is exempt because FastMCP >= 4 runs
# middleware for every inbound message, whereas FastMCP 2 never rate limited it.
_EXEMPT_METHODS = frozenset({"initialize", "server/discover", "tools/list", "ping"})


class HandshakeExemptRateLimitingMiddleware(RateLimitingMiddleware):
    """RateLimitingMiddleware that exempts certain MCP handshake methods.

    Originally a workaround for a FastMCP bug where McpError raised during
    'initialize' middleware was reported as INVALID_PARAMS to the client.

    Exempting the negotiation requests ('initialize', 'server/discover') and
    'tools/list' always allows agent clients to register the MCP server.
    """

    async def on_request(self, context: MiddlewareContext, call_next: CallNext) -> object:
        if context.method in _EXEMPT_METHODS:
            return await call_next(context)
        return await super().on_request(context, call_next)
