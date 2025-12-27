"""
Daytona Sandbox Tools
=====================
Enhanced code execution tools using Daytona sandbox.
"""

from typing import Any, List

from agno.tools.daytona import DaytonaTools

from ..policies import AgentSpec


def build_daytona_tools(spec: AgentSpec) -> List[Any]:
    """
    Build Daytona sandbox tools based on spec configuration.

    Features:
    - Secure code execution in isolated sandbox
    - Stateful code interpreter with context persistence
    - Automatic chart/artifact extraction
    - Auto-install missing packages

    Args:
        spec: Agent specification with codeact policy

    Returns:
        List containing configured DaytonaTools
    """
    if not spec.codeact.enabled:
        return []

    # Build DaytonaTools with enhanced configuration
    daytona_tools = DaytonaTools(
        auto_stop_interval=spec.codeact.sandbox_timeout_minutes,
        persistent=True,  # Keep sandbox alive across calls in session
    )

    return [daytona_tools]
