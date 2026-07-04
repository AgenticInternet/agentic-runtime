"""
Tests for Durable Execution
============================
Comprehensive tests for checkpoint, resume, and idempotency.
"""


import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine

from core.durability import (
    DurableAgent,
    DurableRunner,
    RunJournal,
    RunState,
    build_durable_tool_hook,
    run_idempotency_key,
    tool_idempotency_key,
)
from core.durability.policy import DurableExecutionPolicy
from core.policies import AgentSpec, CodeActPolicy, McpPolicy, create_durable_coding_spec

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def tmp_db_path(tmp_path):
    """Provide a temporary SQLite database path."""
    return str(tmp_path / "test_journal.db")


@pytest.fixture
def engine(tmp_db_path):
    """Create an in-memory SQLite engine."""
    return create_engine("sqlite:///:memory:")


@pytest.fixture
def journal(engine):
    """Create a RunJournal with a fresh in-memory database."""
    return RunJournal(engine)


@pytest.fixture
def run_state():
    """Create a fresh RunState."""
    return RunState(run_id="test-run-001", session_id="test-session")


# =============================================================================
# DurableExecutionPolicy Tests
# =============================================================================


class TestDurableExecutionPolicy:
    def test_default_values(self):
        policy = DurableExecutionPolicy()
        assert policy.enabled is False
        assert policy.journal_db_file is None
        assert policy.replay_mode == "strict"
        assert policy.retry_on_partial_failure is True
        assert policy.max_journal_events == 10000
        assert policy.schema_version == 1

    def test_enable_with_custom_db(self):
        policy = DurableExecutionPolicy(
            enabled=True,
            journal_db_file="/tmp/my_journal.db",
        )
        assert policy.enabled is True
        assert policy.journal_db_file == "/tmp/my_journal.db"

    def test_replay_mode_validation(self):
        policy = DurableExecutionPolicy(replay_mode="lenient")
        assert policy.replay_mode == "lenient"

        with pytest.raises(ValidationError):
            DurableExecutionPolicy(replay_mode="invalid")

    def test_schema_version_must_be_positive(self):
        with pytest.raises(ValidationError):
            DurableExecutionPolicy(schema_version=0)

    def test_max_events_minimum(self):
        with pytest.raises(ValidationError):
            DurableExecutionPolicy(max_journal_events=50)

    def test_extra_fields_forbidden(self):
        with pytest.raises(ValidationError):
            DurableExecutionPolicy(unknown_field="value")

    def test_on_agent_spec(self):
        spec = AgentSpec()
        assert isinstance(spec.durability, DurableExecutionPolicy)
        assert spec.durability.enabled is False

    def test_on_agent_spec_enabled(self):
        spec = AgentSpec(
            durability=DurableExecutionPolicy(enabled=True),
        )
        assert spec.durability.enabled is True


# =============================================================================
# Idempotency Key Tests
# =============================================================================


class TestIdempotencyKeys:
    def test_tool_key_deterministic(self):
        """Same inputs produce the same key."""
        key1 = tool_idempotency_key("run-1", 1, "search", {"query": "hello"})
        key2 = tool_idempotency_key("run-1", 1, "search", {"query": "hello"})
        assert key1 == key2

    def test_tool_key_varies_with_run_id(self):
        key1 = tool_idempotency_key("run-1", 1, "search", {"query": "hello"})
        key2 = tool_idempotency_key("run-2", 1, "search", {"query": "hello"})
        assert key1 != key2

    def test_tool_key_varies_with_step(self):
        key1 = tool_idempotency_key("run-1", 1, "search", {"query": "hello"})
        key2 = tool_idempotency_key("run-1", 2, "search", {"query": "hello"})
        assert key1 != key2

    def test_tool_key_varies_with_tool_name(self):
        key1 = tool_idempotency_key("run-1", 1, "search", {"query": "hello"})
        key2 = tool_idempotency_key("run-1", 1, "write", {"query": "hello"})
        assert key1 != key2

    def test_tool_key_varies_with_args(self):
        key1 = tool_idempotency_key("run-1", 1, "search", {"query": "hello"})
        key2 = tool_idempotency_key("run-1", 1, "search", {"query": "world"})
        assert key1 != key2

    def test_tool_key_arg_order_invariant(self):
        """Argument order should not affect the key."""
        key1 = tool_idempotency_key("run-1", 1, "fn", {"a": 1, "b": 2})
        key2 = tool_idempotency_key("run-1", 1, "fn", {"b": 2, "a": 1})
        assert key1 == key2

    def test_tool_key_length(self):
        key = tool_idempotency_key("run-1", 1, "search", {"q": "test"})
        assert len(key) == 32

    def test_run_key_deterministic(self):
        key1 = run_idempotency_key("run-1", "What is 2+2?")
        key2 = run_idempotency_key("run-1", "What is 2+2?")
        assert key1 == key2

    def test_run_key_varies_with_input(self):
        key1 = run_idempotency_key("run-1", "What is 2+2?")
        key2 = run_idempotency_key("run-1", "What is 3+3?")
        assert key1 != key2

    def test_run_key_length(self):
        key = run_idempotency_key("run-1", "hello")
        assert len(key) == 32


