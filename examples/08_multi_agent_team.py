"""
Multi-Agent Team Example
------------------------
Team of specialized agents working together on complex tasks.
Good for: Research, content creation, complex analysis.

Requirements:
- OPENROUTER_API_KEY in .env file
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from core import (
    build_team,
    AgentSpec,
    AgentRole,
    TeamPolicy,
    CodeActPolicy,
    ObservabilityPolicy,
)


def main():
    # Define team members with specialized roles
    members = [
        AgentRole(
            name="researcher",
            role="Research and gather information on topics",
            instructions=[
                "Search for accurate, up-to-date information",
                "Cite sources when possible",
                "Focus on factual, verifiable data",
            ],
        ),
        AgentRole(
            name="analyst",
            role="Analyze data and provide insights",
            instructions=[
                "Identify patterns and trends",
                "Provide data-driven conclusions",
                "Consider multiple perspectives",
            ],
        ),
        AgentRole(
            name="writer",
            role="Write clear, engaging content",
            instructions=[
                "Write in a professional but accessible style",
                "Structure content logically",
                "Summarize key points clearly",
            ],
        ),
    ]

    # Create team specification
    # Uses advanced model for complex team coordination: x-ai/grok-code-fast-1
    spec = AgentSpec(
        name="research_team",
        model_id="x-ai/grok-code-fast-1",
        team=TeamPolicy(
            enabled=True,
            members=members,
            mode="coordinate",
            share_member_interactions=True,
            show_members_responses=True,
            leader_instructions=[
                "You are the team leader coordinating research and content creation.",
                "Delegate tasks to the appropriate team members.",
                "First use the researcher to gather information.",
                "Then use the analyst to identify key insights.",
                "Finally use the writer to create the final output.",
            ],
        ),
        codeact=CodeActPolicy(enabled=False),
        observability=ObservabilityPolicy(debug_mode=True),
    )

    # Build and run the team
    team = build_team(spec)

    print("=" * 60)
    print("Multi-Agent Research Team")
    print("=" * 60)

    team.print_response(
        """
        Research the current state of quantum computing in 2024.
        Focus on:
        1. Recent breakthroughs and milestones
        2. Key players (companies and research institutions)
        3. Practical applications emerging
        4. Challenges remaining
        
        Provide a comprehensive but concise summary.
        """,
        stream=True,
    )


if __name__ == "__main__":
    main()
