"""
Tests for Agentic Runtime Policies
==================================
Comprehensive tests for all policy configurations.
"""

import pytest
from pydantic import ValidationError

from core.policies import (
    AgentRole,
    AgentSpec,
    CodeActPolicy,
    CodingPolicy,
    ContextPolicy,
    KnowledgePolicy,
    McpPolicy,
    McpServerConfig,
    ObservabilityPolicy,
    ReasoningPolicy,
    StructuredOutputPolicy,
    SystemPromptPolicy,
    TeamPolicy,
    ToolPolicy,
    WorkflowPolicy,
    WorkflowStep,
    create_basic_spec,
    create_codeact_spec,
    create_coding_spec,
    create_research_spec,
    create_team_spec,
)

# =============================================================================
# Context Policy Tests
# =============================================================================


class TestContextPolicy:
    def test_default_values(self):
        policy = ContextPolicy()
        assert policy.enable_user_memories is True
        assert policy.enable_session_summaries is True
        assert policy.add_history_to_context is True
        assert policy.num_history_runs == 3

    def test_custom_values(self):
        policy = ContextPolicy(
            enable_user_memories=False,
            num_history_runs=10,
        )
        assert policy.enable_user_memories is False
        assert policy.num_history_runs == 10

    def test_num_history_runs_validation(self):
        with pytest.raises(ValidationError):
            ContextPolicy(num_history_runs=-1)


# =============================================================================
# Tool Policy Tests
# =============================================================================


class TestToolPolicy:
    def test_default_values(self):
        policy = ToolPolicy()
        assert policy.timeout_seconds == 45.0
        assert policy.max_retries == 2
        assert policy.max_result_chars == 16_000
        assert policy.error_strategy == "structured"

    def test_validates_positive_timeout(self):
        with pytest.raises(ValidationError):
            ToolPolicy(timeout_seconds=0)

    def test_validates_non_negative_retries(self):
        with pytest.raises(ValidationError):
            ToolPolicy(max_retries=-1)

    def test_error_strategy_options(self):
        policy = ToolPolicy(error_strategy="raise")
        assert policy.error_strategy == "raise"


# =============================================================================
# CodeAct Policy Tests
# =============================================================================


class TestCodeActPolicy:
    def test_default_values(self):
        policy = CodeActPolicy()
        assert policy.enabled is True
        assert policy.sandbox == "daytona"
        assert policy.max_iterations == 6
        assert policy.enable_code_interpreter is True
        assert policy.extract_charts is True

    def test_enhanced_features(self):
        policy = CodeActPolicy(
            max_iterations=10,
            enable_code_interpreter=False,
            sandbox_timeout_minutes=10,
        )
        assert policy.max_iterations == 10
        assert policy.enable_code_interpreter is False
        assert policy.sandbox_timeout_minutes == 10


# =============================================================================
# MCP Policy Tests
# =============================================================================


class TestMcpPolicy:
    def test_default_values(self):
        policy = McpPolicy()
        assert policy.enabled is False
        assert policy.transport == "streamable-http"
        assert policy.url is None

    def test_requires_url_when_enabled(self):
        with pytest.raises(ValidationError):
            McpPolicy(enabled=True, url=None)

    def test_url_stripped(self):
        policy = McpPolicy(enabled=True, url="  https://example.com  ")
        assert policy.url == "https://example.com"

    def test_multi_server_config(self):
        servers = [
            McpServerConfig(name="server1", url="https://server1.com"),
            McpServerConfig(name="server2", url="https://server2.com", transport="sse"),
        ]
        policy = McpPolicy(enabled=True, servers=servers)
        assert len(policy.servers) == 2
        assert policy.servers[0].name == "server1"
        assert policy.servers[1].transport == "sse"


# =============================================================================
# Knowledge Policy Tests
# =============================================================================


class TestKnowledgePolicy:
    def test_default_values(self):
        policy = KnowledgePolicy()
        assert policy.enabled is False
        assert policy.vector_db == "lancedb"
        assert policy.embedder == "openai"
        assert policy.search_type == "hybrid"
        assert policy.max_results == 5

    def test_custom_configuration(self):
        policy = KnowledgePolicy(
            enabled=True,
            vector_db="pgvector",
            embedder="sentence-transformer",
            search_type="vector",
            max_results=10,
            content_sources=["https://example.com/docs"],
        )
        assert policy.vector_db == "pgvector"
        assert policy.embedder == "sentence-transformer"
        assert len(policy.content_sources) == 1

    def test_similarity_threshold_validation(self):
        with pytest.raises(ValidationError):
            KnowledgePolicy(similarity_threshold=1.5)


