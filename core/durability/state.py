"""
Run State
=========
Mutable state tracked during a durable run.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RunState:
    """Mutable state tracked during a durable run."""

    run_id: str
    session_id: Optional[str] = None
    step_counter: int = field(default=0)

    def increment_step(self) -> int:
        """Increment and return the step counter."""
        self.step_counter += 1
        return self.step_counter

    def reset(self) -> None:
        """Reset step counter for a new run or resume."""
        self.step_counter = 0