# =============================================================================
# RunState Tests
# =============================================================================


class TestRunState:
    def test_basic_creation(self):
        state = RunState(run_id="run-1")
        assert state.run_id == "run-1"
        assert state.session_id is None
        assert state.step_counter == 0

    def test_increment_step(self):
        state = RunState(run_id="run-1")
        assert state.increment_step() == 1
        assert state.increment_step() == 2
        assert state.increment_step() == 3
        assert state.step_counter == 3

    def test_reset(self):
        state = RunState(run_id="run-1")
        state.increment_step()
        state.increment_step()
        state.reset()
        assert state.step_counter == 0


# =============================================================================
# RunJournal Tests
# =============================================================================


class TestRunJournal:
    def test_create_table(self, journal, engine):
        """Table should be created on init."""
        from sqlalchemy import inspect as sa_inspect

        inspector = sa_inspect(engine)
        tables = inspector.get_table_names()
        assert "run_events" in tables

    def test_record_tool_start(self, journal):
        event_id = journal.record_tool_start(
            run_id="run-1",
            idempotency_key="key-1",
            tool_name="search",
            tool_args={"query": "hello"},
        )
        assert isinstance(event_id, int)
        assert event_id > 0

    def test_record_tool_complete(self, journal):
        event_id = journal.record_tool_start(
            run_id="run-1",
            idempotency_key="key-1",
            tool_name="search",
            tool_args={"query": "hello"},
        )
        journal.record_tool_complete(event_id, "search result", status="completed")

        # Verify the result is stored
        result = journal.lookup_tool_result("key-1")
        assert result == "search result"

    def test_lookup_tool_result_not_found(self, journal):
        result = journal.lookup_tool_result("nonexistent-key")
        assert result is None

    def test_lookup_tool_result_in_flight(self, journal):
        """In-flight tools should not be returned by lookup."""
        journal.record_tool_start(
            run_id="run-1",
            idempotency_key="key-1",
            tool_name="search",
            tool_args={"query": "hello"},
        )
        # Not completed yet — should return None
        result = journal.lookup_tool_result("key-1")
        assert result is None

    def test_record_run_complete(self, journal):
        journal.record_run_complete(
            run_id="run-1",
            idempotency_key="run-key-1",
            run_output={"content": "Hello world", "messages": []},
        )
        result = journal.lookup_run_output("run-key-1")
        assert result is not None
        assert result["content"] == "Hello world"

    def test_lookup_run_output_not_found(self, journal):
        result = journal.lookup_run_output("nonexistent")
        assert result is None

    def test_get_in_flight_events(self, journal):
        journal.record_tool_start(
            run_id="run-1",
            idempotency_key="key-1",
            tool_name="tool_a",
            tool_args={},
        )
        event_id_2 = journal.record_tool_start(
            run_id="run-1",
            idempotency_key="key-2",
            tool_name="tool_b",
            tool_args={},
        )
        # Complete one
        journal.record_tool_complete(event_id_2, "done", status="completed")

        in_flight = journal.get_in_flight_events("run-1")
        assert len(in_flight) == 1
        assert in_flight[0]["tool_name"] == "tool_a"

    def test_mark_event_retrying(self, journal):
        event_id = journal.record_tool_start(
            run_id="run-1",
            idempotency_key="key-1",
            tool_name="search",
            tool_args={},
        )
        journal.mark_event_retrying(event_id)

        # Event should be deleted
        in_flight = journal.get_in_flight_events("run-1")
        assert len(in_flight) == 0

    def test_get_events_for_run(self, journal):
        journal.record_tool_start(
            run_id="run-1",
            idempotency_key="key-1",
            tool_name="tool_a",
            tool_args={},
        )
        journal.record_tool_start(
            run_id="run-1",
            idempotency_key="key-2",
            tool_name="tool_b",
            tool_args={},
        )
        journal.record_tool_start(
            run_id="run-2",
            idempotency_key="key-3",
            tool_name="tool_c",
            tool_args={},
        )

        events = journal.get_events_for_run("run-1")
        assert len(events) == 2

    def test_compact(self, journal):
        event_id = journal.record_tool_start(
            run_id="run-1",
            idempotency_key="key-1",
            tool_name="search",
            tool_args={},
        )
        journal.record_tool_complete(event_id, "result", status="completed")

        # Also add an in-flight event
        journal.record_tool_start(
            run_id="run-1",
            idempotency_key="key-2",
            tool_name="write",
            tool_args={},
        )

        deleted = journal.compact("run-1")
        assert deleted == 1  # Only the completed event

        # In-flight event should still be there
        remaining = journal.get_events_for_run("run-1")
        assert len(remaining) == 1
        assert remaining[0]["status"] == "in_flight"

    def test_event_count(self, journal):
        assert journal.event_count("run-1") == 0

        journal.record_tool_start(
            run_id="run-1",
            idempotency_key="key-1",
            tool_name="search",
            tool_args={},
        )
        assert journal.event_count("run-1") == 1

    def test_idempotency_constraint(self, journal):
        """Duplicate idempotency key + event_type should fail."""
        journal.record_tool_start(
            run_id="run-1",
            idempotency_key="key-1",
            tool_name="search",
            tool_args={},
        )
        with pytest.raises(Exception):  # IntegrityError
            journal.record_tool_start(
                run_id="run-1",
                idempotency_key="key-1",
                tool_name="search",
                tool_args={},
            )

    def test_session_id_stored(self, journal):
        journal.record_tool_start(
            run_id="run-1",
            idempotency_key="key-1",
            tool_name="search",
            tool_args={},
            session_id="session-abc",
        )
        events = journal.get_events_for_run("run-1")
        assert events[0]["session_id"] == "session-abc"

    def test_schema_version_stored(self, journal):
        journal.record_tool_start(
            run_id="run-1",
            idempotency_key="key-1",
            tool_name="search",
            tool_args={},
        )
        events = journal.get_events_for_run("run-1")
        assert events[0]["schema_version"] == 1


