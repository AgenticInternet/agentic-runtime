"""
Agentic Runtime Tools
=====================
Tool builders for various capabilities.
"""

from .hooks import build_tool_hooks, create_delegation_hook
from .knowledge import build_knowledge_tools
from .local import build_local_tools
from .mcp import build_mcp_tools
from .reasoning import build_reasoning_tools
from .sandbox import build_sandbox_tools


def build_daytona_tools(spec):
    """Backward-compatible lazy export for the Daytona tool builder."""
    from .daytona import build_daytona_tools as _build_daytona_tools

    return _build_daytona_tools(spec)


__all__ = [
    "build_local_tools",
    "build_sandbox_tools",
    "build_daytona_tools",
    "build_mcp_tools",
    "build_knowledge_tools",
    "build_reasoning_tools",
    "build_tool_hooks",
    "create_delegation_hook",
]
