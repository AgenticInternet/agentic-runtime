"""
Agentic Runtime Core
====================
A state-of-the-art agentic runtime built on Agno framework.
"""

from .factory import build_agent, build_team, build_workflow
from .policies import (
    AgentRole,
    # Main spec
    AgentSpec,
    # Capability policies
    CodeActPolicy,
    CodingPolicy,
    # Core policies
    ContextPolicy,
    KnowledgePolicy,
    McpPolicy,
    McpServerConfig,
    # Observability
    ObservabilityPolicy,
    ReasoningPolicy,
    StructuredOutputPolicy,
    SystemPromptPolicy,
    # Multi-agent policies
    TeamPolicy,
    ToolPolicy,
    WorkflowPolicy,
    WorkflowStep,
    # Presets
    create_basic_spec,
    create_codeact_spec,
    create_coding_spec,
    create_research_spec,
    create_team_spec,
)

__all__ = [
    # Factories
    "build_agent",
    "build_team",
    "build_workflow",
    # Main spec
    "AgentSpec",
    # Core policies
    "ContextPolicy",
    "ToolPolicy",
    "SystemPromptPolicy",
    # Capability policies
    "CodeActPolicy",
    "McpPolicy",
    "McpServerConfig",
    "KnowledgePolicy",
    "ReasoningPolicy",
    "StructuredOutputPolicy",
    "CodingPolicy",
    # Multi-agent policies
    "TeamPolicy",
    "AgentRole",
    "WorkflowPolicy",
    "WorkflowStep",
    # Observability
    "ObservabilityPolicy",
    # Presets
    "create_basic_spec",
    "create_codeact_spec",
    "create_research_spec",
    "create_team_spec",
    "create_coding_spec",
]

__version__ = "0.2.0"
