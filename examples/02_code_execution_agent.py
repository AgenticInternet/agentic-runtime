"""
Code Execution Agent Example
----------------------------
Agent with Daytona sandbox for running Python code.
Good for: Data analysis, code generation, computations.

Requirements:
- DAYTONA_API_KEY in .env file
"""

from dotenv import load_dotenv

load_dotenv()

from core import build_agent
from core.policies import AgentSpec, CodeActPolicy, McpPolicy


def main():
    # Uses default model: google/gemini-3-flash-preview
    spec = AgentSpec(
        codeact=CodeActPolicy(enabled=True),
        mcp=McpPolicy(enabled=False),
    )

    agent = build_agent(spec)

    # Simple code execution
    agent.print_response(
        "Write and run Python code to calculate the first 10 Fibonacci numbers",
        stream=True,
    )


if __name__ == "__main__":
    main()
