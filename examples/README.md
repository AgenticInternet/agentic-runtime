# Examples

Progressive examples from basic to advanced usage of the Agentic Runtime.

## Prerequisites

```bash
# Install dependencies
uv sync

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys
```

## Models

| Tier | Model ID | Use Case |
|------|----------|----------|
| Default | `google/gemini-3-flash-preview` | Fast, basic tasks |
| Useful | `z-ai/glm-4.7` | Data analysis, conversations |
| Advanced | `x-ai/grok-code-fast-1` | Complex workflows, coding |
| Alt | `minimax/minimax-m2.1` | Code execution, conversations |

## Examples

| # | File | Features | Description |
|---|------|----------|-------------|
| 01 | `01_basic_agent.py` | Basic | Simple Q&A, no sandbox |
| 02 | `02_code_execution_agent.py` | CodeAct | Run Python code in Daytona |
| 03 | `03_data_analysis_agent.py` | CodeAct | Data analysis & charts |
| 04 | `04_mcp_agent.py` | MCP | External MCP tools |
| 05 | `05_full_featured_agent.py` | All | Complex workflows |
| 06 | `06_conversational_session.py` | Session | Interactive chat |
| 07 | `07_structured_output.py` | Structured | Validated Pydantic responses |
| 08 | `08_multi_agent_team.py` | Teams | Multi-agent coordination |

## Running Examples

```bash
# From project root
uv run python examples/01_basic_agent.py
uv run python examples/02_code_execution_agent.py
uv run python examples/07_structured_output.py
uv run python examples/08_multi_agent_team.py
# etc.
```

## New Features (v0.2.0)

### Structured Output
```python
from pydantic import BaseModel
from core import build_agent, AgentSpec

class MySchema(BaseModel):
    name: str
    value: int

spec = AgentSpec().with_output_schema(MySchema)
agent = build_agent(spec)
response = agent.run("Extract data...")
# response.content is now a validated MySchema instance
```

### Multi-Agent Teams
```python
from core import build_team, AgentSpec, AgentRole, TeamPolicy

members = [
    AgentRole(name="researcher", role="Research topics"),
    AgentRole(name="writer", role="Write content"),
]

spec = AgentSpec(
    team=TeamPolicy(enabled=True, members=members)
)
team = build_team(spec)
team.print_response("Research and write about AI...")
```

### Reasoning
```python
from core import build_agent, AgentSpec, ReasoningPolicy

spec = AgentSpec(
    reasoning=ReasoningPolicy(enabled=True, mode="extended")
)
agent = build_agent(spec)
# Agent now uses chain-of-thought reasoning
```

### Knowledge Base (RAG)
```python
from core import build_agent, AgentSpec, KnowledgePolicy

spec = AgentSpec(
    knowledge=KnowledgePolicy(
        enabled=True,
        vector_db="lancedb",
        content_sources=["https://docs.example.com"],
    )
)
agent = build_agent(spec)
# Agent can now search the knowledge base
```

## Sandbox Lifecycle

- Sandbox auto-stops after **5 minutes** of inactivity
- Sandbox persists across calls within a session
- No manual cleanup needed

## Policy Reference

See `core/policies.py` for all available configuration options:

- `ContextPolicy` - Memory and history settings
- `ToolPolicy` - Tool execution behavior
- `CodeActPolicy` - Daytona sandbox settings
- `McpPolicy` - MCP integration
- `KnowledgePolicy` - RAG/vector database
- `ReasoningPolicy` - Chain-of-thought
- `StructuredOutputPolicy` - Pydantic schemas
- `TeamPolicy` - Multi-agent teams
- `WorkflowPolicy` - Workflow orchestration
- `ObservabilityPolicy` - Logging and metrics
- `SystemPromptPolicy` - Prompt templates
