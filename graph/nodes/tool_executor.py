"""
Node 4: Tool Executor — Defense in Depth Layer 3
- Re-checks permission before executing EVERY tool call
- A tool call not in allowed_tools is rejected here even if the LLM requested it
- Appends ToolMessage results back into state.messages
"""

from langchain_core.messages import AIMessage, ToolMessage

from graph.secure_state import SecureAgentState
from graph.nodes.secure_agent import ALL_TOOLS
from security.rbac import is_tool_allowed


def tool_executor_node(state: SecureAgentState) -> SecureAgentState:
    if state.get("status") == "permission_denied":
        return state

    messages = list(state.get("messages", []))
    if not messages:
        return state

    last_msg = messages[-1]
    if not isinstance(last_msg, AIMessage) or not last_msg.tool_calls:
        return state

    role = state.get("user_role", "")
    tool_results: list[ToolMessage] = []
    tools_called = list(state.get("tools_called", []))

    for call in last_msg.tool_calls:
        tool_name = call["name"]
        tool_id = call["id"]
        tool_args = call.get("args", {})

        # Re-check permission at execution time
        if not is_tool_allowed(role, tool_name):
            result = ToolMessage(
                content=f"PERMISSION DENIED: role '{role}' may not call '{tool_name}'",
                tool_call_id=tool_id,
            )
            tool_results.append(result)
            continue

        tool_fn = ALL_TOOLS.get(tool_name)
        if tool_fn is None:
            result = ToolMessage(
                content=f"ERROR: tool '{tool_name}' not found",
                tool_call_id=tool_id,
            )
            tool_results.append(result)
            continue

        try:
            output = tool_fn.invoke(tool_args)
        except Exception as exc:
            output = f"ERROR: {exc}"

        tools_called.append(tool_name)
        tool_results.append(ToolMessage(content=str(output), tool_call_id=tool_id))

    return {
        **state,
        "messages": tool_results,
        "tools_called": tools_called,
    }
