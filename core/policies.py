"""
Agentic Runtime Policies
========================
Comprehensive policy definitions for configuring agents, teams, workflows,
knowledge bases, reasoning, and observability.
"""

from typing import Any, Dict, List, Literal, Optional, Type

from pydantic import BaseModel, Field, field_validator


# =============================================================================
# Context & Memory Policies
# =============================================================================


class ContextPolicy(BaseModel):
    """Policy for managing conversation context and history."""

    enable_user_memories: bool = True
    enable_session_summaries: bool = True
    add_history_to_context: bool = True
    num_history_runs: int = Field(default=3, ge=0)

    model_config = {"extra": "forbid"}


# =============================================================================
# Tool Policies
# =============================================================================


class ToolPolicy(BaseModel):
    """Policy for tool execution behavior."""

    timeout_seconds: float = Field(default=45.0, gt=0)
    max_retries: int = Field(default=2, ge=0)
    max_result_chars: int = Field(default=16_000, gt=0)
    error_strategy: Literal["structured", "raise"] = "structured"

    model_config = {"extra": "forbid"}


# =============================================================================
# Code Execution (Daytona) Policies
# =============================================================================


class CodeActPolicy(BaseModel):
    """Policy for code execution in sandboxed environments."""

    enabled: bool = True
    sandbox: Literal["daytona"] = "daytona"
    max_iterations: int = Field(default=6, ge=1)

    # Enhanced Daytona features
    enable_code_interpreter: bool = Field(
        default=True, description="Enable stateful code interpreter with context persistence"
    )
    extract_charts: bool = Field(
        default=True, description="Automatically extract matplotlib charts as artifacts"
    )
    auto_install_packages: bool = Field(
        default=True, description="Auto-install missing Python packages"
    )
    max_file_size_mb: int = Field(default=10, ge=1, le=100)
    sandbox_timeout_minutes: int = Field(
        default=5, ge=1, le=60, description="Auto-stop sandbox after inactivity"
    )

    model_config = {"extra": "forbid"}


# =============================================================================
# MCP (Model Context Protocol) Policies
# =============================================================================


class McpServerConfig(BaseModel):
    """Configuration for a single MCP server."""

    name: str = Field(..., min_length=1)
    url: str = Field(..., min_length=1)
    transport: Literal["stdio", "sse", "streamable-http"] = "streamable-http"
    enabled: bool = True
    auth_token: Optional[str] = None

    model_config = {"extra": "forbid"}


class McpPolicy(BaseModel):
    """Policy for MCP tool integration."""

    enabled: bool = False
    transport: Literal["stdio", "sse", "streamable-http"] = "streamable-http"
    url: Optional[str] = None

    # Multi-server support
    servers: List[McpServerConfig] = Field(default_factory=list)

    # Advanced features
    cache_tool_definitions: bool = Field(
        default=True, description="Cache tool definitions for faster subsequent calls"
    )
    tool_timeout_seconds: float = Field(default=30.0, gt=0)
    enable_elicitation: bool = Field(
        default=False, description="Enable interactive elicitation callbacks"
    )

    model_config = {"extra": "forbid"}

    @field_validator("url")
    @classmethod
    def _strip_url(cls, value: Optional[str]) -> Optional[str]:
        return value.strip() if isinstance(value, str) else value

    @field_validator("url")
    @classmethod
    def _require_url_if_enabled(cls, value: Optional[str], info):
        # URL is required if enabled and no servers are configured
        if info.data.get("enabled") and not value and not info.data.get("servers"):
            raise ValueError("mcp.url is required when MCP is enabled (or configure servers)")
        return value


# =============================================================================
# Knowledge Base & RAG Policies
# =============================================================================


