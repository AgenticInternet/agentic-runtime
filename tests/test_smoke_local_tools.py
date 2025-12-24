from core.factory import build_agent
from core.policies import AgentSpec, CodeActPolicy


def test_smoke_local():
    spec = AgentSpec(codeact=CodeActPolicy(enabled=False))
    agent = build_agent(spec)
    agent.run("Call healthcheck tool and return the JSON only.")
