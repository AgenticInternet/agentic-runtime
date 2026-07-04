"""
Durable Execution Policy
========================
Configuration for checkpoint, resume, and idempotency behavior.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class DurableExecutionPolicy(BaseModel):
    """Policy for durable execution with checkpointing and resume."""

    enabled: bool = False

    journal_db_file: Optional[str] = Field(
        default=None,
        description="Path to journal database file. None = use agent's existing db.",
    )

    replay_mode: Literal["strict", "lenient"] = Field(
        default="strict",
        description="strict: fail on journal divergence, lenient: warn and continue",
    )

    retry_on_partial_failure: bool = Field(
        default=True,
        description="Re-execute in_flight tools on resume. False = treat as failed.",
    )

    max_journal_events: int = Field(
        default=10000,
        ge=100,
        description="Maximum events per run before compaction is triggered.",
    )

    schema_version: int = Field(
        default=1,
        ge=1,
        description="Journal schema version for forward compatibility.",
    )

    model_config = {"extra": "forbid"}
