# Agent Instructions

This project uses **bd** (beads) for issue tracking. Run `bd onboard` to get started.

## Quick Reference

```bash
bd ready              # Find available work
bd show <id>          # View issue details
bd update <id> --status in_progress  # Claim work
bd close <id>         # Complete work
bd sync               # Sync with git
```

---

## 1. Project Purpose

**Agentic Runtime** is a state-of-the-art agentic runtime built on [Agno](https://github.com/agno-agi/agno) framework.

- **Primary users**: Developers building AI agents with code execution, multi-agent teams, and RAG capabilities
- **Core value**: Unified `AgentSpec` configuration for agents, teams, and workflows with Daytona sandbox execution
- **Non-goals**: Not a standalone LLM, not a hosting platform

---

## 2. Tech Stack

- **Language**: Python 3.10+
- **Runtime**: uv (package manager), pytest (testing)
- **Frameworks**: Agno, FastAPI, Pydantic
- **Execution**: Daytona sandbox for isolated code execution
- **Integrations**: OpenRouter (LLM), MCP, LanceDB/Chroma (RAG)

---

## 3. Repository Layout

```
agentic-runtime/
├── core/                    # Main library
│   ├── __init__.py          # Public API exports
│   ├── factory.py           # build_agent, build_team, build_workflow
│   ├── policies.py          # AgentSpec and all policy classes
│   ├── prompts/
│   │   └── system.py        # System prompt templates
│   └── tools/
│       ├── coding.py        # File operations (read, write, edit, grep)
│       ├── git.py           # Git operations (status, diff, log, etc.)
│       ├── daytona.py       # Daytona sandbox integration
│       ├── mcp.py           # MCP tool integration
│       ├── knowledge.py     # RAG/knowledge base tools
│       ├── reasoning.py     # Reasoning tools
│       ├── local.py         # Local utility tools
│       └── hooks.py         # Observability hooks
├── examples/                # Example scripts
│   └── 09_agentic_coding_agent.py  # Agentic coding with Daytona
├── tests/                   # Test suite
└── pyproject.toml           # Project configuration
```

---

## 4. Commands

### Build & Install

```bash
# Basic installation
uv sync

# With knowledge/RAG support
uv sync --extra knowledge

# Full installation (all optional deps)
uv sync --extra full

# Development (includes pytest, ruff)
uv sync --extra dev
```

### Testing

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific test file
uv run pytest tests/test_policies.py

# Run specific test class
uv run pytest tests/test_policies.py::TestCodingPolicy
```

### Linting

```bash
# Check code style
uv run ruff check .

# Auto-fix issues
uv run ruff check --fix .
```

### Running Examples

```bash
# Basic agent
uv run python examples/01_basic_agent.py

# Agentic coding (Daytona sandbox)
uv run python examples/09_agentic_coding_agent.py --mode analyze
uv run python examples/09_agentic_coding_agent.py --repo https://github.com/owner/repo.git --mode interactive
```

---

## 5. Key Patterns

### Creating an Agent

```python
from core import build_agent, AgentSpec, CodeActPolicy

spec = AgentSpec(
    model_id="anthropic/claude-sonnet-4",
    codeact=CodeActPolicy(enabled=True),
)
agent = build_agent(spec)
agent.print_response("Hello", stream=True)
```

### Using Presets

```python
from core import create_coding_spec, build_agent

spec = create_coding_spec(workspace_root=".", enable_codeact=True)
agent = build_agent(spec)
```

### Adding New Tools

1. Create tool file in `core/tools/`
2. Use `@tool` decorator from `agno.tools`
3. Add builder function `build_*_tools(spec)`
4. Import in `core/factory.py`
5. Add to `_build_tools()` function

### Adding New Policies

1. Add policy class to `core/policies.py`
2. Add field to `AgentSpec`
3. Export in `core/__init__.py`
4. Add tests in `tests/test_policies.py`

---

## 6. Environment Variables

```bash
OPENROUTER_API_KEY=...    # Required for LLM access
DAYTONA_API_KEY=...       # Required for sandbox execution
DAYTONA_API_URL=...       # Optional: custom Daytona endpoint
```

---

## 7. Landing the Plane (Session Completion)

**When ending a work session**, you MUST complete ALL steps below. Work is NOT complete until `git push` succeeds.

**MANDATORY WORKFLOW:**

1. **File issues for remaining work** - Create issues for anything that needs follow-up
2. **Run quality gates** (if code changed):
   ```bash
   uv run pytest
   uv run ruff check .
   ```
3. **Update issue status** - Close finished work, update in-progress items
4. **PUSH TO REMOTE** - This is MANDATORY:
   ```bash
   git pull --rebase
   bd sync
   git push
   git status  # MUST show "up to date with origin"
   ```
5. **Clean up** - Clear stashes, prune remote branches
6. **Verify** - All changes committed AND pushed
7. **Hand off** - Provide context for next session

**CRITICAL RULES:**
- Work is NOT complete until `git push` succeeds
- NEVER stop before pushing - that leaves work stranded locally
- NEVER say "ready to push when you are" - YOU must push
- If push fails, resolve and retry until it succeeds
