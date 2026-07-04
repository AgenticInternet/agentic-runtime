"""
Tests for Agentic Runtime Factory
=================================
Tests for agent, team, and workflow building.
"""

from typing import Any, cast, get_args

import pytest

from core import (
    AgentRole,
    AgentSpec,
    CodeActPolicy,
    CodingPolicy,
    McpPolicy,
    ModelProviderPolicy,
    ReasoningPolicy,
    SkillsPolicy,
    StoragePolicy,
    TeamPolicy,
    WorkflowPolicy,
    WorkflowStep,
    build_agent,
    build_team,
    build_workflow,
)
from core.factory import _PROVIDER_REGISTRY, _resolve_db, _resolve_model
from core.policies import ModelProvider

# =============================================================================
# Agent Factory Tests
# =============================================================================


class TestBuildAgent:
    def test_build_basic_agent(self):
        spec = AgentSpec(
            codeact=CodeActPolicy(enabled=False),
            mcp=McpPolicy(enabled=False),
        )
        agent = build_agent(spec)
        assert agent is not None
        assert agent.name == "agent"

    def test_build_agent_with_name(self):
        spec = AgentSpec(
            name="my_agent",
            description="A test agent",
            codeact=CodeActPolicy(enabled=False),
        )
        agent = build_agent(spec)
        assert agent.name == "my_agent"

    def test_build_agent_with_reasoning(self):
        spec = AgentSpec(
            codeact=CodeActPolicy(enabled=False),
            reasoning=ReasoningPolicy(enabled=True, mode="basic"),
        )
        agent = build_agent(spec)
        assert agent is not None

    def test_build_agent_with_structured_output(self):
        from pydantic import BaseModel

        class OutputSchema(BaseModel):
            answer: str
            confidence: float

        spec = AgentSpec(
            codeact=CodeActPolicy(enabled=False),
        ).with_output_schema(OutputSchema)

        agent = build_agent(spec)
        assert agent is not None

    def test_build_agent_with_skills(self, tmp_path):
        skill_dir = tmp_path / "skills" / "code-review"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            "---\n"
            "name: code-review\n"
            "description: Review code carefully.\n"
            "---\n"
            "Use careful review.\n"
        )

        spec = AgentSpec(
            codeact=CodeActPolicy(enabled=False),
            coding=CodingPolicy(enabled=True, workspace_root=str(tmp_path)),
            skills=SkillsPolicy(enabled=True, paths=["skills"]),
        )

        agent = build_agent(spec)
        skills = getattr(agent, "skills", None)
        assert skills is not None
        assert skills.get_skill_names() == ["code-review"]

    def test_build_agent_with_missing_skills_path(self, tmp_path):
        spec = AgentSpec(
            codeact=CodeActPolicy(enabled=False),
            coding=CodingPolicy(enabled=True, workspace_root=str(tmp_path)),
            skills=SkillsPolicy(enabled=True, paths=["skills"]),
        )

        with pytest.raises(FileNotFoundError, match="Skills path does not exist"):
            build_agent(spec)

    def test_build_agent_with_custom_storage(self, tmp_path):
        db_file = str(tmp_path / "custom.db")
        spec = AgentSpec(
            codeact=CodeActPolicy(enabled=False),
            mcp=McpPolicy(enabled=False),
            storage=StoragePolicy(db_file=db_file),
        )
        agent = build_agent(spec)
        assert agent is not None

    def test_build_agent_with_db_url_not_implemented(self):
        spec = AgentSpec(
            codeact=CodeActPolicy(enabled=False),
            mcp=McpPolicy(enabled=False),
            storage=StoragePolicy(db_url="sqlite:///tmp/agents.db"),
        )
        with pytest.raises(NotImplementedError, match="storage.db_url"):
            build_agent(spec)


# =============================================================================
# Team Factory Tests
# =============================================================================


class TestBuildTeam:
    def test_build_team_requires_enabled(self):
        spec = AgentSpec(team=TeamPolicy(enabled=False))
        with pytest.raises(ValueError, match="Team policy must be enabled"):
            build_team(spec)

    def test_build_team_requires_members(self):
        spec = AgentSpec(
            team=TeamPolicy(enabled=True, members=[]),
            codeact=CodeActPolicy(enabled=False),
        )
        with pytest.raises(ValueError, match="at least one member"):
            build_team(spec)

    def test_build_team_with_members(self):
        members = [
            AgentRole(name="researcher", role="Research topics"),
            AgentRole(name="writer", role="Write content"),
        ]
        spec = AgentSpec(
            name="research_team",
            team=TeamPolicy(
                enabled=True,
                members=members,
                leader_instructions=["Coordinate research and writing"],
            ),
            codeact=CodeActPolicy(enabled=False),
        )
        team = build_team(spec)
        assert team is not None
        assert len(team.members) == 2

    def test_build_team_members_with_skills(self, tmp_path):
        skill_dir = tmp_path / "skills" / "code-review"
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(
            "---\n"
            "name: code-review\n"
            "description: Review code carefully.\n"
            "---\n"
            "Use careful review.\n"
        )

        spec = AgentSpec(
            codeact=CodeActPolicy(enabled=False),
            coding=CodingPolicy(enabled=True, workspace_root=str(tmp_path)),
            skills=SkillsPolicy(enabled=True, paths=["skills"]),
            team=TeamPolicy(
                enabled=True,
                members=[AgentRole(name="researcher", role="Research topics")],
            ),
        )

        team = build_team(spec)
        skills = getattr(team.members[0], "skills", None)
        assert skills is not None
        assert skills.get_skill_names() == ["code-review"]


