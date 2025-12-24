from core.factory import build_agent
from core.policies import AgentSpec, McpPolicy, CodeActPolicy


def test_conformance_daytona_enabled():
    spec = AgentSpec(codeact=CodeActPolicy(enabled=True))
    agent = build_agent(spec)
    agent.run("Write python code to print 2+2 and execute it using the Daytona tool.")