# =============================================================================
# Durable Tool Hook Tests
# =============================================================================


class TestDurableToolHook:
    def test_first_call_executes_and_journals(self, journal, run_state):
        hook = build_durable_tool_hook(journal, run_state)

        call_count = 0

        def mock_tool(**kwargs):
            nonlocal call_count
            call_count += 1
            return f"result for {kwargs['query']}"

        result = hook("search", mock_tool, {"query": "hello"})
        assert result == "result for hello"
        assert call_count == 1

    def test_cached_call_short_circuits(self, journal, run_state):
        hook = build_durable_tool_hook(journal, run_state)

        call_count = 0

        def mock_tool(**kwargs):
            nonlocal call_count
            call_count += 1
            return f"result for {kwargs['query']}"

        # First call
        result1 = hook("search", mock_tool, {"query": "hello"})

        # Reset step counter to replay the same step
        run_state.reset()
        result2 = hook("search", mock_tool, {"query": "hello"})

        assert result1 == "result for hello"
        assert result2 == "result for hello"
        assert call_count == 1  # Tool only called once

    def test_failed_call_journals_error(self, journal, run_state):
        hook = build_durable_tool_hook(journal, run_state)

        def failing_tool(**kwargs):
            raise ValueError("tool failed")

        with pytest.raises(ValueError, match="tool failed"):
            hook("bad_tool", failing_tool, {"input": "x"})

        # The event should be recorded as failed
        events = journal.get_events_for_run(run_state.run_id)
        assert len(events) == 1
        assert events[0]["status"] == "failed"
        assert "tool failed" in events[0]["result"]

    def test_multiple_tools_journaled_in_order(self, journal, run_state):
        hook = build_durable_tool_hook(journal, run_state)

        hook("tool_a", lambda **kw: "a_result", {"x": 1})
        hook("tool_b", lambda **kw: "b_result", {"y": 2})

        events = journal.get_events_for_run(run_state.run_id)
        assert len(events) == 2
        assert events[0]["tool_name"] == "tool_a"
        assert events[1]["tool_name"] == "tool_b"

    def test_step_counter_increments(self, journal, run_state):
        hook = build_durable_tool_hook(journal, run_state)

        hook("tool_a", lambda **kw: "a", {})
        hook("tool_b", lambda **kw: "b", {})

        assert run_state.step_counter == 2


