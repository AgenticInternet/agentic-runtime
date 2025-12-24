from agno.tools.daytona import DaytonaTools

from ..policies import AgentSpec


def build_daytona_tools(spec: AgentSpec):
    return [
        DaytonaTools(
            auto_stop_interval=5,  # Auto-stop after 5 min of inactivity
            persistent=True,  # Keep sandbox alive across calls in session
        )
    ]
