import pytest
from pydantic import ValidationError

from core.policies import AgentSpec, McpPolicy, ToolPolicy


def test_mcp_policy_requires_url_when_enabled():
    with pytest.raises(ValidationError):
        McpPolicy(enabled=True, url=None)


def test_tool_policy_validates_positive_timeout_and_retries():
    with pytest.raises(ValidationError):
        ToolPolicy(timeout_seconds=0)
    with pytest.raises(ValidationError):
        ToolPolicy(max_retries=-1)


def test_agent_spec_requires_model_id():
    with pytest.raises(ValidationError):
        AgentSpec(model_id="")
