# Agentic Runtime

Agentic runtime with Agno + OpenRouter, Daytona sandbox execution, and MCP support.

## Setup

```bash
cp .env.example .env
# Fill in your API keys
uv sync --all-extras
```

## Usage

```python
from core import build_agent, AgentSpec

agent = build_agent(AgentSpec())
agent.run("Hello!")
```

## Testing

```bash
uv run pytest
```