# =============================================================================
# Reasoning Policy Tests
# =============================================================================


class TestReasoningPolicy:
    def test_default_values(self):
        policy = ReasoningPolicy()
        assert policy.enabled is False
        assert policy.mode == "basic"
        assert policy.show_full_reasoning is False

    def test_extended_mode(self):
        policy = ReasoningPolicy(
            enabled=True,
            mode="extended",
            show_full_reasoning=True,
        )
        assert policy.mode == "extended"
        assert policy.show_full_reasoning is True

    def test_tools_mode(self):
        policy = ReasoningPolicy(
            enabled=True,
            mode="tools",
            add_instructions=True,
        )
        assert policy.mode == "tools"


# =============================================================================
# Structured Output Policy Tests
# =============================================================================


class TestStructuredOutputPolicy:
    def test_default_values(self):
        policy = StructuredOutputPolicy()
        assert policy.enabled is False
        assert policy.use_json_mode is False
        assert policy.strict_validation is True


# =============================================================================
# Observability Policy Tests
# =============================================================================


class TestObservabilityPolicy:
    def test_default_values(self):
        policy = ObservabilityPolicy()
        assert policy.enabled is True
        assert policy.enable_tool_hooks is True
        assert policy.log_tool_calls is True
        assert policy.debug_mode is False

    def test_metrics_configuration(self):
        policy = ObservabilityPolicy(
            collect_metrics=True,
            metrics_export_format="prometheus",
        )
        assert policy.collect_metrics is True
        assert policy.metrics_export_format == "prometheus"


# =============================================================================
# Team Policy Tests
# =============================================================================


class TestTeamPolicy:
    def test_default_values(self):
        policy = TeamPolicy()
        assert policy.enabled is False
        assert policy.mode == "coordinate"
        assert policy.share_member_interactions is True

    def test_with_members(self):
        members = [
            AgentRole(name="researcher", role="Research topics"),
            AgentRole(name="writer", role="Write content"),
        ]
        policy = TeamPolicy(
            enabled=True,
            members=members,
            leader_instructions=["Coordinate the team"],
        )
        assert len(policy.members) == 2
        assert policy.members[0].name == "researcher"


class TestAgentRole:
    def test_basic_role(self):
        role = AgentRole(name="assistant", role="Help users")
        assert role.name == "assistant"
        assert role.role == "Help users"
        assert role.model_id is None
        assert role.tools == []

    def test_role_with_tools(self):
        role = AgentRole(
            name="coder",
            role="Write code",
            model_id="gpt-4",
            tools=["daytona", "knowledge"],
        )
        assert role.model_id == "gpt-4"
        assert "daytona" in role.tools


# =============================================================================
# Workflow Policy Tests
# =============================================================================


class TestWorkflowPolicy:
    def test_default_values(self):
        policy = WorkflowPolicy()
        assert policy.enabled is False
        assert policy.name == "default_workflow"
        assert policy.parallel_execution is False

    def test_with_steps(self):
        steps = [
            WorkflowStep(name="research", agent_name="researcher"),
            WorkflowStep(name="write", agent_name="writer", depends_on=["research"]),
        ]
        policy = WorkflowPolicy(
            enabled=True,
            name="content_workflow",
            steps=steps,
        )
        assert len(policy.steps) == 2
        assert policy.steps[1].depends_on == ["research"]


# =============================================================================
# System Prompt Policy Tests
# =============================================================================


class TestSystemPromptPolicy:
    def test_default_values(self):
        policy = SystemPromptPolicy()
        assert policy.template == "default"
        assert policy.add_datetime is True
        assert policy.tone == "professional"

    def test_custom_template_required(self):
        with pytest.raises(ValidationError):
            SystemPromptPolicy(template="custom", custom_template=None)

    def test_custom_template_valid(self):
        policy = SystemPromptPolicy(
            template="custom",
            custom_template="You are a helpful assistant.",
        )
        assert policy.custom_template == "You are a helpful assistant."


