"""
Durable Runner
==============
Wraps agent.run() to journal RunOutput and support resume.
"""

from typing import Any, Optional
from uuid import uuid4

from .journal import RunJournal
from .keys import run_idempotency_key
from .policy import DurableExecutionPolicy
from .state import RunState


class DurableRunner:
    """Wraps an Agno Agent to provide durable execution.

    Journals RunOutput after each agent.run() call and supports
    resume from the last checkpoint.
    """

    def __init__(
        self,
        agent: Any,
        journal: RunJournal,
        policy: DurableExecutionPolicy,
        run_state: Optional[RunState] = None,
    ):
        self.agent = agent
        self.journal = journal
        self.policy = policy
        self.run_state = run_state or RunState(
            run_id=getattr(agent, "run_id", None) or str(uuid4()),
            session_id=getattr(agent, "session_id", None),
        )

    def run(self, message: str, **kwargs: Any) -> Any:
        """Run with durability: check journal, execute, journal result."""
        key = run_idempotency_key(self.run_state.run_id, str(message))

        # Check for completed run
        cached = self.journal.lookup_run_output(key)
        if cached is not None:
            return cached

        # Resolve any in_flight tool events from a prior crash
        self._resolve_in_flight_events()

        # Execute (tool_hooks handle per-tool journaling)
        run_output = self.agent.run(message, **kwargs)

        # Journal the completed run
        self.journal.record_run_complete(
            run_id=self.run_state.run_id,
            idempotency_key=key,
            run_output=self._serialize_run_output(run_output),
            session_id=self.run_state.session_id,
        )

        return run_output

    def resume(self, message: str, **kwargs: Any) -> Any:
        """Explicitly resume a prior run. Alias for run() with same semantics."""
        return self.run(message, **kwargs)

    def _resolve_in_flight_events(self) -> None:
        """Handle tool calls that were in_flight when a crash occurred."""
        in_flight = self.journal.get_in_flight_events(self.run_state.run_id)
        for event in in_flight:
            if self.policy.retry_on_partial_failure:
                # Delete the in_flight record so it can be re-executed
                self.journal.mark_event_retrying(event["id"])
            else:
                self.journal.record_tool_complete(
                    event["id"],
                    "Marked as failed after crash",
                    status="failed",
                )

    @staticmethod
    def _serialize_run_output(run_output: Any) -> dict:
        """Serialize a RunOutput to a dict for journal storage."""
        if hasattr(run_output, "to_dict"):
            return run_output.to_dict()
        if hasattr(run_output, "__dict__"):
            return {"content": str(getattr(run_output, "content", run_output))}
        return {"content": str(run_output)}