class KnowledgePolicy(BaseModel):
    """Policy for knowledge base and RAG (Retrieval-Augmented Generation)."""

    enabled: bool = False

    # Vector database configuration
    vector_db: Literal["lancedb", "pgvector", "chroma", "qdrant"] = Field(
        default="lancedb", description="Vector database backend"
    )
    vector_db_uri: str = Field(
        default="tmp/lancedb", description="URI/path for vector database"
    )
    table_name: str = Field(default="knowledge", min_length=1)

    # Embedder configuration
    embedder: Literal["openai", "sentence-transformer", "voyage", "azure-openai"] = Field(
        default="openai", description="Embedding model provider"
    )
    embedder_model: Optional[str] = Field(
        default=None, description="Specific embedding model ID (uses provider default if None)"
    )

    # Search configuration
    search_type: Literal["vector", "keyword", "hybrid"] = Field(
        default="hybrid", description="Search strategy"
    )
    max_results: int = Field(default=5, ge=1, le=50)
    similarity_threshold: float = Field(
        default=0.7, ge=0.0, le=1.0, description="Minimum similarity score for results"
    )

    # Content sources (URLs, files to load)
    content_sources: List[str] = Field(
        default_factory=list, description="URLs or file paths to load into knowledge base"
    )

    model_config = {"extra": "forbid"}


# =============================================================================
# Reasoning Policies
# =============================================================================


class ReasoningPolicy(BaseModel):
    """Policy for reasoning and chain-of-thought capabilities."""

    enabled: bool = False

    # Reasoning mode
    mode: Literal["basic", "extended", "tools"] = Field(
        default="basic",
        description="basic: simple CoT, extended: deep thinking, tools: use ReasoningTools",
    )

    # Display options
    show_full_reasoning: bool = Field(
        default=False, description="Show complete reasoning chain in output"
    )
    stream_reasoning_steps: bool = Field(
        default=True, description="Stream reasoning steps as they occur"
    )

    # Model configuration
    reasoning_model: Optional[str] = Field(
        default=None, description="Dedicated model for reasoning (uses main model if None)"
    )

    # Reasoning tools configuration
    add_instructions: bool = Field(
        default=True, description="Add reasoning instructions to ReasoningTools"
    )

    model_config = {"extra": "forbid"}


# =============================================================================
# Structured Output Policies
# =============================================================================


class StructuredOutputPolicy(BaseModel):
    """Policy for structured output generation."""

    enabled: bool = False

    # Output schema (will be set programmatically with Pydantic model)
    # This is a placeholder - actual schema is passed via output_schema parameter
    use_json_mode: bool = Field(
        default=True, description="Force JSON mode for models that support it"
    )
    strict_validation: bool = Field(
        default=True, description="Strictly validate output against schema"
    )

    model_config = {"extra": "forbid"}


# =============================================================================
# Observability & Hooks Policies
# =============================================================================


class ObservabilityPolicy(BaseModel):
    """Policy for observability, logging, and hooks."""

    enabled: bool = True

    # Tool hooks
    enable_tool_hooks: bool = Field(
        default=True, description="Enable pre/post hooks for tool calls"
    )
    log_tool_calls: bool = Field(default=True, description="Log all tool invocations")
    log_tool_results: bool = Field(default=False, description="Log tool results (may be verbose)")

    # Event streaming
    enable_event_streaming: bool = Field(
        default=True, description="Enable RunEvent streaming for real-time monitoring"
    )
    stream_reasoning_events: bool = Field(
        default=True, description="Include reasoning events in stream"
    )

    # Metrics
    collect_metrics: bool = Field(
        default=False, description="Collect execution metrics (timing, token usage)"
    )
    metrics_export_format: Literal["json", "prometheus", "none"] = "none"

    # Debug mode
    debug_mode: bool = Field(default=False, description="Enable verbose debug output")

    model_config = {"extra": "forbid"}


# =============================================================================
# Team & Multi-Agent Policies
# =============================================================================


class AgentRole(BaseModel):
    """Definition of an agent role within a team."""

    name: str = Field(..., min_length=1)
    role: str = Field(..., min_length=1, description="Role description for the agent")
    model_id: Optional[str] = Field(
        default=None, description="Model ID (uses team default if None)"
    )
    instructions: List[str] = Field(default_factory=list)
    tools: List[str] = Field(
        default_factory=list, description="Tool names to enable for this agent"
    )

    model_config = {"extra": "forbid"}


