# Durable Execution for Agentic Runtime

**Date:** 2026-02-17
**Status:** Brainstorm
**Scope:** Durable execution (checkpoint + resume + idempotency) as the foundational layer, with security/permissions and verification gates to follow

---

## What We're Building

A **hook-based event journal** that gives the agentic-runtime production-grade durability: checkpoint after every LLM response and tool result, resume from the last good state after crashes, and skip already-completed side effects on replay via idempotency keys.

The system adds a `DurableExecutionPolicy` to `AgentSpec`. When enabled, it transparently instruments the existing `build_agent()` / `build_workflow()` paths -- no new entrypoints, no breaking changes.

### Core components

1. **RunJournal** -- SQLite-backed event log (`run_events` table in the existing `tmp/agents.db`). Records tool_call_start, tool_call_complete, llm_response_complete events with idempotency keys and serialized results.

2. **Durable tool hooks** -- Leverages Agno's existing `tool_hooks` mechanism. Before a tool executes, the hook checks the journal for a matching idempotency key. If found, returns the cached result without re-executing. If not found, executes and journals the result.

3. **LLM call wrapper** -- A thin wrapper around `agent.run()` that journals LLM responses at call boundaries. On replay, serves cached LLM responses instead of re-calling the API.

4. **DurableExecutionPolicy** -- New policy on `AgentSpec` controlling: enabled flag, journal path, replay mode (strict/lenient), checkpoint granularity, idempotency key generation strategy.

### What it enables

- **Crash recovery**: Agent runs resume from the last checkpoint, not from scratch
- **Safe retries**: Idempotency keys prevent duplicate git commits, file writes, MCP calls, or any side-effecting tool invocation
- **Audit trail**: The journal doubles as a tamper-evident log of everything the agent did (foundation for security/observability later)
- **Replay debugging**: Re-run a failed run deterministically by replaying the journal

---

## Why This Approach

### Chosen: Hook-Based Event Journal (Approach A)

Uses Agno's existing `tool_hooks` to intercept tool calls plus a light `agent.run()` wrapper for LLM boundaries. Writes to SQLite.

**Why it won over alternatives:**

- **vs. Event-Sourced Workflow (Approach B):** B only checkpoints at workflow step boundaries (coarse). We want LLM+tool granularity for maximum durability. A step could involve 10+ tool calls; losing all of them on crash is unacceptable for long-running coding agents.

- **vs. Middleware Chain (Approach C):** C is more composable but wrapping every tool function changes signatures and may conflict with Agno's internal dispatch. A achieves the same granularity through hooks, which Agno already supports.

**Key tradeoff accepted:** LLM response caching requires wrapping `agent.run()`, which sits slightly outside the hook model. This is a thin wrapper, not a rewrite -- it calls through to Agno and journals the response.

---

## Key Decisions

1. **Stay on Agno** -- No framework rewrite. Durable execution is layered on top via hooks and wrappers.

2. **SQLite journal** -- Extend existing `tmp/agents.db` with a `run_events` table. No new infrastructure dependency (no Temporal, no Redis, no external queue).

3. **LLM + tool boundary granularity** -- Checkpoint after every LLM response and every tool result. This is the finest practical granularity while staying on Agno.

4. **Uniform idempotency** -- All side-effecting tools get idempotency keys equally (git, files, MCP, Daytona). No special-casing. Key = hash(run_id + step_index + tool_name + serialized_args).

5. **Transparent upgrade** -- New `DurableExecutionPolicy` on `AgentSpec`. When enabled, `build_agent()` automatically instruments hooks and wraps `agent.run()`. Existing code works unchanged when disabled.

6. **Durable execution ships first** -- Security/permissions and verification gates come after, and will use the journal as their recording mechanism.

---

## Constraints and Boundaries

- **Agno is a black box for the agent loop**: We can hook tool dispatch and wrap `agent.run()`, but we cannot modify Agno's internal LLM-call-to-tool-dispatch cycle. Checkpointing within a single `agent.run()` turn relies on hooks seeing every tool call.

- **Replay fidelity**: Replay assumes deterministic tool routing from Agno. If the LLM generates different tool calls on replay (because the cached LLM response is served), the journal must detect divergence and either warn or re-execute.

- **Journal size**: At LLM+tool granularity, a long-running coding session could generate thousands of events. Need a retention/compaction strategy (e.g., archive completed runs, keep only latest N runs in hot storage).

- **Concurrency**: Single-agent runs are sequential (Agno loops are synchronous). Multi-agent teams may have concurrent tool calls -- the journal must handle concurrent writes safely (SQLite WAL mode).

---

## Resolved Questions

1. **Agno hook coverage**: Unknown whether `tool_hooks` fire for all tool types (MCP, Daytona, Knowledge) or only `@tool`-decorated functions. **Action:** Investigate Agno source or test empirically during planning. If hooks don't cover all types, add a fallback wrapper at the tool-builder level in `_build_tools()`.

2. **Journal schema versioning**: Store `schema_version` in the journal table. On read, check version and apply migrations if needed. Keep it lightweight (not Alembic-scale) but robust enough for production.

3. **Partial tool results**: Configurable via `DurableExecutionPolicy.retry_on_partial_failure` (boolean). Default: re-execute (mark as "in_flight", retry on resume with idempotency key). Operators can set to `False` to treat partial failures as errors and let the LLM decide next steps.

## Open Questions

1. **LLM response interception**: What does `agent.run()` return exactly? Is the full LLM response (including tool_calls metadata) accessible for journaling, or only the final text output? This affects replay fidelity. **Action:** Investigate Agno's `RunResponse` object during planning phase.

---

## Future Layers (Not In Scope Now)

These will build on the event journal foundation:

- **Security/permissions**: Journal records authorization decisions. Tool allowlists reference journal events for audit. `require_confirmation_for_destructive` checks emit approval events.
- **Verification gates**: Gate events (lint_pass, test_pass) recorded in journal. Workflow blocks on gate failure. Test traces fed back to LLM.
- **Operator controls**: Pause/resume reads journal state. Cancel marks run as terminated. Step-level approvals become journal events requiring external input.
