"""
Agentic Runtime Factory
=======================
Factory functions for building agents, teams, and workflows.
"""

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type

from dotenv import load_dotenv

load_dotenv()

from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.models.openrouter import OpenRouter
from agno.team import Team
from agno.workflow.step import Step
from agno.workflow.workflow import Workflow

from .policies import AgentSpec, AgentRole
from .tools.local import build_local_tools
from .tools.daytona import build_daytona_tools
from .tools.mcp import build_mcp_tools
from .tools.knowledge import build_knowledge_tools
from .tools.reasoning import build_reasoning_tools
from .tools.hooks import build_tool_hooks
from .prompts.system import build_system_prompt


def _ensure_db_dir() -> SqliteDb:
    """Ensure database directory exists and return SqliteDb instance."""
    Path("tmp").mkdir(parents=True, exist_ok=True)
    return SqliteDb(db_file="tmp/agents.db")


def _build_tools(spec: AgentSpec) -> List[Any]:
    """Build all tools based on spec configuration."""
    tools = []

    # Always include local tools
    tools.extend(build_local_tools())

    # MCP tools
    if spec.mcp.enabled:
        tools.extend(build_mcp_tools(spec))

    # Daytona/CodeAct tools
    if spec.codeact.enabled:
        tools.extend(build_daytona_tools(spec))

    # Knowledge/RAG tools
    if spec.knowledge.enabled:
        tools.extend(build_knowledge_tools(spec))

    # Reasoning tools
    if spec.reasoning.enabled and spec.reasoning.mode == "tools":
        tools.extend(build_reasoning_tools(spec))

    return tools


def _build_tool_hooks(spec: AgentSpec) -> Optional[List[Callable]]:
    """Build tool hooks based on observability policy."""
    if not spec.observability.enabled or not spec.observability.enable_tool_hooks:
        return None
    return build_tool_hooks(spec)


def build_agent(
    spec: AgentSpec,
    db: Optional[SqliteDb] = None,
) -> Agent:
    """
    Build an Agno Agent from specification.

    Args:
        spec: Agent specification with all policies
        db: Optional database instance (creates default if None)

    Returns:
        Configured Agno Agent instance
    """
    if db is None:
        db = _ensure_db_dir()

    tools = _build_tools(spec)
    tool_hooks = _build_tool_hooks(spec)
    instructions = build_system_prompt(spec)

    # Build agent kwargs
    agent_kwargs: Dict[str, Any] = {
        "model": OpenRouter(id=spec.model_id),
        "tools": tools,
        "db": db,
        "user_id": spec.user_id,
        "session_id": spec.session_id,
        "instructions": instructions,
        "enable_user_memories": spec.context.enable_user_memories,
        "enable_session_summaries": spec.context.enable_session_summaries,
        "add_history_to_context": spec.context.add_history_to_context,
        "num_history_runs": spec.context.num_history_runs,
        "markdown": True,
    }

    # Add name and description if provided
    if spec.name:
        agent_kwargs["name"] = spec.name
    if spec.description:
        agent_kwargs["description"] = spec.description

    # Add tool hooks if configured
    if tool_hooks:
        agent_kwargs["tool_hooks"] = tool_hooks

    # Add reasoning if enabled (basic mode)
    if spec.reasoning.enabled and spec.reasoning.mode in ("basic", "extended"):
        agent_kwargs["reasoning"] = True

    # Add structured output schema if configured
    if spec.structured_output.enabled and spec.output_schema:
        agent_kwargs["output_schema"] = spec.output_schema
        if spec.structured_output.use_json_mode:
            agent_kwargs["use_json_mode"] = True

    # Add debug mode if enabled
    if spec.observability.debug_mode:
        agent_kwargs["debug_mode"] = True

    # Add datetime to context if configured
    if spec.system_prompt.add_datetime:
        agent_kwargs["add_datetime_to_context"] = True

    return Agent(**agent_kwargs)


def _build_team_member(
    role: AgentRole,
    spec: AgentSpec,
    db: SqliteDb,
) -> Agent:
    """Build a team member agent from role definition."""
    # Use role-specific model or fall back to spec default
    model_id = role.model_id or spec.model_id

    # Build tools for this member
    member_tools = build_local_tools()

    # Add specific tools based on role configuration
    for tool_name in role.tools:
        if tool_name == "daytona" and spec.codeact.enabled:
            member_tools.extend(build_daytona_tools(spec))
        elif tool_name == "mcp" and spec.mcp.enabled:
            member_tools.extend(build_mcp_tools(spec))
        elif tool_name == "knowledge" and spec.knowledge.enabled:
            member_tools.extend(build_knowledge_tools(spec))
        elif tool_name == "reasoning":
            member_tools.extend(build_reasoning_tools(spec))

    return Agent(
        name=role.name,
        role=role.role,
        model=OpenRouter(id=model_id),
        tools=member_tools,
        instructions=role.instructions if role.instructions else None,
        markdown=True,
    )


