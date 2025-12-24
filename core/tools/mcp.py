from agno.tools.mcp import MCPTools

from ..policies import AgentSpec


def build_mcp_tools(spec: AgentSpec):
    if not spec.mcp.url:
        raise ValueError("MCP enabled but mcp.url is not set")
    return [MCPTools(transport=spec.mcp.transport, url=spec.mcp.url)]