# =============================================================================
# Agent Spec Tests
# =============================================================================


class TestAgentSpec:
    def test_default_values(self):
        spec = AgentSpec()
        assert spec.version == "0.2.0"
        assert spec.model_id == "google/gemini-3-flash-preview"
        assert spec.user_id == "user"

    def test_requires_model_id(self):
        with pytest.raises(ValidationError):
            AgentSpec(model_id="")

    def test_with_output_schema(self):
        from pydantic import BaseModel

        class TestSchema(BaseModel):
            name: str
            value: int

        spec = AgentSpec().with_output_schema(TestSchema)
        assert spec.structured_output.enabled is True
        assert spec.output_schema == TestSchema

    def test_all_policies_accessible(self):
        spec = AgentSpec()
        assert isinstance(spec.context, ContextPolicy)
        assert isinstance(spec.tools, ToolPolicy)
        assert isinstance(spec.codeact, CodeActPolicy)
        assert isinstance(spec.mcp, McpPolicy)
        assert isinstance(spec.knowledge, KnowledgePolicy)
        assert isinstance(spec.reasoning, ReasoningPolicy)
        assert isinstance(spec.team, TeamPolicy)
        assert isinstance(spec.workflow, WorkflowPolicy)
        assert isinstance(spec.observability, ObservabilityPolicy)


# =============================================================================
# Preset Tests
# =============================================================================


class TestPresets:
    def test_create_basic_spec(self):
        spec = create_basic_spec()
        assert spec.codeact.enabled is False
        assert spec.mcp.enabled is False

    def test_create_codeact_spec(self):
        spec = create_codeact_spec(max_iterations=10)
        assert spec.codeact.enabled is True
        assert spec.codeact.max_iterations == 10
        assert spec.system_prompt.template == "codeact"

    def test_create_research_spec(self):
        spec = create_research_spec(
            knowledge_sources=["https://docs.example.com"]
        )
        assert spec.knowledge.enabled is True
        assert spec.reasoning.enabled is True
        assert len(spec.knowledge.content_sources) == 1

    def test_create_team_spec(self):
        members = [
            AgentRole(name="agent1", role="Role 1"),
            AgentRole(name="agent2", role="Role 2"),
        ]
        spec = create_team_spec(members=members)
        assert spec.team.enabled is True
        assert len(spec.team.members) == 2

    def test_create_coding_spec(self):
        spec = create_coding_spec(
            workspace_root="/tmp/project",
            allow_write=True,
            allow_git_write=False,
        )
        assert spec.coding.enabled is True
        assert spec.coding.workspace_root == "/tmp/project"
        assert spec.coding.allow_write is True
        assert spec.coding.allow_git_write is False
        assert spec.codeact.enabled is True
        assert spec.reasoning.enabled is True


# =============================================================================
# Coding Policy Tests
# =============================================================================


class TestCodingPolicy:
    def test_default_values(self):
        policy = CodingPolicy()
        assert policy.enabled is False
        assert policy.workspace_root == "."
        assert policy.allow_write is True
        assert policy.max_file_size_kb == 512
        assert policy.max_search_results == 100
        assert policy.enable_git is True
        assert policy.allow_git_write is False

    def test_custom_values(self):
        policy = CodingPolicy(
            enabled=True,
            workspace_root="/home/user/project",
            allow_write=False,
            max_file_size_kb=1024,
            enable_git=False,
        )
        assert policy.enabled is True
        assert policy.workspace_root == "/home/user/project"
        assert policy.allow_write is False
        assert policy.max_file_size_kb == 1024
        assert policy.enable_git is False

    def test_exclude_patterns_default(self):
        policy = CodingPolicy()
        assert "**/.git/**" in policy.exclude_patterns
        assert "**/node_modules/**" in policy.exclude_patterns
        assert "**/__pycache__/**" in policy.exclude_patterns

    def test_max_file_size_validation(self):
        with pytest.raises(ValidationError):
            CodingPolicy(max_file_size_kb=0)
        with pytest.raises(ValidationError):
            CodingPolicy(max_file_size_kb=20000)

    def test_max_search_results_validation(self):
        with pytest.raises(ValidationError):
            CodingPolicy(max_search_results=0)
        with pytest.raises(ValidationError):
            CodingPolicy(max_search_results=2000)
