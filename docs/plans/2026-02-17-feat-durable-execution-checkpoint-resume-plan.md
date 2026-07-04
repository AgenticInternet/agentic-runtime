---
title: "feat: Add Durable Execution with Checkpoint, Resume, and Idempotency"
type: feat
status: active
date: 2026-02-17
brainstorm: docs/brainstorms/2026-02-17-durable-execution-brainstorm.md
---

# feat: Add Durable Execution with Checkpoint, Resume, and Idempotency

## Overview

Add production-grade durable execution to the agentic-runtime: automatic checkpointing after every tool call and LLM response, crash-safe resume from the last good state, and idempotency keys that prevent duplicate side effects on replay. The system is transparent -- a new `DurableExecutionPolicy` on `AgentSpec` activates it without API changes.

## Problem Statement

Long-running agent sessions (coding agents, multi-step workflows, team coordination) are fragile:

- **Crash = total loss**: A crash mid-session discards all progress. The agent must restart from scratch, re-calling the LLM and re-executing all tools.
- **Unsafe retries**: Restarting a failed session can duplicate side effects -- double git commits, duplicate file writes, repeated MCP API calls.
- **No audit trail**: There is no durable record of what the agent did, making debugging and compliance difficult.
- **No replay capability**: Failed runs cannot be replayed deterministically for debugging.

