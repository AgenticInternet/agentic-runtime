"""
Basic Agent Example
-------------------
Simple agent with local tools only (no sandbox, no MCP).
Good for: Q&A, simple tasks, testing.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from core import build_agent
from core.policies import AgentSpec, CodeActPolicy, McpPolicy


def main():
    # Uses default model: google/gemini-3-flash-preview
    spec = AgentSpec(
        codeact=CodeActPolicy(enabled=False),
        mcp=McpPolicy(enabled=False),
    )

    agent = build_agent(spec)
    agent.print_response("What is the capital of France?", stream=True)


if __name__ == "__main__":
    main()
