"""
Agentic Coding Agent Example
----------------------------
Agent with full coding capabilities: file operations, git, and code execution via Daytona.
Good for: Code refactoring, bug fixing, feature implementation, code review.

Requirements:
- DAYTONA_API_KEY in .env file
- OPENROUTER_API_KEY in .env file
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from core import build_agent, create_coding_spec
from core.policies import AgentSpec, CodeActPolicy, CodingPolicy, ReasoningPolicy


def main():
    workspace = os.getcwd()
    
    spec = create_coding_spec(
        model_id="anthropic/claude-sonnet-4",
        workspace_root=workspace,
        enable_codeact=True,
        allow_write=True,
        allow_git_write=False,
        max_iterations=10,
    )
    
    agent = build_agent(spec)
    
    print("=" * 60)
    print("AGENTIC CODING AGENT")
    print("=" * 60)
    print(f"Workspace: {workspace}")
    print("Tools: file read/write/edit, grep, git status/diff/log, code execution")
    print("=" * 60)
    
    agent.print_response(
        """Analyze this codebase and:
1. List the main files and their purposes
2. Identify any potential improvements or issues
3. Show the recent git history

Focus on the core/ directory structure.""",
        stream=True,
    )


def example_refactoring():
    """Example: Ask the agent to refactor code."""
    workspace = os.getcwd()
    
    spec = create_coding_spec(
        workspace_root=workspace,
        allow_write=True,
    )
    
    agent = build_agent(spec)
    
    agent.print_response(
        """Find all Python files in core/tools/ and analyze them for:
1. Code duplication
2. Missing docstrings
3. Potential type hint improvements

Provide a summary report.""",
        stream=True,
    )


def example_bug_investigation():
    """Example: Ask the agent to investigate a bug."""
    workspace = os.getcwd()
    
    spec = create_coding_spec(
        workspace_root=workspace,
        enable_codeact=True,
    )
    
    agent = build_agent(spec)
    
    agent.print_response(
        """Write and execute a Python script that:
1. Imports the core module
2. Creates a basic AgentSpec
3. Prints out all the available policies and their default values

Use the Daytona sandbox to run the code.""",
        stream=True,
    )


def example_interactive():
    """Interactive coding session with the agent."""
    workspace = os.getcwd()
    
    spec = create_coding_spec(
        workspace_root=workspace,
        enable_codeact=True,
        allow_write=True,
    )
    
    agent = build_agent(spec)
    
    print("=" * 60)
    print("INTERACTIVE CODING SESSION")
    print("Type 'quit' to exit")
    print("=" * 60)
    
    while True:
        try:
            user_input = input("\n> ").strip()
            if user_input.lower() in ("quit", "exit", "q"):
                print("Goodbye!")
                break
            if not user_input:
                continue
            
            agent.print_response(user_input, stream=True)
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Agentic Coding Agent Examples")
    parser.add_argument(
        "--mode",
        choices=["analyze", "refactor", "debug", "interactive"],
        default="analyze",
        help="Example mode to run",
    )
    
    args = parser.parse_args()
    
    if args.mode == "analyze":
        main()
    elif args.mode == "refactor":
        example_refactoring()
    elif args.mode == "debug":
        example_bug_investigation()
    elif args.mode == "interactive":
        example_interactive()
