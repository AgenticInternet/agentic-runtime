"""
Idempotency Key Generation
===========================
Deterministic key generation for tool calls and agent runs.
"""

import hashlib
import json


def tool_idempotency_key(
    run_id: str,
    step_index: int,
    tool_name: str,
    tool_args: dict,
) -> str:
    """Generate a deterministic idempotency key for a tool call.

    Key = SHA-256(run_id + step_index + tool_name + sorted_args)[:32]
    """
    payload = json.dumps(
        {
            "run_id": run_id,
            "step": step_index,
            "tool": tool_name,
            "args": tool_args,
        },
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:32]


def run_idempotency_key(run_id: str, input_content: str) -> str:
    """Generate a deterministic idempotency key for an agent.run() call.

    Key = SHA-256(run_id + input_content)[:32]
    """
    payload = json.dumps(
        {
            "run_id": run_id,
            "input": input_content,
        },
        sort_keys=True,
        default=str,
    )
    return hashlib.sha256(payload.encode()).hexdigest()[:32]
