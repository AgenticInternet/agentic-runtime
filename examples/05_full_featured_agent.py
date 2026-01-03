"""
Full-Featured Agent Example
---------------------------
Agent with all capabilities: Daytona sandbox + MCP tools + session persistence.
Good for: Complex workflows, multi-step tasks, production use.

Requirements:
- DAYTONA_API_KEY in .env file
- MCP server URL (optional)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from core import build_agent
from core.policies import (
    AgentSpec,
    CodeActPolicy,
    ContextPolicy,
    McpPolicy,
    ToolPolicy,
)


def main():
    # Uses advanced model for complex tasks: x-ai/grok-code-fast-1
    spec = AgentSpec(
        model_id="x-ai/grok-code-fast-1",
        user_id="demo_user_1",
        session_id="demo_session_0012",
        context=ContextPolicy(
            enable_user_memories=True,
            enable_session_summaries=True,
            add_history_to_context=True,
            num_history_runs=5,
        ),
        tools=ToolPolicy(
            timeout_seconds=60.0,
            max_retries=3,
            max_result_chars=32_000,
        ),
        codeact=CodeActPolicy(
            enabled=True,
            max_iterations=15,
        ),
        mcp=McpPolicy(enabled=False),
    )

    agent = build_agent(spec)

    # Multi-step complex task
    agent.print_response(
        """
        I need you to help me with a complete data science workflow:
        
        1. Generate synthetic customer data (500 records) with:
           - customer_id, name, email, signup_date, plan_type, monthly_spend
        
        2. Perform exploratory data analysis:
           - Summary statistics
           - Distribution of plan types
           - Spend patterns by plan type
        
        3. Build a simple prediction:
           - Predict if a customer is high-value (spend > $100)
           - Use logistic regression
           - Report accuracy
        
        4. Create visualizations:
           - Histogram of monthly spend
           - Box plot of spend by plan type
        
        Save all outputs and provide a summary report.
        """,
        stream=True,
    )


if __name__ == "__main__":
    main()
