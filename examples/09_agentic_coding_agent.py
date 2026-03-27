"""
Agentic Coding Agent Example
----------------------------
Agent with sandboxed coding capabilities using the runtime's AgentSpec/build_agent flow.
The agent operates within a Daytona sandbox, clones GitHub repos, and analyzes or modifies
code inside that isolated environment.

Requirements:
- DAYTONA_API_KEY in `.env`
- OPENROUTER_API_KEY in `.env` (or update the provider policy below)
"""

import argparse
import os

from dotenv import load_dotenv

from core import build_agent
from core.policies import (
    AgentSpec,
    CodeActPolicy,
    McpPolicy,
    ModelProviderPolicy,
    SystemPromptPolicy,
)

load_dotenv()

DEFAULT_REPO = "https://github.com/AgenticInternet/agentic-runtime.git"
SANDBOX_PROMPT = """You are an expert software engineer working in an isolated execution environment.

When solving coding tasks:
1. Use the sandbox tools for shell commands and code execution.
2. Clone repositories into `/home/daytona/repo` unless the user asks for a different path.
3. Inspect the repository before making changes.
4. Verify changes by running tests or targeted commands inside the sandbox.
5. Explain your findings and changes clearly.
"""


def _github_repo() -> str:
    return os.getenv("GITHUB_REPO_URL", DEFAULT_REPO)


def _github_branch() -> str:
    return os.getenv("GITHUB_REPO_BRANCH", "main")


def create_sandbox_coding_agent(model_id: str = "anthropic/claude-sonnet-4"):
    """Create a coding agent that executes through the runtime's Daytona policy."""
    spec = AgentSpec(
        name="agentic_coding_agent",
        model_id=model_id,
        model_provider=ModelProviderPolicy(provider="openrouter"),
        codeact=CodeActPolicy(
            enabled=True,
            sandbox="daytona",
            sandbox_timeout_minutes=60,
        ),
        mcp=McpPolicy(enabled=False),
        system_prompt=SystemPromptPolicy(
            template="custom",
            custom_template=SANDBOX_PROMPT,
        ),
    )
    return build_agent(spec)


def _run_prompt(prompt: str) -> None:
    agent = create_sandbox_coding_agent()
    agent.print_response(prompt, stream=True)


def main() -> None:
    """Analyze a GitHub repository in an isolated Daytona sandbox."""
    github_repo = _github_repo()
    branch = _github_branch()

    print("=" * 70)
    print("AGENTIC CODING AGENT - Daytona Sandbox")
    print("=" * 70)
    print(f"Repository: {github_repo}")
    print(f"Branch: {branch}")
    print("Environment: Isolated Daytona Sandbox (/home/daytona)")
    print("=" * 70)

    _run_prompt(
        f"""First, clone the repository and then analyze the codebase:

1. Clone {github_repo} (branch: {branch}) into /home/daytona/repo
2. List the main files and directories
3. Read the README.md to understand the project
4. Show the recent git history (last 5 commits)
5. Identify the main modules and their purposes
6. Suggest any potential improvements or issues you notice"""
    )


def example_refactoring() -> None:
    """Clone a repo and perform a code review in the sandbox."""
    github_repo = _github_repo()
    _run_prompt(
        f"""Clone {github_repo} and perform a code review:

1. Clone the repo to /home/daytona/repo
2. Find all Python files in the project
3. Analyze them for:
   - Code duplication
   - Missing docstrings
   - Type hint improvements
4. Provide a detailed report with specific file locations"""
    )


def example_bug_fix() -> None:
    """Clone a repo and investigate test failures in the sandbox."""
    github_repo = _github_repo()
    _run_prompt(
        f"""Clone {github_repo} and run tests:

1. Clone the repo to /home/daytona/repo
2. Check if there are any test files
3. Install dependencies (look for pyproject.toml or requirements.txt)
4. Run the test suite
5. Report any failing tests and analyze potential causes"""
    )


def example_feature_implementation() -> None:
    """Clone a repo and sketch a small feature in the sandbox."""
    github_repo = _github_repo()
    _run_prompt(
        f"""Clone {github_repo} and add a new utility function:

1. Clone the repo to /home/daytona/repo
2. Examine the project structure
3. Create a new file: core/tools/utils.py with:
   - A function to format file sizes (bytes to KB/MB/GB)
   - A function to calculate directory sizes recursively
   - Proper docstrings and type hints
4. Show the complete file content
5. Run a quick test of the functions using the sandbox code runner"""
    )


def example_interactive() -> None:
    """Interactive coding session in the Daytona sandbox."""
    github_repo = _github_repo()
    agent = create_sandbox_coding_agent()

    print("=" * 70)
    print("INTERACTIVE CODING SESSION - Daytona Sandbox")
    print(f"Repository: {github_repo}")
    print("Type 'quit' to exit")
    print("=" * 70)

    agent.print_response(
        f"Clone {github_repo} to /home/daytona/repo and show the directory structure",
        stream=True,
    )

    while True:
        try:
            user_input = input("\n> ").strip()
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break

        if user_input.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break
        if not user_input:
            continue

        agent.print_response(user_input, stream=True)


if __name__ == "__main__":
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