def build_team(
    spec: AgentSpec,
    db: Optional[SqliteDb] = None,
) -> Team:
    """
    Build an Agno Team from specification.

    Args:
        spec: Agent specification with team policy configured
        db: Optional database instance (creates default if None)

    Returns:
        Configured Agno Team instance
    """
    if not spec.team.enabled:
        raise ValueError("Team policy must be enabled to build a team")

    if db is None:
        db = _ensure_db_dir()

    # Build team members
    members = [
        _build_team_member(role, spec, db) for role in spec.team.members
    ]

    if not members:
        raise ValueError("Team must have at least one member")

    # Build team leader model
    leader_model_id = spec.team.leader_model_id or spec.model_id

    # Build tool hooks for team
    tool_hooks = _build_tool_hooks(spec)

    # Build team kwargs
    team_kwargs: Dict[str, Any] = {
        "model": OpenRouter(id=leader_model_id),
        "members": members,
        "db": db,
        "share_member_interactions": spec.team.share_member_interactions,
        "show_members_responses": spec.team.show_members_responses,
        "markdown": True,
    }

    # Add team name if provided
    if spec.name:
        team_kwargs["name"] = spec.name

    # Add leader instructions
    if spec.team.leader_instructions:
        team_kwargs["instructions"] = spec.team.leader_instructions

    # Add tool hooks if configured
    if tool_hooks:
        team_kwargs["tool_hooks"] = tool_hooks

    # Add member information tool
    if spec.team.get_member_information_tool:
        team_kwargs["get_member_information_tool"] = True

    # Add member tools to context
    if spec.team.add_member_tools_to_context:
        team_kwargs["add_member_tools_to_context"] = True

    # Add debug mode if enabled
    if spec.observability.debug_mode:
        team_kwargs["debug_mode"] = True

    return Team(**team_kwargs)


def build_workflow(
    spec: AgentSpec,
    agents: Optional[Dict[str, Agent]] = None,
    teams: Optional[Dict[str, Team]] = None,
    functions: Optional[Dict[str, Callable]] = None,
    db: Optional[SqliteDb] = None,
) -> Workflow:
    """
    Build an Agno Workflow from specification.

    Args:
        spec: Agent specification with workflow policy configured
        agents: Dictionary of named agents for workflow steps
        teams: Dictionary of named teams for workflow steps
        functions: Dictionary of named functions for workflow steps
        db: Optional database instance (creates default if None)

    Returns:
        Configured Agno Workflow instance
    """
    if not spec.workflow.enabled:
        raise ValueError("Workflow policy must be enabled to build a workflow")

    if db is None:
        db = _ensure_db_dir()

    agents = agents or {}
    teams = teams or {}
    functions = functions or {}

    # Build workflow steps
    steps = []
    for step_config in spec.workflow.steps:
        step_kwargs: Dict[str, Any] = {"name": step_config.name}

        if step_config.description:
            step_kwargs["description"] = step_config.description

        # Determine executor
        if step_config.agent_name:
            if step_config.agent_name not in agents:
                raise ValueError(f"Agent '{step_config.agent_name}' not found for step '{step_config.name}'")
            step_kwargs["agent"] = agents[step_config.agent_name]
        elif step_config.team_name:
            if step_config.team_name not in teams:
                raise ValueError(f"Team '{step_config.team_name}' not found for step '{step_config.name}'")
            step_kwargs["team"] = teams[step_config.team_name]
        elif step_config.function_name:
            if step_config.function_name not in functions:
                raise ValueError(f"Function '{step_config.function_name}' not found for step '{step_config.name}'")
            step_kwargs["function"] = functions[step_config.function_name]
        else:
            raise ValueError(f"Step '{step_config.name}' must have an agent, team, or function")

        steps.append(Step(**step_kwargs))

    # Build workflow
    return Workflow(
        name=spec.workflow.name,
        description=spec.workflow.description,
        db=db,
        steps=steps,
    )
