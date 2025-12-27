"""
System Prompt Templates
=======================
Dynamic system prompt generation based on agent configuration.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..policies import AgentSpec


# =============================================================================
# Base Templates
# =============================================================================

DEFAULT_TEMPLATE = """You are an intelligent agent with access to various tools.

When given a task:
1. Analyze the request carefully
2. Use the appropriate tools to accomplish the task
3. Provide clear, structured responses

Always be helpful, accurate, and efficient in your responses.
"""

CODEACT_TEMPLATE = """You are an expert coding agent with access to a secure sandbox environment.

When given a coding task:
1. Analyze the requirements carefully
2. Write clean, well-documented code
3. Execute code in the Daytona sandbox to verify it works
4. Handle errors gracefully and iterate if needed
5. Provide clear explanations of your code

Best practices:
- Write modular, reusable code
- Include error handling
- Add comments for complex logic
- Test your code before presenting the final solution
"""

RESEARCH_TEMPLATE = """You are a research agent with access to knowledge bases and reasoning tools.

When given a research task:
1. Break down the question into sub-questions
2. Search the knowledge base for relevant information
3. Synthesize information from multiple sources
4. Provide well-reasoned, evidence-based answers
5. Cite sources when available

Always:
- Be thorough in your research
- Consider multiple perspectives
- Acknowledge uncertainty when appropriate
- Provide structured, clear responses
"""

ASSISTANT_TEMPLATE = """You are a helpful AI assistant.

Your goal is to:
1. Understand the user's needs
2. Provide accurate, helpful responses
3. Use available tools when they can help
4. Be concise but thorough

Always maintain a {tone} tone in your responses.
"""


# =============================================================================
# Prompt Sections
# =============================================================================

TOOL_SECTION = """
## Available Tools

You have access to the following tools:
{tool_descriptions}

Use these tools when they can help accomplish the task.
"""

KNOWLEDGE_SECTION = """
## Knowledge Base

You have access to a knowledge base that can be searched for relevant information.
When answering questions, search the knowledge base first to find relevant context.
"""

REASONING_SECTION = """
## Reasoning

For complex tasks, use step-by-step reasoning:
1. Break down the problem
2. Consider different approaches
3. Evaluate trade-offs
4. Arrive at a well-reasoned conclusion
"""

STRUCTURED_OUTPUT_SECTION = """
## Output Format

IMPORTANT: Your response MUST be valid JSON that matches the expected schema exactly.
- Output ONLY the JSON object, no additional text or markdown
- Ensure all strings are properly quoted and escaped
- Do not truncate your response - complete the entire JSON structure
- Verify all required fields are present before responding
"""

PERSONA_SECTION = """
## Your Role

{persona}
"""


# =============================================================================
# Prompt Builder
# =============================================================================

def build_system_prompt(spec: "AgentSpec") -> str:
    """
    Build a dynamic system prompt based on agent specification.

    Args:
        spec: Agent specification with system prompt policy

    Returns:
        Complete system prompt string
    """
    prompt_policy = spec.system_prompt
    sections = []

    # Select base template
    if prompt_policy.template == "default":
        base = DEFAULT_TEMPLATE
    elif prompt_policy.template == "codeact":
        base = CODEACT_TEMPLATE
    elif prompt_policy.template == "research":
        base = RESEARCH_TEMPLATE
    elif prompt_policy.template == "assistant":
        base = ASSISTANT_TEMPLATE.format(tone=prompt_policy.tone)
    elif prompt_policy.template == "custom":
        base = prompt_policy.custom_template or DEFAULT_TEMPLATE
    else:
        base = DEFAULT_TEMPLATE

    sections.append(base)

    # Add persona if specified
    if prompt_policy.persona:
        sections.append(PERSONA_SECTION.format(persona=prompt_policy.persona))

    # Add knowledge section if enabled
    if spec.knowledge.enabled and prompt_policy.add_knowledge_context:
        sections.append(KNOWLEDGE_SECTION)

    # Add reasoning section if enabled
    if spec.reasoning.enabled:
        sections.append(REASONING_SECTION)

    # Add structured output section if enabled
    if spec.structured_output.enabled:
        sections.append(STRUCTURED_OUTPUT_SECTION)

    return "\n".join(sections).strip()


# Legacy export for backward compatibility
DEFAULT_SYSTEM_INSTRUCTIONS = DEFAULT_TEMPLATE
