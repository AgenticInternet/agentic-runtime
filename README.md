# Agentic Runtime

A state-of-the-art agentic runtime built on [Agno](https://github.com/agno-agi/agno) framework with OpenRouter, Daytona sandbox execution, MCP support, RAG, multi-agent teams, and more.

## Features

- **Multi-Agent Teams** - Coordinate multiple specialized agents
- **Workflows** - Orchestrate complex multi-step tasks
- **Knowledge Base (RAG)** - Vector database integration with LanceDB, PgVector, Chroma
- **Structured Output** - Pydantic-validated responses
- **Reasoning** - Chain-of-thought and extended thinking
- **Code Execution** - Secure sandbox via Daytona
- **MCP Integration** - Model Context Protocol tools
- **Observability** - Tool hooks, logging, and metrics

## Setup

```bash
# Clone and install
cp .env.example .env
# Fill in your API keys (OPENROUTER_API_KEY, DAYTONA_API_KEY)

# Basic installation
uv sync

# With knowledge/RAG support
uv sync --extra knowledge

# Full installation
uv sync --extra full
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

## Configuration

All configuration is done through `AgentSpec` and its policies:

```python
from core import (
    AgentSpec,
    ContextPolicy,
    ToolPolicy,
    CodeActPolicy,
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
    model_id="google/gemini-3-flash-preview",  # or z-ai/glm-4.7, x-ai/grok-code-fast-1
    
    # Context and memory
    context=ContextPolicy(
        enable_user_memories=True,
        num_history_runs=5,
    ),
    
    # Code execution
    codeact=CodeActPolicy(
        enabled=True,
        max_iterations=10,
        extract_charts=True,
    ),
    
    # Knowledge base
    knowledge=KnowledgePolicy(
        enabled=True,
        vector_db="lancedb",
        search_type="hybrid",
    ),
    
    # Reasoning
    reasoning=ReasoningPolicy(
        enabled=True,
        mode="extended",
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
from core import create_basic_spec, create_codeact_spec, create_research_spec

# Basic agent (no tools)
spec = create_basic_spec()

# Code execution agent
spec = create_codeact_spec(max_iterations=10)

# Research agent with RAG
spec = create_research_spec(
    knowledge_sources=["https://docs.example.com"]
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

```bash
uv run python examples/01_basic_agent.py
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
├── factory.py           # Agent/Team/Workflow builders
├── policies.py          # All configuration policies
├── prompts/
│   └── system.py        # System prompt templates
└── tools/
    ├── local.py         # Local utility tools
    ├── daytona.py       # Daytona sandbox tools
    ├── mcp.py           # MCP integration
    ├── knowledge.py     # RAG/knowledge tools
    ├── reasoning.py     # Reasoning tools
    └── hooks.py         # Observability hooks
```

## License

MIT