# =============================================================================
# DurableRunner Tests
# =============================================================================


class TestDurableRunner:
    def _make_mock_agent(self, run_output="mock output"):
        """Create a mock agent with run() and basic attributes."""

        class MockAgent:
            run_id = "mock-run-id"
            session_id = "mock-session"
            call_count = 0

            def run(self, message, **kwargs):
                self.call_count += 1
                return run_output

        return MockAgent()

    def test_run_executes_and_journals(self, journal):
        agent = self._make_mock_agent()
        policy = DurableExecutionPolicy(enabled=True)
        runner = DurableRunner(agent, journal, policy)

        result = runner.run("Hello")
        assert result == "mock output"
        assert agent.call_count == 1

    def test_run_returns_cached_on_replay(self, journal):
        agent = self._make_mock_agent()
        policy = DurableExecutionPolicy(enabled=True)
        runner = DurableRunner(agent, journal, policy)

        result1 = runner.run("Hello")
        result2 = runner.run("Hello")

        assert result1 == "mock output"
        assert isinstance(result2, dict)  # Deserialized from journal
        assert agent.call_count == 1  # Only called once

    def test_resume_alias_for_run(self, journal):
        agent = self._make_mock_agent()
        policy = DurableExecutionPolicy(enabled=True)
        runner = DurableRunner(agent, journal, policy)

        result = runner.resume("Hello")
        assert result == "mock output"

    def test_shared_run_state(self, journal, run_state):
        agent = self._make_mock_agent()
        policy = DurableExecutionPolicy(enabled=True)
        runner = DurableRunner(agent, journal, policy, run_state=run_state)

        assert runner.run_state is run_state

    def test_in_flight_resolution_retry(self, journal):
        """In-flight events should be deleted when retry_on_partial_failure=True."""
        # Simulate a crash: record tool start without completion
        journal.record_tool_start(
            run_id="crash-run",
            idempotency_key="key-1",
            tool_name="search",
            tool_args={},
        )

        agent = self._make_mock_agent()
        policy = DurableExecutionPolicy(enabled=True, retry_on_partial_failure=True)
        state = RunState(run_id="crash-run")
        runner = DurableRunner(agent, journal, policy, run_state=state)

        # Run should resolve the in-flight event first
        runner.run("resume after crash")

        # The in-flight event should have been deleted (mark_event_retrying)
        in_flight = journal.get_in_flight_events("crash-run")
        assert len(in_flight) == 0

    def test_in_flight_resolution_fail(self, journal):
        """In-flight events should be marked failed when retry_on_partial_failure=False."""
        journal.record_tool_start(
            run_id="crash-run",
            idempotency_key="key-1",
            tool_name="search",
            tool_args={},
        )

        agent = self._make_mock_agent()
        policy = DurableExecutionPolicy(enabled=True, retry_on_partial_failure=False)
        state = RunState(run_id="crash-run")
        runner = DurableRunner(agent, journal, policy, run_state=state)

        runner.run("resume after crash")

        # The in-flight event should now be marked as failed
        events = journal.get_events_for_run("crash-run")
        tool_events = [e for e in events if e["event_type"] == "tool_start"]
        assert len(tool_events) == 1
        assert tool_events[0]["status"] == "failed"

    def test_serialize_run_output_with_to_dict(self):
        """RunOutput with to_dict() should serialize properly."""

        class FakeRunOutput:
            def to_dict(self):
                return {"content": "hello", "messages": []}

        result = DurableRunner._serialize_run_output(FakeRunOutput())
        assert result == {"content": "hello", "messages": []}

    def test_serialize_run_output_with_dict(self):
        """RunOutput with __dict__ should serialize content."""

        class FakeRunOutput:
            def __init__(self):
                self.content = "hello world"

        result = DurableRunner._serialize_run_output(FakeRunOutput())
        assert result == {"content": "hello world"}

    def test_serialize_run_output_fallback(self):
        """Plain values should be stringified."""
        result = DurableRunner._serialize_run_output("plain string")
        assert result == {"content": "plain string"}


