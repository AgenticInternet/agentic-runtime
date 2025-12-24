from agno.tools import tool


@tool
def healthcheck() -> dict:
    """Check if the agent runtime is healthy and operational."""
    return {"status": "ok"}


def build_local_tools():
    return [healthcheck]
