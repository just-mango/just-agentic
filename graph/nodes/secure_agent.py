"""
Node 3: Secure Agent
- Builds tool list filtered to allowed_tools only
- Injects clearance-filtered context into system prompt
- LLM never sees tools or data it is not cleared for
"""

import os
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.tools import BaseTool

from graph.secure_state import SecureAgentState
from llm.adapter import get_adapter
from security.classification import chunks_to_context_text
from security.rbac import Clearance

# All available tools indexed by name
from tools.shell import run_shell, git_status
from tools.file_ops import read_file, write_file, list_files, search_code, read_log
from tools.code_exec import execute_python, run_tests, get_env
from tools.web_search import web_search

ALL_TOOLS: dict[str, BaseTool] = {
    t.name: t for t in [
        run_shell, git_status,
        read_file, write_file, list_files, search_code, read_log,
        execute_python, run_tests, get_env,
        web_search,
    ]
}

_SYSTEM_PROMPT_TEMPLATE = """\
You are a secure AI assistant.

User role: {role}
Clearance level: {clearance_label}

You may ONLY call the tools provided to you in this session.
You may ONLY reference information present in the context below.
Do not speculate about data you cannot see.

{context_section}
"""


def _build_system_prompt(state: SecureAgentState) -> str:
    role = state.get("user_role", "viewer")
    clearance = state.get("clearance_level", 1)
    visible = state.get("visible_context", [])

    context_text = chunks_to_context_text(visible)
    context_section = (
        f"Available context:\n{context_text}" if context_text
        else "No additional context provided."
    )

    return _SYSTEM_PROMPT_TEMPLATE.format(
        role=role,
        clearance_label=Clearance.label(clearance),
        context_section=context_section,
    )


def secure_agent_node(state: SecureAgentState) -> SecureAgentState:
    if state.get("status") == "permission_denied":
        return state

    allowed = set(state.get("allowed_tools", []))
    active_tools = [t for name, t in ALL_TOOLS.items() if name in allowed]

    adapter = get_adapter()
    llm = adapter.chat_model()

    if active_tools:
        llm = llm.bind_tools(active_tools)

    system_prompt = _build_system_prompt(state)
    messages = [SystemMessage(content=system_prompt)] + list(state.get("messages", []))

    response = llm.invoke(messages)

    return {
        **state,
        "messages": [response],
        "iteration": state.get("iteration", 0) + 1,
    }
