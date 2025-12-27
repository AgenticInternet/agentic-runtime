from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class ContextPolicy(BaseModel):
    enable_user_memories: bool = True
    enable_session_summaries: bool = True
    add_history_to_context: bool = True
    num_history_runs: int = Field(default=3, ge=0)

    model_config = {"extra": "forbid"}


class ToolPolicy(BaseModel):
    timeout_seconds: float = Field(default=45.0, gt=0)
    max_retries: int = Field(default=2, ge=0)
    max_result_chars: int = Field(default=16_000, gt=0)
    error_strategy: Literal["structured", "raise"] = "structured"

    model_config = {"extra": "forbid"}


class CodeActPolicy(BaseModel):
    enabled: bool = True
    sandbox: Literal["daytona"] = "daytona"
    max_iterations: int = Field(default=6, ge=1)

    model_config = {"extra": "forbid"}


class McpPolicy(BaseModel):
    enabled: bool = False
    transport: Literal["stdio", "sse", "streamable-http"] = "streamable-http"
    url: Optional[str] = None

    model_config = {"extra": "forbid"}

    @field_validator("url")
    @classmethod
    def _strip_url(cls, value: Optional[str]) -> Optional[str]:
        return value.strip() if isinstance(value, str) else value

    @field_validator("url")
    @classmethod
    def _require_url_if_enabled(cls, value: Optional[str], info):
        if info.data.get("enabled") and not value:
            raise ValueError("mcp.url is required when MCP is enabled")
        return value


class AgentSpec(BaseModel):
    version: str = "0.1.0"
    model_id: str = Field(default="google/gemini-3-flash-preview", min_length=1)
    user_id: str = Field(default="user", min_length=1)
    session_id: Optional[str] = None
    context: ContextPolicy = Field(default_factory=ContextPolicy)
    tools: ToolPolicy = Field(default_factory=ToolPolicy)
    codeact: CodeActPolicy = Field(default_factory=CodeActPolicy)
    mcp: McpPolicy = Field(default_factory=McpPolicy)

    model_config = {"extra": "forbid"}

    @field_validator("version")
    @classmethod
    def _version_non_empty(cls, value: str) -> str:
        if not value:
            raise ValueError("version must be non-empty")
        return value
