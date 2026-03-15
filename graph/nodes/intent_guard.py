"""
Intent Guard — deterministic pre-check before supervisor routing.
Blocks requests that require capabilities the role doesn't have.
No LLM involved — pure code logic.
"""

from langchain_core.messages import AIMessage, HumanMessage
from graph.state import AgentState

# Tasks that require write_file
_WRITE_PATTERNS = [
    "create", "write", "generate file", "make file", "save file",
    "save this to", "save to a file", "save as",
    "dockerfile", "docker-compose", "new file", "สร้างไฟล์", "เขียนไฟล์",
    "สร้าง dockerfile", "สร้าง docker",
]

# Tasks that require run_shell / execute
_EXEC_PATTERNS = [
    "run", "execute", "deploy", "start", "restart", "รัน", "execute command",
    "run command", "shell", "bash",
]


def _last_user_message(state: AgentState) -> str:
    for msg in reversed(state.get("messages", [])):
        if isinstance(msg, HumanMessage):
            return msg.content.lower()
    return state.get("user_goal", "").lower()


def intent_guard_node(state: AgentState) -> AgentState:
    """Block tasks that require tools the role doesn't have."""
    if state.get("status") == "permission_denied":
        return state

    allowed = set(state.get("allowed_tools") or [])
    text = _last_user_message(state)

    # Check write intent
    if "write_file" not in allowed:
        if any(p in text for p in _WRITE_PATTERNS):
            msg = AIMessage(
                content=(
                    f"Permission denied: your role '{state.get('user_role')}' "
                    f"cannot create or write files. "
                    f"Contact an admin or manager to perform this action."
                )
            )
            return {
                **state,
                "messages": [msg],
                "status": "permission_denied",
                "error": "write_file not in allowed_tools",
            }

    # Check execute intent
    if "run_shell" not in allowed:
        if any(p in text for p in _EXEC_PATTERNS):
            msg = AIMessage(
                content=(
                    f"Permission denied: your role '{state.get('user_role')}' "
                    f"cannot run shell commands. "
                    f"Contact an admin or manager to perform this action."
                )
            )
            return {
                **state,
                "messages": [msg],
                "status": "permission_denied",
                "error": "run_shell not in allowed_tools",
            }

    return state
