"""
Agentic Runtime Factory
=======================
Factory functions for building agents, teams, and workflows.
"""

import importlib
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union
from uuid import uuid4

from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.team import Team
from agno.workflow.step import Step
from agno.workflow.workflow import Workflow
from dotenv import load_dotenv
from pydantic import SecretStr
from sqlalchemy import create_engine

from .durability import (
    DurableAgent,
    DurableRunner,
    RunJournal,
    RunState,
    build_durable_tool_hook,
)
from .policies import AgentRole, AgentSpec, ModelProvider
from .prompts.system import build_system_prompt
from .tools.coding import build_coding_tools
from .tools.git import build_git_tools
from .tools.hooks import build_tool_hooks
from .tools.knowledge import build_knowledge_tools
from .tools.local import build_local_tools
from .tools.mcp import build_mcp_tools
from .tools.reasoning import build_reasoning_tools
from .tools.sandbox import build_sandbox_tools

load_dotenv()

# =============================================================================
# Model Provider Registry
# =============================================================================

_PROVIDER_REGISTRY: Dict[ModelProvider, tuple[str, str]] = {
    "openrouter": ("agno.models.openrouter", "OpenRouter"),
    "openai": ("agno.models.openai", "OpenAIChat"),
    "anthropic": ("agno.models.anthropic", "Claude"),
    "google": ("agno.models.google", "Gemini"),
    "ollama": ("agno.models.ollama", "Ollama"),
    "groq": ("agno.models.groq", "Groq"),
    "deepseek": ("agno.models.deepseek", "DeepSeek"),
    "mistral": ("agno.models.mistral", "MistralChat"),
    "xai": ("agno.models.xai", "xAI"),
}


def _resolve_model(model_id: str, provider: ModelProvider = "openrouter", **kwargs: Any) -> Any:
    """Resolve a model_id + provider into an Agno model instance.

    Uses lazy imports so that only the provider packages actually needed
    must be installed.
    """
    entry = _PROVIDER_REGISTRY.get(provider)
    if entry is None:
        supported = ", ".join(sorted(_PROVIDER_REGISTRY))
        raise ValueError(f"Unknown model provider '{provider}'. Supported: {supported}")

    module_path, class_name = entry
    try:
        module = importlib.import_module(module_path)
    except ImportError as exc:
        raise ImportError(
            f"Provider '{provider}' requires the '{module_path}' package. "
            f"Install it or choose a different provider. Original error: {exc}"
        ) from exc

    model_class = getattr(module, class_name, None)
    if model_class is None:
        raise AttributeError(
            f"Module '{module_path}' has no class '{class_name}' "
            f"(provider: '{provider}'). Check _PROVIDER_REGISTRY."
        )
    return model_class(id=model_id, **kwargs)


# =============================================================================
# Storage Backend
# =============================================================================


def _resolve_db(spec: AgentSpec) -> SqliteDb:
    """Create a database instance from the storage policy."""
    storage = spec.storage
    if storage.db_url is not None:
        raise NotImplementedError(
            "Remote database support via storage.db_url is not yet implemented. "
            "Use storage.db_file for SQLite storage."
        )
    if storage.backend == "sqlite":
        Path(storage.db_file).parent.mkdir(parents=True, exist_ok=True)
        return SqliteDb(db_file=storage.db_file)
    raise ValueError(f"Unsupported storage backend: {storage.backend}")


# =============================================================================
# Internal Builders
# =============================================================================


def _build_tools(spec: AgentSpec) -> List[Any]:
    """Build all tools based on spec configuration."""
    tools = []

    tools.extend(build_local_tools())

    if spec.mcp.enabled:
        tools.extend(build_mcp_tools(spec))

    if spec.codeact.enabled:
        tools.extend(build_sandbox_tools(spec))

    if spec.knowledge.enabled:
        tools.extend(build_knowledge_tools(spec))

    if spec.reasoning.enabled and spec.reasoning.mode == "tools":
        tools.extend(build_reasoning_tools(spec))

    if spec.coding.enabled:
        tools.extend(build_coding_tools(spec))
        tools.extend(build_git_tools(spec))

    return tools


