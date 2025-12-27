"""
Reasoning Tools
===============
Tools for chain-of-thought reasoning and extended thinking.
"""

from typing import Any, List

from ..policies import AgentSpec


def build_reasoning_tools(spec: AgentSpec) -> List[Any]:
    """
    Build reasoning tools based on spec configuration.

    Args:
        spec: Agent specification with reasoning policy

    Returns:
        List of reasoning tools
    """
    if not spec.reasoning.enabled:
        return []

    tools: List[Any] = []

    try:
        from agno.tools.reasoning import ReasoningTools

        reasoning_tools = ReasoningTools(
            add_instructions=spec.reasoning.add_instructions,
        )
        tools.append(reasoning_tools)

    except ImportError as e:
        import warnings
        warnings.warn(f"Could not import reasoning tools: {e}")

    return tools
