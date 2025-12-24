"""
MCP Tools Agent Example
-----------------------
Agent with Model Context Protocol (MCP) tools.
Good for: External integrations, custom tool servers.

Requirements:
- MCP server URL configured
"""

from dotenv import load_dotenv

load_dotenv()

from core import build_agent
from core.policies import AgentSpec, CodeActPolicy, McpPolicy


def main():
    # Uses default model: google/gemini-3-flash-preview
    spec = AgentSpec(
        codeact=CodeActPolicy(enabled=False),
        mcp=McpPolicy(
            enabled=True,
            transport="streamable-http",
            url="http://localhost:8080/mcp",  # Your MCP server URL
        ),
    )

    agent = build_agent(spec)
    agent.print_response("List available tools from the MCP server", stream=True)


if __name__ == "__main__":
    main()
