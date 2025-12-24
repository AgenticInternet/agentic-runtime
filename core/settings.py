import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class Settings:
    openrouter_api_key: Optional[str] = None
    daytona_api_key: Optional[str] = None
    daytona_api_url: Optional[str] = None
    mcp_url: Optional[str] = None

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            openrouter_api_key=os.getenv("OPENROUTER_API_KEY"),
            daytona_api_key=os.getenv("DAYTONA_API_KEY"),
            daytona_api_url=os.getenv("DAYTONA_API_URL"),
            mcp_url=os.getenv("MCP_URL"),
        )


settings = Settings.from_env()
