from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from agno.agent import Agent
from agno.db.sqlite import SqliteDb
from agno.models.openrouter import OpenRouter

from .policies import AgentSpec
from .tools.local import build_local_tools
from .tools.daytona import build_daytona_tools
from .tools.mcp import build_mcp_tools
from .prompts.system import DEFAULT_SYSTEM_INSTRUCTIONS


def build_agent(spec: AgentSpec) -> Agent:
    Path("tmp").mkdir(parents=True, exist_ok=True)
    db = SqliteDb(db_file="tmp/agents.db")

    tools = []
    tools.extend(build_local_tools())
    if spec.mcp.enabled:
        tools.extend(build_mcp_tools(spec))
    if spec.codeact.enabled:
        tools.extend(build_daytona_tools(spec))

    return Agent(
        model=OpenRouter(id=spec.model_id),
        tools=tools,
        db=db,
        user_id=spec.user_id,
        session_id=spec.session_id,
        instructions=DEFAULT_SYSTEM_INSTRUCTIONS,
        enable_user_memories=spec.context.enable_user_memories,
        enable_session_summaries=spec.context.enable_session_summaries,
        add_history_to_context=spec.context.add_history_to_context,
        num_history_runs=spec.context.num_history_runs,
        markdown=True,
    )