class TeamPolicy(BaseModel):
    """Policy for multi-agent team configuration."""

    enabled: bool = False

    # Team composition
    members: List[AgentRole] = Field(
        default_factory=list, description="Agent roles in the team"
    )

    # Coordination settings
    mode: Literal["coordinate", "route", "collaborate"] = Field(
        default="coordinate",
        description="coordinate: leader delegates, route: direct routing, collaborate: shared work",
    )
    share_member_interactions: bool = Field(
        default=True, description="Share interactions between team members"
    )
    show_members_responses: bool = Field(
        default=True, description="Show individual member responses"
    )

    # Team leader configuration
    leader_model_id: Optional[str] = Field(
        default=None, description="Model for team leader (uses default if None)"
    )
    leader_instructions: List[str] = Field(
        default_factory=list, description="Instructions for team leader"
    )

    # Advanced features
    get_member_information_tool: bool = Field(
        default=True, description="Add tool for leader to query member capabilities"
    )
    add_member_tools_to_context: bool = Field(
        default=True, description="Include member tool definitions in context"
    )

    model_config = {"extra": "forbid"}


# =============================================================================
# Workflow Policies
# =============================================================================


class WorkflowStep(BaseModel):
    """Definition of a workflow step."""

    name: str = Field(..., min_length=1)
    description: Optional[str] = None

    # Executor (one of these must be set)
    agent_name: Optional[str] = Field(
        default=None, description="Name of agent to execute this step"
    )
    team_name: Optional[str] = Field(
        default=None, description="Name of team to execute this step"
    )
    function_name: Optional[str] = Field(
        default=None, description="Name of function to execute this step"
    )

    # Step configuration
    depends_on: List[str] = Field(
        default_factory=list, description="Names of steps this step depends on"
    )
    retry_on_failure: bool = Field(default=True)
    max_retries: int = Field(default=2, ge=0)

    model_config = {"extra": "forbid"}

    @field_validator("agent_name")
    @classmethod
    def _validate_executor(cls, value, info):
        # At least one executor must be set
        agent = value
        team = info.data.get("team_name")
        func = info.data.get("function_name")
        if not any([agent, team, func]):
            # This will be validated at runtime when all fields are available
            pass
        return value


class WorkflowPolicy(BaseModel):
    """Policy for workflow orchestration."""

    enabled: bool = False

    # Workflow definition
    name: str = Field(default="default_workflow", min_length=1)
    description: Optional[str] = None
    steps: List[WorkflowStep] = Field(default_factory=list)

    # Execution settings
    parallel_execution: bool = Field(
        default=False, description="Execute independent steps in parallel"
    )
    stop_on_failure: bool = Field(
        default=True, description="Stop workflow on step failure"
    )

    model_config = {"extra": "forbid"}


# =============================================================================
# System Prompt Policies
# =============================================================================


class SystemPromptPolicy(BaseModel):
    """Policy for system prompt configuration."""

    # Base template
    template: Literal["default", "codeact", "research", "assistant", "custom"] = Field(
        default="default", description="Base prompt template to use"
    )
    custom_template: Optional[str] = Field(
        default=None, description="Custom template (required if template='custom')"
    )

    # Dynamic sections
    add_datetime: bool = Field(
        default=True, description="Add current datetime to context"
    )
    add_tool_descriptions: bool = Field(
        default=True, description="Add tool descriptions to prompt"
    )
    add_knowledge_context: bool = Field(
        default=True, description="Add retrieved knowledge to prompt"
    )

    # Persona
    persona: Optional[str] = Field(
        default=None, description="Agent persona/role description"
    )
    tone: Literal["professional", "friendly", "technical", "concise"] = Field(
        default="professional", description="Response tone"
    )

    model_config = {"extra": "forbid"}

    @field_validator("custom_template")
    @classmethod
    def _require_custom_template(cls, value, info):
        if info.data.get("template") == "custom" and not value:
            raise ValueError("custom_template is required when template='custom'")
        return value


