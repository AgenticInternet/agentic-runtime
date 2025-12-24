# Examples

Progressive examples from basic to complex usage.

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

## Examples

| # | File | Model | Description |
|---|------|-------|-------------|
| 01 | `01_basic_agent.py` | default | Simple Q&A, no sandbox |
| 02 | `02_code_execution_agent.py` | default | Run Python code |
| 03 | `03_data_analysis_agent.py` | useful | Data analysis & charts |
| 04 | `04_mcp_agent.py` | default | MCP external tools |
| 05 | `05_full_featured_agent.py` | advanced | Complex workflows |
| 06 | `06_conversational_session.py` | useful | Interactive chat |

## Running Examples

```bash
# From project root
uv run python examples/01_basic_agent.py
uv run python examples/02_code_execution_agent.py
# etc.
```

## Sandbox Lifecycle

- Sandbox auto-stops after **5 minutes** of inactivity
- Sandbox persists across calls within a session
- No manual cleanup needed
