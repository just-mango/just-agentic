"""
Tools registry — single source of truth.

Usage in agents:
    from tools import ALL_TOOLS, TOOL_MAP, set_role_context

    set_role_context(state["user_role"])
    tools = [t for t in ALL_TOOLS if t.name in state["allowed_tools"]]
"""

from langchain_core.tools import BaseTool

from tools.shell import run_shell, git_status
from tools.file_ops import read_file, write_file, list_files, search_code, read_log
from tools.code_exec import execute_python, run_tests, get_env
from tools.web_search import web_search
from tools._permission import set_role_context, get_role_context, permission_required


# ── Master tool list ───────────────────────────────────────────────────────

ALL_TOOLS: list[BaseTool] = [
    read_file,
    write_file,
    list_files,
    search_code,
    read_log,
    run_shell,
    git_status,
    execute_python,
    run_tests,
    get_env,
    web_search,
]

TOOL_MAP: dict[str, BaseTool] = {t.name: t for t in ALL_TOOLS}
