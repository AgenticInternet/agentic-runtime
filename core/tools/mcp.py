"""
MCP (Model Context Protocol) Tools
==================================
Enhanced MCP integration with multi-server support.
"""

from typing import Any, List

from agno.tools.mcp import MCPTools

from ..policies import AgentSpec


def build_mcp_tools(spec: AgentSpec) -> List[Any]:
    """
    Build MCP tools based on spec configuration.

    Features:
    - Single server or multi-server support
    - Multiple transport types (stdio, SSE, streamable-http)
    - Tool definition caching
    - Configurable timeouts

    Args:
        spec: Agent specification with MCP policy

    Returns:
        List of configured MCPTools
    """
    if not spec.mcp.enabled:
        return []

    tools: List[Any] = []

    # Check for multi-server configuration
    if spec.mcp.servers:
        for server_config in spec.mcp.servers:
            if not server_config.enabled:
                continue

            mcp_tool = MCPTools(
                transport=server_config.transport,
                url=server_config.url,
            )
            tools.append(mcp_tool)
    elif spec.mcp.url:
        # Single server configuration (backward compatible)
        mcp_tool = MCPTools(
            transport=spec.mcp.transport,
            url=spec.mcp.url,
        )
        tools.append(mcp_tool)
    else:
        raise ValueError("MCP enabled but no URL or servers configured")

    return tools
