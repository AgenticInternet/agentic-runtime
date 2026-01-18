# Agentic Runtime

A state-of-the-art agentic runtime built on [Agno](https://github.com/agno-agi/agno) framework with OpenRouter, Daytona sandbox execution, MCP support, RAG, multi-agent teams, and more.

## Features

- **Agentic Coding** - File operations, code search, and git integration for autonomous coding tasks
- **Code Execution** - Secure sandbox via Daytona with stateful code interpreter
- **Multi-Agent Teams** - Coordinate multiple specialized agents with leader delegation
- **Workflows** - Orchestrate complex multi-step tasks with dependencies
- **Knowledge Base (RAG)** - Vector database integration with LanceDB, PgVector, Chroma, Qdrant
- **Structured Output** - Pydantic-validated responses with JSON mode
- **Reasoning** - Chain-of-thought (basic, extended, tools modes)
- **MCP Integration** - Model Context Protocol tools with multi-server support
- **Observability** - Tool hooks, event streaming, logging, and metrics

## Setup

```bash
# Clone and install
cp .env.example .env
# Fill in your API keys (OPENROUTER_API_KEY, DAYTONA_API_KEY)

# Basic installation
uv sync

# With knowledge/RAG support
uv sync --extra knowledge

# Full installation (all vector DBs)
uv sync --extra full

# Development (includes pytest, ruff)
uv sync --extra dev
```

## Quick Start

### Basic Agent

```python
from core import build_agent, AgentSpec

# Uses default model: google/gemini-3-flash-preview
agent = build_agent(AgentSpec())
agent.print_response("What is the capital of France?", stream=True)
```

### Code Execution Agent

```python
from core import build_agent, AgentSpec, CodeActPolicy

spec = AgentSpec(
    codeact=CodeActPolicy(enabled=True, max_iterations=10)
)
agent = build_agent(spec)
agent.print_response("Calculate the first 10 Fibonacci numbers", stream=True)
```

### Structured Output

```python
from pydantic import BaseModel
from core import build_agent, AgentSpec

class Analysis(BaseModel):
    summary: str
    sentiment: str
    confidence: float

spec = AgentSpec().with_output_schema(Analysis)
agent = build_agent(spec)
response = agent.run("Analyze: 'This product is amazing!'")
print(response.content)  # Validated Analysis object
```

### Multi-Agent Team

```python
from core import build_team, AgentSpec, AgentRole, TeamPolicy

members = [
    AgentRole(name="researcher", role="Research topics"),
    AgentRole(name="writer", role="Write content"),
]

spec = AgentSpec(
    team=TeamPolicy(
        enabled=True,
        members=members,
        leader_instructions=["Coordinate research and writing"],
    )
)
team = build_team(spec)
team.print_response("Research and write about quantum computing", stream=True)
```

### With Reasoning

```python
from core import build_agent, AgentSpec, ReasoningPolicy

spec = AgentSpec(
    reasoning=ReasoningPolicy(enabled=True, mode="extended")
)
agent = build_agent(spec)
agent.print_response("Solve this step by step: ...", stream=True)
```

### Agentic Coding Agent (Daytona Sandbox)

```python
from agno.agent import Agent
from agno.models.openrouter import OpenRouter
from agno.tools.daytona import DaytonaTools

# Create an agent that works entirely in an isolated Daytona sandbox
agent = Agent(
    name="coding_agent",
    model=OpenRouter(id="anthropic/claude-sonnet-4"),
    tools=[DaytonaTools(persistent=True, auto_stop_interval=60)],
    instructions=[
        "You work in a Daytona sandbox at /home/daytona.",
        "Clone repos with: git clone <url> /home/daytona/repo",
    ],
)

# Agent clones repo and analyzes code in the sandbox
agent.print_response(
    "Clone https://github.com/user/repo.git, list the structure, and analyze the README",
    stream=True,
)
```

## Configuration

All configuration is done through `AgentSpec` and its policies:

```python
from core import (
    AgentSpec,
    ContextPolicy,
    ToolPolicy,
    CodeActPolicy,
    CodingPolicy,
    McpPolicy,
    KnowledgePolicy,
    ReasoningPolicy,
    TeamPolicy,
    WorkflowPolicy,
    ObservabilityPolicy,
    SystemPromptPolicy,
)

spec = AgentSpec(
    name="my_agent",
    model_id="google/gemini-3-flash-preview",
    
    # Context and memory
    context=ContextPolicy(
        enable_user_memories=True,
        num_history_runs=5,
    ),
    
    # Code execution (Daytona sandbox)
    codeact=CodeActPolicy(
        enabled=True,
        max_iterations=10,
        extract_charts=True,
    ),
    
    # Knowledge base (RAG)
    knowledge=KnowledgePolicy(
        enabled=True,
        vector_db="lancedb",  # lancedb, pgvector, chroma, qdrant
        search_type="hybrid",
    ),
    
    # Reasoning
    reasoning=ReasoningPolicy(
        enabled=True,
        mode="extended",  # basic, extended, tools
    ),
    
    # Agentic coding (local file ops)
    coding=CodingPolicy(
        enabled=True,
        workspace_root="/path/to/project",
        allow_write=True,
        enable_git=True,
    ),
    
    # Observability
    observability=ObservabilityPolicy(
        log_tool_calls=True,
        debug_mode=True,
    ),
)
```

## Presets

Use convenience functions for common configurations:

```python
from core import (
    create_basic_spec,
    create_codeact_spec,
    create_research_spec,
    create_coding_spec,
    create_team_spec,
)

# Basic agent (no code execution)
spec = create_basic_spec()

# Code execution agent (Daytona sandbox)
spec = create_codeact_spec(max_iterations=10)

# Research agent with RAG and extended reasoning
spec = create_research_spec(
    knowledge_sources=["https://docs.example.com"]
)

# Agentic coding agent (file ops + git + code execution)
spec = create_coding_spec(
    workspace_root=".",
    enable_codeact=True,
    allow_write=True,
    allow_git_write=False,
)

# Multi-agent team
from core import AgentRole
spec = create_team_spec(
    members=[
        AgentRole(name="analyst", role="Analyze data"),
        AgentRole(name="reporter", role="Write reports"),
    ]
)
```

## Examples

See the `examples/` directory for complete examples:

| Example | Description |
|---------|-------------|
| `01_basic_agent.py` | Simple Q&A agent |
| `02_code_execution_agent.py` | Code execution with Daytona |
| `03_data_analysis_agent.py` | Data analysis and charts |
| `04_mcp_agent.py` | MCP tool integration |
| `05_full_featured_agent.py` | All features combined |
| `06_conversational_session.py` | Interactive chat |
| `07_structured_output.py` | Pydantic-validated responses |
| `08_multi_agent_team.py` | Multi-agent coordination |
| `09_agentic_coding_agent.py` | Agentic coding with Daytona sandbox |

```bash
# Run basic example
uv run python examples/01_basic_agent.py

# Run agentic coding agent (works in Daytona sandbox with GitHub repos)
uv run python examples/09_agentic_coding_agent.py --mode analyze
uv run python examples/09_agentic_coding_agent.py --mode refactor
uv run python examples/09_agentic_coding_agent.py --mode test
uv run python examples/09_agentic_coding_agent.py --mode feature
uv run python examples/09_agentic_coding_agent.py --mode interactive

# Use a custom GitHub repository
uv run python examples/09_agentic_coding_agent.py --repo https://github.com/owner/repo.git --branch main
```

## Testing

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific test file
uv run pytest tests/test_policies.py
```

## Architecture

```
core/
├── __init__.py          # Public API exports
├── factory.py           # build_agent, build_team, build_workflow
├── policies.py          # All configuration policies & presets
├── context_manager.py   # Context management utilities
├── settings.py          # Environment settings
├── tool_runtime.py      # Tool runtime utilities
├── prompts/
│   └── system.py        # System prompt templates
└── tools/
    ├── local.py         # Local utility tools
    ├── daytona.py       # Daytona sandbox integration
    ├── coding.py        # File operations & code search
    ├── git.py           # Git integration tools
    ├── mcp.py           # MCP tool integration
    ├── knowledge.py     # RAG/knowledge tools
    ├── reasoning.py     # Reasoning tools
    └── hooks.py         # Observability hooks
```

### Coding Tools

| Tool | Description |
|------|-------------|
| `read_file` | Read file contents with optional line range |
| `write_file` | Create or overwrite files |
| `edit_file` | Edit files by replacing text (single or all occurrences) |
| `list_directory` | List directory contents |
| `find_files` | Find files matching glob patterns |
| `grep` | Regex-based code search with context |
| `get_file_info` | Get file metadata (size, type, etc.) |

### Git Tools

| Tool | Description |
|------|-------------|
| `git_status` | Show working tree status |
| `git_diff` | Show changes between commits or working tree |
| `git_log` | Show commit history |
| `git_branch` | List branches |
| `git_show` | Show commit details |
| `git_blame` | Show line-by-line authorship |
| `git_add` | Stage files (if `allow_git_write=True`) |
| `git_commit` | Create commits (if `allow_git_write=True`) |

### Daytona Sandbox Operations

| Tool | Description |
|------|-------------|
| `run_shell_command` | Execute bash commands (git, ls, grep, etc.) |
| `run_code` | Execute Python code in sandbox |
| `create_file` | Create or update files in sandbox |
| `read_file` | Read file contents from sandbox |
| `list_files` | List directory contents in sandbox |
| `delete_file` | Delete files in sandbox |

## Environment Variables

```bash
OPENROUTER_API_KEY=...    # Required for LLM access
DAYTONA_API_KEY=...       # Required for sandbox execution
DAYTONA_API_URL=...       # Optional: custom Daytona endpoint
```

## License

MIT
