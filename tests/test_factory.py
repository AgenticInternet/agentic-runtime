"""
Tests for Agentic Runtime Factory
=================================
Tests for agent, team, and workflow building.
"""

import pytest

from core import (
    AgentRole,
    AgentSpec,
    CodeActPolicy,
    McpPolicy,
    ReasoningPolicy,
    TeamPolicy,
    WorkflowPolicy,
    WorkflowStep,
    build_agent,
    build_team,
    build_workflow,
)

# =============================================================================
# Agent Factory Tests
# =============================================================================


class TestBuildAgent:
    def test_build_basic_agent(self):
        """Test building a basic agent without tools."""
        spec = AgentSpec(
            codeact=CodeActPolicy(enabled=False),
            mcp=McpPolicy(enabled=False),
        )
        agent = build_agent(spec)
        assert agent is not None
        assert agent.name == "agent"

    def test_build_agent_with_name(self):
        """Test building an agent with custom name."""
        spec = AgentSpec(
            name="my_agent",
            description="A test agent",
            codeact=CodeActPolicy(enabled=False),
        )
        agent = build_agent(spec)
        assert agent.name == "my_agent"

    def test_build_agent_with_reasoning(self):
        """Test building an agent with reasoning enabled."""
        spec = AgentSpec(
            codeact=CodeActPolicy(enabled=False),
            reasoning=ReasoningPolicy(enabled=True, mode="basic"),
        )
        agent = build_agent(spec)
        assert agent is not None

    def test_build_agent_with_structured_output(self):
        """Test building an agent with structured output."""
        from pydantic import BaseModel

        class OutputSchema(BaseModel):
            answer: str
            confidence: float

        spec = AgentSpec(
            codeact=CodeActPolicy(enabled=False),
        ).with_output_schema(OutputSchema)

        agent = build_agent(spec)
        assert agent is not None


# =============================================================================
# Team Factory Tests
# =============================================================================


class TestBuildTeam:
    def test_build_team_requires_enabled(self):
        """Test that build_team requires team policy to be enabled."""
        spec = AgentSpec(team=TeamPolicy(enabled=False))
        with pytest.raises(ValueError, match="Team policy must be enabled"):
            build_team(spec)

    def test_build_team_requires_members(self):
        """Test that build_team requires at least one member."""
        spec = AgentSpec(
            team=TeamPolicy(enabled=True, members=[]),
            codeact=CodeActPolicy(enabled=False),
        )
        with pytest.raises(ValueError, match="at least one member"):
            build_team(spec)

    def test_build_team_with_members(self):
        """Test building a team with members."""
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


# =============================================================================
# Workflow Factory Tests
# =============================================================================


class TestBuildWorkflow:
    def test_build_workflow_requires_enabled(self):
        """Test that build_workflow requires workflow policy to be enabled."""
        spec = AgentSpec(workflow=WorkflowPolicy(enabled=False))
        with pytest.raises(ValueError, match="Workflow policy must be enabled"):
            build_workflow(spec)

    def test_build_workflow_requires_valid_agents(self):
        """Test that build_workflow validates agent references."""
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
        """Test building a workflow with agents."""
        # First create agents
        agent_spec = AgentSpec(
            name="test_agent",
            codeact=CodeActPolicy(enabled=False),
        )
        test_agent = build_agent(agent_spec)

        # Then create workflow
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
        """Test that local tools are always included."""
        spec = AgentSpec(
            codeact=CodeActPolicy(enabled=False),
            mcp=McpPolicy(enabled=False),
        )
        agent = build_agent(spec)
        # Agent should have at least the healthcheck tool
        assert len(agent.tools) >= 1

    def test_daytona_tools_when_enabled(self):
        """Test that Daytona tools are included when codeact is enabled."""
        spec = AgentSpec(
            codeact=CodeActPolicy(enabled=True),
            mcp=McpPolicy(enabled=False),
        )
        agent = build_agent(spec)
        # Should have local tools + Daytona tools
        assert len(agent.tools) >= 2
