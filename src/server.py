# Copyright (c) 2026 Dedalus Labs, Inc.
# SPDX-License-Identifier: MIT

import os

from dedalus_mcp import MCPServer
from dedalus_mcp.server import TransportSecuritySettings

from supermemory import supermemory, supermemory_tools


def create_server() -> MCPServer:
    """Create MCP server with current env config."""
    as_url = os.getenv("DEDALUS_AS_URL", "https://as.dedaluslabs.ai")
    return MCPServer(
        name="supermemory-mcp",
        connections=[supermemory],
        http_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
        streamable_http_stateless=True,
        authorization_server=as_url,
    )


async def main() -> None:
    """Start MCP server."""
    server = create_server()
    server.collect(*supermemory_tools)
    await server.serve(port=8080)
