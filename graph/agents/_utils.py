"""Shared utilities for agent nodes."""

from langchain_core.messages import AIMessage


def extract_tools_called(messages: list) -> list[str]:
    """Extract tool names that were actually called from a message list."""
    called = []
    for msg in messages:
        if isinstance(msg, AIMessage) and msg.tool_calls:
            for tc in msg.tool_calls:
                called.append(tc["name"])
    return called


def build_prompt_with_tools(base_prompt: str, allowed_tools: list[str]) -> str:
    """Inject allowed_tools list into agent prompt.
    If a task requires a tool NOT in this list, the agent must refuse —
    never provide the result as plain text instead.
    """
    tools_str = ", ".join(sorted(allowed_tools)) if allowed_tools else "(none)"
    return (
        f"{base_prompt}\n"
        f"Your available tools: {tools_str}\n"
        f"IMPORTANT: If the task requires a tool that is NOT in your available tools list, "
        f"respond with: 'Permission denied: [tool_name] is not available for your role.' "
        f"Do NOT provide the result as plain text instead of using the tool."
    )