# =============================================================================
# Workflow Factory Tests
# =============================================================================


class TestBuildWorkflow:
    def test_build_workflow_requires_enabled(self):
        spec = AgentSpec(workflow=WorkflowPolicy(enabled=False))
        with pytest.raises(ValueError, match="Workflow policy must be enabled"):
            build_workflow(spec)

    def test_build_workflow_requires_valid_agents(self):
        spec = AgentSpec(
            workflow=WorkflowPolicy(
                enabled=True,
                steps=[
                    WorkflowStep(name="step1", agent_name="nonexistent"),
                ],
            ),
        )
        with pytest.raises(ValueError, match="not found"):
            build_workflow(spec, agents={})

    def test_build_workflow_with_agents(self):
        agent_spec = AgentSpec(
            name="test_agent",
            codeact=CodeActPolicy(enabled=False),
        )
        test_agent = build_agent(agent_spec)

        workflow_spec = AgentSpec(
            workflow=WorkflowPolicy(
                enabled=True,
                name="test_workflow",
                steps=[
                    WorkflowStep(name="step1", agent_name="test_agent"),
                ],
            ),
        )
        workflow = build_workflow(
            workflow_spec,
            agents={"test_agent": test_agent},
        )
        assert workflow is not None
        assert workflow.name == "test_workflow"


# =============================================================================
# Tool Building Tests
# =============================================================================


class TestToolBuilding:
    def test_local_tools_always_included(self):
        spec = AgentSpec(
            codeact=CodeActPolicy(enabled=False),
            mcp=McpPolicy(enabled=False),
        )
        agent = build_agent(spec)
        assert len(agent.tools) >= 1

    def test_daytona_tools_when_enabled(self):
        spec = AgentSpec(
            codeact=CodeActPolicy(enabled=True),
            mcp=McpPolicy(enabled=False),
        )
        agent = build_agent(spec)
        assert len(agent.tools) >= 2

    def test_local_sandbox_returns_no_tools(self):
        spec = AgentSpec(
            codeact=CodeActPolicy(enabled=True, sandbox="local"),
            mcp=McpPolicy(enabled=False),
        )
        agent = build_agent(spec)
        assert len(agent.tools) >= 1

    def test_docker_sandbox_not_implemented(self):
        spec = AgentSpec(
            codeact=CodeActPolicy(enabled=True, sandbox="docker"),
            mcp=McpPolicy(enabled=False),
        )
        with pytest.raises(NotImplementedError, match="Docker sandbox"):
            build_agent(spec)


# =============================================================================
# Model Provider Resolution Tests
# =============================================================================


class TestModelResolution:
    def test_default_provider_is_openrouter(self):
        spec = AgentSpec()
        assert spec.model_provider.provider == "openrouter"

    def test_resolve_model_openrouter(self):
        model = _resolve_model("google/gemini-3-flash-preview", "openrouter")
        assert model is not None
        assert model.id == "google/gemini-3-flash-preview"

    def test_resolve_model_unknown_provider_raises(self):
        with pytest.raises(ValueError, match="Unknown model provider"):
            _resolve_model("test-model", cast(Any, "nonexistent_provider"))

    def test_resolve_model_propagates_kwargs(self):
        model = _resolve_model("gpt-4o", "openrouter", api_key="test-key")
        assert model is not None

    def test_all_registry_entries_have_valid_format(self):
        for provider, (module_path, class_name) in _PROVIDER_REGISTRY.items():
            assert "." in module_path, f"Provider {provider} has invalid module path"
            assert class_name, f"Provider {provider} has empty class name"

    def test_provider_registry_matches_literal(self):
        assert set(_PROVIDER_REGISTRY) == set(get_args(ModelProvider))

    def test_build_agent_with_explicit_provider(self):
        spec = AgentSpec(
            model_id="google/gemini-3-flash-preview",
            model_provider=ModelProviderPolicy(provider="openrouter"),
            codeact=CodeActPolicy(enabled=False),
            mcp=McpPolicy(enabled=False),
        )
        agent = build_agent(spec)
        assert agent is not None
        assert getattr(agent.model, "id", None) == "google/gemini-3-flash-preview"

    def test_resolve_db_creates_nested_parent_directory(self, tmp_path):
        db_file = tmp_path / "nested" / "state" / "agents.db"
        spec = AgentSpec(storage=StoragePolicy(db_file=str(db_file)))
        _resolve_db(spec)
        assert db_file.parent.exists()
