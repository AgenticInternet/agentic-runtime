"""
MCP Tools Agent Example
-----------------------
Agent with Model Context Protocol (MCP) tools.
Good for: External integrations, custom tool servers.

Requirements:
- MCP server URL configured
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from core import build_agent
from core.policies import AgentSpec, CodeActPolicy, McpPolicy


async def main():
    spec = AgentSpec(
        model_id="z-ai/glm-4.7",
        codeact=CodeActPolicy(enabled=False),
        mcp=McpPolicy(
            enabled=True,
            transport="streamable-http",
            url="https://mcp-server-google-se-e9b57459.alpic.live",
        ),
    )

    agent = build_agent(spec)
    await agent.aprint_response("Perform a search about the current groq situation with NVIDIA", stream=True)


if __name__ == "__main__":
    asyncio.run(main())
