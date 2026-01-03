"""
Agentic Coding Agent Example
----------------------------
Agent with full coding capabilities: file operations, git, and code execution via Daytona.
The agent operates entirely within an isolated Daytona sandbox, cloning GitHub repos
and performing all file operations in that secure environment.

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

from agno.agent import Agent
from agno.models.openrouter import OpenRouter
from agno.tools.daytona import DaytonaTools


def create_sandbox_coding_agent(
    github_repo: str,
    branch: str = "main",
    model_id: str = "anthropic/claude-sonnet-4",
) -> Agent:
    """
    Create an agentic coding agent that works entirely within a Daytona sandbox.
    
    The agent will:
    1. Clone the specified GitHub repository into the sandbox
    2. Perform all file operations (read, write, edit) in the sandbox
    3. Execute code in the sandbox
    4. Run git commands in the sandbox
    
    Args:
        github_repo: GitHub repository URL (e.g., "https://github.com/owner/repo.git")
        branch: Branch to clone (default: "main")
        model_id: OpenRouter model ID
    
    Returns:
        Configured Agent with DaytonaTools
    """
    daytona_tools = DaytonaTools(
        persistent=True,
        auto_stop_interval=60,
        sandbox_env_vars={
            "REPO_URL": github_repo,
            "REPO_BRANCH": branch,
        },
    )

    agent = Agent(
        name="agentic_coding_agent",
        model=OpenRouter(id=model_id),
        tools=[daytona_tools],
        instructions=[
            "You are an expert software engineer working in an isolated Daytona sandbox.",
            "Your workspace is at /home/daytona.",
            "",
            "## Setup Instructions",
            f"1. Clone the repository: git clone -b {branch} {github_repo} /home/daytona/repo",
            "2. Change to the repo directory: cd /home/daytona/repo",
            "3. All file operations should be relative to /home/daytona/repo",
            "",
            "## Available Operations",
            "- run_shell_command: Execute bash commands (git, ls, cat, grep, etc.)",
            "- run_code: Execute Python code",
            "- create_file: Create or update files",
            "- read_file: Read file contents",
            "- list_files: List directory contents",
            "- delete_file: Delete files",
            "",
            "## Best Practices",
            "- Always clone the repo first before any file operations",
            "- Use git commands for version control (git status, git diff, git log)",
            "- Test code changes by running them in the sandbox",
            "- Show file contents before and after edits for verification",
        ],
        markdown=True,
    )

    return agent


def main():
    """Analyze a GitHub repository in an isolated sandbox."""
    github_repo = os.getenv(
        "GITHUB_REPO_URL",
        "https://github.com/AgenticInternet/agentic-runtime.git"
    )
    branch = os.getenv("GITHUB_REPO_BRANCH", "main")

    print("=" * 70)
    print("AGENTIC CODING AGENT - Daytona Sandbox")
    print("=" * 70)
    print(f"Repository: {github_repo}")
    print(f"Branch: {branch}")
    print("Environment: Isolated Daytona Sandbox (/home/daytona)")
    print("=" * 70)

    agent = create_sandbox_coding_agent(
        github_repo=github_repo,
        branch=branch,
        model_id="anthropic/claude-sonnet-4",
    )

    agent.print_response(
        f"""First, clone the repository and then analyze the codebase:

1. Clone {github_repo} (branch: {branch}) into /home/daytona/repo
2. List the main files and directories
3. Read the README.md to understand the project
4. Show the recent git history (last 5 commits)
5. Identify the main modules and their purposes
6. Suggest any potential improvements or issues you notice""",
        stream=True,
    )


def example_refactoring():
    """Example: Clone a repo and refactor code in the sandbox."""
    github_repo = os.getenv(
        "GITHUB_REPO_URL",
        "https://github.com/AgenticInternet/agentic-runtime.git"
    )

    agent = create_sandbox_coding_agent(github_repo=github_repo)

    agent.print_response(
        f"""Clone {github_repo} and perform a code review:

1. Clone the repo to /home/daytona/repo
2. Find all Python files in the project
3. Analyze them for:
   - Code duplication
   - Missing docstrings  
   - Type hint improvements
4. Provide a detailed report with specific file locations""",
        stream=True,
    )


def example_bug_fix():
    """Example: Clone a repo and investigate/fix a bug."""
    github_repo = os.getenv(
        "GITHUB_REPO_URL",
        "https://github.com/AgenticInternet/agentic-runtime.git"
    )

    agent = create_sandbox_coding_agent(github_repo=github_repo)

    agent.print_response(
        f"""Clone {github_repo} and run tests:

1. Clone the repo to /home/daytona/repo
2. Check if there are any test files
3. Install dependencies (look for pyproject.toml or requirements.txt)
4. Run the test suite
5. Report any failing tests and analyze potential causes""",
        stream=True,
    )


def example_feature_implementation():
    """Example: Clone a repo and implement a new feature."""
    github_repo = os.getenv(
        "GITHUB_REPO_URL",
        "https://github.com/AgenticInternet/agentic-runtime.git"
    )

    agent = create_sandbox_coding_agent(github_repo=github_repo)

    agent.print_response(
        f"""Clone {github_repo} and add a new utility function:

1. Clone the repo to /home/daytona/repo
2. Examine the project structure
3. Create a new file: core/tools/utils.py with:
   - A function to format file sizes (bytes to KB/MB/GB)
   - A function to calculate directory sizes recursively
   - Proper docstrings and type hints
4. Show the complete file content
5. Run a quick test of the functions using run_code""",
        stream=True,
    )


def example_interactive():
    """Interactive coding session in the Daytona sandbox."""
    github_repo = os.getenv(
        "GITHUB_REPO_URL",
        "https://github.com/AgenticInternet/agentic-runtime.git"
    )

    agent = create_sandbox_coding_agent(github_repo=github_repo)

    print("=" * 70)
    print("INTERACTIVE CODING SESSION - Daytona Sandbox")
    print(f"Repository: {github_repo}")
    print("Type 'quit' to exit")
    print("=" * 70)

    # Initial setup: clone the repo
    agent.print_response(
        f"Clone {github_repo} to /home/daytona/repo and show the directory structure",
        stream=True,
    )

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

    parser = argparse.ArgumentParser(
        description="Agentic Coding Agent - Works in Daytona Sandbox with GitHub repos"
    )
    parser.add_argument(
        "--mode",
        choices=["analyze", "refactor", "test", "feature", "interactive"],
        default="analyze",
        help="Example mode to run",
    )
    parser.add_argument(
        "--repo",
        type=str,
        default=None,
        help="GitHub repository URL to work with",
    )
    parser.add_argument(
        "--branch",
        type=str,
        default="main",
        help="Branch to clone (default: main)",
    )

    args = parser.parse_args()

    # Set repo from args if provided
    if args.repo:
        os.environ["GITHUB_REPO_URL"] = args.repo
    if args.branch:
        os.environ["GITHUB_REPO_BRANCH"] = args.branch

    if args.mode == "analyze":
        main()
    elif args.mode == "refactor":
        example_refactoring()
    elif args.mode == "test":
        example_bug_fix()
    elif args.mode == "feature":
        example_feature_implementation()
    elif args.mode == "interactive":
        example_interactive()
