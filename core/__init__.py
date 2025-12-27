"""
Agentic Runtime Core
====================
A state-of-the-art agentic runtime built on Agno framework.
"""

from .factory import build_agent, build_team, build_workflow
from .policies import (
    # Main spec
    AgentSpec,
    # Core policies
    ContextPolicy,
    ToolPolicy,
    SystemPromptPolicy,
    # Capability policies
    CodeActPolicy,
    McpPolicy,
    McpServerConfig,
    KnowledgePolicy,
    ReasoningPolicy,
    StructuredOutputPolicy,
    # Multi-agent policies
    TeamPolicy,
    AgentRole,
    WorkflowPolicy,
    WorkflowStep,
    # Observability
    ObservabilityPolicy,
    # Presets
    create_basic_spec,
    create_codeact_spec,
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
]

__version__ = "0.2.0"