# =============================================================================
# Main Agent Specification
# =============================================================================


class AgentSpec(BaseModel):
    """
    Complete specification for an agentic runtime instance.

    This is the main configuration object that combines all policies
    to define agent behavior, capabilities, and integrations.
    """

    # Version and identification
    version: str = "0.2.0"
    name: str = Field(default="agent", min_length=1)
    description: Optional[str] = None

    # Model configuration
    model_id: str = Field(default="google/gemini-3-flash-preview", min_length=1)

    # Session management
    user_id: str = Field(default="user", min_length=1)
    session_id: Optional[str] = None

    # Core policies
    context: ContextPolicy = Field(default_factory=ContextPolicy)
    tools: ToolPolicy = Field(default_factory=ToolPolicy)
    system_prompt: SystemPromptPolicy = Field(default_factory=SystemPromptPolicy)

    # Capability policies
    codeact: CodeActPolicy = Field(default_factory=CodeActPolicy)
    mcp: McpPolicy = Field(default_factory=McpPolicy)
    knowledge: KnowledgePolicy = Field(default_factory=KnowledgePolicy)
    reasoning: ReasoningPolicy = Field(default_factory=ReasoningPolicy)
    structured_output: StructuredOutputPolicy = Field(default_factory=StructuredOutputPolicy)

    # Multi-agent policies
    team: TeamPolicy = Field(default_factory=TeamPolicy)
    workflow: WorkflowPolicy = Field(default_factory=WorkflowPolicy)

    # Observability
    observability: ObservabilityPolicy = Field(default_factory=ObservabilityPolicy)

    # Structured output schema (set programmatically)
    # This allows passing a Pydantic model class for structured outputs
    _output_schema: Optional[Type[BaseModel]] = None

    model_config = {"extra": "forbid"}

    @field_validator("version")
    @classmethod
    def _version_non_empty(cls, value: str) -> str:
        if not value:
            raise ValueError("version must be non-empty")
        return value

    def with_output_schema(self, schema: Type[BaseModel]) -> "AgentSpec":
        """Set the output schema for structured outputs."""
        self._output_schema = schema
        self.structured_output.enabled = True
        return self

    @property
    def output_schema(self) -> Optional[Type[BaseModel]]:
        """Get the output schema if set."""
        return self._output_schema


# =============================================================================
# Convenience Presets
# =============================================================================


def create_basic_spec(model_id: str = "google/gemini-3-flash-preview") -> AgentSpec:
    """Create a basic agent spec with minimal configuration."""
    return AgentSpec(
        model_id=model_id,
        codeact=CodeActPolicy(enabled=False),
        mcp=McpPolicy(enabled=False),
    )


def create_codeact_spec(
    model_id: str = "google/gemini-3-flash-preview",
    max_iterations: int = 6,
) -> AgentSpec:
    """Create an agent spec optimized for code execution."""
    return AgentSpec(
        model_id=model_id,
        codeact=CodeActPolicy(
            enabled=True,
            max_iterations=max_iterations,
            enable_code_interpreter=True,
            extract_charts=True,
        ),
        system_prompt=SystemPromptPolicy(template="codeact"),
    )


def create_research_spec(
    model_id: str = "z-ai/glm-4.7",
    knowledge_sources: Optional[List[str]] = None,
) -> AgentSpec:
    """Create an agent spec optimized for research tasks."""
    return AgentSpec(
        model_id=model_id,
        knowledge=KnowledgePolicy(
            enabled=True,
            search_type="hybrid",
            content_sources=knowledge_sources or [],
        ),
        reasoning=ReasoningPolicy(enabled=True, mode="extended"),
        system_prompt=SystemPromptPolicy(template="research"),
    )


def create_team_spec(
    members: List[AgentRole],
    leader_model_id: Optional[str] = None,
) -> AgentSpec:
    """Create an agent spec for multi-agent team."""
    return AgentSpec(
        team=TeamPolicy(
            enabled=True,
            members=members,
            leader_model_id=leader_model_id,
            mode="coordinate",
        ),
    )