The existing SQLite session storage (`tmp/agents.db` via Agno's `SqliteDb`) only persists conversation history and memories -- not individual tool/LLM execution events.

## Proposed Solution

A **hook-based event journal** layered on top of Agno:

1. **RunJournal** -- SQLite table (`run_events`) recording every tool call and LLM response with idempotency keys and serialized results.
2. **Durable tool hook** -- An Agno `tool_hook` that checks the journal before execution and short-circuits with cached results on replay.
3. **DurableRunner** -- A thin wrapper around `agent.run()` that journals `RunOutput` at run boundaries and handles resume orchestration.
4. **DurableExecutionPolicy** -- New policy on `AgentSpec` controlling all durability behavior.

## Technical Approach

### Architecture

```
User Code
    |
    v
AgentSpec(durability=DurableExecutionPolicy(enabled=True))
    |
    v
build_agent(spec) / build_workflow(spec)
    |
    ├── Injects durable_tool_hook into agent.tool_hooks
    ├── Creates RunJournal (SQLite table via shared db_engine)
    └── Wraps agent.run() in DurableRunner
            |
            v
        DurableRunner.run(message)
            |
            ├── Check journal for completed run with same idempotency key
            │   ├── Found → return cached RunOutput (skip LLM call entirely)
            │   └── Not found → call agent.run()
            │       |
            │       ├── Tool call dispatched by Agno
            │       │   └── durable_tool_hook intercepts
            │       │       ├── Check journal for matching tool idempotency key
            │       │       │   ├── Found → return cached result (short-circuit)
            │       │       │   └── Not found → journal "in_flight", execute, journal result
            │       │       └── Return result to Agno loop
            │       |
            │       └── RunOutput returned
            │           └── Journal run_completed event with full RunOutput
            |
            v
        Return RunOutput to user
```

### Key Agno Integration Points (Verified from Source)

1. **`tool_hooks`** (Agno `Function.tool_hooks`): Middleware chain using `functools.reduce`. Hooks receive `function_name`, `function_call` (next in chain), `arguments`, `agent`, `run_context`, `session_state`. **Can short-circuit** by returning a value without calling `function_call()`. Fires for ALL tool types (MCPTools, DaytonaTools, KnowledgeTools -- all extend `Toolkit`).

2. **`RunOutput`** (Agno `agno.run.agent.RunOutput`): Dataclass returned by `agent.run()`. Contains `messages: List[Message]`, `tools: List[ToolExecution]` (with `tool_name`, `tool_args`, `result`, `metrics`), `metrics: Metrics` (tokens, cost, duration), `run_id`, `session_id`. Full audit trail in a single object.

3. **`SqliteDb`** (Agno `agno.db.sqlite.SqliteDb`): Uses SQLAlchemy. Exposes `db_engine` and `Session` factory. We can create custom tables on the same engine without touching Agno's tables.

4. **No per-LLM-call hook**: Agno has `pre_hooks` (before run loop) and `post_hooks` (after run completes) but no per-model-call interception. The `DurableRunner` wrapper addresses this at the `agent.run()` boundary.

### Implementation Phases

#### Phase 1: Foundation -- RunJournal + DurableExecutionPolicy

New files and modifications to establish the journal and policy.

**Tasks:**
- [x] Create `core/durability/__init__.py` -- package for all durability code
- [x] Create `core/durability/policy.py` -- `DurableExecutionPolicy` Pydantic model
- [x] Create `core/durability/journal.py` -- `RunJournal` class (SQLite table management)
- [x] Create `core/durability/keys.py` -- Idempotency key generation
- [x] Add `durability: DurableExecutionPolicy` field to `AgentSpec` in `core/policies.py`
- [x] Export new types in `core/__init__.py`
- [x] Add tests in `tests/test_durability.py`

**Success criteria:**
- DurableExecutionPolicy validates correctly with default values
- RunJournal creates `run_events` table on the shared SQLite engine
- Events can be written and read back with correct idempotency keys
- Schema version is stored and checked

**Estimated files:**

```python
# core/durability/policy.py
class DurableExecutionPolicy(BaseModel):
    model_config = {"extra": "forbid"}

    enabled: bool = False
    journal_db_file: Optional[str] = None  # None = use agent's db
    replay_mode: str = "strict"  # "strict" (fail on divergence) | "lenient" (warn and continue)
    retry_on_partial_failure: bool = True  # Re-execute in_flight tools on resume
    max_journal_events: int = 10000  # Retention limit per run
    schema_version: int = 1
```

```python
# core/durability/journal.py
class RunJournal:
    """SQLite-backed event journal for durable execution."""

    def __init__(self, engine: Engine, schema_version: int = 1): ...

    def record_tool_start(self, run_id: str, idempotency_key: str,
                          tool_name: str, tool_args: dict) -> int: ...

    def record_tool_complete(self, event_id: int, result: str,
                             status: str = "completed") -> None: ...

    def record_run_complete(self, run_id: str, idempotency_key: str,
                            run_output: dict) -> None: ...

    def lookup_tool_result(self, idempotency_key: str) -> Optional[str]: ...

    def lookup_run_output(self, idempotency_key: str) -> Optional[dict]: ...

    def get_in_flight_events(self, run_id: str) -> List[dict]: ...

    def compact(self, run_id: str) -> int: ...
```

```python
# core/durability/keys.py
import hashlib, json

def tool_idempotency_key(run_id: str, step_index: int,
                         tool_name: str, tool_args: dict) -> str:
    """Generate deterministic idempotency key for a tool call."""
    payload = json.dumps({
        "run_id": run_id,
        "step": step_index,
        "tool": tool_name,
        "args": tool_args,
    }, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:32]

def run_idempotency_key(run_id: str, input_content: str) -> str:
    """Generate idempotency key for an agent.run() call."""
    payload = json.dumps({
        "run_id": run_id,
        "input": input_content,
    }, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:32]
```

**SQLite schema (`run_events` table):**

```sql
CREATE TABLE IF NOT EXISTS run_events (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    schema_version  INTEGER NOT NULL DEFAULT 1,
    run_id          TEXT NOT NULL,
    session_id      TEXT,
    event_type      TEXT NOT NULL,  -- 'tool_start', 'tool_complete', 'run_complete'
    idempotency_key TEXT NOT NULL,
    tool_name       TEXT,
    tool_args       TEXT,           -- JSON serialized
    result          TEXT,           -- JSON serialized result or RunOutput
    status          TEXT NOT NULL DEFAULT 'in_flight',  -- 'in_flight', 'completed', 'failed'
    error           TEXT,
    created_at      REAL NOT NULL,
    completed_at    REAL,
    UNIQUE(idempotency_key, event_type)
);

CREATE INDEX IF NOT EXISTS idx_run_events_run_id ON run_events(run_id);
CREATE INDEX IF NOT EXISTS idx_run_events_idempotency ON run_events(idempotency_key);
CREATE INDEX IF NOT EXISTS idx_run_events_status ON run_events(status);
```

#### Phase 2: Durable Tool Hook

Wire the journal into Agno's tool execution chain.

**Tasks:**
- [x] Create `core/durability/hooks.py` -- `build_durable_tool_hook(journal, run_state)` function
- [x] Modify `core/factory.py` `_build_tool_hooks()` to inject the durable hook when policy is enabled
- [x] Handle `tool_hooks` composition (durable hook + existing observability hooks)
- [x] Handle `in_flight` event cleanup on resume (re-execute or mark failed per policy)
- [ ] Add integration tests with mock tools

**Success criteria:**
- Tool calls are journaled with correct idempotency keys
- On replay, cached tool results are returned without re-execution
- `in_flight` events are handled according to `retry_on_partial_failure` setting
- Existing observability hooks continue to work alongside the durable hook

**Key implementation:**

```python
# core/durability/hooks.py

def build_durable_tool_hook(journal: RunJournal, run_state: RunState):
    """Build an Agno tool_hook that provides durable execution.

    This hook checks the journal before executing a tool. If a result
    exists for the same idempotency key, it returns the cached result
    without calling the tool (short-circuit). Otherwise, it records
    the call, executes, and journals the result.
    """
    def durable_tool_hook(function_name: str, function_call, arguments: dict):
        key = tool_idempotency_key(
            run_id=run_state.run_id,
            step_index=run_state.increment_step(),
            tool_name=function_name,
            tool_args=arguments,
        )

        # Check cache
        cached = journal.lookup_tool_result(key)
        if cached is not None:
            return cached

        # Record start
        event_id = journal.record_tool_start(
            run_id=run_state.run_id,
            idempotency_key=key,
            tool_name=function_name,
            tool_args=arguments,
        )

        # Execute
        try:
            result = function_call(**arguments)
            journal.record_tool_complete(event_id, str(result), status="completed")
            return result
        except Exception as e:
            journal.record_tool_complete(event_id, str(e), status="failed")
            raise

    return durable_tool_hook
```

```python
# core/durability/state.py

@dataclass
class RunState:
    """Mutable state tracked during a durable run."""
    run_id: str
    session_id: Optional[str] = None
    step_counter: int = 0

    def increment_step(self) -> int:
        self.step_counter += 1
        return self.step_counter
```

#### Phase 3: DurableRunner (Run-Level Journaling + Resume)

Wrap `agent.run()` to journal at the LLM response boundary and support resume.

**Tasks:**
- [x] Create `core/durability/runner.py` -- `DurableRunner` class
- [x] Modify `core/factory.py` `build_agent()` to return a `DurableRunner`-wrapped agent when policy is enabled
- [x] Implement resume logic: detect existing journal events for the run, replay completed tools via hook, continue from last checkpoint
- [x] Handle `in_flight` cleanup on startup (resolve partial failures)
- [ ] Add integration tests with crash simulation

**Success criteria:**
- `agent.run()` return value (`RunOutput`) is journaled with full content
- Resuming a run with the same `run_id` skips completed work
- `in_flight` events are resolved per policy on resume
- API surface is unchanged for callers (`agent.run()` still works normally)

**Key implementation:**

```python
# core/durability/runner.py

class DurableRunner:
    """Wraps an Agno Agent to provide durable execution.

    Journals RunOutput after each agent.run() call and supports
    resume from the last checkpoint.
    """

    def __init__(self, agent: Agent, journal: RunJournal,
                 policy: DurableExecutionPolicy):
        self.agent = agent
        self.journal = journal
        self.policy = policy
        self.run_state = RunState(
            run_id=agent.run_id or str(uuid4()),
            session_id=agent.session_id,
        )

    def run(self, message: str, **kwargs) -> RunOutput:
        """Run with durability: check journal, execute, journal result."""
        key = run_idempotency_key(self.run_state.run_id, message)

        # Check for completed run
        cached = self.journal.lookup_run_output(key)
        if cached is not None:
            return self._deserialize_run_output(cached)

        # Resolve any in_flight tool events from a prior crash
        self._resolve_in_flight_events()

        # Execute (tool_hooks handle per-tool journaling)
        run_output = self.agent.run(message, **kwargs)

        # Journal the completed run
        self.journal.record_run_complete(
            run_id=self.run_state.run_id,
            idempotency_key=key,
            run_output=self._serialize_run_output(run_output),
        )

        return run_output

    def _resolve_in_flight_events(self):
        """Handle tool calls that were in_flight when a crash occurred."""
        in_flight = self.journal.get_in_flight_events(self.run_state.run_id)
        for event in in_flight:
            if self.policy.retry_on_partial_failure:
                # Will be re-executed naturally (key won't match completed)
                self.journal.mark_event_retrying(event["id"])
            else:
                self.journal.record_tool_complete(
                    event["id"], "Marked as failed after crash", status="failed"
                )

    def resume(self, message: str, **kwargs) -> RunOutput:
        """Explicitly resume a prior run. Alias for run() with same semantics."""
        return self.run(message, **kwargs)
```

#### Phase 4: Factory Integration + Workflow Support

Wire everything into the existing factory functions.

**Tasks:**
- [x] Modify `build_agent()` in `core/factory.py` to create `RunJournal` and `DurableRunner` when `spec.durability.enabled`
- [ ] Modify `build_workflow()` to journal at step boundaries (step_started, step_completed events)
- [ ] Modify `build_team()` to enable WAL mode for concurrent journal writes
- [x] Update preset functions to optionally enable durability
- [x] Add `create_durable_coding_spec()` preset
- [x] Update `core/__init__.py` exports

**Success criteria:**
- `build_agent(spec)` with durability enabled returns a durable agent transparently
- Workflows checkpoint at both step and tool granularity
- Team execution with concurrent agents writes safely to journal
- Existing specs without durability work unchanged (backward compatible)

**Key factory changes:**

```python
# core/factory.py (modifications to build_agent)

def build_agent(spec: AgentSpec) -> Agent:
    # ... existing code ...
    agent = Agent(
        model=OpenRouter(id=spec.model_id),
        tools=tools,
        tool_hooks=_build_hooks(spec),  # includes durable hook if enabled
        db=db,
        # ... rest of config ...
    )

    if spec.durability.enabled:
        journal = RunJournal(
            engine=db.db_engine,
            schema_version=spec.durability.schema_version,
        )
        runner = DurableRunner(agent, journal, spec.durability)
        # Attach runner to agent for transparent access
        agent._durable_runner = runner
        agent._original_run = agent.run
        # Monkey-patch or use a wrapper -- see implementation notes
    return agent
```

**Implementation note on wrapping `agent.run()`:** Rather than monkey-patching, the cleaner approach is to return a `DurableAgent` wrapper that delegates to the underlying `Agent` but intercepts `run()` and `print_response()`. This preserves the Agno Agent interface while adding durability.

```python
# core/durability/agent.py

class DurableAgent:
    """Wrapper that adds durable execution to an Agno Agent."""

    def __init__(self, agent: Agent, runner: DurableRunner):
        self._agent = agent
        self._runner = runner

    def run(self, message, **kwargs):
        return self._runner.run(message, **kwargs)

    def print_response(self, message, **kwargs):
        # For streaming, journal after completion
        return self._agent.print_response(message, **kwargs)

    def __getattr__(self, name):
        return getattr(self._agent, name)
```

## Alternative Approaches Considered

1. **Temporal SDK**: Full durable workflow engine. Rejected because it adds infrastructure dependency (Temporal server) and changes the execution model fundamentally. Overkill for a library that runs as scripts.

2. **Event-Sourced Workflow Runner**: Step-level checkpoints only. Rejected because a single `agent.run()` can involve 10+ tool calls -- losing all of them on crash is unacceptable.

3. **Middleware Chain wrapping tool functions**: Most composable but changes tool function signatures and may conflict with Agno's internal dispatch. The hook approach achieves the same result within Agno's supported extension mechanism.

## Acceptance Criteria

### Functional Requirements

- [ ] `DurableExecutionPolicy` can be added to any `AgentSpec` with `enabled=True`
- [ ] Tool calls are journaled with idempotency keys in SQLite `run_events` table
- [ ] `RunOutput` is journaled after each `agent.run()` call
- [ ] Resuming a run with the same `run_id` returns cached results without re-executing
- [ ] `in_flight` tool events are resolved on resume per `retry_on_partial_failure` policy
- [ ] Schema version is stored and validated; mismatches produce clear errors
- [ ] Existing code without `durability` enabled works identically (no regressions)
- [ ] Workflow steps are checkpointed at step boundaries
- [ ] Team execution with concurrent agents uses WAL mode for safe concurrent writes

### Non-Functional Requirements

- [ ] Journal writes add <5ms latency per tool call (SQLite is fast for local writes)
- [ ] Journal does not grow unbounded: `max_journal_events` triggers compaction
- [ ] No new infrastructure dependencies (SQLite only)
- [ ] Thread-safe for concurrent team execution

### Quality Gates

- [ ] Unit tests for RunJournal CRUD operations
- [ ] Unit tests for idempotency key generation (deterministic, collision-free)
- [ ] Unit tests for DurableExecutionPolicy validation
- [ ] Integration test: normal run with durability enabled journals all events
- [ ] Integration test: simulated crash + resume skips completed tools
- [ ] Integration test: `in_flight` cleanup on resume (both retry and fail modes)
- [ ] Integration test: idempotent replay produces identical results
- [ ] All existing tests pass (backward compatibility)
- [ ] `ruff check .` passes

## Dependencies & Prerequisites

- Agno `tool_hooks` must fire for all tool types (verified from source: yes)
- Agno `RunOutput` must be serializable (verified: has `to_dict()` / `from_dict()`)
- Agno `SqliteDb` must expose `db_engine` for custom tables (verified: yes)
- No new pip dependencies required (SQLAlchemy already in stack via Agno)

## Risk Analysis & Mitigation

| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| Agno updates break tool_hooks contract | High | Low | Pin agno version; add integration test that exercises hooks |
| Journal corruption on crash mid-write | Medium | Low | SQLite WAL mode + transactions per event; fsync on commit |
| Idempotency key collisions | High | Very Low | SHA-256 hash of deterministic payload; include run_id for isolation |
| Step counter drift on replay | Medium | Medium | Reset step counter on resume; validate against journal sequence |
| Large RunOutput serialization overhead | Low | Medium | Truncate large tool results (reuse existing ToolPolicy.max_result_chars) |
| `print_response()` streaming vs journaling | Medium | High | Journal after stream completes; accept that streaming runs have coarser checkpoints (run-level, not token-level) |

## Future Considerations

These build on the event journal foundation (not in scope for this plan):

- **Security/permissions**: Journal records authorization decisions. Tool allowlists emit approval events. `require_confirmation_for_destructive` checks become journal events.
- **Verification gates**: Gate events (lint_pass, test_pass) recorded in journal. Workflow blocks on gate failure.
- **Operator controls**: Pause/resume reads journal state. Cancel marks run as terminated.
- **Remote journal**: Swap SQLite for PostgreSQL or event stream (Kafka) for distributed deployments.

## References & Research

### Internal References

- Brainstorm: `docs/brainstorms/2026-02-17-durable-execution-brainstorm.md`
- Factory pattern: `core/factory.py:77` (`build_agent`)
- Existing hooks: `core/tools/hooks.py` (observability hooks pattern)
- Policy convention: `core/policies.py` (all policies use `model_config = {"extra": "forbid"}`)
- Adding policies guide: `AGENTS.md:147` (4-step process)
- Existing SQLite usage: `core/factory.py:33` (`_ensure_db_dir`)

### Agno Framework (Source-Verified)

- `tool_hooks` chain: `agno/tools/function.py:826-872` (`_build_nested_execution_chain`)
- Hook argument injection: `agno/tools/function.py:790-824` (`_build_hook_args`)
- `RunOutput` definition: `agno/run/agent.py:522` (dataclass with messages, tools, metrics)
- `ToolExecution`: `agno/models/response.py` (tool_name, tool_args, result, metrics)
- `SqliteDb` engine: `agno/db/sqlite/sqlite.py:120` (`self.db_engine: Engine`)
- Agent hook injection: `agno/agent/agent.py:6540-6583` (hooks propagated to all Function objects)

### External References

- Temporal Durable Execution concept: [tweag.io](https://tweag.io/blog/2025-10-23-agentic-coding-intro/)
- Agentic design patterns: [machinelearningmastery](https://machinelearningmastery.com/7-must-know-agentic-ai-design-patterns/)
- Agentic program repair verification: [arxiv](https://arxiv.org/html/2507.18755v1)