def _build_skills(spec: AgentSpec) -> Optional[Any]:
    """Build Agno skills from local filesystem loaders."""
    if not spec.skills.enabled:
        return None

    try:
        from agno.skills import LocalSkills, Skills
    except ImportError as exc:
        raise ImportError(
            "Skills support requires an Agno version that provides agno.skills"
        ) from exc

    base_path = Path(spec.coding.workspace_root if spec.coding.enabled else ".").expanduser()
    loaders = []

    for skill_path in spec.skills.paths:
        resolved_path = Path(skill_path).expanduser()
        if not resolved_path.is_absolute():
            resolved_path = base_path / resolved_path

        resolved_path = resolved_path.resolve()
        if not resolved_path.exists():
            raise FileNotFoundError(f"Skills path does not exist: {resolved_path}")

        loaders.append(LocalSkills(str(resolved_path), validate=spec.skills.validate_on_load))

    return Skills(loaders=loaders)


def _build_tool_hooks(
    spec: AgentSpec,
    durable_hook: Optional[Callable] = None,
) -> Optional[List[Callable]]:
    """Build tool hooks, composing durability and observability hooks."""
    hooks: List[Callable] = []

    if durable_hook is not None:
        hooks.append(durable_hook)

    if spec.observability.enabled and spec.observability.enable_tool_hooks:
        hooks.extend(build_tool_hooks(spec))

    return hooks if hooks else None


def _create_journal_engine(spec: AgentSpec, db: SqliteDb) -> Any:
    """Create the SQLAlchemy engine for the durability journal."""
    if spec.durability.journal_db_file:
        Path(spec.durability.journal_db_file).parent.mkdir(parents=True, exist_ok=True)
        return create_engine(f"sqlite:///{spec.durability.journal_db_file}")
    return db.db_engine


def _model_kwargs(spec: AgentSpec) -> Dict[str, Any]:
    """Build kwargs dict for _resolve_model from spec.model_provider."""
    kwargs: Dict[str, Any] = {}
    mp = spec.model_provider
    if mp.api_key:
        kwargs["api_key"] = (
            mp.api_key.get_secret_value() if isinstance(mp.api_key, SecretStr) else mp.api_key
        )
    if mp.base_url:
        kwargs["base_url"] = mp.base_url
    conflicts = set(kwargs) & set(mp.extra)
    if conflicts:
        conflict_list = ", ".join(sorted(conflicts))
        raise ValueError(f"model_provider.extra cannot override explicit fields: {conflict_list}")
    kwargs.update(mp.extra)
    return kwargs


# =============================================================================
# Public Factory Functions
# =============================================================================


