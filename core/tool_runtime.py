import asyncio
from dataclasses import dataclass
from typing import Any, Callable, Optional

from .policies import ToolPolicy


@dataclass
class ToolResult:
    success: bool
    data: Any
    error: Optional[str] = None


class ToolRuntime:
    def __init__(self, policy: ToolPolicy):
        self.policy = policy

    async def execute(self, fn: Callable, *args, **kwargs) -> ToolResult:
        for attempt in range(self.policy.max_retries + 1):
            try:
                result = await asyncio.wait_for(
                    self._run(fn, *args, **kwargs),
                    timeout=self.policy.timeout_seconds
                )
                return ToolResult(success=True, data=self._truncate(result))
            except asyncio.TimeoutError:
                if attempt == self.policy.max_retries:
                    return self._handle_error("Tool execution timed out")
            except Exception as e:
                if attempt == self.policy.max_retries:
                    return self._handle_error(str(e))
        return self._handle_error("Max retries exceeded")

    async def _run(self, fn: Callable, *args, **kwargs) -> Any:
        if asyncio.iscoroutinefunction(fn):
            return await fn(*args, **kwargs)
        return fn(*args, **kwargs)

    def _truncate(self, result: Any) -> Any:
        if isinstance(result, str) and len(result) > self.policy.max_result_chars:
            return result[:self.policy.max_result_chars] + "...[truncated]"
        return result

    def _handle_error(self, error: str) -> ToolResult:
        if self.policy.error_strategy == "raise":
            raise RuntimeError(error)
        return ToolResult(success=False, data=None, error=error)
