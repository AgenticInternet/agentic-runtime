"""
Tool Hooks
==========
Observability hooks for monitoring and logging tool execution.
"""

import time
from typing import Any, Callable, Dict, List

from ..policies import AgentSpec


def build_tool_hooks(spec: AgentSpec) -> List[Callable]:
    """
    Build tool hooks based on observability policy.

    Args:
        spec: Agent specification with observability policy

    Returns:
        List of hook functions
    """
    hooks: List[Callable] = []

    if spec.observability.log_tool_calls:
        hooks.append(_create_logger_hook(spec))

    if spec.observability.collect_metrics:
        hooks.append(_create_metrics_hook(spec))

    return hooks


def _create_logger_hook(spec: AgentSpec) -> Callable:
    """Create a logging hook for tool calls."""

    def logger_hook(
        function_name: str,
        function_call: Callable,
        arguments: Dict[str, Any],
    ) -> Any:
        """
        Hook that logs function calls and measures execution time.

        Args:
            function_name: Name of the function being called
            function_call: The actual function to call
            arguments: Arguments passed to the function

        Returns:
            The result of the function call
        """
        from agno.utils.log import logger

        # Log function start
        if spec.observability.debug_mode:
            logger.debug(f"[TOOL] Starting: {function_name}")
            logger.debug(f"[TOOL] Arguments: {arguments}")

        # Start timer
        start_time = time.time()

        try:
            # Execute the function
            result = function_call(**arguments)

            # Calculate duration
            duration = time.time() - start_time

            # Log completion
            logger.info(f"[TOOL] {function_name} completed in {duration:.2f}s")

            if spec.observability.log_tool_results and spec.observability.debug_mode:
                # Truncate result for logging
                result_str = str(result)
                if len(result_str) > 500:
                    result_str = result_str[:500] + "..."
                logger.debug(f"[TOOL] Result: {result_str}")

            return result

        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"[TOOL] {function_name} failed after {duration:.2f}s: {e}")
            raise

    return logger_hook


def _create_metrics_hook(spec: AgentSpec) -> Callable:
    """Create a metrics collection hook for tool calls."""

    # Simple in-memory metrics storage
    metrics: Dict[str, List[Dict[str, Any]]] = {}

    def metrics_hook(
        function_name: str,
        function_call: Callable,
        arguments: Dict[str, Any],
    ) -> Any:
        """
        Hook that collects execution metrics.

        Args:
            function_name: Name of the function being called
            function_call: The actual function to call
            arguments: Arguments passed to the function

        Returns:
            The result of the function call
        """
        start_time = time.time()
        success = True
        error_msg = None

        try:
            result = function_call(**arguments)
            return result
        except Exception as e:
            success = False
            error_msg = str(e)
            raise
        finally:
            duration = time.time() - start_time

            # Record metrics
            if function_name not in metrics:
                metrics[function_name] = []

            metrics[function_name].append({
                "timestamp": start_time,
                "duration_seconds": duration,
                "success": success,
                "error": error_msg,
            })

    return metrics_hook


def create_delegation_hook() -> Callable:
    """Create a hook specifically for team delegation logging."""

    def delegation_hook(
        function_name: str,
        function_call: Callable,
        arguments: Dict[str, Any],
    ) -> Any:
        """Hook that logs team delegation events."""
        from agno.utils.log import logger

        member_id = "unknown"
        if function_name == "delegate_task_to_member":
            member_id = arguments.get("member_id", "unknown")
            task = arguments.get("task", "")[:100]
            logger.info(f"[TEAM] Delegating to {member_id}: {task}...")

        result = function_call(**arguments)

        if function_name == "delegate_task_to_member":
            logger.info(f"[TEAM] Delegation to {member_id} completed")

        return result

    return delegation_hook
