"""
Durable Tool Hooks
==================
Agno tool_hook that provides checkpoint and replay for tool calls.
"""

from typing import Any, Callable, Dict

from .journal import RunJournal
from .keys import tool_idempotency_key
from .state import RunState


def build_durable_tool_hook(journal: RunJournal, run_state: RunState) -> Callable:
    """Build an Agno tool_hook that provides durable execution.

    This hook checks the journal before executing a tool. If a result
    exists for the same idempotency key, it returns the cached result
    without calling the tool (short-circuit). Otherwise, it records
    the call, executes, and journals the result.

    Args:
        journal: The run journal for recording events.
        run_state: Mutable run state with step counter.

    Returns:
        A tool_hook function compatible with Agno's hook signature.
    """

    def durable_tool_hook(
        function_name: str,
        function_call: Callable,
        arguments: Dict[str, Any],
    ) -> Any:
        key = tool_idempotency_key(
            run_id=run_state.run_id,
            step_index=run_state.increment_step(),
            tool_name=function_name,
            tool_args=arguments,
        )

        # Check cache -- short-circuit if already completed
        cached = journal.lookup_tool_result(key)
        if cached is not None:
            return cached

        # Record start (status = in_flight)
        event_id = journal.record_tool_start(
            run_id=run_state.run_id,
            idempotency_key=key,
            tool_name=function_name,
            tool_args=arguments,
            session_id=run_state.session_id,
        )

        # Execute the tool
        try:
            result = function_call(**arguments)
            journal.record_tool_complete(event_id, str(result), status="completed")
            return result
        except Exception as e:
            journal.record_tool_complete(event_id, str(e), status="failed")
            raise

    return durable_tool_hook
