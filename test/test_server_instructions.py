"""Tests for the server instructions sent in the initialize response."""

from __future__ import annotations

import pytest


class TestServerInstructions:
    @pytest.mark.asyncio
    async def test_instructions_are_sent(self, mcp_client_no_jq):
        instructions = mcp_client_no_jq.initialize_result.instructions

        assert instructions
        assert "search_entities" in instructions

    @pytest.mark.asyncio
    async def test_instructions_mention_every_registered_tool(self, mcp_client_no_jq):
        instructions = mcp_client_no_jq.initialize_result.instructions
        tool_names = {tool.name for tool in await mcp_client_no_jq.list_tools()}

        referenced = {name for name in tool_names if f"`{name}`" in instructions}
        assert referenced == tool_names
