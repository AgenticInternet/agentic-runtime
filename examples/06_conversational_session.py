"""
Conversational Session Example
------------------------------
Interactive agent with session persistence for multi-turn conversations.
Good for: Chatbots, iterative development, exploratory analysis.

Requirements:
- DAYTONA_API_KEY in .env file (if using code execution)
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from core import build_agent
from core.policies import AgentSpec, CodeActPolicy, ContextPolicy


def main():
    # Uses useful model for conversations: minimax/minimax-m2.1
    spec = AgentSpec(
        model_id="minimax/minimax-m2.1",
        user_id="interactive_user",
        session_id="interactive_session",
        context=ContextPolicy(
            enable_user_memories=True,
            enable_session_summaries=True,
            add_history_to_context=True,
            num_history_runs=10,
        ),
        codeact=CodeActPolicy(enabled=True),
    )

    agent = build_agent(spec)

    print("Interactive Agent Session")
    print("=" * 40)
    print("Type 'quit' or 'exit' to end the session")
    print("=" * 40)

    while True:
        try:
            user_input = input("\nYou: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ["quit", "exit"]:
                print("Ending session. Goodbye!")
                break

            print("\nAgent:", end=" ")
            agent.print_response(user_input, stream=True)

        except KeyboardInterrupt:
            print("\n\nSession interrupted. Goodbye!")
            break


if __name__ == "__main__":
    main()
