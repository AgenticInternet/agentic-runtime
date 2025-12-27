"""
Data Analysis Agent Example
---------------------------
Agent with Daytona sandbox for data analysis tasks.
Good for: CSV processing, visualizations, statistics.

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
    # Uses useful model for data tasks: z-ai/glm-4.7
    spec = AgentSpec(
        model_id="z-ai/glm-4.7",
        codeact=CodeActPolicy(enabled=True, max_iterations=10),
        mcp=McpPolicy(enabled=False),
    )

    agent = build_agent(spec)

    # Data analysis task
    agent.print_response(
        """
        Create a sample dataset of 100 sales records with columns:
        - date (random dates in 2024)
        - product (randomly chosen from: Widget, Gadget, Gizmo)
        - quantity (1-50)
        - price (10.0-100.0)
        
        Then analyze:
        1. Total revenue by product
        2. Monthly sales trend
        3. Create a bar chart of revenue by product
        """,
        stream=True,
    )


if __name__ == "__main__":
    main()