def build_agent(
    spec: AgentSpec,
    db: Optional[SqliteDb] = None,
) -> Union[Agent, DurableAgent]:
    """
    Build an Agno Agent from specification.

    When spec.durability.enabled is True, returns a DurableAgent that
    wraps the Agno Agent with journal-backed checkpoint and resume.

    Args:
        spec: Agent specification with all policies
        db: Optional database instance (creates default if None)

    Returns:
        Configured Agno Agent (or DurableAgent when durability is enabled)
    """
    if db is None:
        db = _resolve_db(spec)

    durable_hook = None
    journal = None
    run_state = None

    if spec.durability.enabled:
        engine = _create_journal_engine(spec, db)
        journal = RunJournal(engine, schema_version=spec.durability.schema_version)
        run_state = RunState(
            run_id=spec.session_id or str(uuid4()),
            session_id=spec.session_id,
        )
        durable_hook = build_durable_tool_hook(journal, run_state)

    tools = _build_tools(spec)
    skills = _build_skills(spec)
    tool_hooks = _build_tool_hooks(spec, durable_hook=durable_hook)
    instructions = build_system_prompt(spec)

    mk = _model_kwargs(spec)
    agent_kwargs: Dict[str, Any] = {
        "model": _resolve_model(spec.model_id, spec.model_provider.provider, **mk),
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

    if skills is not None:
        agent_kwargs["skills"] = skills

    if spec.name:
        agent_kwargs["name"] = spec.name
    if spec.description:
        agent_kwargs["description"] = spec.description

    if tool_hooks:
        agent_kwargs["tool_hooks"] = tool_hooks

    if spec.reasoning.enabled and spec.reasoning.mode in ("basic", "extended"):
        agent_kwargs["reasoning"] = True

    if spec.structured_output.enabled and spec.output_schema:
        agent_kwargs["output_schema"] = spec.output_schema
        if spec.structured_output.use_json_mode:
            agent_kwargs["use_json_mode"] = True

    if spec.observability.debug_mode:
        agent_kwargs["debug_mode"] = True

    if spec.system_prompt.add_datetime:
        agent_kwargs["add_datetime_to_context"] = True

    agent = Agent(**agent_kwargs)

    if spec.durability.enabled and journal is not None and run_state is not None:
        runner = DurableRunner(agent, journal, spec.durability, run_state=run_state)
        return DurableAgent(agent, runner)

    return agent


def _build_team_member(
    role: AgentRole,
    spec: AgentSpec,
    db: SqliteDb,
    skills: Optional[Any] = None,
) -> Agent:
    """Build a team member agent from role definition."""
    model_id = role.model_id or spec.model_id

    member_tools = build_local_tools()

    for tool_name in role.tools:
        if tool_name in ("daytona", "sandbox") and spec.codeact.enabled:
            member_tools.extend(build_sandbox_tools(spec))
        elif tool_name == "mcp" and spec.mcp.enabled:
            member_tools.extend(build_mcp_tools(spec))
        elif tool_name == "knowledge" and spec.knowledge.enabled:
            member_tools.extend(build_knowledge_tools(spec))
        elif tool_name == "reasoning":
            member_tools.extend(build_reasoning_tools(spec))

    mk = _model_kwargs(spec)
    member_kwargs: Dict[str, Any] = {
        "name": role.name,
        "role": role.role,
        "model": _resolve_model(model_id, spec.model_provider.provider, **mk),
        "tools": member_tools,
        "instructions": role.instructions if role.instructions else None,
        "markdown": True,
    }

    if skills is not None:
        member_kwargs["skills"] = skills

    return Agent(**member_kwargs)


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
        db = _resolve_db(spec)

    skills = _build_skills(spec)
    members = [_build_team_member(role, spec, db, skills=skills) for role in spec.team.members]

    if not members:
        raise ValueError("Team must have at least one member")

    leader_model_id = spec.team.leader_model_id or spec.model_id

    tool_hooks = _build_tool_hooks(spec)

    mk = _model_kwargs(spec)
    team_kwargs: Dict[str, Any] = {
        "model": _resolve_model(leader_model_id, spec.model_provider.provider, **mk),
        "members": members,
        "db": db,
        "share_member_interactions": spec.team.share_member_interactions,
        "show_members_responses": spec.team.show_members_responses,
        "markdown": True,
    }

    if spec.name:
        team_kwargs["name"] = spec.name

    if spec.team.leader_instructions:
        team_kwargs["instructions"] = spec.team.leader_instructions

    if tool_hooks:
        team_kwargs["tool_hooks"] = tool_hooks

    if spec.team.get_member_information_tool:
        team_kwargs["get_member_information_tool"] = True

    if spec.team.add_member_tools_to_context:
        team_kwargs["add_member_tools_to_context"] = True

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
        db = _resolve_db(spec)

    agents = agents or {}
    teams = teams or {}
    functions = functions or {}

    steps = []
    for step_config in spec.workflow.steps:
        step_kwargs: Dict[str, Any] = {"name": step_config.name}

        if step_config.description:
            step_kwargs["description"] = step_config.description

        if step_config.agent_name:
            if step_config.agent_name not in agents:
                raise ValueError(
                    f"Agent '{step_config.agent_name}' not found for step '{step_config.name}'"
                )
            step_kwargs["agent"] = agents[step_config.agent_name]
        elif step_config.team_name:
            if step_config.team_name not in teams:
                raise ValueError(
                    f"Team '{step_config.team_name}' not found for step '{step_config.name}'"
                )
            step_kwargs["team"] = teams[step_config.team_name]
        elif step_config.function_name:
            if step_config.function_name not in functions:
                raise ValueError(
                    f"Function '{step_config.function_name}' not found for step '{step_config.name}'"
                )
            step_kwargs["function"] = functions[step_config.function_name]
        else:
            raise ValueError(f"Step '{step_config.name}' must have an agent, team, or function")

        steps.append(Step(**step_kwargs))

    return Workflow(
        name=spec.workflow.name,
        description=spec.workflow.description,
        db=db,
        steps=steps,
    )
