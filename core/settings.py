from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    openrouter_api_key: Optional[str] = Field(default=None, alias="OPENROUTER_API_KEY")
    daytona_api_key: Optional[str] = Field(default=None, alias="DAYTONA_API_KEY")
    daytona_api_url: Optional[str] = Field(default=None, alias="DAYTONA_API_URL")
    mcp_url: Optional[str] = Field(default=None, alias="MCP_URL")

    model_config = SettingsConfigDict(
        frozen=True,
        extra="ignore",
        populate_by_name=True,
    )


settings = Settings()
