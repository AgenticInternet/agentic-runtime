"""
Sandbox Tools Dispatcher
========================
Routes to the appropriate sandbox backend based on CodeActPolicy.sandbox.
"""

from typing import Any, List

from ..policies import AgentSpec

__all__ = ["build_sandbox_tools"]


def build_sandbox_tools(spec: AgentSpec) -> List[Any]:
    """Build sandbox tools based on ``spec.codeact.sandbox``.

    Dispatches to the correct backend builder. Currently supported:
      - ``daytona`` — Daytona remote sandbox (agno.tools.daytona)
      - ``local``   — No sandbox tools (agent runs without sandboxing)
      - ``docker``  — Placeholder for future Docker-based sandbox
    """
    if not spec.codeact.enabled:
        return []

    sandbox = spec.codeact.sandbox

    if sandbox == "daytona":
        from .daytona import build_daytona_tools

        return build_daytona_tools(spec)

    if sandbox == "local":
        return []

    if sandbox == "docker":
        raise NotImplementedError("Docker sandbox support is not yet implemented")

    raise ValueError(f"Unsupported sandbox backend '{sandbox}'. Supported: daytona, local, docker")
