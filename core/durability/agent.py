"""
Durable Agent
=============
Wrapper that adds durable execution to an Agno Agent.
"""

from typing import Any


class DurableAgent:
    """Wrapper that adds durable execution to an Agno Agent.

    Intercepts run() calls to provide journaling and resume.
    Delegates all other attribute access to the underlying agent.
    """

    def __init__(self, agent: Any, runner: Any):
        # Use object.__setattr__ to avoid triggering __getattr__
        object.__setattr__(self, "_agent", agent)
        object.__setattr__(self, "_runner", runner)

    def run(self, message: str, **kwargs: Any) -> Any:
        """Run with durable execution (journal + resume)."""
        return self._runner.run(message, **kwargs)

    def resume(self, message: str, **kwargs: Any) -> Any:
        """Resume a prior run from the last checkpoint."""
        return self._runner.resume(message, **kwargs)

    def print_response(self, message: str, **kwargs: Any) -> Any:
        """Stream response. Journals after stream completes."""
        # Streaming uses the underlying agent directly.
        # Tool-level durability still applies via tool_hooks.
        return self._agent.print_response(message, **kwargs)

    def __getattr__(self, name: str) -> Any:
        """Delegate all other attribute access to the underlying agent."""
        return getattr(self._agent, name)

    def __setattr__(self, name: str, value: Any) -> None:
        """Delegate attribute setting to the underlying agent."""
        setattr(self._agent, name, value)
