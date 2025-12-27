"""
Code Execution Agent Example
----------------------------
Agent with Daytona sandbox for running Python code.
Good for: Data analysis, code generation, computations.

Requirements:
- DAYTONA_API_KEY in .env file
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from core import build_agent
from core.policies import AgentSpec, CodeActPolicy, McpPolicy


def main():
    # Uses fast model for code execution
    spec = AgentSpec(
        model_id="minimax/minimax-m2.1",
        codeact=CodeActPolicy(enabled=True),
        mcp=McpPolicy(enabled=False),
    )

    agent = build_agent(spec)

    # Simple code execution
    agent.print_response(
        "How many r in strawbery, build a code for that specific task using syntax or execution base approach",
        stream=True,
    )


if __name__ == "__main__":
    main()
