"""
Run Journal
============
SQLite-backed event journal for durable execution.
"""

import json
import time
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Column,
    Float,
    Index,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
)
from sqlalchemy.engine import Engine


class RunJournal:
    """SQLite-backed event journal for durable execution.

    Records tool call starts/completions and run completions with
    idempotency keys. Supports lookup for replay and resume.
    """

    TABLE_NAME = "run_events"

    def __init__(self, engine: Engine, schema_version: int = 1):
        self._engine = engine
        self._schema_version = schema_version
        self._metadata = MetaData()
        self._table = self._define_table()
        self._ensure_table()

    def _define_table(self) -> Table:
        """Define the run_events table schema."""
        return Table(
            self.TABLE_NAME,
            self._metadata,
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("schema_version", Integer, nullable=False, default=self._schema_version),
            Column("run_id", String, nullable=False),
            Column("session_id", String, nullable=True),
            Column("event_type", String, nullable=False),
            Column("idempotency_key", String, nullable=False),
            Column("tool_name", String, nullable=True),
            Column("tool_args", Text, nullable=True),
            Column("result", Text, nullable=True),
            Column("status", String, nullable=False, default="in_flight"),
            Column("error", Text, nullable=True),
            Column("created_at", Float, nullable=False),
            Column("completed_at", Float, nullable=True),
            UniqueConstraint("idempotency_key", "event_type", name="uq_idempotency_event"),
            Index("idx_run_events_run_id", "run_id"),
            Index("idx_run_events_idempotency", "idempotency_key"),
            Index("idx_run_events_status", "status"),
        )

    def _ensure_table(self) -> None:
        """Create the table if it doesn't exist."""
        self._metadata.create_all(self._engine)

    def record_tool_start(
        self,
        run_id: str,
        idempotency_key: str,
        tool_name: str,
        tool_args: dict,
        session_id: Optional[str] = None,
    ) -> int:
        """Record a tool call starting. Returns the event row id."""
        with self._engine.connect() as conn:
            result = conn.execute(
                self._table.insert().values(
                    schema_version=self._schema_version,
                    run_id=run_id,
                    session_id=session_id,
                    event_type="tool_start",
                    idempotency_key=idempotency_key,
                    tool_name=tool_name,
                    tool_args=json.dumps(tool_args, default=str),
                    status="in_flight",
                    created_at=time.time(),
                )
            )
            conn.commit()
            return result.lastrowid  # type: ignore[return-value]

    def record_tool_complete(
        self,
        event_id: int,
        result: str,
        status: str = "completed",
    ) -> None:
        """Mark a tool call as completed (or failed)."""
        with self._engine.connect() as conn:
            conn.execute(
                self._table.update()
                .where(self._table.c.id == event_id)
                .values(
                    result=result,
                    status=status,
                    completed_at=time.time(),
                )
            )
            conn.commit()

    def record_run_complete(
        self,
        run_id: str,
        idempotency_key: str,
        run_output: dict,
        session_id: Optional[str] = None,
    ) -> None:
        """Record a completed agent.run() with its full RunOutput."""
        with self._engine.connect() as conn:
            conn.execute(
                self._table.insert().values(
                    schema_version=self._schema_version,
                    run_id=run_id,
                    session_id=session_id,
                    event_type="run_complete",
                    idempotency_key=idempotency_key,
                    result=json.dumps(run_output, default=str),
                    status="completed",
                    created_at=time.time(),
                    completed_at=time.time(),
                )
            )
            conn.commit()

    def lookup_tool_result(self, idempotency_key: str) -> Optional[str]:
        """Look up a cached tool result by idempotency key.

        Returns the result string if found and completed, None otherwise.
        """
        with self._engine.connect() as conn:
            row = conn.execute(
                self._table.select().where(
                    (self._table.c.idempotency_key == idempotency_key)
                    & (self._table.c.event_type == "tool_start")
                    & (self._table.c.status == "completed")
                )
            ).fetchone()
            if row is not None:
                return row.result  # type: ignore[union-attr]
        return None

    def lookup_run_output(self, idempotency_key: str) -> Optional[dict]:
        """Look up a cached RunOutput by idempotency key.

        Returns the deserialized RunOutput dict if found, None otherwise.
        """
        with self._engine.connect() as conn:
            row = conn.execute(
                self._table.select().where(
                    (self._table.c.idempotency_key == idempotency_key)
                    & (self._table.c.event_type == "run_complete")
                    & (self._table.c.status == "completed")
                )
            ).fetchone()
            if row is not None and row.result is not None:
                return json.loads(row.result)
        return None

    def get_in_flight_events(self, run_id: str) -> List[Dict[str, Any]]:
        """Get all in_flight events for a run (unfinished tool calls)."""
        with self._engine.connect() as conn:
            rows = conn.execute(
                self._table.select().where(
                    (self._table.c.run_id == run_id)
                    & (self._table.c.status == "in_flight")
                )
            ).fetchall()
            return [dict(row._mapping) for row in rows]

    def mark_event_retrying(self, event_id: int) -> None:
        """Mark an in_flight event as retrying (will be re-executed)."""
        with self._engine.connect() as conn:
            conn.execute(
                self._table.delete().where(self._table.c.id == event_id)
            )
            conn.commit()

    def get_events_for_run(self, run_id: str) -> List[Dict[str, Any]]:
        """Get all events for a run, ordered by creation time."""
        with self._engine.connect() as conn:
            rows = conn.execute(
                self._table.select()
                .where(self._table.c.run_id == run_id)
                .order_by(self._table.c.created_at)
            ).fetchall()
            return [dict(row._mapping) for row in rows]

    def compact(self, run_id: str) -> int:
        """Remove completed events for a run. Returns count of deleted rows."""
        with self._engine.connect() as conn:
            result = conn.execute(
                self._table.delete().where(
                    (self._table.c.run_id == run_id)
                    & (self._table.c.status == "completed")
                )
            )
            conn.commit()
            return result.rowcount  # type: ignore[return-value]

    def event_count(self, run_id: str) -> int:
        """Count events for a run."""
        with self._engine.connect() as conn:
            from sqlalchemy import func

            row = conn.execute(
                self._table.select()
                .with_only_columns(func.count())
                .where(self._table.c.run_id == run_id)
            ).fetchone()
            return row[0] if row else 0
