from dataclasses import dataclass, field
from typing import Literal, Optional


@dataclass
class ContextPolicy:
    enable_user_memories: bool = True
    enable_session_summaries: bool = True
    add_history_to_context: bool = True
    num_history_runs: int = 3


@dataclass
class ToolPolicy:
    timeout_seconds: float = 45.0
    max_retries: int = 2
    max_result_chars: int = 16_000
    error_strategy: Literal["structured", "raise"] = "structured"


@dataclass
class CodeActPolicy:
    enabled: bool = True
    sandbox: Literal["daytona"] = "daytona"
    max_iterations: int = 6


@dataclass
class McpPolicy:
    enabled: bool = False
    transport: str = "streamable-http"
    url: Optional[str] = None


@dataclass
class AgentSpec:
    version: str = "0.1.0"
    model_id: str = "google/gemini-3-flash-preview"
    user_id: str = "user"
    session_id: Optional[str] = None
    context: ContextPolicy = field(default_factory=ContextPolicy)
    tools: ToolPolicy = field(default_factory=ToolPolicy)
    codeact: CodeActPolicy = field(default_factory=CodeActPolicy)
    mcp: McpPolicy = field(default_factory=McpPolicy)