# =============================================================================
# DurableAgent Tests
# =============================================================================


class TestDurableAgent:
    def _make_mock_agent(self):
        class MockAgent:
            name = "test_agent"
            run_id = "run-1"
            session_id = "session-1"

            def run(self, message, **kwargs):
                return f"agent: {message}"

            def print_response(self, message, **kwargs):
                return f"printed: {message}"

            def some_other_method(self):
                return "delegated"

        return MockAgent()

    def _make_mock_runner(self):
        class MockRunner:
            def run(self, message, **kwargs):
                return f"durable: {message}"

            def resume(self, message, **kwargs):
                return f"resumed: {message}"

        return MockRunner()

    def test_run_delegates_to_runner(self):
        agent = self._make_mock_agent()
        runner = self._make_mock_runner()
        durable = DurableAgent(agent, runner)

        result = durable.run("hello")
        assert result == "durable: hello"

    def test_resume_delegates_to_runner(self):
        agent = self._make_mock_agent()
        runner = self._make_mock_runner()
        durable = DurableAgent(agent, runner)

        result = durable.resume("hello")
        assert result == "resumed: hello"

    def test_print_response_delegates_to_agent(self):
        agent = self._make_mock_agent()
        runner = self._make_mock_runner()
        durable = DurableAgent(agent, runner)

        result = durable.print_response("hello")
        assert result == "printed: hello"

    def test_attribute_delegation(self):
        agent = self._make_mock_agent()
        runner = self._make_mock_runner()
        durable = DurableAgent(agent, runner)

        assert durable.name == "test_agent"
        assert durable.some_other_method() == "delegated"

    def test_setattr_delegation(self):
        agent = self._make_mock_agent()
        runner = self._make_mock_runner()
        durable = DurableAgent(agent, runner)

        durable.name = "new_name"
        assert agent.name == "new_name"

    def test_isinstance_check(self):
        """DurableAgent is not an Agent, but wraps one."""
        agent = self._make_mock_agent()
        runner = self._make_mock_runner()
        durable = DurableAgent(agent, runner)

        assert isinstance(durable, DurableAgent)


# =============================================================================
# Factory Integration Tests
# =============================================================================


class TestFactoryDurability:
    def test_build_agent_with_durability(self, tmp_db_path):
        from pathlib import Path

        from agno.db.sqlite import SqliteDb

        Path("tmp").mkdir(parents=True, exist_ok=True)
        db = SqliteDb(db_file="tmp/agents.db")

        spec = AgentSpec(
            codeact=CodeActPolicy(enabled=False),
            mcp=McpPolicy(enabled=False),
            durability=DurableExecutionPolicy(
                enabled=True,
                journal_db_file=tmp_db_path,
            ),
        )

        from core.factory import build_agent

        agent = build_agent(spec, db=db)
        assert isinstance(agent, DurableAgent)

    def test_build_agent_without_durability(self):
        from pathlib import Path

        from agno.agent import Agent
        from agno.db.sqlite import SqliteDb

        Path("tmp").mkdir(parents=True, exist_ok=True)
        db = SqliteDb(db_file="tmp/agents.db")

        spec = AgentSpec(
            codeact=CodeActPolicy(enabled=False),
            mcp=McpPolicy(enabled=False),
        )

        from core.factory import build_agent

        agent = build_agent(spec, db=db)
        assert type(agent) is Agent

    def test_create_durable_coding_spec_preset(self):
        spec = create_durable_coding_spec()
        assert spec.durability.enabled is True
        assert spec.coding.enabled is True
        assert spec.name == "durable_coding_agent"

    def test_create_durable_coding_spec_with_custom_db(self):
        spec = create_durable_coding_spec(journal_db_file="/tmp/custom.db")
        assert spec.durability.journal_db_file == "/tmp/custom.db"

    def test_backward_compatibility(self):
        """Default AgentSpec should work without durability."""
        spec = AgentSpec()
        assert spec.durability.enabled is False
        # Should not break existing code
        assert spec.durability.schema_version == 1
